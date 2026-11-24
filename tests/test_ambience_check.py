"""Measure continuity on synthetic stereo room tone through the public CLI."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
from scipy.io import wavfile

SCRIPT = Path(__file__).resolve().parents[1] / "skills/dula-voice/scripts/ambience_check.py"
RATE = 8000


class AmbienceCheck(unittest.TestCase):
    def check(self, envelope, *args):
        time = np.arange(len(envelope)) / RATE
        wave = .02 * envelope * np.sin(2 * np.pi * 200 * time)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "stem.wav"
            report = Path(folder) / "check.json"
            wavfile.write(path, RATE, np.column_stack((wave, -wave)).astype(np.float32))
            result = subprocess.run([sys.executable, str(SCRIPT), str(path), "--report",
                                     str(report), *args], capture_output=True, text=True)
            return result.returncode, json.loads(report.read_text())

    def test_short_dip_between_louder_windows(self):
        gain = np.ones(3 * RATE)
        gain[RATE:RATE + RATE // 2] = .25
        code, report = self.check(gain)
        self.assertEqual(code, 1)
        self.assertAlmostEqual(report["max_drop_db"], 12.041, places=2)
        self.assertTrue(any(row["kind"] == "drop" for row in report["flags"]))

    def test_motivated_cut_is_local_and_silence_still_flags(self):
        gain = np.ones(3 * RATE)
        gain[RATE:] = .2
        self.assertEqual(self.check(gain, "--cut", "1")[0], 0)
        gain[2 * RATE:] = 0
        code, report = self.check(gain, "--cut", "1")
        self.assertEqual(code, 1)
        self.assertEqual({row["kind"] for row in report["flags"]}, {"silence", "drop"})

    def test_gentle_fade_and_quiet_short_stem(self):
        self.assertEqual(self.check(10 ** (np.linspace(0, -13, 3 * RATE) / 20))[0], 0)
        self.assertEqual(self.check(np.full(RATE // 10, .03))[0], 0)

    def test_full_mix_checks_each_release_and_ignores_unrelated_drops(self):
        gain = np.ones(4 * RATE)
        gain[RATE:2 * RATE] = .01
        gain[3 * RATE:] = .1
        code, report = self.check(gain, "--line-end", "1", "--line-end", "3")
        self.assertEqual(code, 1)
        self.assertEqual([flag["line_end_s"] for flag in report["flags"]], [1])
        self.assertEqual([row["max_drop_db"] for row in report["lines"]], [40, 20])
        self.assertEqual(self.check(gain, "--line-end", "3")[0], 0)

    def test_full_mix_cut_only_exempts_the_change_across_it(self):
        gain = np.ones(3 * RATE)
        gain[RATE:] = .01
        gain[2 * RATE:] = .0001
        code, report = self.check(gain, "--line-end", ".9", "--line-end", "1",
                                  "--line-end", "2", "--cut", "1")
        self.assertEqual(code, 1)
        self.assertEqual([flag["line_end_s"] for flag in report["flags"]], [2])
        self.assertEqual(report["lines"][1]["status"], "at_cut")
