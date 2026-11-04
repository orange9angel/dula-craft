#!/usr/bin/env python3
"""Gatekeeper for this public repository. Runs in CI and before every release.

Fails on credentials, personal paths, media outside docs/, drift between the shared helper
copies, and names on the blocklist. The blocklist holds hashes, so this public file does not
itself name what must stay out.

  python scripts/check_public.py
  python scripts/check_public.py --hash "term"     print the entry for a new blocklist term

Extra terms can stay on one machine, one per line: DULA_PRIVATE_TERMS=path/to/terms.txt
"""
import hashlib
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SELF = "scripts/check_public.py"

RULES = {
    "credential": r"\bsk-[A-Za-z0-9_-]{20,}|\bAKLT[A-Za-z0-9_-]{16,}|\bAKIA[0-9A-Z]{12,}|Bearer [A-Za-z0-9._-]{24,}"
                  r"|-----BEGIN [A-Z ]*PRIVATE KEY"
                  r"|(?i:(?:api[_-]?key|secret|password|token)[\"' ]*[:=][ ]*[\"'][^\"'\s$<{*.]{10,}[\"'])",
    "personal path": r"(?i)[a-z]:[\\/]+users[\\/]+[a-z0-9_.-]+|/home/[a-z0-9_-]+/|/users/[a-z0-9_-]+/",
    "email": r"[A-Za-z0-9._%+-]+@(?:gmail|qq|163|126|outlook|hotmail|foxmail)\.com",
}
MEDIA = re.compile(r"\.(png|jpe?g|webp|gif|mp3|wav|flac|m4a|mp4|mov|mkv|avi)$", re.I)
ALLOWED_MEDIA = re.compile(r"^docs/")  # anything under docs/ is cleared original work

BLOCKED = {
    "03c33c8bc99dad70", "144e505a35066787", "14895f8c5b0314f9", "234af911e971bff2",
    "241e6cad9afce57a", "33c614ca3cf78827", "34a533dfd7273a9b", "3583c4551b4d0baf",
    "38868dc905f4d6d6", "3a3a7aecc5768b86", "42e76d834d545ea6", "43999461d22f6784",
    "44de3ed43a38bbf7", "4970fbb8bd6bac22", "4a9037e79117c3d9", "4bc26b0e51bf757b",
    "5e5ab783bcc50d64", "61c220d696ce5502", "6371ea6c1afe6763", "64168e1ca791c61b",
    "6d8575709ff8d5c1", "6f7b4186bf2a98f5", "732e87e711b72833", "738e22f0acab814c",
    "7bb192c5b74e762b", "7ef694629a9665b4", "822c4a3f965ffded", "846f6a76ffc11155",
    "8a1718ee736f769f", "92c8dacf02cc570f", "980f89cbce241a9d", "a7df6d691d297911",
    "a95f7ccb200c8f80", "b486cd48c5f0d07b", "be4250f514c973fb", "c0af9747c7763d2c",
    "d5248395b1158fb4", "dec0891c5b060b87", "e306d054601988ef", "eaa2bded32cc585d",
    "f52909ec675ecf2b", "f782f7d2a21da28c",
}


def digest(term):
    return hashlib.sha256(term.lower().encode("utf-8")).hexdigest()[:16]


def tokens(line):
    """Latin words and every 2-5 character run of Chinese, lowercased."""
    lowered = line.lower()
    for word in re.findall(r"[a-z0-9][a-z0-9_.-]*[a-z0-9]", lowered):
        yield word
        # also the parts of a compound such as name_of_thing or some-name
        yield from re.split(r"[_.-]", word)
    for run in re.findall(r"[一-鿿]+", lowered):
        for size in range(2, 6):
            for start in range(len(run) - size + 1):
                yield run[start:start + size]


def tracked():
    out = subprocess.run(["git", "-C", str(ROOT), "ls-files", "-co", "--exclude-standard"],
                         capture_output=True, text=True, encoding="utf-8", check=True).stdout
    return [p for p in out.splitlines() if (ROOT / p).is_file()]


def main():
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    if len(sys.argv) == 3 and sys.argv[1] == "--hash":
        print(digest(sys.argv[2]))
        return 0

    rules = {name: re.compile(pattern) for name, pattern in RULES.items()}
    private = os.environ.get("DULA_PRIVATE_TERMS")
    if private:
        terms = [t.strip() for t in Path(private).read_text(encoding="utf-8").splitlines() if t.strip()]
        rules["private term"] = re.compile("|".join(map(re.escape, terms)), re.I)

    problems = 0
    paths = tracked()
    for path in paths:
        if MEDIA.search(path):
            if not ALLOWED_MEDIA.match(path):
                print(f"{path}: media files must be cleared original work under docs/")
                problems += 1
            continue
        if path == SELF:
            continue
        try:
            text = (ROOT / path).read_text(encoding="utf-8")
        except UnicodeDecodeError:
            print(f"{path}: binary file")
            problems += 1
            continue
        for number, line in enumerate(text.splitlines(), 1):
            # Never echo the matched line: it may be the secret itself.
            for name, rule in rules.items():
                if rule.search(line):
                    print(f"{path}:{number}: {name}")
                    problems += 1
            if any(digest(t) in BLOCKED for t in tokens(line)):
                print(f"{path}:{number}: blocked name")
                problems += 1

    copies = sorted(ROOT.glob("skills/*/scripts/_bootstrap.py"))
    if len({c.read_bytes().replace(b"\r\n", b"\n") for c in copies}) > 1:
        print("skills/*/scripts/_bootstrap.py: copies differ")
        problems += 1

    print(f"checked {len(paths)} files, {problems} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
