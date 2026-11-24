#!/usr/bin/env python3
"""Check one isolated WAV take. Times in the JSON report are seconds from the start."""
import argparse
import json
from pathlib import Path

import _bootstrap

_bootstrap.ensure("numpy", "scipy")
import numpy as np
from scipy.io import wavfile


def db(value):
    return 20 * np.log10(np.maximum(value, 1e-12))


def runs(mask):
    edges = np.flatnonzero(np.diff(mask.astype(int), prepend=0, append=0))
    return zip(edges[::2], edges[1::2])


def read_wav(path):
    rate, pcm = wavfile.read(path)
    if pcm.dtype.kind == "u":
        samples = (pcm.astype(float) - 128) / 128
    elif pcm.dtype.kind == "i":
        samples = pcm.astype(float) / float(-np.iinfo(pcm.dtype).min)
    else:
        samples = pcm.astype(float)
    if not len(samples) or rate < 4000 or not np.isfinite(samples).all():
        raise ValueError("Expected finite audio samples at 4 kHz or higher")
    return samples.reshape(len(samples), -1), rate


def word_times(path, duration):
    if path is None:
        return []
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(data, list) or not data:
        raise ValueError("Expected a nonempty list of word intervals")
    words = []
    for item in data:
        start, end = float(item["start"]), float(item["end"])
        if not (0 <= start < end <= duration) or (words and start < words[-1][1]):
            raise ValueError("Word times must be ordered, non-overlapping seconds within the clip")
        words.append((start, end))
    return words


