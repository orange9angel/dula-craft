#!/usr/bin/env python3
"""Save an optional service key on this computer, for this user only.

  python configure.py             asks for the key; typing is hidden
  python configure.py --status    says whether a key is saved, never what it is
  python configure.py --remove    deletes the saved key

The person runs this in their own terminal, so the key never passes through the AI's
conversation. It is stored in ~/.dula-craft/config.env, outside every project folder,
so it cannot end up in a film folder or a git commit.
"""
import argparse
import getpass
import os
import stat
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

VOICE_KEY = "VOLC_SPEECH_API_KEY"
HELP = """Voices use Volcano Engine Seed-Audio, billed to your own account:
  1. Enable "Audio Generation 1.0": https://console.volcengine.com/speech/new/setting/activate
  2. Create an API key: https://console.volcengine.com/speech/new/setting/apikeys
"""


def write(values):
    path = _bootstrap.config_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    text = "".join(f"{k}={v}\n" for k, v in values.items())
    # Create it private from the first byte rather than tightening it afterwards.
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, stat.S_IRUSR | stat.S_IWUSR)
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        f.write(text)


def read():
    path = _bootstrap.config_file()
    values = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep:
                values[key.strip()] = value.strip()
    return values


def main():
    _bootstrap.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--status", action="store_true")
    ap.add_argument("--remove", action="store_true")
    ap.add_argument("--stdin", action="store_true", help="read the key from standard input, for scripts")
    args = ap.parse_args()

    values = read()
    if args.status:
        print("Voice key: " + ("set" if _bootstrap.setting(VOICE_KEY) else "not set"))
        return 0
    if args.remove:
        values.pop(VOICE_KEY, None)
        write(values)
        print("Voice key removed.")
        return 0

    if args.stdin:
        key = sys.stdin.readline().strip()
    else:
        print(HELP)
        key = getpass.getpass("Paste your API key (it stays hidden as you type), then press Enter: ").strip()
    if not key:
        print("Nothing entered. Nothing changed.")
        return 1
    if any(c.isspace() for c in key) or "=" in key:
        print("That does not look like an API key. Not saved.")
        return 1
    values[VOICE_KEY] = key
    write(values)
    print(f"Saved to {_bootstrap.config_file()}. This file stays on your computer.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
