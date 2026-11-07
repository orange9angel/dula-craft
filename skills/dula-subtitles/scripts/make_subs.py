#!/usr/bin/env python3
"""dula-subtitles: make dual-language subtitles and optionally burn them in.

  make_subs.py --events subs.json --ass-out out.ass
  make_subs.py --events subs.json --ass-out out.ass --video in.mp4 --out-video out.mp4

The events format is described in SKILL.md.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

for _s in (sys.stdout, sys.stderr):
    if hasattr(_s, "reconfigure"):
        _s.reconfigure(encoding="utf-8", errors="replace")

# Speaker colours (ABGR), assigned in order of appearance
PALETTE = [
    "&H00D0E8FF",  # pale gold
    "&H00FFE8D0",  # pale cyan
    "&H00D0FFD0",  # pale green
    "&H00FFD0F0",  # pale pink
    "&H00C0E0FF",  # light orange
    "&H00E8D0FF",  # pale purple
]

HEADER = """[Script Info]
Title: {project} — {group}
ScriptType: v4.00+
PlayResX: {width}
PlayResY: {height}
WrapStyle: 0
ScaledBorderAndShadow: yes
YCbCr Matrix: TV.709

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
"""

# Sizes are written for a 720-pixel-high canvas and scaled to the video's real height.
STYLE_CN = ("Style: CN_{idx},{cn_font},{size},{color},&H000000FF,{outline_colour},&H8C000000,"
            "-1,0,0,0,100,100,0.5,0,1,{outline},0.8,2,40,40,{margin},1\n")
STYLE_EN = ("Style: EN,Calibri,{size},&H0000D8FF,&H000000FF,&H8C140F0F,&H8C000000,"
            "0,-1,0,0,100,100,0,0,1,{outline},0.6,2,40,40,{margin},1\n")
STYLE_GROUP = ("Style: Group,{cn_font},{size},&H00FFFFFF,&H000000FF,&H8C00A078,&H8C000000,"
               "-1,0,0,0,100,100,2,0,1,{outline},1.2,8,40,40,{margin},1\n")
STYLE_GSUB = ("Style: GroupSub,Calibri,{size},&H00D8E4E4,&H000000FF,&H8C140F0F,&H8C000000,"
              "0,-1,0,0,100,100,1,0,1,{outline},0.6,8,40,40,{margin},1\n")

EVENTS_HEADER = ("\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR,"
                 " MarginV, Effect, Text\n")


def ts(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = sec % 60
    return f"{h}:{m:02d}:{s:05.2f}"


def build_ass(doc: dict, cn_font: str, width: int = 1280, height: int = 720, plain: bool = False) -> str:
    k = height / 720  # style sizes are written for 720 pixels high
    two_lines = any(ev.get("translation") or ev.get("en") for ev in doc["events"])
    group = doc.get("group", "")
    project = doc.get("project", "")
    speakers: list[str] = []
    for ev in doc["events"]:
        if ev["speaker"] not in speakers:
            speakers.append(ev["speaker"])

    out = HEADER.format(project=project, group=group, width=width, height=height)
    style_of = {}
    for i, spk in enumerate(speakers):
        style_of[spk] = f"CN_{i}"
        out += STYLE_CN.format(idx=i, cn_font=cn_font, size=round(44 * k),
                               color="&H00FFFFFF" if plain else PALETTE[i % len(PALETTE)],
                               outline_colour="&H00000000" if plain else "&H8C140F0F",
                               outline=round((4 if plain else 3) * k, 1),
                               margin=round((96 if two_lines else 36) * k))
    out += (STYLE_EN.format(size=round(26 * k), outline=round(2.4 * k, 1), margin=round(56 * k))
            + STYLE_GROUP.format(cn_font=cn_font, size=round(40 * k), outline=round(3.2 * k, 1), margin=round(40 * k))
            + STYLE_GSUB.format(size=round(22 * k), outline=round(2 * k, 1), margin=round(88 * k))
            + EVENTS_HEADER)

    if group:
        out += (f"Dialogue: 1,0:00:00.10,0:00:02.80,Group,,0,0,0,,"
                f"{{\\fad(600,800)}}{group}\n")
    if project:
        out += (f"Dialogue: 1,0:00:00.10,0:00:02.80,GroupSub,,0,0,0,,"
                f"{{\\fad(600,800)}}{project}\n")
    for ev in doc["events"]:
        start, end = ts(ev["start"]), ts(ev["end"])
        short = int((ev["end"] - ev["start"]) * 1000 / 5)  # a long fade leaves a short line faint
        fade = ev.get("fade", f"{min(400, short)},{min(500, short)}")
        out += (f"Dialogue: 0,{start},{end},{style_of[ev['speaker']]},,0,0,0,,"
                f"{{\\fad({fade})}}{ev.get('text') or ev['cn']}\n")
        second = ev.get("translation") or ev.get("en")
        if second:
            out += (f"Dialogue: 0,{start},{end},EN,,0,0,0,,"
                    f"{{\\fad({fade})}}{second}\n")
    return out


def main() -> int:
    ap = argparse.ArgumentParser(description="Make and burn in dual-language subtitles")
    ap.add_argument("--events", required=True, type=Path, help="events JSON")
    ap.add_argument("--ass-out", required=True, type=Path)
    ap.add_argument("--font", "--cn-font", dest="cn_font", default="Microsoft YaHei" if sys.platform == "win32" else "PingFang SC" if sys.platform == "darwin" else "Noto Sans CJK SC")
    ap.add_argument("--video", type=Path, help="clean source video, without subtitles")
    ap.add_argument("--out-video", type=Path, help="output video with subtitles burned in")
    ap.add_argument("--plain", action="store_true",
                    help="white text with a solid black outline for every speaker (best on phones and busy pictures)")
    ap.add_argument("--size", help="canvas WIDTHxHEIGHT; taken from --video when given, else 1280x720")
    args = ap.parse_args()

    doc = json.loads(args.events.read_text(encoding="utf-8"))
    args.ass_out.parent.mkdir(parents=True, exist_ok=True)
    width, height = 1280, 720
    if args.size:
        width, height = (int(v) for v in args.size.lower().split("x"))
    elif args.video:  # match the real frame, or a 4:3 film gets stretched, raised text
        probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                "stream=width,height", "-of", "csv=p=0", str(args.video)],
                               capture_output=True, text=True, check=True).stdout.strip().split(",")
        width, height = int(probe[0]), int(probe[1])
    args.ass_out.write_text(build_ass(doc, args.cn_font, width, height, args.plain), encoding="utf-8")
    print(f"ass: {args.ass_out}")

    if args.video or args.out_video:
        if not (args.video and args.out_video):
            sys.exit("--video and --out-video must be given together")
        # The ffmpeg ass filter needs the colon in a Windows drive path escaped
        ass_path = str(args.ass_out.resolve()).replace("\\", "/").replace(":", "\\:")
        cmd = [
            "ffmpeg", "-loglevel", "error", "-y", "-i", str(args.video),
            "-vf", f"ass='{ass_path}'",
            "-c:v", "libx264", "-crf", "18", "-pix_fmt", "yuv420p",
            "-c:a", "copy", str(args.out_video),
        ]
        subprocess.run(cmd, check=True)
        print(f"video: {args.out_video}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
