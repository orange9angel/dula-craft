#!/usr/bin/env python3
"""Cold-read critique of story pitches or a storyboard by a second model (mediated evidence, not a verdict).

  python blind_pitch.py pitches.md [--mode pitch|board] [--ledger PAST_WORKS.md] [--lang English]
                        [--cmd "codex exec --skip-git-repo-check -s read-only -"] [--out report.md] [--timeout 900]

pitch mode: each pitch is read cold. The reader predicts the ending after reading only the hook, then reads the rest
and reports whether the turn surprised it, what feels familiar (named works or formulas), what overlaps the ledger of
earlier films, and what it would remember a day later; it ranks the pitches.
board mode: the reader reads the storyboard as a first-time viewer and writes, per shot, what happened and why; it
lists causes that are missing or come after their effects.

Pitches file format: sections starting with "## ", each with lines "Hook:", "Turn:", "Ending:" (more text allowed).
--cmd is any command that reads a prompt on stdin and prints the answer (default: Codex in read-only mode; for
example `claude -p` also works). The prompt is passed through a file on stdin; an interactive stdin can make a CLI
wait forever.
"""
import argparse
import re
import shlex
import subprocess
import sys
from pathlib import Path

PITCH_PROMPT = """You are a demanding story editor reading pitches for a 2-5 minute animated short or music video cold.
For EACH pitch below:
1. Read ONLY its Hook line first. Write the ending you would predict from the hook alone (one sentence).
2. Then read Turn and Ending. Say whether the turn surprised you (yes / partly / no) and why.
3. Name anything familiar: specific films, music videos, ads or well-known formulas it resembles.
4. Compare with the ledger of the studio's earlier films below: list every shared title word, setting, weather,
   time of day, prop, palette element or emotional arc.
5. What image would you still remember a day later? If none, say so.
6. Score originality and emotional payoff 1-10 each, with one line of reasoning.
Finish with a ranking and the single most important fix for the top pitch. Be blunt; flattery is useless here.
Answer in {lang}.

LEDGER OF EARLIER FILMS:
{ledger}

PITCHES:
{text}
"""

BOARD_PROMPT = """You are a first-time viewer who has not read any script. Below is a storyboard (shot by shot).
1. For each shot, write in one or two sentences what happened and why, using only what the shot description shows.
2. List every effect whose cause is not shown, is shown after the effect, or is hidden (dark, off-screen, unclear).
3. List every character or object whose identity, position or size is unclear or jumps between shots.
4. Say where you got bored and where you were moved.
Answer in {lang}.

STORYBOARD:
{text}
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("file")
    ap.add_argument("--mode", choices=["pitch", "board"], default="pitch")
    ap.add_argument("--ledger", help="markdown ledger of earlier films (title words, setting, palette, arc, verdict)")
    ap.add_argument("--lang", default="English", help="language of the report")
    ap.add_argument("--cmd", default="codex exec --skip-git-repo-check -s read-only -")
    ap.add_argument("--out")
    ap.add_argument("--timeout", type=int, default=900)
    a = ap.parse_args()
    text = Path(a.file).read_text(encoding="utf-8")
    if a.mode == "pitch":
        if not re.findall(r"^## ", text, re.M):
            sys.exit("no '## ' pitch sections found")
        ledger = Path(a.ledger).read_text(encoding="utf-8") if a.ledger else "(no earlier films recorded)"
        prompt = PITCH_PROMPT.format(ledger=ledger, text=text, lang=a.lang)
    else:
        prompt = BOARD_PROMPT.format(text=text, lang=a.lang)
    out = Path(a.out) if a.out else Path(a.file).with_name(Path(a.file).stem + f"_{a.mode}_coldread.md")
    pf = out.with_suffix(".prompt.txt")
    pf.write_text(prompt, encoding="utf-8")
    cmd = a.cmd if sys.platform == "win32" else shlex.split(a.cmd)
    with open(pf, encoding="utf-8") as fin:
        r = subprocess.run(cmd, stdin=fin, capture_output=True, text=True, encoding="utf-8", timeout=a.timeout,
                           shell=(sys.platform == "win32"))
    if r.returncode != 0 or not r.stdout.strip():
        sys.exit(f"reader failed ({r.returncode}): {r.stderr[-800:]}")
    out.write_text(r.stdout, encoding="utf-8")
    print(f"wrote {out}")


if __name__ == "__main__":
    main()
