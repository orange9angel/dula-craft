#!/usr/bin/env python3
"""Check that this machine can make a film, and fix what can be fixed safely.

  python doctor.py          report only
  python doctor.py --fix    also create the private Python environment

--fix only touches ~/.dula-craft. System software such as ffmpeg is never installed
without the person asking: the report prints the command for them to approve.
"""
import argparse
import json
import platform
import shutil
import subprocess
import sys
import venv
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
import _bootstrap  # noqa: E402

REQUIREMENTS = Path(__file__).resolve().parents[1] / "requirements.txt"
MODULES = {"numpy": "numpy", "PIL": "pillow", "cv2": "opencv-python-headless", "scipy": "scipy"}


def ffmpeg_hint():
    system = platform.system()
    if system == "Windows":
        return "winget install Gyan.FFmpeg"
    if system == "Darwin":
        return "brew install ffmpeg"
    return "sudo apt install ffmpeg"


def modules_in(python):
    code = (
        "import importlib.util, json;"
        f"print(json.dumps([m for m in {list(MODULES)!r} if importlib.util.find_spec(m) is None]))"
    )
    out = subprocess.run([str(python), "-c", code], capture_output=True, text=True, check=True)
    return json.loads(out.stdout)


def fix_environment():
    python = _bootstrap.venv_python()
    if not python.exists():
        print(f"Creating environment: {python.parents[1]}")
        venv.create(python.parents[1], with_pip=True, clear=False)
    print("Installing dependencies (about a minute the first time)...")
    subprocess.run(
        [str(python), "-m", "pip", "install", "--quiet", "--disable-pip-version-check", "-r", str(REQUIREMENTS)],
        check=True,
    )


def main():
    _bootstrap.utf8_console()
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fix", action="store_true")
    args = ap.parse_args()

    if sys.version_info < (3, 9):
        sys.exit(f"[MISSING] Python 3.9 or newer is required, found {platform.python_version()}")
    print(f"[OK] Python {platform.python_version()}")

    if args.fix:
        fix_environment()

    python = _bootstrap.venv_python()
    target = python if python.exists() else Path(sys.executable)
    missing = modules_in(target)
    blocking = []
    if missing:
        names = ", ".join(MODULES[m] for m in missing)
        print(f"[MISSING] Python packages: {names}. Run: python doctor.py --fix")
        blocking.append("deps")
    else:
        print("[OK] Python packages")

    for tool in ("ffmpeg", "ffprobe"):
        if shutil.which(tool):
            print(f"[OK] {tool}")
        else:
            print(f"[MISSING] {tool}. Install with: {ffmpeg_hint()}")
            blocking.append(tool)

    if shutil.which("codex"):
        print("[OK] Codex CLI: images can be generated automatically, using your ChatGPT plan")
    else:
        print("[OPTIONAL] No Codex CLI: paint.py lists the prompts, and you make the images with any tool")

    if _bootstrap.setting("VOLC_SPEECH_API_KEY"):
        print("[OK] Voice key is set")
    else:
        print("[OPTIONAL] No voice key: use your own audio, or run scripts/configure.py")

    if blocking:
        print("\nNot ready yet: fix the items marked [MISSING] above.")
        return 1
    print("\nReady to make a film.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
