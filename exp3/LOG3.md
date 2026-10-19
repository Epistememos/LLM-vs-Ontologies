# Experiment 3 log

Every change to a prompt, question, artifact or harness, with the evidence behind it. Experiments 1 and 2 are frozen.

## Step 1 (2026-10-17)

Generator, ground truth with a consistency check, 76 questions split by seed (23 DEV, 53 TEST), and the draft
pre-registration. Seed 3021 instead of 3020 for the smallest graph: the first seed the unchanged generator accepts.

## Step 2 (2026-10-19)

| Change | Reason / evidence |
|---|---|
| Trap audit: added a "match by name similarity" wrong reading (monitoring identifiers matched to the CMDB record with the most similar normalized name). It changes 6 of 64 cross-source answers. Questions, answers and the DEV/TEST split are unchanged. | Diagnostic of how much exact entity resolution matters. |
| Measured the pre-specified H2 "lost" change before any run: it changes 29 of 53 TEST answers (29 of 44 cross-source, 0 controls). Kept unchanged. | Checking the change is not too small to measure breakage. |
| PREREG: the primary CI is dominated by the two larger scales (29 of 44 cross-source TEST questions); per-seed results descriptive only; control counts reported per seed and size. | Make the weighting of the primary test explicit. |
| Failure is region-parametric in both artifacts: C3 materializes `lostIn`, `downIn`, `breachedIn` for every region; B3's glue methods take the datacenter as an argument. | Questions name the failed datacenter; the harness must not learn it from the hidden answer key, so both artifacts compute every region from the exports alone. |
| Team and region crosswalks derived from the two exports by majority vote over non-stale records (`derive_tables.py`), one shared file for B3 and C3. | Same mappings in both by construction; derived from data, not from the hidden key; checked against the key. |
| Built B3 (`glue.py`) and C3 (`to_rdf3.py`, `rules3.py`, `ontology3.ttl`). Both match the key and `truth3.py` on the first verification run; 0 fixes each. | `verify3.py`, with a negative control (planted bugs are caught). |
| Hidden-data guard: an audit hook that refuses opening or listing any path under `data/hidden/`, installed in the harness process and at the top of every sandbox program and SPARQL runner. | Rule: no condition, prompt builder, harness or sandbox may read `data/hidden/`. |
| Harness fix: the guard first deleted names it still needed when called (`NameError` on the first dry run); bound them as default arguments. | Harness bug, before any model call; not an artifact fix. |
| Test fix: the static part of the guard test first flagged comments that mention `data/hidden/`; it now checks only string values the code can use. A negative control confirms it still flags the two files that really read the folder (`truth3.py`, `score3.py`). | Test precision, before any model call. |
| Repeats: repeat k > 1 uses its own cache namespace (`e3-<condition>-r<k>`), bypassing the response cache without changing temperature or Experiment 1's `llm.py`. | Pre-registered: 3 repeats at temperature 0, cache bypassed. |

Prompt versions: A3 1, B3 1, C3 1. Prompt iterations used: 0 of 3 per condition.
