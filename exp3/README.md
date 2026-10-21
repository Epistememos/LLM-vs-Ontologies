# Experiment 3: two conflicting sources, changing definitions

Pre-registered in [PREREG_EXP3.md](PREREG_EXP3.md) before any TEST question was sent; every change is logged in
[LOG3.md](LOG3.md), and authoring effort is in [EFFORT3.md](EFFORT3.md).

> **H1 (accuracy):** with two exports that name the same infrastructure differently and contradict each other, an
> ontology with materialized rules (C3) answers cross-source questions better than Python glue that applies the same
> resolution and definitions (B3).

## Result

**The pre-registered test does not support H1. Both conditions were perfect, as the pre-registration expected.**

| Pre-registered test (TEST, 44 cross-source questions in 44 clusters, 3 repeats) | Mean F1 difference | 95% CI | Decision |
|---|---|---|---|
| **Primary: C3 − B3, cluster bootstrap by question text × graph seed** | **0.000** | **[0.000, 0.000]** | CI includes 0: **not supported** |
| C3 − B3, per-question bootstrap (secondary) | 0.000 | [0.000, 0.000] | agrees with the primary |

B3 and C3 each scored 1.000 on every cross-source question in every repeat. The tie was expected: after the DEV pilot
both conditions were above the pre-registered 0.90 ceiling in both rounds, and raising the difficulty knobs could not
move them, because both artifacts resolve all the planted noise before the model sees it. I recorded H1 as an
expected null on ceiling grounds in `PREREG_EXP3.md` before TEST.

**Resolving the sources first is what mattered** (descriptive, the two smaller graphs only, 30 cross-source questions):

| Contrast | Mean F1 difference | Cluster 95% CI | Per-question 95% CI |
|---|---|---|---|
| B3 − A3 | **+0.532** | [+0.377, +0.687] | [+0.377, +0.683] |
| C3 − A3 | **+0.532** | [+0.377, +0.687] | [+0.377, +0.683] |

A3, the model alone with both raw exports in its prompt, scored 0.468 on these questions. B3 and C3 scored 1.000.
Whether the resolving was done in Python or in an ontology made no difference.

**H2 (maintenance, exploratory; two changes, n = 1 each).** After renaming one CMDB field and changing the definition of
"lost", the unchanged ontology failed loudly on every question, while the unchanged Python glue failed silently on 18:
the model's retries worked around the rename and kept the old definition. After a minimal edit each, both recovered
(B3 0.981, C3 1.000) with the same number of changed code lines (4 each). Details below.

## Setup

| Condition | What the model gets | Tool |
|---|---|---|
| **A3** | both raw exports in the prompt, the shared docs | none (answers from the text); 22- and 120-node graphs only |
| **B3** | export schemas, the shared docs, and `glue.py`, which resolves entities, applies the authority and stale rules and implements every definition (13 public methods) | Python sandbox over the two JSON exports |
| **C3** | the shared docs and the ontology; the graph is built from both exports by `to_rdf3.py` and materialized by `rules3.py` (26 SPARQL CONSTRUCT rules in 14 strata) | one SPARQL query over the materialized graph |

