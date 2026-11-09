#!/usr/bin/env python3
"""config/film.json -> build/sheet.json (exposure sheet) + build/mix.wav. Run from the film folder.

Shots run back to back and a shot is as long as its lines plus padding, so a retimed voice
re-flows the film. Anything missing fails loudly: a film never renders with a silent gap.
"""
import json
import subprocess
import sys
import wave
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

_bootstrap.ensure("cv2", "numpy", "PIL", "scipy")
import cv2  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
from scipy.signal import butter, fftconvolve, sosfiltfilt  # noqa: E402

SR = 48000
FLAT = Path("assets/flat")
_boxes = {}
_sizes = {}


def fail(message):
    sys.exit(f"[ERROR] {message}")


def decode(path):
    if not Path(path).exists():
        fail(f"Audio file not found: {path}")
    cmd = ["ffmpeg", "-v", "error", "-i", str(path), "-f", "f32le", "-ac", "1", "-ar", str(SR), "-"]
    done = subprocess.run(cmd, capture_output=True)
    if done.returncode:
        fail(f"Cannot read audio {path}: {done.stderr.decode(errors='replace')[-300:]}")
    return np.frombuffer(done.stdout, np.float32).astype(np.float64)


def has_cel(name):
    return (FLAT / f"{name}.png").exists()


def box(name):
    if name not in _boxes:
        if not has_cel(name):
            fail(f"Drawing not found: {FLAT / (name + '.png')}")
        im = Image.open(FLAT / f"{name}.png").convert("RGBA")
        _sizes[name] = im.size
        _boxes[name] = im.getchannel("A").point(lambda v: 255 if v > 40 else 0).getbbox()
        if _boxes[name] is None:
            fail(f"{name} is fully transparent")
    return _boxes[name]


def gray(name):
    a = np.array(Image.open(FLAT / f"{name}.png").convert("RGBA"))
    alpha = a[..., 3:4] / 255.0
    return cv2.cvtColor((a[..., :3] * alpha + 128 * (1 - alpha)).astype(np.uint8), cv2.COLOR_RGB2GRAY)


def head_offsets(cels, canvas_height):
    """Register each drawing's head onto the first one so a cycle's head does not jump.
    Viewers watch the face: a steady head matters more than steady clothes."""
    x0, y0, x1, y1 = box(cels[0])
    region = (x0, y0, x0 + int((x1 - x0) * 0.5), y0 + int((y1 - y0) * 0.42))
    reference = gray(cels[0])[region[1]:region[3], region[0]:region[2]]
    k = canvas_height / _sizes[cels[0]][1]
    offsets = {}
    for cel in cels[1:]:
        _, _, _, (mx, my) = cv2.minMaxLoc(cv2.matchTemplate(gray(cel), reference, cv2.TM_CCOEFF_NORMED))
        offsets[cel] = [round((region[0] - mx) * k, 1), round((region[1] - my) * k, 1)]
    return offsets


def talk_states(cel):
    """Closed base drawing plus whichever open variants exist."""
    m1 = f"{cel}_m1" if has_cel(f"{cel}_m1") else cel
    m2 = f"{cel}_m2" if has_cel(f"{cel}_m2") else m1
    return [cel, m1, m2]


def resolve_actor(actor, frame_width, frame_height):
    """cx, ground and height describe the visible drawing. One scale for all of an actor's drawings,
    taken from the first: scaling each to its own visible height makes a cycle pulse tall and short."""
    out = dict(actor)
    cels = out["cels"] = [out["cels"]] if isinstance(out["cels"], str) else out["cels"]
    if out.pop("overlay", False):
        # An effect layer covers the frame exactly, whatever its visible pixels happen to be.
        for cel in cels:
            box(cel)
        out.update(x=[frame_width / 2] * 2, y=[frame_height] * 2, h=frame_height)
        return out
    x0, y0, x1, y1 = box(cels[0])
    for cel in cels:
        box(cel)
    width, height = _sizes[cels[0]]
    h = out.pop("height") * height / (y1 - y0)
    w = h * width / height
    cx = out.pop("cx")
    place = lambda c: round(c - ((x0 + x1) / 2 - width / 2) / width * w, 1)  # noqa: E731
    out["x"] = [place(v) for v in cx] if isinstance(cx, list) else [place(cx)] * 2
    y = round(out.pop("ground") + (height - y1) / height * h, 1)
    out["y"] = [y, y + out.pop("dy", 0)]
    out["h"] = round(h, 1)
    if out.pop("align_head", False) and len(cels) > 1:
        out["offs"] = head_offsets(cels, h)
    return out


