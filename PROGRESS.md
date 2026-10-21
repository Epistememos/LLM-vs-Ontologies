# Progress log

Every commit and tag in this repository, in order (the latest entry is the commit that adds it, so it is listed by message: a commit cannot contain its own hash), with the decisions behind it and why I made them. Times are
commit times (local). Each experiment's own log (`exp1/PROMPT_LOG.md`, `exp2/LOG.md`, `exp3/LOG3.md`) has the
line-level detail.

## Summary

| # | Date | Commit / tag | What |
|---|---|---|---|
| 1 | 2026-10-08 14:53 | `053ce74` | Experiment 1: benchmark, harnesses, DEV round 1 |
| 2 | 2026-10-08 15:15 | `7360045` | Experiment 1: prompts frozen, pre-registration |
| 3 | 2026-10-08 21:39 | `f555646` | Experiment 1: TEST results |
| 4 | 2026-10-08 21:44 | `75a4415` | Experiment 1: plots and write-up |
| 5 | 2026-10-09 15:30 | `3dc4eb1` | Experiment 1: README wording |
| – | 2026-10-13 12:46 | tag `exp1-final` | Experiment 1 frozen |
| 6 | 2026-10-13 14:43 | `3a202c2` | Experiment 2: definitions, harness, DEV, pre-registration |
| 7 | 2026-10-16 17:38 | `735a830` | Research notebook |
| 8 | 2026-10-16 18:23 | `961adae` | Experiment 2: TEST results and post-run log |
| 9 | 2026-10-16 18:25 | `9a54132` | Experiment 2 write-up, Experiment 1 addendum |
| – | 2026-10-17 13:40 | tag `exp2-final` | Experiment 2 frozen |
| 10 | 2026-10-17 17:26 | `b8e36a7` | Experiment 3 step 1: data, ground truth, questions, pre-registration draft |
| 11 | 2026-10-19 11:16 | `7ec1ef6` | Repository restructure and project README |
| 12 | 2026-10-19 11:36 | `a8c4cd6` | Progress log |
| 13 | 2026-10-19 15:41 | `4ed7fd4` | Experiment 3 step 2: B3 glue, C3 ontology and rules, guard, verification |
| 14 | 2026-10-20 10:25 | `a756e25` | Experiment 3: DEV pilot, clarity fix, freeze for TEST |
| 15 | 2026-10-20 11:18 | `ce06e5f` | Project README: plain language, Palantir section |
| 16 | 2026-10-20 12:21 | `f7cab91` | Project README: a critical Palantir section |
| 17 | 2026-10-21 11:40 | `1c24a5e` | Experiment 3: TEST results |
| 18 | 2026-10-21 16:53 | `7062d91` | Experiment 3: H2 change test |
| 19 | 2026-10-21 | "Exp3 write-up" | Experiment 3 write-up, notebook, project README |

---

## Experiment 1

### 1. `053ce74` Benchmark harness and DEV round 1 (2026-10-08 14:53)

**What changed:** the whole Experiment 1 benchmark: the graph generator, NetworkX ground truth, question generator,
scorer and tests, the model client with a disk cache, the four condition harnesses (A, B, B+, C), the Python and
SPARQL sandbox, the RDFS/OWL schema, and the first DEV results.

**Decisions and why:**
- **Thesis and design.** I set out to test "LLMs grounded in an ontology reason better about system topology than
  LLMs alone", and I wanted a result that would be credible, so the design isolates the ontology from two confounds:
  tool use and schema documentation. That is why there are four conditions: LLM alone (A), Python over raw JSON (B),
  Python plus the same schema documentation C gets (B+), and SPARQL over an ontology (C). B+ separates "knowing the
  schema" from "having a formal ontology". I skipped RAG.
- **Ground truth independent of every harness.** Answers come from NetworkX only, never from a harness or from rdflib,
  so no condition can grade itself.
- **Precise region-failure definition, given to every condition.** I defined footprint, lost and down exactly and put
  the definition in the question text for all conditions: if only C's schema encoded it, the test would measure who
  was told the rule, not who reasons better. I also planted cases that tell the variants apart (a service saved by a
  replica outside the failed region, a dependency lost deep in a chain, a database lost while its dependents live
  elsewhere), and fixed the direction of `replicaOf` with a symmetric replica group.