- **Data:** one hidden canonical graph per size (exp1's generator, seeds 3021, 3100 and 3500; 22, 120 and 567 nodes),
  exported twice: a CMDB-style export (`CI-NNNNN` IDs, `ci_name`, `datacenter`, owner groups) and a monitoring-style
  export (`mon:` IDs, display names and aliases, zones, teams, SLAs). Planted noise, final knobs (round 1): alias rate
  0.7; 4 / 6 / 10 stale ghost services; 4 / 8 / 16 region conflicts and as many team conflicts. A fixed rulebook,
  identical in every condition's docs, says which export is authoritative for which fact and that stale records are
  ignored.
- **Questions:** cross-source questions need both exports (region failure computed from the CMDB, ownership and SLAs
  from monitoring); single-source controls need one. TEST: 53 questions, 44 cross-source and 9 controls. DEV/TEST
  split by seed, never moved.
- **Unchanged from Experiments 1 and 2:** Haiku 4.5, temperature 0, 8192 output tokens, 60 s sandbox and query timeout,
  one retry on errors only. **New:** 3 repeats per question with the cache bypassed, and a hidden-data guard (an audit
  hook) in the harness, every sandbox program and every SPARQL runner, refusing any read of `data/hidden/`.
- **Verification before any model call:** `glue.py` and the C3 conversion and rules both reproduce the entity
  resolution key and every fact and definition in the ground truth (`verify3.py`, with a negative control).

## Descriptive findings (TEST)

**Mean F1 per graph** (repeats averaged; A3 not run on the 567-node graph)

| Questions | Nodes | A3 | B3 | C3 | Questions per graph |
|---|---|---|---|---|---|
| cross-source | 22 | 0.287 | 1.000 | 1.000 | 15 |
| cross-source | 120 | 0.649 | 1.000 | 1.000 | 15 |
| cross-source | 567 | n/a | 1.000 | 1.000 | 14 |
| controls | 22 | 0.833 | 1.000 | 1.000 | 2 |
| controls | 120 | 1.000 | 1.000 | 1.000 | 3 |
| controls | 567 | n/a | 1.000 | 1.000 | 4 |
| **all cross-source** | | **0.468** | **1.000** | **1.000** | 44 |
| **all controls** | | **0.933** | **1.000** | **1.000** | 9 |

A3 scored lower on the 22-node graph than on the 120-node one. The planted noise is densest there: 4 stale ghosts,
4 region conflicts and 4 team conflicts among 19 records per export, against 6, 8 and 8 among 104 records on the
120-node graph. This explanation is my inference; it was not pre-registered and I did not test it.

**Why A3's answers were wrong** (60 wrong cross-source answers across the 3 repeats; exploratory)

| Wrong reading the answer matches | Count |
|---|---|
| ignored the monitoring export | 12 |
| kept stale records and trusted the non-authoritative source | 15 |
| trusted the non-authoritative source | 3 |
| none of the planted traps | 30 |

Half of A3's errors match a specific integration mistake. B3 and C3 made none.

**Reliability and cost** (all 3 repeats)

| | A3 | B3 | C3 |
|---|---|---|---|
| Records | 105 | 159 | 159 |
| Questions whose answer varied across repeats | 1 of 35 | 0 of 53 | 0 of 53 |
| Retries / timeouts | 0 / 0 | 0 / 0 | 0 / 0 |
| C3 valid SPARQL | | | 159/159, all first try |
| Hallucinated IDs | 6 | 0 | 0 |
| Median latency | 7.9 s | 5.6 s | 1.6 s |
| TEST cost (spent) | $0.82 | $0.89 | $0.51 |

**Authoring effort** (from [EFFORT3.md](EFFORT3.md); code lines, non-blank, excluding comments and docstrings)

| Artifact | Condition | Code lines | Fixes after the first verification run |
|---|---|---|---|
| `glue.py` | B3 | 83 | 0 |
| `to_rdf3.py` + `rules3.py` + `ontology3.ttl` | C3 | 52 + 102 + 47 = 201 | 0 |
| shared: `derive_tables.py`, `docs3.py` | both | 25, 51 | 0 |

C3 needed about 2.4 times the code of B3 for identical behaviour. B3 and C3 each got one documented clarity fix to
their docs during DEV (prompt version 2), logged with the evidence in `LOG3.md`; A3's prompt was not changed.

## H2 change test (exploratory, descriptive)

Two pre-specified changes, applied after TEST, one run each on the 53 TEST questions:

1. **Schema change:** the CMDB field `datacenter` is renamed to `site`.
2. **Definition change ("lost"):** a database is now lost if fewer than two of its footprint regions lie outside the
   failed region; any other node is still lost if its footprint contains only the failed region. This changes 29 of
   the 53 TEST answers, all cross-source.

With two changes and one run of each, n = 1 per change: these are case studies, not estimates.

**Phase (a): the unchanged artifacts against the changed export, scored against the new answer key**

| | Loud (no answer) | Silent (answer with F1 < 1) | Unaffected (F1 = 1) | Mean F1 |
|---|---|---|---|---|
| B3 | 28 | 18 | 7 | 0.221 |
| C3 | 53 | 0 | 0 | 0.000 |

- **C3 failed loudly everywhere.** The graph build (`to_rdf3.py`) raised `KeyError: 'datacenter'` on all three graphs,
  so no question reached the model.
- **B3's retries turned loud failures into silent ones.** All 53 first attempts failed with the same `KeyError` inside
  the glue. On the retry, 50 of 53 programs noticed the rename and 25 worked around it and answered: 21 mapped `site`
  back to `datacenter` and then used the glue, and 4 wrote their own code. The workarounds kept the old definition of
  "lost", so 18 of those 25 answers were wrong. The other 28 stayed loud.
- **The loudness comes from where the check runs, not from the ontology.** B3's glue already failed loudly; the model
  routed around it by rewriting the export (13 of the 25 answers loaded a rewritten copy of the file). A one-line
  schema check in B3's harness, run before the model is called the way C3's graph build is, would match C3's loudness;
  the same check inside `glue.py` would not, because the model can work around anything in its sandbox. This is my
  reading of the programs, not something I ran.
- **A definition change raises no error in either artifact.** Both computed the old "lost" without complaint; only the
  edit fixes it.

**Phase (b): minimal correct edits, then a re-run against the new key**

| | Code lines changed (`git diff --numstat`) | Mean F1 (53 questions) | Loud / silent / unaffected | Cost |
|---|---|---|---|---|
| B3 | `glue.py` +2/−2 (4) | **0.981** (cross-source 0.977, controls 1.000) | 0 / 1 / 52 | $0.30 |
| C3 | `to_rdf3.py` +1/−1, `rules3.py` +2/−0 (4); 6 with the `ontology3.ttl` comment +1/−1 | **1.000** | 0 / 0 / 53 | $0.18 |

- **Docs:** `docs3.py` +6/−2 shared by both conditions (the new "lost" sentence and "region (site)" in the rules) and
  +1/−1 for B3 only (the export schema). Fixes: 0 artifact fixes each, 1 documented docs fix (a line break inside a
  string literal, caught in review before any run).
- **B3's one miss** (`e3-100-17`, "is Payments Catalog Service down if dc-sin fails?") came from a program that matched
  the service by name substring instead of calling `g.resolve`; it is not caused by the edit, and B3 answered this
  question correctly in all three TEST repeats.
- **C3's rule change needed a new rule.** The original `lostIn` rule only considers regions in a node's own footprint;
  under the new definition a database with one footprint region is lost when *any* region fails, so a second rule over
  every region is required.
- **Deviation: the edits run are smaller than the ones I approved.** I reviewed and approved larger diffs (B3 `glue.py`
  +3/−1; C3 `rules3.py` +3/−1, with a guard excluding databases from the original rule). Before the re-run I found
  smaller edits with identical output on all three graphs (36, 274 and 1,842 lost, down and breached facts): one changed
  `return` line in B3, and no guard in C3, since the original rule's database facts are a subset of the new rule's.
  The pre-registration measures the minimal correct edit, so I chose to keep the smaller edits. The approved versions
  are kept as the alternative in [h2/approved/](h2/approved/).

**Reading H2 against its pre-registered prediction** (C3 needs fewer changed lines and breaks fewer questions): not
borne out. Both needed 4 lines of code; C3 broke more questions with its unchanged artifacts (53 against 46), but every
one of its breaks was loud, while 18 of B3's were silent.

## Interpretation

- **Entity resolution before the model is the effect.** Moving the reconciliation of two conflicting exports out of the
  model's prompt and into an artifact took cross-source accuracy from 0.468 to 1.000. Python and an ontology did it
  equally well.
- **The ontology added nothing to accuracy and cost more code.** C3 tied B3 exactly, with about 2.4 times the code.
- **On maintenance, the difference was in failure mode, not in effort.** Both needed the same small edit. The ontology's
  build step failed before any model call, which made its breakage loud; the glue failed inside a sandbox the model
  could patch, which made half of its breakage silent. That is a property of where validation runs, and a Python
  pipeline can have it too.

## Limitations

- **One model** (Haiku 4.5), temperature 0, 3 repeats; no variation across models.
- **Synthetic data:** three graphs from one generator, with noise planted by a program.
- **Artifacts authored by Claude Code.** B3's glue and C3's conversion, rules and ontology were written by Claude Code
  under my direction, with the same information and instructions for both, and reviewed by me.
- **Entity resolution solved for both conditions.** Both artifacts resolve every entity correctly by construction,
  verified against the hidden key. Imperfect resolution, the hard part in practice, was not tested, and it is why H1
  hit the ceiling.
- **A3 on two sizes only.** The A3 contrast covers the 22- and 120-node graphs (30 cross-source questions), as
  pre-registered; there is no A3 result on the 567-node graph.
- **The 22-node A3 explanation is an unregistered inference.**
- **H2 is two changes with one run each** (n = 1 per change), descriptive only, and the edits were made by the same
  process that wrote the artifacts.
- **Small numbers:** 44 cross-source and 9 control TEST questions; per-graph and per-trap results are exploratory.

## Cost

| | Spent |
|---|---|
| DEV pilot (rounds 0 and 1, C3 clarity check) | $0.68 |
| TEST (3 repeats) | $2.22 |
| H2 (phases a and b) | $1.17 |
| **Experiment 3 total** | **$4.07** |

Experiments 1-3 together: $7.99, under the $11 cap.

## Reproduce

```
python exp3/truth3.py                 # exports consistent with the hidden canonical graphs
python exp3/verify3.py                # glue and rules match the key and ground truth
python exp3/test_run3.py              # docs check, hidden-data guard, offline reproduction
python exp3/analyze3.py               # the pre-registered TEST analysis (all tables above)
python exp3/h2/make_h2.py             # the two H2 changes: changed CMDB exports and the new answer key
python exp3/h2/verify_h2.py           # edited artifacts reproduce the new ground truth
python exp3/h2/run_h2.py {unchanged,edited} --dry-run   # H2 harness (without --dry-run: model calls)
```

Model calls are cached, so re-running completed steps costs nothing.

## Source of truth

The frozen data files are the source of truth, not the generator. Experiment 1's generator, which `gen3.py` builds on,
iterates Python sets whose order changes between processes, so re-running it does not reproduce the same graph. The
canonical graphs in `data/hidden/graph_{20,100,500}.json` were generated once in step 1 and frozen; `gen3.py` derives
the two exports from them. Their hashes, and those of every other frozen file, are listed in `PREREG_EXP3.md` and
checked by `python tools/verify_frozen.py`.

## Files

| File | Role |
|---|---|
| `gen3.py` | derives the CMDB and monitoring exports and the entity-resolution key from the frozen canonical graphs |
| `truth3.py` | ground truth and the cross-export consistency check |
| `questions3.py` | questions, answer key and the DEV/TEST split (fixed by seed) |
| `glue.py` | B3's glue library |
| `to_rdf3.py`, `rules3.py`, `ontology3.ttl` | C3's conversion, rules and ontology |
| `derive_tables.py`, `mapping_tables.json` | team and region crosswalks, derived from the exports, shared by B3 and C3 |
| `docs3.py` | the documentation every condition receives |
| `run3.py` | harnesses for A3, B3 and C3, with the hidden-data guard |
| `score3.py`, `pilot3.py`, `analyze3.py` | scoring, the DEV pilot report, the pre-registered TEST analysis |
| `verify3.py`, `test_run3.py` | artifact verification against the key and ground truth; offline tests |
| `results/` | raw TEST and DEV responses, one file per condition and repeat |
| `h2/` | H2: `make_h2.py`, `run_h2.py`, `verify_h2.py`, the edited artifacts (`artifacts/`), the approved alternatives (`approved/`) and the results (`results/`) |