def features(samples, rate, hop):
    # Center 30 ms windows on 10 ms cells. Use the loudest channel in each
    # window so a panned signal or opposite-polarity stereo cannot cancel.
    width = 3 * hop
    padded = np.pad(samples, ((hop, width), (0, 0)))
    level, periodic, noisy = [], [], []
    window = np.hanning(width)
    fft_size = 1 << (2 * width - 1).bit_length()
    for i in range(0, len(samples), hop):
        block = padded[i:i + width]
        power = np.mean(block ** 2, axis=0)
        frame = block[:, power.argmax()]
        level.append(float(db(np.sqrt(power.max()))))
        spectrum = np.abs(np.fft.rfft((frame - frame.mean()) * window, fft_size)) ** 2
        corr = np.fft.irfft(spectrum, fft_size)
        lags = corr[max(1, rate // 1100):min(width, rate // 65 + 1)]
        maxima = lags[1:-1][(lags[1:-1] > lags[:-2]) & (lags[1:-1] >= lags[2:])]
        pitch_score = maxima.max(initial=0) / max(corr[0], 1e-18)
        # Exclude a mains-frequency fundamental in otherwise quiet gaps.
        dominant_hz = spectrum.argmax() * rate / fft_size
        periodic.append(pitch_score > .48 and dominant_hz >= 80)
        flatness = np.exp(np.mean(np.log(spectrum + 1e-24))) / max(spectrum.mean(), 1e-24)
        zcr = np.mean(np.signbit(frame[1:]) != np.signbit(frame[:-1]))
        noisy.append(flatness > .10 or zcr > .12)
    return np.array(level), np.array(periodic), np.array(noisy)


def click_locations(samples, rate):
    # Compare each jump with nearby ordinary slopes in the same channel.
    # A loud sibilant has many large slopes, a discontinuity usually has one.
    silence = np.zeros((1, samples.shape[1]))
    jumps = np.abs(np.diff(samples, axis=0, prepend=silence, append=silence))
    width = max(1, round(.01 * rate))
    hits = []
    for ch in range(samples.shape[1]):
        for i in range(0, len(jumps), width):
            block = jumps[i:i + width, ch]
            if block.max() < .055:
                continue
            near = jumps[max(0, i - width):i + 2 * width, ch]
            threshold = max(.055, 7 * np.percentile(near, 95))
            hits.extend(np.minimum(i + np.flatnonzero(block > threshold), len(samples) - 1))
    times = sorted(set(hits))
    return [t for i, t in enumerate(times) if not i or t - times[i - 1] > .002 * rate]


def analyze(samples, rate, words=()):
    n = len(samples)
    hop = max(1, round(.010 * rate))
    dt = hop / rate
    duration = n / rate
    level, periodic, noisy = features(samples, rate, hop)
    center = (np.arange(len(level)) + .5) * dt
    # The high-energy reference is independent of the amount of silence.
    active = level[level > -60]
    reference = np.percentile(active, 90) if len(active) else -60
    voiced = periodic & (level >= max(-58, reference - 25))
    for a, b in runs(voiced):
        if (b - a) * dt < .025:
            voiced[a:b] = False
    flags = []

    def flag(kind, start, end, **detail):
        flags.append(dict(kind=kind, start=round(float(start), 6),
                          end=round(min(duration, float(end)), 6), **detail))

    peak = np.max(np.abs(samples), axis=1)
    hot = np.flatnonzero(peak > 10 ** (-1 / 20))
    if len(hot):
        index = int(peak.argmax())
        flag("raw_peak", index / rate, (index + 1) / rate,
             dbfs=round(float(db(peak[index])), 2), full_scale=bool(peak[index] >= 1 - 1 / 32768))
    for t in click_locations(samples, rate):
        flag("click", t / rate, (t + 1) / rate)

    speech = np.zeros(len(level), dtype=bool)
    if words:
        for start, end in words:
            speech |= (center + dt / 2 > start) & (center - dt / 2 < end)
        onset, offset = words[0][0], words[-1][1]
    elif voiced.any():
        speech[:] = voiced
        # Protect connected consonants at word edges. Stop at quiet valleys.
        audible = level > max(-55, reference - 34)
        for a, b in runs(voiced):
            for i in range(a - 1, max(-1, a - 13), -1):
                if not audible[i]:
                    break
                speech[i] = True
            for i in range(b, min(len(speech), b + 12)):
                if not audible[i]:
                    break
                speech[i] = True
        ix = np.flatnonzero(speech)
        onset, offset = ix[0] * dt, min(duration, (ix[-1] + 1) * dt)
    else:
        flag("no_speech_anchor", 0, duration)
        onset = offset = None

    cut = None
    if onset is not None:
        first = max(0, round((onset - .040) * rate))
        last = min(n, round((offset + .250) * rate))
        # Keep connected word decay. A quiet valley before another sound ends
        # the natural tail, even if that sound starts within the 250 ms allowance.
        for a, b in runs((center >= offset) & (level <= -60)):
            if (b - a) * dt >= .020:
                last = min(last, max(round(offset * rate), round((a * dt + .020) * rate)))
                break
        # An immediately attached bed of steady hiss/hum has no silent valley.
        # Preserve falling energy, but cut a sustained noise plateau after a word.
        tail = (center >= offset) & (center < last / rate) & ~periodic & (level > -60)
        for a, b in runs(tail):
            if (b - a) * dt >= .09 and np.ptp(level[a + 1:b - 1]) < 5:
                last = min(last, max(round(offset * rate), round(a * dt * rate)))
                break
        cut = [first, last]
        for name, mask in [("leading_noise", center < onset), ("trailing_noise", center > offset)]:
            for a, b in runs(mask & (level > -60)):
                left, right = a * dt, min(b * dt, duration)
                # Ignore frame-window bleed at a boundary and attached decay.
                if name == "leading_noise" and left >= onset - .040:
                    continue
                if name == "trailing_noise" and right <= last / rate + dt:
                    continue
                if right - left >= .025:
                    flag(name, left, right, peak_rms_dbfs=round(float(level[a:b].max()), 1))

        inside = (center >= onset) & (center < offset)
        gap = inside & ~speech
        for a, b in runs(gap & ~periodic & noisy & (level > -45)):
            if (b - a) * dt > .150:
                flag("unvoiced_gap", a * dt, b * dt)
        for a, b in runs(gap & (level > -60) & (~periodic | (level < reference - 25))):
            interior = level[a + 1:b - 1]
            if len(interior) * dt >= .080:
                flag("gap_noise_floor", (a + 1) * dt, (b - 1) * dt,
                     floor_dbfs=round(float(np.percentile(interior, 20)), 1))
        # Several quiet rough syllables can precede the first strong vowel.
        # A long low-level onset needs a listener before anyone cuts it.
        strong = np.flatnonzero(inside & voiced & (level >= reference - 9))
        if len(strong):
            weak = inside & (center < center[strong[0]]) & (level > -60)
            if np.count_nonzero(weak) * dt > .35:
                flag("weak_word_onset", onset, strong[0] * dt)
                if not words:
                    cut[0] = 0  # Require word times before discarding a possibly whispered opening.
    return dict(duration_s=duration, sample_rate=rate, channels=samples.shape[1],
                peak_dbfs=round(float(db(peak.max())), 2),
                boundary_source="word_times" if words else "estimated",
                speech_seconds=None if onset is None else [round(float(onset), 6), round(float(offset), 6)],
                keep_samples=cut, flags=flags)


def fix_copy(samples, rate, cut, path, pcm16=False):
    edited = samples[cut[0]:cut[1]].copy()
    fade = min(round(.008 * rate), len(edited) // 2)
    if fade:
        gain = np.linspace(0, 1, fade)[:, None]
        edited[:fade] *= gain
        edited[-fade:] *= gain[::-1]
    # Float WAV preserves both over-range samples and low-level noise for recheck.
    if pcm16:
        # Catalog references use PCM WAVs. Only clean, in-range takes use this path.
        wavfile.write(path, rate, np.rint(edited * 32768).clip(-32768, 32767).astype(np.int16))
    else:
        wavfile.write(path, rate, edited.astype(np.float32))
    return edited


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("wav", type=Path)
    ap.add_argument("--words", type=Path, help="JSON list of {start, end} in seconds")
    ap.add_argument("--fix", type=Path, metavar="OUT.wav", help="write a separate edge-trimmed, faded WAV")
    ap.add_argument("--report", type=Path, help="also save the JSON report here")
    args = ap.parse_args()
    try:
        paths = [p.resolve() for p in (args.wav, args.words, args.fix, args.report) if p is not None]
        if len(paths) != len(set(paths)):
            raise ValueError("Inputs and outputs must have distinct paths")
        samples, rate = read_wav(args.wav)
        words = word_times(args.words, len(samples) / rate)
        result = analyze(samples, rate, words)
        result["input"] = str(args.wav)
        remaining = result["flags"]
        cut = result["keep_samples"]
        if args.fix and cut:
            edited = fix_copy(samples, rate, cut, args.fix)
            shifted = [(a - cut[0] / rate, b - cut[0] / rate) for a, b in words]
            check = analyze(edited, rate, shifted)
            result["output"] = str(args.fix)
            result["output_check"] = check
            remaining = check["flags"]
        result["regenerate_if_confirmed"] = [f for f in remaining
                                             if f["kind"] not in ("leading_noise", "trailing_noise")]
        code = int(bool(result["flags"] or remaining))
    except (ValueError, OSError, KeyError, TypeError) as error:
        result, code = {"error": str(error)}, 2
    message = json.dumps(result, indent=2)
    print(message)
    if args.report:
        if args.report.resolve() in [p.resolve() for p in (args.wav, args.words, args.fix) if p]:
            return 2
        args.report.write_text(message + "\n", encoding="utf-8")
    return code


if __name__ == "__main__":
    raise SystemExit(main())
