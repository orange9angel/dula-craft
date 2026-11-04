"""Let every script run with plain `python script.py`, on any agent, on any OS.

If a dependency is missing and the dula-craft environment exists, the script re-runs
itself inside that environment. Standard library only.
"""
import importlib.util
import os
import subprocess
import sys
from pathlib import Path


def home():
    return Path(os.environ.get("DULA_CRAFT_HOME") or Path.home() / ".dula-craft")


def venv_python():
    venv = home() / "venv"
    return venv / "Scripts" / "python.exe" if os.name == "nt" else venv / "bin" / "python"


def config_file():
    return home() / "config.env"


def setting(name):
    """An environment variable wins; otherwise the private file written by configure.py."""
    value = os.environ.get(name)
    if value:
        return value
    path = config_file()
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            key, sep, val = line.partition("=")
            if sep and key.strip() == name:
                return val.strip()
    return None


def utf8_console():
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")


def ensure(*modules):
    utf8_console()
    missing = [m for m in modules if importlib.util.find_spec(m) is None]
    if not missing:
        return
    python = venv_python()
    if python.exists() and Path(sys.prefix).resolve() != (home() / "venv").resolve():
        sys.exit(subprocess.call([str(python), *sys.argv]))
    sys.exit(
        f"Missing dependencies: {', '.join(missing)}.\n"
        "Run scripts/doctor.py --fix from the dula-start skill. It sets everything up."
    )