- **Same budget and format for everyone.** One retry, on errors only, never on a legitimately empty result (an empty
  list is often correct, and retrying on it would bias towards over-generating); A gets no retry; same token limit and
  answer format. C returns its query result directly and declares the answer type, so mapping is deterministic.
- **Out-of-schema questions (L5)** reported separately and excluded from the thesis test.
- **Best-effort sandbox** with a temp directory holding only the graph file: it guards against accidents from
  model-written code, not adversaries.
- **Same inputs for A, B and B+:** B and B+ get a few sample records and the file path, never the full graph, because
  the point is that code reads it.
- **Cost control:** prompt caching on the graph prefix for A, compact serialization, and a cost estimate before any run.
- **Generator fixes before any question existed.** The first graphs made region-failure answers "every SLA", which
  carries no signal; I raised replication of hub dependencies and added region locality so answers vary.
- **Small-graph and primary-only questions.** At 24 nodes every failure breached every SLA, so I asked about down
  services there; questions consider primary nodes only.
- **DEV-driven fixes, applied to every condition equally:** `region_down` limited to primary services (replicas of a
  down service counted as "up", which tested rule-following rather than topology); a parser fix for C when it wrapped
  its type declaration in a code fence; sandbox timeout raised from 30 s to 60 s with timeouts reported separately;
  `max_tokens` raised from 4096 to 8192 because A was cut off on the largest graph; the "primary" clause reworded to
  state the edge direction because two conditions read it backwards. Tuning was capped at 3 rounds, mechanical or
  clarity fixes only, and only 1 was used.
- **Commit identity.** I re-authored this first commit with my own email and force-pushed it (the repository had one
  commit), because the earlier email attributed the commit to the wrong GitHub account.

### 2. `7360045` Freeze prompts, add PREREG (2026-10-08 15:15)

**What changed:** DEV round 2 results and `PREREG.md`.

**Decisions and why:** I wrote the refutation criteria before any TEST run, so the result could not be bent after
the fact: the thesis is **not supported** if the C − B+ confidence interval on levels 2-4 includes zero, and if B+
matches C the conclusion is "schema knowledge plus code helps, a formal ontology is not needed". L1 and L5 were
excluded from the test, timeouts got a sensitivity check, every frozen file got a hash, and I committed to reporting
the result even if it went against the thesis. I reviewed the TEST cost estimate before giving the go.

### 3. `f555646` Add TEST results (2026-10-08 21:39)

**What changed:** TEST results for all four conditions.

**Decisions and why:** I ran TEST once, conditions in sequence, with no code or prompt changes, and a rule to re-run
only missing questions if anything crashed (nothing did). I ran the pre-registered analysis exactly as written and
looked at the numbers before any write-up. Result: C − B+ = −0.005 [−0.055, +0.055], **not supported**.

### 4. `75a4415` Add plots and README (2026-10-08 21:44)

**What changed:** `plots.py`, two figures, and the Experiment 1 write-up.

**Decisions and why:** I wanted the negative primary result reported plainly and first, subgroup results labelled
exploratory, a failure analysis of C's 9 wrong region-failure answers, and a full limitations section (synthetic data,
circularity risk, one model, no reasoner, ontology construction cost not measured, best-effort sandbox, the changes
made on DEV, small per-cell counts, shared question wording). No further tuning or re-runs.

### 5. `3dc4eb1` README wording (2026-10-09 15:30)

**What changed:** the model is described neutrally in the README.

**Why:** I wanted no product branding in the write-up beyond a neutral model description.

### Tag `exp1-final` (2026-10-13 12:46)

Experiment 1 frozen at `3dc4eb1`: its files, results and hashes are not modified afterwards.

---

## Between the experiments: the diagnosis

Looking back at Experiment 1, I concluded the ontology was not leveraging any real object structure: it was a thin
typed graph with no reasoner, and the concepts the hard questions depend on lived only in prose in the question text.
So the tie partly reflected how little the ontology was asked to do. That motivated Experiment 2. I worked on it on my
own branch, `ontology-object-structure`.

