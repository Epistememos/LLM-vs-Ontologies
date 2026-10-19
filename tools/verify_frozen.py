"""verify_frozen.py - check every file hash pre-registered in exp1/PREREG.md and exp2/PREREG_EXP2.md.

The PREREG hashes were taken on Windows working-tree bytes, where Git (core.autocrlf=true) may write a file with
CRLF or LF line endings depending on how it was last checked out. A file counts as unchanged if its bytes, its
LF-normalized bytes or its CRLF-normalized bytes reproduce the pre-registered hash; the form that matched is shown.
Run (from the repo root): python tools/verify_frozen.py
"""
import hashlib
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PREREGS = {"exp1": ROOT / "exp1" / "PREREG.md", "exp2": ROOT / "exp2" / "PREREG_EXP2.md"}
LINE = re.compile(r"^([0-9a-f]{16}) (\S+)$")


def forms(data):
    lf = data.replace(b"\r\n", b"\n")
    return {"raw": data, "LF": lf, "CRLF": lf.replace(b"\n", b"\r\n")}


def check(folder, prereg):
    block = prereg.read_text(encoding="utf-8").split("```")
    rows = [LINE.match(l.strip()) for part in block[1::2] for l in part.splitlines()]
    results = []
    for m in filter(None, rows):
        h, rel = m.groups()
        path = ROOT / folder / rel
        if not path.exists():
            results.append((rel, "MISSING"))
            continue
        hit = [name for name, b in forms(path.read_bytes()).items() if hashlib.sha256(b).hexdigest()[:16] == h]
        results.append((rel, hit[0] if hit else "CHANGED"))
    return results


if __name__ == "__main__":
    ok = True
    for folder, prereg in PREREGS.items():
        res = check(folder, prereg)
        bad = [r for r in res if r[1] in ("CHANGED", "MISSING")]
        ok &= not bad
        kinds = {k: sum(r[1] == k for r in res) for k in ("raw", "LF", "CRLF")}
        print(f"{folder}: {len(res) - len(bad)}/{len(res)} unchanged (matched as {kinds})")
        for rel, status in bad:
            print(f"   {status}: {folder}/{rel}")
    print("ALL FROZEN FILES UNCHANGED" if ok else "FROZEN FILES CHANGED")
    sys.exit(0 if ok else 1)