def envelope(y, fps):
    hop = SR // fps
    frames = max(1, len(y) // hop)
    rms = np.array([np.sqrt((y[i * hop:(i + 2) * hop] ** 2).mean()) if len(y[i * hop:(i + 2) * hop]) else 0
                    for i in range(frames)])
    top = np.percentile(rms, 95)
    return [round(float(v), 3) for v in rms / (top if top > 1e-6 else 1)]


def fade(y, ms=30):
    n = min(int(SR * ms / 1000), len(y) // 2)
    if n:
        ramp = np.linspace(0, 1, n)
        y = y.copy()
        y[:n] *= ramp
        y[-n:] *= ramp[::-1]
    return y


def gate(y, floor=0.04, ms=40):
    """Silence a sound effect's noise floor, so level matching cannot lift it into audible hiss."""
    w = int(SR * ms / 1000)
    env = np.sqrt(fftconvolve(y ** 2, np.ones(w) / w, "same").clip(0))
    hann = np.hanning(w)
    return y * fftconvolve((env > env.max() * floor).astype(float), hann / hann.sum(), "same").clip(0, 1)


def bed(conf):
    """Ambience: band-limit, even out bursts, and level by loudness with a capped gain.
    Scaling a near-silent clip to a peak target turns its noise floor into a constant hiss,
    so the quiet default is safe for room tone. A stated level_db is for a sound that is part
    of the story, such as rain, and gets more headroom."""
    conf = {"file": conf} if isinstance(conf, str) else conf
    level, cap = (conf["level_db"], 8.0) if "level_db" in conf else (-50, 2.0)
    y = decode(conf["file"])
    y = sosfiltfilt(butter(4, [60, 12000], "bp", fs=SR, output="sos"), y)
    w = int(SR * 0.4)
    env = np.sqrt(fftconvolve(y ** 2, np.ones(w) / w, "same").clip(1e-10))
    y = y * (np.median(env) / env) ** 0.7
    rms = np.sqrt((y ** 2).mean())
    return y * min(10 ** (level / 20) / max(rms, 1e-9), cap)


def main():
    _bootstrap.utf8_console()
    film = json.loads(Path("config/film.json").read_text(encoding="utf-8"))
    fps = film.get("fps", 24)
    width, height = film.get("width", 1440), film.get("height", 1080)
    if width % 2 or height % 2:
        fail("width and height must be even numbers")

    lines = {}
    for line in film["lines"]:
        item = dict(line)
        audio_path = line.get("file") or f"audio/voice/{line['id']}.wav"
        if Path(audio_path).exists():
            y = decode(audio_path)
            peak = max(np.abs(y).max(), 1e-6)
            item["audio"] = y / peak * 0.55 * line.get("gain", 1.0)
            item["dur"] = len(y) / SR
        elif line.get("seconds"):
            item["audio"] = None
            item["dur"] = float(line["seconds"])
            print(f"[NOTE] {line['id']} has no audio: {line['seconds']} s of silence, and the mouth will not move.")
        else:
            fail(f"Line {line['id']} has no audio at {audio_path}. For a silent draft, give the line a seconds value.")
        lines[line["id"]] = item

    used = set()
    t = 0.0
    lines_at, env, shots = {}, {}, []
    for raw in film["shots"]:
        ids = raw.get("lines", [])
        for lid in ids:
            if lid not in lines:
                fail(f"Shot {raw['id']} uses unknown line {lid}")
            if lid in used:
                fail(f"Line {lid} is used twice")
            used.add(lid)
        pre, post = raw.get("pre", 0.15), raw.get("post", 0.25)
        together = raw.get("together", False)   # duets: every line starts at pre (one per singer)
        spoken = max((lines[i]["dur"] + 0.05 for i in ids), default=0) if together else sum(lines[i]["dur"] + 0.05 for i in ids)
        duration = max(raw.get("seconds", 0), pre + post + spoken)
        if duration <= 0:
            fail(f"Shot {raw['id']} has no lines, so it needs seconds")
        cursor = t + pre
        for lid in ids:
            lines_at[lid] = round(cursor, 3)
            audio = lines[lid]["audio"]
            env[lid] = envelope(audio, fps) if audio is not None else [0.0] * int(lines[lid]["dur"] * fps)
            if not together:
                cursor += lines[lid]["dur"] + 0.05
        plate = dict(raw["plate"])
        if plate["key"] not in film["plates"]:
            fail(f"Shot {raw['id']} uses unregistered plate {plate['key']}")
        for axis, default in (("x", width / 2), ("y", height)):
            value = plate.get(axis, default)
            plate[axis] = value if isinstance(value, list) else [value, value]
        plate.setdefault("height", height)
        shot = dict(id=raw["id"], t0=round(t, 3), t1=round(t + duration, 3), hold=raw.get("hold", 3), plate=plate, actors=[])
        for field in ("fade_in", "fade_out"):
            if raw.get(field):
                shot[field] = raw[field]
        for actor in raw.get("actors", []):
            resolved = resolve_actor(actor, width, height)
            mine = [lid for lid in ids if lines[lid].get("who") == actor.get("who")] if actor.get("who") else []
            if mine:
                talk = resolved.pop("talk", None)
                resolved["talk"] = {c: (talk if isinstance(talk, list) else (talk or {}).get(c) or talk_states(c)) for c in resolved["cels"]}
                resolved["talk_lines"] = mine
                for states in resolved["talk"].values():
                    for state in states:
                        box(state)
            else:
                resolved.pop("talk", None)   # no line of theirs in this shot: show the first (closed) state
            shot["actors"].append(resolved)
        # A visible speaker whose mouth cannot move is the easiest mistake to ship.
        for lid in ids:
            who = lines[lid].get("who")
            if lines[lid]["audio"] is None or lines[lid].get("mouth_ok"):
                continue
            on_screen = [a for a in shot["actors"] if a.get("who") == who]
            moving = [a for a in on_screen if lid in a.get("talk_lines", []) and
                      any(len(set(s)) > 1 for s in a["talk"].values())]
            if on_screen and not moving:
                fail(f"Frozen mouth: line {lid} ({who}) in shot {raw['id']}. Add mouth variants. "
                     f"If it is deliberate, such as one long scream, set mouth_ok on the line with the reason.")
        shots.append((shot, raw))
        t += duration
    total = round(t, 3)
    for lid in lines:
        if lid not in used:
            print(f"[NOTE] Line {lid} is not used by any shot")

    n = int((total + 1) * SR)
    vox, song, sfx, amb, music = (np.zeros(n) for _ in range(5))

    def add(bus, y, at, gain=1.0):
        i = int(at * SR)
        y = y[:max(n - i, 0)]
        bus[i:i + len(y)] += y * gain

    for lid, at in lines_at.items():
        if lines[lid]["audio"] is not None:
            add(vox, lines[lid]["audio"], at)

    beds = {k: bed(p) for k, p in film.get("ambience", {}).items()}
    bgm_conf = film.get("bgm")
    bgm_src = decode(bgm_conf["file"]) if bgm_conf else None
    bgm_gain = (bgm_conf or {}).get("gain", 0.16)
    bgm_pos, bgm_on, current_bed = 0, False, None
    for shot, raw in shots:
        i0, i1 = int(shot["t0"] * SR), int(shot["t1"] * SR)
        if "ambience" in raw:
            current_bed = raw["ambience"]
        if current_bed:
            if current_bed not in beds:
                fail(f"Shot {raw['id']} uses unregistered ambience {current_bed}")
            source = beds[current_bed]
            amb[i0:i1] = np.resize(np.roll(source, -i0 % len(source)), i1 - i0)
        if raw.get("bgm") in ("on", "off"):
            bgm_on = raw["bgm"] == "on"
        if bgm_on and bgm_src is not None:
            piece = np.resize(np.roll(bgm_src, -bgm_pos % len(bgm_src)), i1 - i0)
            music[i0:i1] = piece / max(np.abs(bgm_src).max(), 1e-6) * bgm_gain
            bgm_pos += i1 - i0
        for cue in raw.get("sfx", []):
            y = gate(decode(cue["file"]))
            # Generated clips often start late: put the loudest point on the cue time.
            peak_at = int(np.argmax(np.abs(y))) / SR
            add(sfx, fade(y), max(shot["t0"] + cue.get("at", 0) - min(peak_at, 0.4), 0),
                cue.get("gain", 0.5) / max(np.abs(y).max(), 1e-3))
        for cue in raw.get("songs", []):
            y = decode(cue["file"])
            peak = max(np.abs(y).max(), 1e-3)
            start = int(cue.get("from", 0) * SR)
            end = int(cue["to"] * SR) if "to" in cue else len(y)
            add(song, fade(y[start:end]), shot["t0"] + cue.get("at", 0), cue.get("gain", 0.85) / peak)

    kernel = np.hanning(int(0.08 * SR))
    music = fftconvolve(music, kernel / kernel.sum(), "same")
    window = np.hanning(int(0.25 * SR))
    active = fftconvolve((np.abs(vox) > 0.01).astype(float), window / window.sum(), "same")
    duck = 1 - 0.45 * np.clip(active * 3, 0, 1)   # dialogue ducks song and score
    mix = vox + song * duck + sfx + amb + music * duck
    peak = np.abs(mix).max()
    if peak > 0.78:
        mix *= 0.78 / peak

    # Only the film's own start and end fade the sound, so a fade mid-film can't cut off a line.
    first_shot, last_shot = shots[0][0], shots[-1][0]
    if first_shot.get("fade_in"):
        print("[NOTE] The first shot fades in from black, so video sites will show a black thumbnail. "
              "Drop its fade_in unless the black opening is wanted.")
        count = int(first_shot["fade_in"] * SR)
        mix[:count] *= np.linspace(0, 1, count)
    if last_shot.get("fade_out"):
        count = int(last_shot["fade_out"] * SR)
        end = int(total * SR)
        mix[max(end - count, 0):end] *= np.linspace(1, 0, min(count, end))
        mix[end:] = 0

    Path("build").mkdir(exist_ok=True)
    pcm = (np.clip(mix[:int(total * SR)], -1, 1) * 32767).astype(np.int16)
    with wave.open("build/mix.wav", "wb") as f:
        f.setnchannels(1)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(pcm.tobytes())

    sheet = dict(
        width=width, height=height, fps=fps, dur=total, env=env, lines=lines_at,
        open_at={k: v["mouth_open_at"] for k, v in lines.items() if "mouth_open_at" in v},
        who={k: v.get("who") for k, v in lines.items()},
        plates=film["plates"], shots=[shot for shot, _ in shots],
    )
    Path("build/sheet.json").write_text(json.dumps(sheet, ensure_ascii=False), encoding="utf-8")
    print(f"{len(shots)} shots, {total:.1f} s in total")
    for shot, _ in shots:
        print(f"  {shot['id']}: {shot['t0']:.2f} - {shot['t1']:.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
