#!/usr/bin/env python3
"""Paint every image a film needs. Run from the film folder.

  python paint.py anchors   config/anchors.tsv   who <TAB> description
  python paint.py cels      config/cels.tsv      name <TAB> who <TAB> description [<TAB> drawing to follow]
  python paint.py variants  config/variants.tsv  name <TAB> base <TAB> description [<TAB> x,y,w,h]
  python paint.py plates    config/plates.tsv    name <TAB> description [<TAB> plate to follow]
  python paint.py plates    config/plates.tsv --only room --force     redo one image

Finished images are skipped, so a rerun continues where it stopped. With Codex CLI installed
the images are generated automatically. Without it, this writes build/images_todo.md: paint
those images with any tool and save them to the listed paths.
"""
import argparse
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

_bootstrap.ensure("PIL")
from PIL import Image  # noqa: E402

CEL_SIZE = "1024x1536"
ALPHA = "FULLY TRANSPARENT background (real PNG alpha), no backdrop, no ground, no shadow."
GENERATED = Path.home() / ".codex" / "generated_images"


def rows(path, only):
    out = []
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            parts = line.split("\t")
            if not only or parts[0] in only:
                out.append(parts)
    return out


def codex_image(out, prompt, refs, size, timeout=600):
    # Codex can lose attached images after any earlier tool call, so the image tool must run first.
    if refs:
        prompt = (
            "CRITICAL FIRST STEP: call your image generation tool IMMEDIATELY as your very first action, "
            "using the attached reference image(s). Do not read files or run commands first. " + prompt
        )
    if size:
        prompt += f" Output exact pixel size: {size}."
    prompt += " Generate the image with your image tool. Do NOT save or move any files yourself."
    # Windows splits a command line at newlines, which would drop the -i attachments.
    prompt = re.sub(r"\s+", " ", prompt).strip()
    exe = shutil.which("codex")
    cmd = [exe, "exec", prompt, "--skip-git-repo-check", "--ephemeral", "-s", "workspace-write"]
    for ref in refs:
        cmd += ["-i", str(Path(ref).resolve())]
    if exe.lower().endswith((".cmd", ".bat")):
        cmd = ["cmd", "/c", *cmd]
    started = time.time()
    proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                            errors="replace", stdin=subprocess.DEVNULL)
    while True:
        try:
            stdout, stderr = proc.communicate(timeout=30)
            break
        except subprocess.TimeoutExpired:
            waited = time.time() - started
            if waited > timeout:
                proc.kill()
                sys.exit(f"Codex did not finish within {timeout} s")
            print(f"  still painting ({waited:.0f} s)...", flush=True)
    log = (stdout or "") + "\n" + (stderr or "")
    if proc.returncode != 0:
        sys.exit(f"Codex image generation failed ({proc.returncode}):\n{log[-2000:]}")
    session = re.search(r"session id:\s*([0-9a-f-]+)", log, re.I)
    found = sorted((GENERATED / session.group(1)).glob("*.png"), key=lambda p: p.stat().st_mtime) if session else []
    if not found:
        found = sorted((p for p in GENERATED.glob("*/*.png") if p.stat().st_mtime >= started - 5),
                       key=lambda p: p.stat().st_mtime)
    if not found:
        sys.exit(f"Codex finished, but no generated image was found:\n{log[-2000:]}")
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(found[-1], out)
    if size:
        want = tuple(int(v) for v in size.split("x"))
        with Image.open(out) as im:
            if im.size != want:
                im.resize(want, Image.LANCZOS).save(out)


def jobs(kind, table):
    style = Path("config/style.txt").read_text(encoding="utf-8").strip() if kind != "plates" else ""
    plate_style = Path("config/plate_style.txt").read_text(encoding="utf-8").strip() if kind == "plates" else ""
    for row in table:
        if kind == "anchors":
            who, desc = row[:2]
            yield Path(f"assets/anchors/{who}.png"), (
                f"Character model sheet of one original character, full body, in the view that shows this "
                f"character best, neutral pose, mouth closed. {desc} {style} {ALPHA}"), [], CEL_SIZE
        elif kind == "cels":
            name, who, desc = row[:3]
            refs = [f"assets/anchors/{who}.png"]
            follow = ""
            if len(row) > 3 and row[3].strip():
                refs.append(f"assets/cels/{row[3].strip()}.png")
                follow = ("Image 2 is the previous drawing of this action: keep its scale, facing direction, "
                          "framing on the canvas and body shape, changing only what the new pose needs. ")
            yield Path(f"assets/cels/{name}.png"), (
                f"Image 1 is the locked character model sheet: keep the exact head shape, face layout, line weight, "
                f"colours and proportions. {follow}New pose for this exact character, alone, full body in frame: "
                f"{desc} {style} {ALPHA}"), refs, CEL_SIZE
        elif kind == "variants":
            name, base, desc = row[:3]
            yield Path(f"assets/cels/raw/{name}.png"), (
                f"Local edit of the attached image. {desc} Every other part of the drawing stays exactly the same: "
                f"same pose, same outline, same flat colours, same canvas size {CEL_SIZE}, same position. {ALPHA} "
                f"Generate exactly one image."), [f"assets/cels/{base}.png"], CEL_SIZE
        else:
            name, desc = row[:2]
            refs, follow = [], ""
            if len(row) > 2 and row[2].strip():
                refs = [f"assets/plates/{row[2].strip()}.png"]
                follow = ("The attached image is this same place: keep the exact layout, objects and viewpoint, "
                          "and change only what this description asks for. ")
            yield Path(f"assets/plates/{name}.png"), f"{follow}{desc} {plate_style} Landscape, 3:2.", refs, None


def main():
    _bootstrap.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("kind", choices=["anchors", "cels", "variants", "plates"])
    ap.add_argument("table")
    ap.add_argument("--only", action="append", default=[], help="only these names; repeatable")
    ap.add_argument("--force", action="store_true", help="repaint existing images; needs --only")
    args = ap.parse_args()
    if args.force and not args.only:
        ap.error("--force needs --only, so nothing is repainted by accident")

    todo = []
    table = rows(args.table, args.only)
    for out, prompt, refs, size in jobs(args.kind, table):
        if out.exists() and out.stat().st_size and not args.force:
            print(f"Already done: {out}")
            continue
        for ref in refs:
            if not Path(ref).exists():
                sys.exit(f"Reference image not found: {ref}. Paint in order: anchors, cels, variants.")
        if shutil.which("codex"):
            print(f"Painting {out}...", flush=True)
            codex_image(out, prompt, refs, size)
            print(f"Done: {out}", flush=True)
        else:
            todo.append((out, prompt, refs, size))

    if todo:
        path = Path("build/images_todo.md")
        path.parent.mkdir(exist_ok=True)
        with path.open("a", encoding="utf-8") as f:
            for out, prompt, refs, size in todo:
                f.write(f"## {out}\n\n- Size: {size or 'landscape, about 1536x1024'}\n- References: {', '.join(refs) or 'none'}\n\n{prompt}\n\n")
        print(f"No Codex CLI. {len(todo)} images are still needed: see {path}. Save them to the listed paths and run this again.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