## Experiment 2

### 6. `3a202c2` Exp2: definitions, harness, DEV results, PREREG (2026-10-13 14:43)

**What changed:** Experiment 2 in `exp2/`: new graphs, executable definitions (Python helpers and ontology rules),
the three harnesses, questions, DEV results and `PREREG_EXP2.md`.

**Decisions and why:**
- **Hypothesis:** ontology-encoded executable definitions (footprint, lost, down, primary) beat the same definitions
  written as prose on region-failure and constraint questions. Conditions: B+ (prose docs), B++ (prose plus Python
  helpers), C2 (an ontology whose classes are materialized by rules before querying).
- **Definitions out of the question text** and into each condition's docs or ontology, so the comparison is about how
  the definitions are given, not whether they are given. I had both the helpers and the rules verified against ground
  truth on every node and scenario before any model saw a question.
- **Failure only in the data.** Questions use neutral wording ("In this scenario, ..."); the failed region is asserted
  in a copy of the graph, plus a few DEV-only "which region failed?" checks. Every condition gets the same
  one-sentence data-format note with no definitions in it. B+ is labelled **exp2-docs** because it is not the same B+
  as in Experiment 1, and I had a check confirm the docs carry every definition the question text used to carry.
- **Power and correlation.** I raised the quotas to about 22 questions per size with distinct entities and kinds,
  fixed per kind before any run, and the DEV/TEST split fixed by seed. Because identical question texts get identical
  prompts, I made a cluster bootstrap by question text the primary test and the per-question CI secondary, with a
  pre-registered rule for when they disagree.
- **Two fixes after DEV, logged:** a 120 s API timeout for all conditions (one call had hung for 42 minutes), and a
  docs fix for B++ stating that `region`, `owner` and `sla` are dictionaries (it caused 3 retries). I had B+ and C2
  checked for similar ambiguity; none found. I ran DEV and reviewed it before freezing.
- **Pre-registered prediction:** C2 and B++ tie. A C2 win over B+ together with that tie would be evidence for encoded
  definitions over prose, in either form, not for ontologies over code. I flagged the ceiling risk in advance.

### 7. `735a830` Add research notebook (2026-10-16 17:38)

**What changed:** `notebook/blast_radius.ipynb`.

**Why:** I wanted one notebook covering Experiment 1 and the transition to Experiment 2, with results shown as
diagrams so the project reads as a research project. Every number in it is computed from the committed results.

### 8. `961adae` Exp2: TEST results and post-run log (2026-10-16 18:23)

**What changed:** Experiment 2 TEST results and scores, post-run log entries, and a corrected line count.

**Decisions and why:**
- Before the first call I had the frozen hashes verified and confirmed the B++ fix and the timeout were in the
  committed state, not just the working tree. TEST ran once, in sequence, with no changes.
- I asked for flag-discovery failures to be separated from logic errors. Reading the programs showed both B+ misses
  were the same "primary" inversion, not a failure to find the failed region, so I logged an override of the
  automatic label and noted that this split was exploratory.
- I logged that the hash differences between disk and Git were line endings only (Windows CRLF on disk, LF in Git).
- I corrected the rules line count (72, not 63): the extra lines are a precompute block added before freezing.
- Result: C2 − B+ = +0.026 [0.000, +0.071], **not supported**; C2 − B++ = 0.000, the predicted tie.

### 9. `9a54132` Exp2 write-up and Exp1 addendum (2026-10-16 18:25)

**What changed:** `exp2/README.md` and an addendum to Experiment 1.

**Decisions and why:** I wanted the write-up to lead with the pre-registered results exactly as measured, then the
descriptive findings, an interpretation (executable definitions removed B+'s only error type, the ontology added
nothing over equivalent Python, and the ceiling effect I flagged came true), the limitations, and a possible
Experiment 3, not run. For Experiment 1 I added a separate, dated addendum rather than editing its frozen files: its
ontology was a thin typed graph whose content fitted entirely in the prose schema B+ received. I then merged my
branch into `main`.

### Tag `exp2-final` (2026-10-17 13:40)

Experiment 2 frozen at `9a54132`.

