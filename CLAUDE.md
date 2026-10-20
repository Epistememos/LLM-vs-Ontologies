# Standing rules for this repository

- Experiments 1 and 2 are frozen (tags `exp1-final`, `exp2-final`): never modify their files, results or hashes.
  Check with `python tools/verify_frozen.py` before every commit.
- No tuning toward a C3 win. Log every change to a prompt, question or harness with the evidence that motivated it.
- `data/hidden/` (e.g. `exp3/data/hidden/`) is never read at runtime and never shown to any condition: not in
  prompts, sandboxes or harnesses.
- The H2 changes are fixed in `exp3/PREREG_EXP3.md` and may not be altered after any run.
- Max 3 prompt iterations per condition, clarity fixes only, each logged with evidence.
- The DEV/TEST split never moves.
- Ask before spending over ~$5 of API budget; print the call count and cost estimate with a 1.6x correction before
  any run.
- I author both the B3 and C3 artifacts, with equal effort and the same information; log line counts, fix counts
  and my review hours for each.

## Layout

- `exp1/`, `exp2/`, `exp3/`: one folder per experiment (code, data, results, PREREG, log, write-up).
- Experiment 1's modules (`truth`, `llm`, `sandbox`, `common`, `score`, ...) are imported by Experiments 2 and 3.
  They become importable from anywhere via `pip install -e .` (see `pyproject.toml`); do not copy them.
- `tools/`: repo-level checks. `notebook/`: the research notebook across experiments.

## Log of exceptions to the freeze rule

| Date | Change | Why | Check |
|---|---|---|---|
| 2026-10-19 | Experiment 1 moved from the repo root into `exp1/` with `git mv` (47 pure renames, no content change); the root `README.md` became a project overview and Experiment 1's write-up is now `exp1/README.md`, byte-identical; the addendum moved to `exp1/ADDENDUM.md` (link path updated, move noted). | Requested repo clean-up; the root README should describe all the work. | `tools/verify_frozen.py`: exp1 20/20 and exp2 19/19 unchanged; all offline test suites pass; both experiments re-score to the committed numbers. The frozen `exp2/check_docs.py` reads the old root path `data/questions.json`; run it via `tools/run_exp2_check_docs.py`, which redirects that one path. |

## Current status

Experiment 3 frozen for TEST (pilot done, ceiling accepted, clarity fix 1 of 3 for B3 and C3);
next: TEST run, 3 repeats, after an explicit go.
