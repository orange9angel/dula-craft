"""Compare a complete scene's mix and aligned stems to an accepted reference."""
import argparse
import json
import math
import subprocess
from pathlib import Path

from line_hygiene import read_wav
import numpy as np
from scipy import signal


def loudness_range(path, seconds):
    if seconds < 3:
        return None  # A short-term loudness window requires three seconds.
    result = subprocess.run(
        ["ffmpeg", "-nostdin", "-hide_banner", "-nostats", "-i", str(path), "-af",
         "loudnorm=print_format=json", "-f", "null", "-"],
        capture_output=True, encoding="utf-8", errors="replace", check=True)
    # Some FFmpeg builds write a muxing summary after the filter's JSON object.
    stats, _ = json.JSONDecoder().raw_decode(result.stderr[result.stderr.rindex("{"):])
    if not math.isfinite(float(stats["input_i"])):
        return None
    return float(stats["input_lra"])


def bed_dialogue_ratio(bed, dialogue, rate):
    # Sum channel powers before gating, so opposite-polarity stereo stays audible.
    width = round(.25 * rate)
    starts = np.arange(0, len(dialogue), width)
    counts = np.diff(np.append(starts, len(dialogue)))
    speech_energy = np.add.reduceat(np.mean(dialogue ** 2, axis=1), starts)
    power = speech_energy / counts
    active = power >= max(1e-7, power.max() * .001)
    if not active.any():
        return None, 0.0
    bed_energy = np.add.reduceat(np.mean(bed ** 2, axis=1), starts)
    ratio = bed_energy[active].sum() / speech_energy[active].sum()
    return (10 * math.log10(ratio) if ratio > 0 else None), counts[active].sum() / rate


def spectral_tilt(samples, rate, upper_hz):
    # Integrate channel power in fixed bands, in bounded blocks for long scenes.
    bands = np.zeros(2)
    width = round(.05 * rate)
    for start in range(0, len(samples), 128 * width):
        block = samples[start:start + 128 * width]
        freq, power = signal.welch(block, fs=rate, axis=0, nperseg=min(width, len(block)),
                                   noverlap=0, nfft=width, scaling="density")
        for i, (low, high) in enumerate(((125, 1000), (2000, upper_hz))):
            bands[i] += power[(freq >= low) & (freq < high)].sum() * len(block)
    if upper_hz <= 2000 or not bands.any():
        return None
    # Bound a band below the numerical floor relative to the strongest band.
    low, high = np.maximum(bands, bands.max() * 1e-12)
    return 10 * math.log10(high / low)


def measure(folder, mix, rate, upper_hz):
    stems = []
    for name in ("bed", "dialogue"):
        samples, stem_rate = read_wav(folder / f"{name}.wav")
        if rate != stem_rate or len(samples) != len(mix):
            raise ValueError(f"{folder / name} must share the mix sample rate, start and length")
        stems.append(samples)
    seconds = len(mix) / rate
    ratio, active_seconds = bed_dialogue_ratio(*stems, rate)
    return dict(duration_s=seconds, active_dialogue_s=active_seconds,
                loudness_range_lu=loudness_range(folder / "mix.wav", seconds),
                bed_dialogue_db=ratio, spectral_tilt_db=spectral_tilt(mix, rate, upper_hz))


def compare(candidate, reference, tolerances):
    mixes = [read_wav(folder / "mix.wav") for folder in (candidate, reference)]
    upper_hz = min(8000, *(rate / 2 for _, rate in mixes))
    current, accepted = [measure(folder, samples, rate, upper_hz)
                         for folder, (samples, rate) in zip((candidate, reference), mixes)]
    checks = {}
    for key, tolerance in tolerances.items():
        values = current[key], accepted[key]
        delta = None if None in values else values[0] - values[1]
        checks[key] = dict(delta=delta, tolerance=tolerance,
                           passed=delta is not None and abs(delta) <= tolerance)
    return dict(passed=all(row["passed"] for row in checks.values()), high_band_end_hz=upper_hz,
                candidate_path=str(candidate), reference_path=str(reference),
                candidate=current, reference=accepted, checks=checks)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("candidate", type=Path, help="Directory with mix.wav, bed.wav and dialogue.wav")
    parser.add_argument("reference", type=Path, help="Equivalent files for the accepted reference scene")
    parser.add_argument("--range-lu", type=float, default=3, help="Maximum absolute loudness range difference")
    parser.add_argument("--ratio-db", type=float, default=3, help="Maximum absolute bed/dialogue difference")
    parser.add_argument("--tilt-db", type=float, default=3, help="Maximum absolute spectral tilt difference")
    parser.add_argument("--report", type=Path, help="Also save the JSON result here")
    args = parser.parse_args()
    try:
        tolerances = dict(loudness_range_lu=args.range_lu, bed_dialogue_db=args.ratio_db,
                          spectral_tilt_db=args.tilt_db)
        if not all(math.isfinite(t) and t >= 0 for t in tolerances.values()):
            raise ValueError("Tolerances must be finite and nonnegative")
        if args.report and args.report.resolve() in {
            (folder / name).resolve() for folder in (args.candidate, args.reference)
            for name in ("mix.wav", "bed.wav", "dialogue.wav")
        }:
            raise ValueError("Report path matches an input WAV")
        result = compare(args.candidate, args.reference, tolerances)
        message = json.dumps(result, indent=2, allow_nan=False)
        if args.report:
            args.report.write_text(message + "\n", encoding="utf-8")
        print(message)
        return int(not result["passed"])
    except (OSError, ValueError, subprocess.CalledProcessError) as error:
        parser.exit(2, f"Scene review: {error}\n")


if __name__ == "__main__":
    raise SystemExit(main())
