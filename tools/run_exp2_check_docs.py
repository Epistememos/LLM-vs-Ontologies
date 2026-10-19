"""run_exp2_check_docs.py - run the frozen exp2/check_docs.py after the repo restructure.

check_docs.py (frozen, hashed in PREREG_EXP2.md) reads Experiment 1's question texts from `<repo>/data/questions.json`,
the layout before Experiment 1 moved into exp1/. This wrapper redirects exactly that one path to
`exp1/data/questions.json` (same bytes, moved with git mv) and runs the script unmodified.
Run (from the repo root): python tools/run_exp2_check_docs.py
"""
import pathlib
import runpy
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OLD, NEW = (ROOT / "data" / "questions.json").resolve(), ROOT / "exp1" / "data" / "questions.json"
_read_text = pathlib.Path.read_text


def read_text(self, *args, **kwargs):
    return _read_text(NEW if self.resolve() == OLD else self, *args, **kwargs)


pathlib.Path.read_text = read_text
sys.argv = [str(ROOT / "exp2" / "check_docs.py")]
runpy.run_path(sys.argv[0], run_name="__main__")
