"""Exercise sound placement and room acoustics with generated stereo test signals."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SCRIPTS = Path(__file__).resolve().parents[1] / "skills/dula-voice/scripts"
sys.path.insert(0, str(SCRIPTS))
import scene_mix


class SceneMix(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.folder = Path(tmp.name)
        self.rate = 16000

    def write(self, name, samples, rate=None):
        wavfile.write(self.folder / name, rate or self.rate, np.asarray(samples, np.float32))
        return name

    def run_cli(self, plan, output):
        path = self.folder / "plan.json"
        path.write_text(json.dumps(plan), encoding="utf-8")
        return subprocess.run([sys.executable, str(SCRIPTS / "scene_mix.py"), str(path),
                               str(self.folder / output)], capture_output=True, text=True)

    def test_j_and_l_cuts_layer_clock_and_stereo_delivery(self):
        left = self.write("left.wav", [[.12, 0]] * 95)
        extra = self.write("extra.wav", [[.08, 0]] * 100)
        right = self.write("right.wav", [[0, .2]] * 96)
        plan = dict(rate=self.rate, duration=3, beds=[
            dict(cut=0, layers=[dict(file=left), dict(file=extra)]),
            dict(cut=1, prelap=.5, layers=[dict(file=right)]),
            dict(cut=2, tail=.5, layers=[dict(file=left), dict(file=extra)])])
        result = self.run_cli(plan, "take")
        self.assertEqual(result.returncode, 0, result.stderr)
        rate, mix = wavfile.read(self.folder / "take/mix.wav")
        self.assertEqual(mix.shape, (3 * rate, 2))
        mid = .2 / np.sqrt(2)
        np.testing.assert_allclose(mix[[0, int(.75*rate), rate, 2*rate, int(2.25*rate), -1]],
                                   [[.2, 0], [mid, mid], [0, .2], [0, .2], [mid, mid], [.2, 0]], atol=1e-6)
        np.testing.assert_allclose(np.linalg.norm(mix, axis=1), .2, atol=1e-6)
        stems = [wavfile.read(self.folder / f"take/{role}.wav")[1]
                 for role in ("bed", "dialogue", "effects", "music")]
        np.testing.assert_allclose(sum(stems), mix)
        self.assertNotEqual(self.run_cli(plan, "take").returncode, 0)

    def test_distance_changes_bass_air_and_direct_to_room_ratio(self):
        rate = 48000
        freq = [80, 1000, 12000]
        t = np.arange(rate // 2) / rate
        clip = self.write("tone.wav", sum(.03 * np.sin(2*np.pi*f*t) for f in freq), rate)
        colors, tails = [], []
        for view in ("close", "medium", "wide"):
            plan = dict(duration=1, rooms={"hall": .3},
                        dialogue=[dict(at=0, file=clip, location="hall", perspective=view)])
            _, buses = scene_mix.render(plan, self.folder)
            voice = buses["dialogue"][:, 0]
            spectrum = np.abs(np.fft.rfft(voice[rate//4:rate//2]))
            bass, middle, air = spectrum[np.array(freq) // 4]
            colors.append([bass / middle, air / middle])
            tails.append(np.linalg.norm(voice[rate//2:]) / np.linalg.norm(voice[:rate//2]))
        self.assertTrue(np.all(np.diff(colors, axis=0) < 0), colors)
        self.assertTrue(np.all(np.diff(tails) > 0), tails)

    def test_cast_and_foley_share_location_tail_across_cuts(self):
        clip = self.write("tap.wav", np.r_[.4, np.zeros(99)], rate=8000)
        row = dict(at=.1, file=clip, location="room", perspective="close")
        plan = dict(rate=self.rate, duration=1, rooms={"room": .24, "yard": .09},
                    dialogue=[row], effects=[dict(row, at=.5)])
        _, buses = scene_mix.render(plan, self.folder)
        first = self.rate // 10
        count = self.rate // 3
        tail = buses["dialogue"][first:first+count]
        np.testing.assert_allclose(tail, buses["effects"][self.rate//2:self.rate//2+count])
        self.assertGreater(np.linalg.norm(tail[300:]), 0)
        self.assertFalse(np.array_equal(tail[:, 0], tail[:, 1]))
        plan["effects"][0]["location"] = "yard"
        _, other = scene_mix.render(plan, self.folder)
        self.assertFalse(np.allclose(tail, other["effects"][self.rate//2:self.rate//2+count]))

    def test_music_handles_touching_lines_and_source_offset(self):
        line = self.write("word.wav", np.full(self.rate // 4, .1))
        track = self.write("phrase.wav", np.r_[np.zeros(self.rate), np.full(self.rate, .2)])
        cue = {"file": track, "in": .5, "out": .8, "prelap": .25, "tail": .2, "source_start": 1}
        plan = dict(rate=self.rate, duration=1.5, rooms={"hall": .2},
                    dialogue=[dict(at=0, file=line, location="hall"), dict(at=1, file=line, location="hall")],
                    music=[cue])
        _, buses = scene_mix.render(plan, self.folder)
        samples = buses["music"][:, 0]
        np.testing.assert_allclose(samples[[0, 4000, 6000, 8000, 12800, 14400, 16000, -1]],
                                   [0, 0, .1, .2, .2, .1, 0, 0], atol=.0001)
        for field, value in (("prelap", .26), ("tail", .21)):
            with self.subTest(field=field):
                plan["music"] = [dict(cue, **{field: value})]
                with self.assertRaisesRegex(ValueError, "overlaps line"):
                    scene_mix.render(plan, self.folder)
        result = self.run_cli(plan, "bad-take")
        self.assertIn("overlaps line", result.stderr)
        self.assertFalse((self.folder / "bad-take").exists())
        plan["music"][0]["kind"] = "pad"
        with self.assertRaisesRegex(ValueError, "pad_reason"):
            scene_mix.render(plan, self.folder)
        plan["music"][0]["pad_reason"] = "A quiet held note carries the entrance."
        _, buses = scene_mix.render(plan, self.folder)
        self.assertGreater(buses["music"][self.rate, 0], 0)

    def test_refuses_overlapping_bed_transitions_and_short_score_source(self):
        beds = [dict(cut=0, layers=[]), dict(cut=.3, tail=.2, layers=[]),
                dict(cut=.6, prelap=.2, layers=[])]
        with self.assertRaisesRegex(ValueError, "non-overlapping"):
            scene_mix.render(dict(duration=1, beds=beds), self.folder)
        short = self.write("short.wav", np.zeros(400))
        with self.assertRaisesRegex(ValueError, "short"):
            scene_mix.render(dict(duration=1, music=[{"file": short, "in": .1, "out": .8}]), self.folder)


if __name__ == "__main__":
    unittest.main()
