#!/usr/bin/env python3
"""Draw-in-code cels: inspect, export and film an SVG scene.

A scene is one SVG file whose viewBox is the stage. Drawings that replace each
other (poses, mouths, eyes) are sibling groups inside a switch group:

    <g data-switch="hero.pose">
      <g data-state="stand"> ... </g>
      <g data-state="point"> ... </g>
    </g>

Exactly one state of a switch is shown at a time. A timeline JSON picks states,
places rigid groups, fades layers and moves the camera per frame.

    python svgcel.py states scene.svg
    python svgcel.py still scene.svg -o out.png --set hero.pose=point --isolate hero
    python svgcel.py sheet scene.svg hero.pose -o poses.png
    python svgcel.py film scene.svg timeline.json -o shot.mp4 --stills 0,48
    python svgcel.py trace scene.svg ref.png -o cmp.png --isolate hero --box 554,146,903,903
"""
from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
from pathlib import Path

PAGE = """<!doctype html><html><head><meta charset="utf-8"><style>
html,body{margin:0;padding:0;background:__BG__;overflow:hidden}
svg#stage{display:block;width:__W__px;height:__H__px}
</style></head><body>__SVG__<script>
const root=document.querySelector('svg');root.id=root.id||'stage';
if(root.id!=='stage'){root.dataset.oldId=root.id;root.id='stage';}
window.sceneInfo=()=>{
  const sw={};
  document.querySelectorAll('[data-switch]').forEach(g=>{
    const names=[...g.children].map(c=>c.dataset.state).filter(s=>s!==undefined);
    sw[g.dataset.switch]=(sw[g.dataset.switch]||[]).concat(names);
  });
  const ids=[...document.querySelectorAll('[id]')].map(e=>e.id);
  return {switches:sw,ids:ids,viewBox:root.getAttribute('viewBox')};
};
window.applyState=(s)=>{
  for(const [name,state] of Object.entries(s.switch||{})){
    document.querySelectorAll('[data-switch="'+name+'"]').forEach(g=>{
      for(const c of g.children){
        if(c.dataset.state!==undefined) c.style.display=(c.dataset.state===state)?'':'none';
      }
    });
  }
  for(const [id,t] of Object.entries(s.move||{})){
    const e=document.getElementById(id); if(e) e.setAttribute('transform',t);
  }
  for(const [id,o] of Object.entries(s.opacity||{})){
    const e=document.getElementById(id);
    if(e){e.style.opacity=o; e.style.visibility=(o<=0)?'hidden':'';}
  }
  if(s.viewBox) root.setAttribute('viewBox',s.viewBox);
};
window.isolate=(id)=>{
  // hide every sibling up the tree; <use> copies of <defs> content stay visible
  let e=document.getElementById(id);
  while(e && e!==root){
    for(const sib of e.parentNode.children){
      const tag=sib.tagName.toLowerCase();
      if(sib!==e && tag!=='defs' && tag!=='style') sib.style.display='none';
    }
    e=e.parentNode;
  }
};
</script></body></html>"""


# ---------- timeline evaluation (pure functions, tested offline) ----------

def ease(t: float, kind: str) -> float:
    t = min(1.0, max(0.0, t))
    if kind == "hold":
        return 0.0 if t < 1.0 else 1.0
    if kind == "in":
        return t * t
    if kind == "out":
        return 1.0 - (1.0 - t) * (1.0 - t)
    if kind == "inout":
        return t * t * (3.0 - 2.0 * t)
    return t


def switch_at(keys: list, frame: int) -> str:
    """Last [frame, state] key at or before `frame`."""
    state = keys[0][1]
    for f, s in keys:
        if f <= frame:
            state = s
        else:
            break
    return state


def _interp(keys: list[dict], frame: float, fields: dict) -> dict:
    """Interpolate numeric fields between dict keys; the target key's ease is used."""
    keys = sorted(keys, key=lambda k: k["f"])
    cur = dict(fields)
    cur.update({k: v for k, v in keys[0].items() if k in fields})
    if frame <= keys[0]["f"]:
        return cur
    prev = cur
    prev_f = keys[0]["f"]
    for key in keys[1:]:
        nxt = dict(prev)
        nxt.update({k: v for k, v in key.items() if k in fields})
        if frame < key["f"]:
            t = ease((frame - prev_f) / (key["f"] - prev_f), key.get("ease", "linear"))
            return {k: prev[k] + (nxt[k] - prev[k]) * t for k in fields}
        prev, prev_f = nxt, key["f"]
    return prev


