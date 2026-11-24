"""Check the reference comparison using controlled changes to a full scene."""
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
import scene_review

TOLERANCES = dict(loudness_range_lu=3, bed_dialogue_db=3, spectral_tilt_db=3)


class SceneReview(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.reference = self.root / "accepted"
        self.candidate = self.root / "candidate"
        self.rate = 16000
        self.reference.mkdir()
        self.candidate.mkdir()

    def tracks(self, folder, bed_db=-18, high_gain=1, dynamic=True, duration=18):
        time = np.arange(self.rate * duration) / self.rate
        levels = np.where(time < duration / 2, .25, 1) if dynamic else 1
        tone = .06 * np.sin(2 * np.pi * 400 * time)
        bed = tone * 10 ** (bed_db / 20)
        dialogue = tone * (time % 2 < 1.5)
        # A narrow high band on its own bus changes spectral balance.
        detail = .04 * high_gain * np.sin(2 * np.pi * 3000 * time)
        for name, mono in (("bed", bed), ("dialogue", dialogue), ("mix", bed + dialogue + detail)):
            stereo = np.column_stack((mono, -mono)) * np.asarray(levels).reshape(-1, 1)
            wavfile.write(folder / f"{name}.wav", self.rate, stereo.astype(np.float32))

    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / "scene_review.py"), str(self.candidate),
                               str(self.reference), *map(str, args)], capture_output=True, text=True)

    def test_identical_scene_passes_and_measures_speech_windows_in_stereo(self):
        self.tracks(self.reference)
        self.tracks(self.candidate)
        path = self.root / "report.json"
        result = self.run_cli("--report", path)
        self.assertEqual(result.returncode, 0, result.stderr)
        data = json.loads(path.read_text())
        self.assertTrue(data["passed"])
        self.assertEqual(data["candidate"]["active_dialogue_s"], 13.5)
        self.assertAlmostEqual(data["candidate"]["bed_dialogue_db"], -18, places=3)
        self.assertGreater(data["candidate"]["loudness_range_lu"], 6)
        self.assertTrue(all(metric["delta"] == 0 for metric in data["checks"].values()))

    def test_each_deliberate_regression_is_flagged(self):
        self.tracks(self.reference)
        for metric, change in (("loudness_range_lu", dict(dynamic=False)),
                               ("bed_dialogue_db", dict(bed_db=-29)),
                               ("spectral_tilt_db", dict(high_gain=.15))):
            with self.subTest(metric=metric):
                self.tracks(self.candidate, **change)
                data = scene_review.compare(self.candidate, self.reference, TOLERANCES)
                self.assertFalse(data["passed"])
                self.assertFalse(data["checks"][metric]["passed"])
                self.assertLess(data["checks"][metric]["delta"], -3)
        self.assertEqual(self.run_cli().returncode, 1)
        self.assertEqual(self.run_cli("--tilt-db", 20).returncode, 0)

    def test_silent_and_short_inputs_cannot_pass_by_matching(self):
        self.tracks(self.reference, duration=2)
        self.tracks(self.candidate, duration=2)
        silence = np.zeros((2 * self.rate, 2), np.float32)
        wavfile.write(self.candidate / "dialogue.wav", self.rate, silence)
        data = scene_review.compare(self.candidate, self.reference, TOLERANCES)
        self.assertFalse(data["passed"])
        self.assertIsNone(data["candidate"]["loudness_range_lu"])
        self.assertIsNone(data["candidate"]["bed_dialogue_db"])
        self.assertEqual(data["candidate"]["active_dialogue_s"], 0)
        self.tracks(self.candidate, duration=2)
        wavfile.write(self.candidate / "bed.wav", self.rate, silence)
        data = scene_review.compare(self.candidate, self.reference, TOLERANCES)
        self.assertIsNone(data["candidate"]["bed_dialogue_db"])
        self.assertIsNone(scene_review.spectral_tilt(silence, self.rate, 8000))

    def test_invalid_stem_alignment_and_report_cannot_damage_input(self):
        self.tracks(self.reference, duration=3)
        self.tracks(self.candidate, duration=3)
        wavfile.write(self.candidate / "bed.wav", self.rate, np.zeros(self.rate, np.float32))
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("length", result.stderr)
        path = self.reference / "mix.wav"
        before = path.read_bytes()
        result = self.run_cli("--report", path)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(before, path.read_bytes())


if __name__ == "__main__":
    unittest.main()
