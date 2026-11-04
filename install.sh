#!/usr/bin/env bash
# Install dula-craft for Claude Code, Codex and Kimi Code. Safe to rerun; rerunning updates.
#   curl -fsSL https://raw.githubusercontent.com/orange9angel/dula-craft/main/install.sh | bash
#   curl -fsSL .../install.sh | bash -s -- --uninstall
set -euo pipefail

# Git Bash on Windows turns ln -s into a plain copy, which cannot be updated or uninstalled cleanly.
case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "This is Windows. Please run this in PowerShell instead:"
    echo "irm https://raw.githubusercontent.com/orange9angel/dula-craft/main/install.ps1 | iex"
    exit 1
    ;;
esac

HOME_DIR="${DULA_CRAFT_HOME:-$HOME/.dula-craft}"
REPO_URL="${DULA_CRAFT_REPO:-https://github.com/orange9angel/dula-craft.git}"
REPO_DIR="$HOME_DIR/repo"
# Claude Code reads the first; Codex and Kimi Code read the second.
TARGETS=("$HOME/.claude/skills" "$HOME/.agents/skills")

skills() { find "$REPO_DIR/skills" -mindepth 1 -maxdepth 1 -type d -exec basename {} \;; }

if [ "${1:-}" = "--uninstall" ]; then
  if [ -d "$REPO_DIR/skills" ]; then
    for name in $(skills); do
      for target in "${TARGETS[@]}"; do
        link="$target/$name"
        if [ -L "$link" ] && [ "$(readlink "$link")" = "$REPO_DIR/skills/$name" ]; then rm "$link"; fi
      done
    done
  fi
  rm -rf "$REPO_DIR" "$HOME_DIR/venv" "$HOME_DIR/config.env"
  rmdir "$HOME_DIR" 2>/dev/null || true
  echo "dula-craft is uninstalled."
  exit 0
fi

command -v git >/dev/null || { echo "Please install git first."; exit 1; }
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null && "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 9))' 2>/dev/null; then
    PY="$candidate"; break
  fi
done
[ -n "$PY" ] || { echo "Python 3.9 or newer is required: https://www.python.org/downloads/"; exit 1; }

mkdir -p "$HOME_DIR"
if [ -d "$REPO_DIR/.git" ]; then
  git -C "$REPO_DIR" pull --quiet --ff-only
else
  git clone --quiet --depth 1 "$REPO_URL" "$REPO_DIR"
fi

for target in "${TARGETS[@]}"; do
  mkdir -p "$target"
  for name in $(skills); do
    link="$target/$name"
    source="$REPO_DIR/skills/$name"
    if [ -L "$link" ] && [ "$(readlink "$link")" = "$source" ]; then continue; fi
    if [ -e "$link" ] || [ -L "$link" ]; then
      echo "Skipped $link: something else is already there, and it was not overwritten."
      continue
    fi
    ln -s "$source" "$link"
  done
done

"$PY" "$REPO_DIR/skills/dula-start/scripts/doctor.py" --fix || true
echo
echo "All set. Restart Claude Code, Codex or Kimi Code and say: make me an animated short"