---

## Experiment 3

### 10. `b8e36a7` Exp3 step 1: generator, truth, questions, PREREG draft (2026-10-17 17:26)

**What changed:** `exp3/`: a generator that derives two conflicting exports from one hidden canonical graph, ground
truth with a consistency check, the question set with its DEV/TEST split, a draft pre-registration, and a
standing-rules file at the root.

**Decisions and why:**
- **Why a third experiment:** Experiments 1 and 2 found no advantage for an ontology over documented schema and code
  on one clean source with static definitions. I wanted to test the settings where ontologies are claimed to pay off:
  several sources with conflicting identifiers (H1, accuracy), and definitions that change over time (H2,
  maintenance). Either may come out null, and all results get reported.
- **Data:** two exports (CMDB-style and monitoring-style) with different IDs, field names and aliases for the same
  services, plus a fixed number of stale and contradictory records. The entity-resolution key lives in a separate
  file no condition ever sees.
- **Conditions:** B3 (Python glue) and C3 (ontology and rules) get the same mappings, the same information and the same
  effort, and resolve entities completely. A3 (LLM alone) runs on the two smaller graphs only. I log line counts, fix
  counts and my own review hours for both artifacts.
- **Headroom controlled in the generator, not by looking at results:** a pilot on DEV with a pre-registered ceiling
  rule (no condition above 0.90 mean F1, otherwise raise the difficulty knobs and re-pilot, at most 2 rounds).
- **Repeats:** 3 per question at temperature 0, bypassing the cache, stored separately, with answer variation reported.
- **H2 change test, fixed in advance:** rename one field and modify the "lost" rule; first measure silent vs loud
  breakage with unchanged artifacts, then apply the minimal correct edit, count lines changed and re-score. H2 is
  exploratory and descriptive.
- **Budget:** a measured estimate with a 1.6× correction after DEV, and a pre-registered cut if TEST would exceed
  about $6.
- **Same rules for both:** the resolution rule for contradictory records and the statement about stale records must
  appear identically in the docs both conditions receive.
- **Seeds:** the first seed at or after each starting value that the unchanged generator accepts (3021 instead of
  3020 for the smallest graph), chosen before looking at any data.
- **Before committing** I checked that nothing frozen had changed and that no API key was in the repository, and pushed
  the `exp2-final` tag. I chose to commit the hidden folder (canonical graphs, resolution keys, answer key) along with
  the rest.

### 11. `7ec1ef6` Restructure repo (2026-10-19 11:16)

**What changed:** Experiment 1 moved into `exp1/`, a new project overview `README.md` at the root, `pyproject.toml`,
and `tools/`.

**Decisions and why:**
- I wanted the root README to give an accurate, current picture of all the work, and the repository files structured
  cleanly. I chose to turn the root README into a project overview and keep Experiment 1's write-up word for word as
  `exp1/README.md`.
- Every Experiment 1 file moved with no content change (pure renames). Experiment 2's frozen code still imports
  Experiment 1's modules unchanged through `pip install -e .`, and one frozen check that read an old path runs through
  a small wrapper rather than being edited.
- Checks before committing: every frozen hash unchanged (a new checker accepts either line-ending form, since Git on
  Windows rewrites them on checkout), all offline test suites pass, and both experiments re-score to exactly their
  committed numbers. I logged the move as the one exception to the freeze rule.

### 12. `a8c4cd6` Add progress log and documentation updates (2026-10-19 11:36)

**What changed:** this file, plus small documentation edits.

**Why:** I wanted one file showing every change and commit, with when it happened and why I made each decision.

---

### 13. `4ed7fd4` Exp3 step 2: B3 glue, C3 ontology and rules, guard, verification (2026-10-19 15:41)

**What changed:** B3's glue library (`glue.py`), C3's conversion, rules and ontology (`to_rdf3.py`, `rules3.py`,
`ontology3.ttl`), the shared crosswalks and docs, the harness with the hidden-data guard, verification and offline
tests.

**Decisions and why:**
- **Failure is region-parametric in both artifacts:** C3 materializes lost, down and breached for every region, and
  B3's methods take the datacenter as an argument, so neither harness has to learn the failed region from the hidden
  answer key.
