"""Exercise the offline dialogue check with synthetic sounds and timestamped words."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SCRIPT = Path(__file__).resolve().parents[1] / "skills/dula-voice/scripts/line_hygiene.py"
RATE = 16000


class LineHygiene(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.folder = Path(self.tmp.name)
        self.wav = self.folder / "take.wav"
        self.rng = np.random.default_rng(42)

    def tone(self, duration, freq=180, gain=.18):
        time = np.arange(round(duration * RATE)) / RATE
        envelope = np.clip(np.minimum(time, duration - time) / .01, 0, 1)
        return gain * envelope * np.sin(2 * np.pi * freq * time)

    def run_check(self, samples, *args):
        wavfile.write(self.wav, RATE, samples.astype(np.float32))
        result = subprocess.run([sys.executable, str(SCRIPT), str(self.wav), *map(str, args)],
                                capture_output=True, text=True, cwd=self.folder)
        return result.returncode, json.loads(result.stdout)

    def test_separate_rasp_and_tail_are_removed_but_words_stay_intact(self):
        word = self.tone(.40)
        noise = self.rng.normal(0, .008, RATE // 5)
        gap = np.zeros(RATE // 10)
        samples = np.concatenate([noise, gap, word, gap, noise])
        edited = self.folder / "edited.wav"
        code, report = self.run_check(samples, "--fix", edited)
        self.assertEqual(code, 1)
        self.assertEqual({f["kind"] for f in report["flags"]}, {"leading_noise", "trailing_noise"})
        self.assertEqual(report["output_check"]["flags"], [])
        rate, actual = wavfile.read(edited)
        left, right = report["keep_samples"]
        self.assertEqual(rate, RATE)
        self.assertEqual(len(actual), right - left)
        self.assertAlmostEqual(left / rate, .26, delta=.025)
        np.testing.assert_allclose(actual[round(.32 * rate) - left:round(.68 * rate) - left],
                                   samples[round(.32 * rate):round(.68 * rate)], atol=1e-7)

    def test_word_fricative_is_protected_and_gap_hiss_and_hum_are_flagged(self):
        fricative = self.rng.normal(0, .014, RATE // 5)
        quiet = np.zeros(RATE // 10)
        word = np.r_[fricative, self.tone(.2)]
        hiss = self.rng.normal(0, .012, RATE // 4)
        hum = self.tone(.24, freq=60, gain=.0025)
        samples = np.r_[word, quiet, hiss, quiet, self.tone(.2), quiet, hum, quiet, self.tone(.2)]
        timings = self.folder / "words.json"
        timings.write_text(json.dumps([{"start": 0, "end": .4}, {"start": .85, "end": 1.05},
                                       {"start": 1.49, "end": 1.69}]))
        code, report = self.run_check(samples, "--words", timings, "--fix", self.folder / "edit.wav")
        self.assertEqual(code, 1)
        flags = report["regenerate_if_confirmed"]
        self.assertTrue(any(f["kind"] == "unvoiced_gap" and .48 < f["start"] < .55 for f in flags))
        self.assertTrue(any(f["kind"] == "gap_noise_floor" and f["start"] > 1.14 for f in flags))
        self.assertFalse(any(f["start"] < .4 for f in flags))

    def test_raw_peak_click_and_opposite_polarity_stereo(self):
        line = self.tone(.5)
        stereo = np.column_stack((line, -line))
        self.assertEqual(self.run_check(stereo)[0], 0)
        stereo[RATE // 4, 1] = 1.0
        code, report = self.run_check(stereo)
        self.assertEqual(code, 1)
        self.assertEqual({f["kind"] for f in report["flags"]}, {"click", "raw_peak"})

    def test_quiet_opening_words_are_flagged_and_preserved(self):
        samples = np.r_[np.zeros(RATE // 10), self.tone(.55, gain=.012), self.tone(.5)]
        code, report = self.run_check(samples, "--fix", self.folder / "edit.wav")
        self.assertEqual(code, 1)
        self.assertIn("weak_word_onset", [f["kind"] for f in report["flags"]])
        self.assertEqual(report["keep_samples"][0], 0)

    def test_an_unanchored_clip_is_never_automatically_cut(self):
        edited = self.folder / "edit.wav"
        code, report = self.run_check(np.zeros(RATE), "--fix", edited)
        self.assertEqual(code, 1)
        self.assertIn("no_speech_anchor", [f["kind"] for f in report["regenerate_if_confirmed"]])
        self.assertFalse(edited.exists())
