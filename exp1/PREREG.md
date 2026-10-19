# Pre-registration: Blast Radius TEST run

Written 2026-10-08, after DEV tuning and **before any TEST question has been sent to a model**.
Prompts, questions, answers, harness and scorer are frozen in the commit that adds this file.
Nothing listed here changes after the TEST run starts. Results are reported in full whether or not
they support the thesis.

## Thesis

"LLMs grounded in an ontology are better at reasoning about system topology than LLMs alone."

## Conditions (same model, same graphs, same questions)

| | Gets | Tools | Retries |
|---|---|---|---|
| A | full graph serialized in the prompt, no schema doc | none | 0 |
| B | file name, JSON shape, 2 sample records per node type and relation | Python sandbox over raw JSON | 1, on error only |
| B+ | B + prose schema documentation (`SCHEMA_DOC`) | Python sandbox over raw JSON | 1, on error only |
| C | prose schema documentation + `schema.ttl`; never the data | one SPARQL query, executed by rdflib | 1, on error only |

- Model `claude-haiku-4-5-20251001`, temperature 0, `max_tokens` 8192 for every call.
- Retry trigger, identical for B, B+ and C: exception, timeout, missing code block, parse failure, or no
  parseable/mappable answer. A legitimately empty result is never retried.
- Sandbox and query timeout: 60 s.
- Prompt versions: A 1, B 1, B+ 1, C 1. No condition-specific prompt tuning was done. One tuning round
  applied to all conditions equally (max_tokens 4096 -> 8192; explicit edge direction in the "primary"
  clause); see `PROMPT_LOG.md`. 2 of the 3 allowed rounds were unused.

## Data

- TEST split: 91 questions over the 20-, 100- and 500-node graphs (actual node counts 24, 117, 553).
- Per size: L1 7, L2 7, L3 6-7, L4 6-7, L5 3. L2-L4 total: **61 questions** (20-node 19, 100-node 21, 500-node 21).
- Ground truth: `truth.py` (NetworkX over the JSON), independent of rdflib and every harness.

## Primary analysis (the thesis test)

- Metric: per-question F1 (set precision/recall; exact match for bool and number).
- Population: TEST questions at levels **L2, L3, L4**, pooled over all three graph sizes (n = 61).
- Statistic: mean paired difference F1(C) - F1(B+), with a 95% percentile bootstrap CI
  (10,000 resamples of questions, numpy seed 0), as implemented in `score.paired_bootstrap`.
- Decision rules:
  - **Thesis supported** only if the CI lower bound is above 0.
  - **Thesis not supported** if the CI includes 0. If B+ also matches or beats C, the conclusion is
    "schema knowledge + code helps; a formal ontology is not needed".
  - **Thesis contradicted** if the CI upper bound is below 0.

## Secondary analyses (reported, not used for the decision)

- C - A and C - B on L2-L4, same bootstrap.
- All differences per graph size and per level.
- F1 vs graph size per condition, one panel per level (`plots.py`).
- Hallucination rate (returned IDs not in the graph), parse rate, answer-type agreement.
- C: SPARQL validity rate, first-try validity, retry rate, and failure type
  (invalid query / valid but wrong / correct).
- Tokens, cost and wall-clock latency per question.

## Excluded from the thesis test

- **L1 (lookup):** reported only; it does not test topology reasoning.
- **L5 (out-of-schema: longest chain, shortest path length, number of distinct paths):** reported separately.
  These need path-length arithmetic that SPARQL property paths do not express directly. They are hard for C
  but not impossible: on DEV, C answered some with bounded unrolling (a UNION of fixed-length paths). L5 is
  expected to favour B and B+.

## Timeouts

- Timeout counts are reported per condition, separately from accuracy.
- In the primary analysis a timed-out question is scored as it ended (F1 0 if no answer survived the retry).
- Sensitivity check: the primary analysis is repeated excluding every question on which any condition timed
  out. If the two disagree on the decision, both are reported and the machine-speed caveat is stated.

## Run protocol

- Each condition runs once on TEST at all sizes; results are scored once by `score.py test`.
- No prompt, question, harness or scorer change after the TEST run starts.
- If a run crashes (network, API outage), only the missing questions are re-run with the same frozen code;
  completed calls come from the disk cache. Any such event is recorded in the README.
- Estimated cost ~$1.8 (from DEV per-question actuals); the run stops and asks before exceeding $5.

## What was known before TEST (DEV, 40 questions, 25 at L2-L4)

| | A | B | B+ | C |
|---|---|---|---|---|
| DEV F1, L2-L4 | 0.80 | 0.79 | 0.96 | 0.98 |

DEV paired differences on L2-L4: C - A +0.18 [+0.06, +0.32]; C - B +0.19 [+0.04, +0.36];
C - B+ +0.02 [-0.04, +0.11]. On DEV the C - B+ interval includes zero. This was known when this file
was written; the decision rule above was set by the project brief before any run.

## Known limitations (to be repeated in the README)

- Synthetic graphs from one generator; the question templates and the ontology were written by the same
  author, so there is a circularity risk (the ontology fits the questions by construction).
- One model (Haiku 4.5), one run at temperature 0; no variance across seeds or models.
- The cost of building the ontology is not measured.
- C cannot post-process awkwardly shaped results; A and B can.
- The sandbox is best-effort (no OS-level isolation); it guards against accidents, not adversaries.

## Frozen file hashes (sha256, first 16 hex chars)

```
5071ace7c1ccaa04 common.py
6e3d94b1d34ced69 llm.py
f226df5c6495747a sandbox.py
a0209cbced2c6a32 run_A.py
8f7208e43dfce33b run_B.py
f2065c680f3f7db4 run_Bplus.py
6902a017750e70ac run_C.py
a3627ccf74ddfc73 schema.ttl
aac18966cf1a293b score.py
7166a6d40bf28e79 questions.py
585c8cfd4bba8bc4 truth.py
e9efe0998887de8a gen.py
36bc09ca84e1b70e data/questions.json
d42baf4fdafc9a45 data/answers.json
9536ccb808c2b177 data/graph_20.json
89df8a019f84ebe4 data/graph_100.json
9d225dfee9a28ad3 data/graph_500.json
4fe0ef5537711a60 data/graph_20.ttl
91c6cd5377257a8e data/graph_100.ttl
2dd68ab7bd5b0413 data/graph_500.ttl
```