- **One shared crosswalk file**, derived from the exports by majority vote over non-stale records, so B3 and C3 use the
  same mappings by construction.
- **A hidden-data guard** (an audit hook refusing any read of `data/hidden/`) in the harness, every sandbox program and
  every SPARQL runner.
- Both artifacts matched the key and the ground truth on the first verification run: 0 fixes each. B3 is 83 code
  lines, C3 201.

### 14. `a756e25` Exp3: DEV pilot, clarity fix, freeze for TEST (2026-10-20 10:25)

**What changed:** the DEV pilot (two rounds), a generator reproducibility fix, one clarity fix each for B3 and C3, and
the freeze of every Experiment 3 file.

**Decisions and why:**
- **Ceiling accepted.** B3 and C3 were above the pre-registered 0.90 ceiling in both rounds; raising the knobs could not
  move them, because both artifacts resolve the noise before the model sees it. I ended the difficulty rule after
  round 1 and recorded H1 as an expected null on ceiling grounds before TEST.
- **Frozen canonical graphs.** Re-running the generator changed one graph (Python set order), so I restored the step-1
  graphs byte for byte and made the frozen files the source of truth.
- **Clarity fix 1 of 3 for C3 and B3:** C3's only two DEV misses looked up teams and SLAs by name; I added the same
  information to both conditions' docs.
- **No cut needed:** the measured TEST estimate was $2.94 with the 1.6× correction.

### 15-16. `ce06e5f`, `f7cab91` Project README (2026-10-20 11:18 and 12:21)

**What changed:** the root README, rewritten for readers with little technical background, with a section on what the
findings suggest about operational ontologies such as Palantir's (`ce06e5f`); then that section rewritten to be
critical rather than flattering (`f7cab91`).

**Why:** I wanted the project readable without a technical background, and the Palantir section critical where the
evidence cuts against the approach, not only where it supports it.

### 17. `1c24a5e` Exp3 TEST results (2026-10-21 11:40)

**What changed:** TEST results for A3, B3 and C3 (3 repeats), and `analyze3.py`, written after the freeze and before
any TEST result existed.

**Decisions and why:** TEST ran once with no changes. The budget cap for Experiments 1-3 was raised to about $11
beforehand (approved 2026-10-20). Result: C3 − B3 = 0.000 [0.000, 0.000], **not supported**, both perfect; B3 − A3 =
C3 − A3 = +0.532 [+0.377, +0.687] on the two smaller graphs. TEST spend $2.22.

### 18. `7062d91` Exp3 H2 change test (2026-10-21 16:53)

**What changed:** the two pre-registered changes (a renamed CMDB field and a new "lost" definition), the H2 harness,
the edited artifacts, and the results of both phases.

**Decisions and why:**
- **Phase (a), unchanged artifacts:** B3 loud 28, silent 18, unaffected 7; C3 loud 53 (its graph build failed). The
  model's retries in B3 worked around the rename and kept the old definition, turning loud failures into silent ones.
- **Minimal edits, smaller than the ones I approved.** Before the re-run I found smaller edits with identical output on
  all three graphs (B3 +2/−2 instead of +3/−1; C3 `rules3.py` +2/−0 instead of +3/−1). The pre-registration measures
  the minimal edit, so I kept them and logged the deviation; the approved versions are kept as the alternative.
- **Phase (b):** B3 0.981, C3 1.000, with 4 changed code lines each. H2 spend $1.17.

### 19. Exp3 write-up (2026-10-21)

**What changed:** `exp3/README.md`, `exp3/EFFORT3.md`, the research notebook (Experiment 3 added), the project README
and this file, plus one corrected total in `exp3/LOG3.md` (C3's H2 code lines are 4, not 5).

**Decisions and why:** I wanted the write-up to lead with the pre-registered H1 result, then the A3 contrast, then H2
labelled exploratory, with the deviation to the minimal edits and every limitation stated, including that the
artifacts were authored by Claude Code under my direction.

---

## Current status

All three experiments are complete. Total API spend: $7.99 (Experiment 1 $3.08, Experiment 2 $0.84, Experiment 3
$4.07).
