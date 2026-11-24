"""Render a stereo sound script with continuous beds, room returns and spotted score."""
import argparse
import json
import math
import tempfile
import zlib
from pathlib import Path

from line_hygiene import read_wav
import numpy as np
from scipy import signal
from scipy.io import wavfile


def frames(seconds, rate):
    if not math.isfinite(seconds) or seconds < 0:
        raise ValueError(f"Expected nonnegative finite seconds, got {seconds}")
    return round(seconds * rate)


def source(row, folder, rate):
    samples, original_rate = read_wav(folder / row["file"])
    if samples.shape[1] > 2:
        raise ValueError(f"Expected mono or stereo: {row['file']}")
    if original_rate != rate:
        common = math.gcd(original_rate, rate)
        samples = signal.resample_poly(samples, rate // common, original_rate // common, axis=0)
    gain = 10 ** (row.get("gain_db", 0) / 20)
    if not math.isfinite(gain):
        raise ValueError("Expected finite gain_db")
    return (samples * gain).astype(np.float32)


def mix_beds(bus, beds, folder, rate):
    # Each incoming cut owns the overlap on both sides of the picture edit.
    joins = []
    for i, bed in enumerate(beds):
        cut = frames(bed["cut"], rate)
        left = cut - frames(bed.get("prelap", 0), rate)
        right = cut + frames(bed.get("tail", 0), rate)
        if i == 0 and (left, right) != (0, 0):
            raise ValueError("The first bed starts at zero without transition handles")
        if left < 0 or right > len(bus) or cut >= len(bus):
            raise ValueError("Bed transition outside the timeline")
        if i and (cut <= frames(beds[i - 1]["cut"], rate) or left < joins[-1][1]):
            raise ValueError("Bed cuts must be ordered with non-overlapping transitions")
        joins.append((left, right))
    joins.append((len(bus), len(bus)))

    for i, bed in enumerate(beds):
        start, fade_in_end = joins[i]
        fade_out_start, end = joins[i + 1]
        envelope = np.ones(end - start, dtype=np.float32)
        for left, right, incoming in ((start, fade_in_end, True), (fade_out_start, end, False)):
            if right > left:
                angle = np.linspace(0, np.pi / 2, right - left, endpoint=False)
                envelope[left-start:right-start] = np.sin(angle) if incoming else np.cos(angle)
        for layer in bed["layers"]:
            loop = source(layer, folder, rate)
            for pos in range(start, end, len(loop)):
                count = min(len(loop), end - pos)
                bus[pos:pos+count] += loop[:count] * envelope[pos-start:pos-start+count, None]


# Low cut, high cut, direct gain (dB), room send relative to direct (dB).
PERSPECTIVE = {"close": (65, 16000, 0, -22), "medium": (100, 9000, -2, -16),
               "wide": (180, 4500, -5, -10)}


def room_impulse(name, decay, rate):
    length = frames(decay, rate)
    if not 0.025 <= decay <= 3:
        raise ValueError("Room decay must be between 0.025 and 3 seconds")
    rng = np.random.default_rng(zlib.crc32(name.encode("utf-8")))
    ir = rng.standard_normal((length, 2)) * np.exp(-np.log(1000) * np.arange(length)[:, None] / length)
    ir[:round(.012 * rate)] = 0
    return (ir / np.linalg.norm(ir, axis=0)).astype(np.float32)


def place_in_room(bus, row, rooms, folder, rate):
    start = frames(row["at"], rate)
    dry = source(row, folder, rate)
    end = start + len(dry)
    if end > len(bus):
        raise ValueError(f"Clip extends past the timeline: {row['file']}")
    low, high, direct_db, send_db = PERSPECTIVE[row.get("perspective", "medium")]
    eq = signal.butter(2, [low, min(high, rate * .49)], btype="bandpass", fs=rate, output="sos")
    dry = signal.sosfilt(eq, dry, axis=0).astype(np.float32) * 10 ** (direct_db / 20)
    bus[start:end] += dry
    # The same location impulse is used for every send, including Foley.
    ir = rooms[row["location"]]
    stereo = np.broadcast_to(dry, (len(dry), 2))
    wet = signal.oaconvolve(stereo, ir, axes=0)[:len(bus)-start]
    bus[start:start+len(wet)] += wet * 10 ** (send_db / 20)
    return start, end


def place_music(bus, cue, lines, folder, rate):
    entry, exit_at = frames(cue["in"], rate), frames(cue["out"], rate)
    prelap, tail = frames(cue.get("prelap", 0), rate), frames(cue.get("tail", 0), rate)
    start, end = entry - prelap, exit_at + tail
    if not 0 <= start <= entry < exit_at <= end <= len(bus):
        raise ValueError(f"Music cue outside the timeline: {cue['file']}")
    kind = cue.get("kind", "score")
    if kind not in ("score", "pad"):
        raise ValueError("Music kind must be score or pad")
    reason = cue.get("pad_reason", "")
    if kind == "pad" and not (isinstance(reason, str) and reason.strip()):
        raise ValueError("A sustained pad needs a pad_reason from the sound script")
    for left, right, name in lines:
        if kind == "score" and start < right and left < end:
            raise ValueError(f"Music {cue['file']} overlaps line {name} at {max(left, start)/rate:g}s")
    offset = frames(cue.get("source_start", 0), rate)
    clip = source(cue, folder, rate)[offset:offset+end-start]
    if len(clip) != end - start:
        raise ValueError(f"Music source is too short for the cue and its handles: {cue['file']}")
    # Even a cue without a musical handle gets a short edit fade.
    edge = min(round(.01 * rate), len(clip) // 2)
    fade_in, fade_out = prelap or edge, tail or edge
    if fade_in:
        clip[:fade_in] *= np.linspace(0, 1, fade_in)[:, None]
    if fade_out:
        clip[-fade_out:] *= np.linspace(1, 0, fade_out)[:, None]
    bus[start:end] += clip


def render(plan, folder):
    rate = plan.get("rate", 48000)
    if type(rate) is not int or rate < 4000:
        raise ValueError("Use an integer sample rate of at least 4000 Hz")
    length = frames(plan["duration"], rate)
    if not length:
        raise ValueError("The timeline must contain at least one sample")
    buses = {name: np.zeros((length, 2), np.float32) for name in ("bed", "dialogue", "effects", "music")}
    mix_beds(buses["bed"], plan.get("beds", []), folder, rate)
    rooms = {name: room_impulse(name, decay, rate) for name, decay in plan.get("rooms", {}).items()}
    lines = []
    for role in ("dialogue", "effects"):
        for row in plan.get(role, []):
            start, end = place_in_room(buses[role], row, rooms, folder, rate)
            if role == "dialogue":
                lines.append((start, end, row["file"]))
    for cue in plan.get("music", []):
        place_music(buses["music"], cue, lines, folder, rate)
    buses["mix"] = sum(buses.values())
    peak = float(np.abs(buses["mix"]).max())
    if not math.isfinite(peak):
        raise ValueError("Mix exceeds the supported gain range")
    gain = .89 / max(.89, peak)
    for bus in buses.values():
        bus *= gain
    return rate, buses


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("plan", type=Path, help="JSON sound timeline. Source paths are relative to this file.")
    parser.add_argument("output", type=Path, help="New directory for mix.wav and aligned stereo stems")
    args = parser.parse_args()
    try:
        if args.output.exists():
            raise ValueError(f"Choose a new output directory: {args.output}")
        plan = json.loads(args.plan.read_text(encoding="utf-8-sig"))
        rate, buses = render(plan, args.plan.parent)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=args.output.parent) as tmp:
            ready = Path(tmp) / "stems"
            ready.mkdir()
            for name, samples in buses.items():
                wavfile.write(ready / f"{name}.wav", rate, samples)
            ready.rename(args.output)
    except (OSError, KeyError, TypeError, ValueError, OverflowError) as error:
        parser.exit(2, f"Scene mix: {error}\n")
    print(args.output / "mix.wav")


if __name__ == "__main__":
    main()
