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

## DEV pilot and freeze (2026-10-19 to 2026-10-20)

| Change | Reason / evidence |
|---|---|
| **Pilot round 0** (Haiku 4.5, DEV, one repeat; knobs alias 0.5, stale 2/3/5, conflicts 2/4/8). Mean F1 on DEV cross-source questions: A3 0.644, B3 1.000, C3 0.950. Cost $0.34. | Pre-registered ceiling rule: B3 and C3 above 0.90. |
| **Generator fix (reproducibility).** Re-running the generator for round 1 silently changed the 120-node canonical graph (two `deployedIn` edges swapped; 3 answers changed). Cause: exp1's generator iterates Python sets, whose order changes between processes, so re-running it is not reproducible. Fix: the canonical graphs were restored byte for byte from the step-1 commit (`b8e36a7`; hashes 7e2de1042a6b4747, d3392d3e800d1ebc, 20bbda1571519393 after line-ending normalization), and `gen3.py` now derives the exports from the frozen canonical files instead of re-running the generator. Questions, split and all 76 answers equal step 1; exp1 and exp2 hashes unchanged (`tools/verify_frozen.py`). | Raising the knobs must change only the exports, never the ground truth. |
| **Pilot round 1** (knobs raised as pre-registered: alias 0.7, stale 4/6/10, conflicts 4/8/16). Mean F1 on DEV cross-source: A3 0.620, B3 1.000, C3 0.950. Cost $0.25 (C3's prompt was unchanged, so its calls came from the cache). Both artifacts re-verified on the new exports. | Ceiling rule, round 1 of at most 2. |
| **Difficulty rule ended after round 1; round 2 not used.** B3's glue and C3's rules resolve all knob-controlled noise before the model sees it, so the knobs cannot move B3 or C3; round 1 confirmed no movement. Final knobs: round 1 values. H1 is now expected null on ceiling grounds. | My decision after the pilot. |
| **Clarity fix, prompt iteration 1 of 3 for C3 and for B3.** Added to C3's docs: "Teams and SLAs have no ex:name: refer to them by IRI only (e.g. ex:team-platform, ex:SLA-GOLD-01); their answer IDs are the IRI local names (team-platform, SLA-GOLD-01)." Added to B3's glue docs (the equivalent gap: its docs said `g.resolve` handles any identifier, but teams and SLAs are not resolvable): "Teams and SLAs are not resolved by g.resolve, which covers components only: compare them as plain strings (e.g. g.team[ci] == "team-platform", g.sla[ci] == "SLA-GOLD-01")." | Evidence: C3's only two DEV misses in both rounds, `e3-100-06` (SLA looked up by `ex:name`) and `e3-20-05` (team looked up by `ex:name`). C3 DEV rerun as a check: both fixed, 23/23 correct, 23/23 valid, no retries, no new errors; cost $0.09. B3 was not rerun; its DEV results are from prompt v1. No further tuning. |
| Frozen for TEST: hashes in `PREREG_EXP3.md`, checked by `tools/verify_frozen.py`. TEST estimate 3 repeats about 489 calls, $2.94 with the 1.6× correction: no cut. | Pre-registered budget rule. |

Prompt versions: A3 1, B3 2, C3 2. Prompt iterations used: A3 0, B3 1, C3 1 (of 3).

## TEST (2026-10-20)

| Date | Entry |
|---|---|
| 2026-10-20 | `exp3/analyze3.py` was written after the freeze but before any TEST result existed. It implements the analysis in `PREREG_EXP3.md` and touches no frozen file. |
