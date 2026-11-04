#!/usr/bin/env python3
"""Voice every line of a film with Seed-Audio, using the person's own key. Run from the film folder.

  python speak.py                 voice all lines that need it
  python speak.py --only l03      redo one line
  python speak.py --dry-run       show what would be sent; spends nothing
  python speak.py --sound "a quiet garden at dawn, birds and light wind" --out audio/sfx/garden.wav

A line is skipped when its text and voice have not changed, so a rerun costs nothing extra.
Without a speaker id, each character's first line becomes the reference for their later
lines, which keeps it the same voice.
"""
import argparse
import base64
import hashlib
import json
import os
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

KEY_NAME = "VOLC_SPEECH_API_KEY"
API_URL = os.environ.get("DULA_SEED_AUDIO_URL") or "https://openspeech.bytedance.com/api/v3/tts/create"
MODEL = "seed-audio-1.0"
VOICE_DIR = Path("audio/voice")


class ServiceError(RuntimeError):
    pass


def generate(key, prompt, references, out, timeout=300):
    payload = {"model": MODEL, "text_prompt": prompt, "audio_config": {"format": "wav", "sample_rate": 48000}}
    if references:
        payload["references"] = references
    request = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"X-Api-Key": key, "X-Api-Request-Id": str(uuid.uuid4()), "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = json.loads(response.read())
    except urllib.error.HTTPError as error:
        detail = error.read().decode("utf-8", errors="replace")[:400]
        if error.code in (401, 403):
            raise ServiceError(f"Key rejected, or Audio Generation 1.0 is not enabled (HTTP {error.code}). {detail}") from error
        raise ServiceError(f"HTTP {error.code}: {detail}") from error
    except urllib.error.URLError as error:
        raise ServiceError(f"Cannot reach the voice service: {error.reason}") from error
    if body.get("code") not in (None, 0, 20000000):
        raise ServiceError(f"The service returned an error: {json.dumps(body, ensure_ascii=False)[:400]}")
    if not body.get("audio"):
        raise ServiceError("The service returned no audio")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(base64.b64decode(body["audio"]))
    return float(body.get("original_duration") or body.get("duration") or 0)


def trim(path):
    """The service tends to pad a short line to the requested length. Mouth timing needs the real one."""
    if not shutil.which("ffmpeg"):
        return
    temp = path.with_suffix(".trim.wav")
    edge = "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03"
    done = subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(path), "-af",
                           f"{edge},areverse,{edge},areverse", str(temp)], capture_output=True)
    if done.returncode == 0 and temp.stat().st_size > 1000:
        temp.replace(path)
    else:
        temp.unlink(missing_ok=True)


def prompt_for(line, voice, has_reference):
    # The framing stays in Chinese because that is the form tested against this service.
    # Voice descriptions and the line itself can be in any language.
    parts = ["生成一段纯人声台词录音，无音乐、无音效、无背景声。"]
    if has_reference:
        parts.append("声音和@音频1是同一个人，音色完全一致。")
    if voice.get("desc"):
        parts.append(f"声音：{voice['desc']}。")
    if line.get("delivery"):
        parts.append(f"这一句的念法：{line['delivery']}。")
    parts.append(f"语言：{voice.get('lang', '和台词原文相同的语言')}。")
    # Spelling the text out stops ellipses and pauses being re-read as other words.
    parts.append(f"台词就是『{line['text']}』，一字不改，念完就结束。")
    return "".join(parts)


def main():
    _bootstrap.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--only", action="append", default=[])
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--sound", help="generate an ambience or sound effect instead of dialogue")
    ap.add_argument("--out", help="output file, used with --sound")
    args = ap.parse_args()

    key = _bootstrap.setting(KEY_NAME)
    if not key and not args.dry_run:
        sys.exit("No voice key yet. Ask the person to run scripts/configure.py from dula-start in their own terminal.\n"
                 "Never ask them to paste the key into the conversation.")

    if args.sound:
        if not args.out:
            sys.exit("--sound also needs --out")
        if args.dry_run:
            print(args.sound)
            return 0
        try:
            seconds = generate(key, f"生成一段纯音效：{args.sound}。无人声、无台词、无音乐。", [], Path(args.out))
        except ServiceError as error:
            sys.exit(f"[ERROR] {error}")
        print(f"Done: {args.out} (billed {seconds:.1f} s)")
        return 0

    film = json.loads(Path("config/film.json").read_text(encoding="utf-8"))
    voices = film.get("voices", {})
    first = {}
    total = 0.0
    for line in film["lines"]:
        who = line.get("who")
        out = Path(line["file"]) if line.get("file") else VOICE_DIR / f"{line['id']}.wav"
        record = out.with_suffix(".source.json")
        voice = voices.get(who, {})
        reference_path = None
        if not voice.get("speaker"):
            reference_path = first.get(who) or (Path(voice["reference"]) if voice.get("reference") else None)
        prompt = prompt_for(line, voice, bool(voice.get("speaker") or reference_path))
        tag = hashlib.sha256(json.dumps([prompt, voice.get("speaker")], ensure_ascii=False).encode()).hexdigest()[:16]
        current = record.exists() and json.loads(record.read_text(encoding="utf-8")).get("tag") == tag
        wanted = line["id"] in args.only if args.only else not (out.exists() and current)

        if args.dry_run:
            print(f"{'generate' if wanted else 'skip'} {line['id']} ({who}): {prompt}")
            first.setdefault(who, out)
            continue
        if wanted:
            print(f"Voicing {line['id']} ({who})...", flush=True)
            references = [{"speaker": voice["speaker"]}] if voice.get("speaker") else []
            if reference_path:
                references = [{"audio_data": base64.b64encode(reference_path.read_bytes()).decode("ascii")}]
            try:
                total += generate(key, prompt, references, out)
            except ServiceError as error:
                sys.exit(f"[ERROR] {line['id']}: {error}")
            trim(out)
            record.write_text(json.dumps({"tag": tag, "text": line["text"], "provider": MODEL,
                                          "reference": str(reference_path) if reference_path else voice.get("speaker")},
                                         ensure_ascii=False, indent=1), encoding="utf-8")
        else:
            print(f"Already done: {out}")
        if out.exists():
            first.setdefault(who, out)
    if not args.dry_run:
        print(f"Voices done. Billed {total:.1f} s this run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