def move_at(track, frame: int) -> str:
    """Rigid placement of one group: translate, optional scale and rotation about a pivot."""
    if isinstance(track, list):
        track = {"keys": track}
    step = int(track.get("step", 1))
    f = (frame // step) * step if step > 1 else frame
    v = _interp(track["keys"], f, {"x": 0.0, "y": 0.0, "s": 1.0, "r": 0.0})
    px, py = track.get("pivot", [0, 0])
    parts = [f"translate({v['x']:.3f} {v['y']:.3f})"]
    if abs(v["r"]) > 1e-6:
        parts.append(f"rotate({v['r']:.3f} {px} {py})")
    if abs(v["s"] - 1.0) > 1e-6:
        parts.append(f"translate({px} {py}) scale({v['s']:.5f}) translate({-px} {-py})")
    return " ".join(parts)


def opacity_at(keys: list, frame: int) -> float:
    dict_keys = [{"f": f, "o": o} for f, o in keys]
    return round(_interp(dict_keys, frame, {"o": 1.0})["o"], 4)


def camera_at(tl: dict, frame: int, stage: list[float]) -> str:
    cam = tl.get("camera")
    if cam:
        keys = [{"f": k["f"], "bx": k["box"][0], "by": k["box"][1], "bw": k["box"][2],
                 "bh": k["box"][3], "ease": k.get("ease", "linear")} for k in cam]
        v = _interp(keys, frame, {"bx": stage[0], "by": stage[1], "bw": stage[2], "bh": stage[3]})
        box = [v["bx"], v["by"], v["bw"], v["bh"]]
    else:
        box = list(stage)
    for sh in tl.get("shake", []):
        n = frame - sh["f"]
        if 0 <= n < sh["len"]:
            amp = sh["amp"] * (1.0 - n / sh["len"])
            box[0] += amp * math.sin(n * 12.9898 + 1.3)
            box[1] += amp * math.cos(n * 78.233 + 0.7)
    return " ".join(f"{b:.3f}" for b in box)


def state_at(tl: dict, frame: int, stage: list[float]) -> dict:
    return {
        "switch": {n: switch_at(k, frame) for n, k in tl.get("switch", {}).items()},
        "move": {i: move_at(t, frame) for i, t in tl.get("move", {}).items()},
        "opacity": {i: opacity_at(k, frame) for i, k in tl.get("opacity", {}).items()},
        "viewBox": camera_at(tl, frame, stage),
    }


def check_timeline(tl: dict, info: dict) -> list[str]:
    """Names in the timeline must exist in the scene. Returns error strings."""
    errors = []
    for name, keys in tl.get("switch", {}).items():
        if name not in info["switches"]:
            errors.append(f"switch '{name}' is not in the scene")
            continue
        for f, s in keys:
            if s not in info["switches"][name]:
                errors.append(f"switch '{name}' has no state '{s}' (frame {f})")
    ids = set(info["ids"])
    for kind in ("move", "opacity"):
        for i in tl.get(kind, {}):
            if i not in ids:
                errors.append(f"{kind} target id '{i}' is not in the scene")
    for name in info["switches"]:
        if name not in tl.get("switch", {}):
            errors.append(f"switch '{name}' has no track: all its states would show at once")
    return errors


# ---------- browser ----------

def _stage_box(info: dict) -> list[float]:
    vb = info.get("viewBox")
    if not vb:
        sys.exit("The root <svg> needs a viewBox; it is the stage.")
    return [float(x) for x in vb.replace(",", " ").split()]


class Stage:
    def __init__(self, svg_path: Path, size: tuple[int, int] | None, bg: str):
        from playwright.sync_api import sync_playwright
        text = svg_path.read_text(encoding="utf-8")
        start = text.find("<svg")
        if start < 0:
            sys.exit(f"{svg_path} has no <svg> element")
        self._pw = sync_playwright().start()
        try:
            self._browser = self._pw.chromium.launch()
        except Exception:
            self._browser = self._pw.chromium.launch(channel="chrome")
        probe = self._browser.new_page()
        probe.set_content(PAGE.replace("__BG__", bg).replace("__W__", "100").replace("__H__", "100")
                          .replace("__SVG__", text[start:]))
        self.info = probe.evaluate("sceneInfo()")
        probe.close()
        self.stage = _stage_box(self.info)
        w, h = size or (round(self.stage[2]), round(self.stage[3]))
        self.size = (w, h)
        self.page = self._browser.new_page(viewport={"width": w, "height": h})
        self.page.set_content(PAGE.replace("__BG__", bg).replace("__W__", str(w)).replace("__H__", str(h))
                              .replace("__SVG__", text[start:]))
        self.transparent = bg == "transparent"

    def apply(self, state: dict):
        self.page.evaluate("s => applyState(s)", state)

    def shot(self) -> bytes:
        return self.page.screenshot(type="png", omit_background=self.transparent)

    def close(self):
        self._browser.close()
        self._pw.stop()


def _parse_sets(pairs: list[str], info: dict) -> dict:
    chosen = {name: states[0] for name, states in info["switches"].items() if states}
    for pair in pairs or []:
        name, _, state = pair.partition("=")
        if name not in info["switches"] or state not in info["switches"][name]:
            sys.exit(f"--set {pair}: unknown switch or state. Run 'states' to list them.")
        chosen[name] = state
    return chosen


def _size(arg: str | None):
    if not arg:
        return None
    w, _, h = arg.lower().partition("x")
    return int(w), int(h)


# ---------- commands ----------

def cmd_states(a):
    st = Stage(Path(a.svg), None, "transparent")
    print(f"stage viewBox: {' '.join(str(x) for x in st.stage)}")
    for name, states in st.info["switches"].items():
        print(f"{name}: {', '.join(states)}")
    if not st.info["switches"]:
        print("no data-switch groups")
    st.close()


def cmd_still(a):
    st = Stage(Path(a.svg), _size(a.size), a.bg)
    st.apply({"switch": _parse_sets(a.set, st.info)})
    if a.isolate:
        if a.isolate not in st.info["ids"]:
            sys.exit(f"--isolate {a.isolate}: no such id")
        st.page.evaluate("id => isolate(id)", a.isolate)
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    Path(a.output).write_bytes(st.shot())
    st.close()
    print(f"wrote {a.output} {st.size[0]}x{st.size[1]}")


def _box(arg: str | None):
    return [float(x) for x in arg.split(",")] if arg else None


def cmd_trace(a):
    """Reference | drawing | drawing's dark lines in red over the reference, at the same framing."""
    from PIL import Image
    import io
    ref = Image.open(a.ref).convert("RGB")
    if a.ref_box:
        x, y, w, h = _box(a.ref_box)
        ref = ref.crop((int(x), int(y), int(x + w), int(y + h)))
    probe = Stage(Path(a.svg), None, "transparent")
    box = _box(a.box) or probe.stage
    probe.close()
    height = a.height
    width = round(height * box[2] / box[3])
    st = Stage(Path(a.svg), (width, height), "transparent")
    st.apply({"switch": _parse_sets(a.set, st.info), "viewBox": " ".join(str(b) for b in box)})
    if a.isolate:
        st.page.evaluate("id => isolate(id)", a.isolate)
    drawn = Image.open(io.BytesIO(st.shot())).convert("RGBA")
    st.close()
    ref = ref.resize((width, height), Image.LANCZOS)
    panel = Image.new("RGB", (width, height), (214, 206, 201))
    panel.paste(drawn, (0, 0), drawn)
    over = ref.copy()
    px, dp = over.load(), drawn.load()
    for yy in range(height):
        for xx in range(width):
            r, g, b, al = dp[xx, yy]
            if al > 128 and (r * 299 + g * 587 + b * 114) < 62000 and max(r, g, b) < 64:
                px[xx, yy] = (255, 30, 30)
    out = Image.new("RGB", (width * 3, height), "white")
    for i, im in enumerate((ref, panel, over)):
        out.paste(im, (i * width, 0))
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    out.save(a.output)
    print(f"wrote {a.output}: reference | drawing | drawing lines (red) over reference, {width}x{height} each")


def cmd_sheet(a):
    """All states of one switch side by side, for looking at drawings before timing them."""
    from PIL import Image
    import io
    st = Stage(Path(a.svg), _size(a.size), a.bg)
    if a.switch not in st.info["switches"]:
        sys.exit(f"unknown switch '{a.switch}'")
    base = _parse_sets(a.set, st.info)
    tiles = []
    for state in st.info["switches"][a.switch]:
        st.apply({"switch": {**base, a.switch: state}})
        tiles.append((state, Image.open(io.BytesIO(st.shot())).convert("RGB")))
    st.close()
    w, h = tiles[0][1].size
    sheet = Image.new("RGB", (w * len(tiles), h), "white")
    for i, (_, im) in enumerate(tiles):
        sheet.paste(im, (i * w, 0))
    Path(a.output).parent.mkdir(parents=True, exist_ok=True)
    sheet.save(a.output)
    print(f"wrote {a.output}: {', '.join(s for s, _ in tiles)}")


def cmd_film(a):
    tl = json.loads(Path(a.timeline).read_text(encoding="utf-8"))
    fps = int(tl.get("fps", 24))
    frames = int(tl["frames"])
    st = Stage(Path(a.svg), tuple(tl["size"]) if tl.get("size") else None, tl.get("bg", "#000"))
    errors = check_timeline(tl, st.info)
    if errors:
        st.close()
        sys.exit("timeline does not match the scene:\n  " + "\n  ".join(errors))
    out = Path(a.output)
    frames_dir = Path(a.frames_dir) if a.frames_dir else out.with_suffix("").parent / (out.stem + "_frames")
    if frames_dir.exists():
        shutil.rmtree(frames_dir)
    frames_dir.mkdir(parents=True)
    last_key, last_png, drawn = None, b"", 0
    for f in range(frames):
        state = state_at(tl, f, st.stage)
        key = json.dumps(state, sort_keys=True)
        if key != last_key:
            st.apply(state)
            last_png, last_key = st.shot(), key
            drawn += 1
        (frames_dir / f"f{f:05d}.png").write_bytes(last_png)
    for n in [int(x) for x in a.stills.split(",")] if a.stills else []:
        shutil.copy(frames_dir / f"f{n:05d}.png", out.with_name(f"{out.stem}_f{n:05d}.png"))
    st.close()
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(fps), "-i", str(frames_dir / "f%05d.png")]
    audio = a.audio or tl.get("audio")
    if audio:
        audio_path = Path(audio) if Path(audio).is_absolute() else Path(a.timeline).parent / audio
        cmd += ["-i", str(audio_path)]
    cmd += ["-c:v", "libx264", "-crf", "15", "-preset", "slow", "-pix_fmt", "yuv420p",
            "-t", f"{frames / fps:.4f}"]
    if audio:
        cmd += ["-c:a", "aac", "-b:a", "256k"]
    cmd += ["-movflags", "+faststart", str(out)]
    out.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(cmd, check=True)
    if not a.keep_frames:
        shutil.rmtree(frames_dir)
    print(f"wrote {out}: {frames} frames at {fps} fps, {drawn} distinct drawings"
          f"{', audio ' + str(audio) if audio else ', no audio'}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("states", help="list switch groups and their states")
    s.add_argument("svg")
    s.set_defaults(fn=cmd_states)
    s = sub.add_parser("still", help="render one PNG")
    s.add_argument("svg")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--set", action="append", metavar="SWITCH=STATE")
    s.add_argument("--isolate", metavar="ID", help="show only this element, on the full stage (a registered cel)")
    s.add_argument("--size", metavar="WxH")
    s.add_argument("--bg", default="transparent")
    s.set_defaults(fn=cmd_still)
    s = sub.add_parser("sheet", help="all states of one switch side by side")
    s.add_argument("svg")
    s.add_argument("switch")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--set", action="append", metavar="SWITCH=STATE")
    s.add_argument("--size", metavar="WxH")
    s.add_argument("--bg", default="#d6cec9")
    s.set_defaults(fn=cmd_sheet)
    s = sub.add_parser("trace", help="compare the drawing with a reference image at the same framing")
    s.add_argument("svg")
    s.add_argument("ref")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--set", action="append", metavar="SWITCH=STATE")
    s.add_argument("--isolate", metavar="ID")
    s.add_argument("--box", metavar="X,Y,W,H", help="stage region that corresponds to the reference frame")
    s.add_argument("--ref-box", metavar="X,Y,W,H", help="crop of the reference image, in its pixels")
    s.add_argument("--height", type=int, default=900)
    s.set_defaults(fn=cmd_trace)
    s = sub.add_parser("film", help="render a timeline to video")
    s.add_argument("svg")
    s.add_argument("timeline")
    s.add_argument("-o", "--output", required=True)
    s.add_argument("--audio")
    s.add_argument("--stills", help="comma-separated frame numbers to keep as PNG next to the video")
    s.add_argument("--frames-dir")
    s.add_argument("--keep-frames", action="store_true")
    s.set_defaults(fn=cmd_film)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
