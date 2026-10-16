# Experiment 2 log

Design decisions and every change to prompts, docs, questions or harness, with dates and reasons.
Experiment 1 is frozen at tag `exp1-final`; nothing under the repo root outside `exp2/` is modified.

## Conditions

| Label | Harness | Docs |
|---|---|---|
| **B+ (exp2-docs)** | exp1 `run_B.py` code path reused; only the doc text and data files change | exp1 `SCHEMA_DOC` + `DEFINITIONS` + `DATA_NOTE_JSON` |
| **B++** | same as B+ (exp2-docs) | B+ (exp2-docs) docs + `HELPERS_DOC`; `helpers.py` copied into the sandbox |
| **C2** | SPARQL over the scenario graph after rule materialization | `ontology2.ttl` (definitions as `rdfs:comment`, executable as rules) + `DATA_NOTE_RDF` |

B+ is labelled **exp2-docs** because its docs differ from exp1's B+: the definitions that exp1 put in question text
now live in its docs.

## Decisions

| Date | Decision | Reason |
|---|---|---|
| 2026-10-13 | Questions use neutral wording ("In this scenario, ..."); the failed region appears only in the data (scenario copy: `"failed": true` on the region node in JSON, `ex:<region> a ex:FailedRegion` in RDF). | No condition is told the failed region in words; every condition must read it from the data. |
| 2026-10-13 | DEV gets one "In this scenario, which region has failed?" check per size (level `check`, excluded from L4 scoring). | Confirms each condition can find the failure in the data before TEST. |
| 2026-10-13 | One-sentence data-format note added to every condition's docs: `DATA_NOTE_JSON` (B+, B++), `DATA_NOTE_RDF` (C2). Same content, contains no definitions. | Without it, B+/B++ docs would not mention the `failed` field at all. |
| 2026-10-13 | All definitions exp1 carried in question text moved to the docs (B+, B++) and to `ontology2.ttl` comments (C2), same wording except five region-neutral grammar changes, listed by `check_docs.py`. | Hypothesis: encoded definitions vs prose definitions. Verified by `python exp2/check_docs.py`. |
| 2026-10-13 | Most question kinds are parameterised by an entity (service, team, database, SLA) so texts are distinct; parameter-free kinds appear once per size. | With identical texts, conditions whose prompt does not change across scenarios (C2 always; B+/B++ within a size) would reuse one cached answer for many questions, inflating n. |

## Changes

| Date | Artifact | Change | Reason |
|---|---|---|---|
| 2026-10-13 | `rules.py` | added a final type-closure stratum | derived-class instances lacked superclass types |
| 2026-10-13 | `ontology2.ttl` | `rdfs:comment` texts aligned word for word with `DEFINITIONS`; `FailedRegion` comment reduced to "Asserted per failure scenario." (the data note carries the rest) | definitions must be identical in content across conditions; re-verified with `verify_defs.py` |
| 2026-10-13 | `questions2.py` | quotas raised to 23 per size over 13 kinds (fixed per kind, listed in `QUOTAS`), DEV = first 6 of a seeded shuffle per size, rest TEST: 69 L4 (18 DEV, 51 TEST) + 3 DEV checks; 53 distinct L4 texts | power: 29 TEST questions was too few for the primary test |
| 2026-10-13 | `run2.py` | B+ and B++ programs get one harness line before the model's code: `sys.path.insert(0, '.')` | `python -I` (exp1 sandbox) drops the script folder from `sys.path`, so `import helpers` failed; added to both B conditions so their environments stay identical |
| 2026-10-13 | `run2.py` | B+ / B++ / C2 reuse exp1's prompt template, code extraction, retry loop, sandbox and SPARQL runner; only the data files per question differ (scenario copy or base graph; materialized graph for C2) | exp1 modules cannot be edited; `test_run2.py` checks every path reproduces the answer key |
| 2026-10-13 | `score2.py` | primary test = cluster bootstrap over distinct question texts; secondary = exp1's per-question paired bootstrap | identical prompts (C2 across sizes and scenarios; B+/B++ within a size) make questions with the same text correlated |
| 2026-10-13 | `run2.py` | 120 s API client timeout for all three conditions (`llm._client` set from `run2.py`; exp1's `llm.py` unchanged) | DEV: one B+ call hung for 42 min under the SDK default (10 min + retries); timeout is not part of the cache key |
| 2026-10-13 | `docs.py` (B++ prompt v2) | `HELPERS_DOC` raw-data line now says `g.region[x]`, `g.owner[x]`, `g.sla[x]` are dicts (index, do not call); `g.nodes` / `g.edges` shapes spelled out | DEV v1: all 3 B++ retries were `TypeError: 'dict' object is not callable`; v2 rerun: 0 retries, F1 unchanged (1.00). v1 results kept in `results/dev_bpp_v1/` |
| 2026-10-13 | review | B+ and C2 prompts checked for similar interface ambiguity: B+ has no API (JSON shape, sample records, data note); C2 names every class/property in the ontology, plus prefix and IRI rules. DEV: 0 errored attempts in either. No change. | requested review |
| 2026-10-13 | `score2.py` | report median latency instead of mean | one hung call dominated the mean |

Tuning rounds used in Experiment 2: 1 of 3 (B++ prompt v2). Prompt versions: B+ (exp2-docs) 1, B++ 2, C2 1.

## Post-run entries (after the TEST run)

| Date | Entry |
|---|---|
| 2026-10-16 | **TEST run.** B+ (exp2-docs), then B++, then C2, once each, sequentially, with the frozen code. All 51 TEST questions answered in every condition; no crash, no missing question, no rerun, no timeout. Spend $0.56. |
| 2026-10-16 | **Hash check before the first call: line endings only.** Every frozen file on disk matched `PREREG_EXP2.md`. Reading the same files from Git gave 11 different hashes (`ontology2.ttl`, `docs.py`, `questions2.py`, `check_docs.py`, `data/questions.json`, `data/answers.json`, `data/graph_{20,100,500}.json`, and exp1's `truth.py` and `gen.py`). The cause is line endings: these files were last written by Python on Windows (CRLF on disk), and Git stores them with LF (`core.autocrlf=true`). After stripping carriage returns, each on-disk file hashes exactly to its committed blob, so the content is identical. The PREREG hashes are hashes of the CRLF working-tree bytes. |
| 2026-10-16 | **B+ error classification override.** The flag-discovery vs logic split of wrong answers was exploratory and **not pre-registered**. The automatic rule labelled `e2-20-L4-18` (B+) a flag-discovery failure because its empty answer equals the no-failure answer. Reading the program shows it found the failed region correctly (`node.get('failed')`). Both B+ misses (`e2-20-L4-18`, `e2-100-L4-15`) are the same logic error: "primary" applied in the inverse direction (a node that *has* replicas treated as non-primary). Corrected counts: **0 flag-discovery failures in every condition**; logic errors B+ 2, B++ 0, C2 0. |
