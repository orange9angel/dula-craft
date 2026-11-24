"""Find abrupt level drops on an isolated ambience WAV."""
import argparse
import json
import math
from pathlib import Path

from line_hygiene import read_wav
import numpy as np


def scan(samples, rate, cuts=()):
    length = len(samples)
    bounds = [0]
    for cut in sorted(cuts):
        if not math.isfinite(cut):
            raise ValueError("Cut times must be finite")
        index = round(cut * rate)
        if not bounds[-1] < index < length:
            raise ValueError("Cuts must identify distinct samples inside the stem")
        bounds.append(index)
    bounds.append(length)
    width, hop = round(.2 * rate), round(.05 * rate)
    flags = []
    largest_drop = largest_rise = 0.0
    for left, right in zip(bounds, bounds[1:]):
        window = min(width, right - left)
        starts = np.arange(left, right - window + 1, hop)
        if starts[-1] != right - window:
            starts = np.append(starts, right - window)
        power = np.mean(samples[left:right] ** 2, axis=1, dtype=np.float64)
        # Sum only local windows to retain small signals after loud passages.
        means = np.array([power[i:i + window].mean() for i in starts - left])
        levels = 10 * np.log10(np.maximum(means, 1e-24))
        silent = means == 0
        for i in np.flatnonzero(silent & ~np.r_[False, silent[:-1]]):
            flags.append(dict(kind="silence", start=starts[i] / rate,
                              end=(starts[i] + window) / rate))
        for i in range(1, len(starts)):
            first = starts.searchsorted(starts[i] - rate)
            previous = levels[first:i]
            peak = first + int(previous.argmax())
            drop = levels[peak] - levels[i]
            largest_drop = max(largest_drop, drop)
            largest_rise = max(largest_rise, levels[i] - previous.min())
            if drop > 6 + 1e-9:
                flags.append(dict(kind="drop", start=(starts[peak] + window / 2) / rate,
                                  end=(starts[i] + window / 2) / rate, db=round(drop, 3)))
    return dict(window_s=.2, hop_s=.05, max_interval_s=1, threshold_db=6,
                cuts_s=sorted(cuts), max_drop_db=round(largest_drop, 3),
                max_rise_db=round(largest_rise, 3), flags=flags)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wav", type=Path)
    parser.add_argument("--cut", type=float, action="append", default=[],
                        help="Time in seconds of a cut that motivates a level change (repeatable)")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    try:
        if args.report and args.wav.resolve() == args.report.resolve():
            raise ValueError("The report path must differ from the input WAV")
        samples, rate = read_wav(args.wav)
        result = scan(samples, rate, args.cut)
        message = json.dumps(result, indent=2)
        if args.report:
            args.report.write_text(message + "\n", encoding="utf-8")
        print(message)
        return int(bool(result["flags"]))
    except (OSError, ValueError) as error:
        parser.exit(2, f"{error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
