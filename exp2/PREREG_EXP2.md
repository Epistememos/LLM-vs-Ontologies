# Pre-registration: Experiment 2 TEST run

Written 2026-10-13, after DEV and **before any TEST question has been sent to a model**. Prompts, questions,
answers, definitions, rules, helpers, harness and scorer are frozen in the commit that adds this file.
Nothing listed here changes after the TEST run starts. Results are reported in full whether or not they
support the hypothesis. Experiment 1 is frozen at tag `exp1-final` and is not modified.

## Hypothesis

> Ontology-encoded executable definitions (footprint, lost, down, primary) outperform prose-described
> definitions on region-failure and constraint questions.

This follows Experiment 1's finding that its ontology carried no executable structure: the hard concepts lived
only in question text, and C failed 9 of 12 region-failure questions while writing them by hand in SPARQL.

## Conditions (same model, same graphs, same questions)

| Label | Definitions available as | Tools | Prompt version |
|---|---|---|---|
| **B+ (exp2-docs)** | prose in the docs (`SCHEMA_DOC` + `DEFINITIONS`) | Python sandbox over raw JSON | 1 |
| **B++** | prose (same as B+) + `helpers.py`, executable Python, documented in the prompt | Python sandbox over raw JSON | 2 |
| **C2** | `ontology2.ttl`: rule-defined classes and properties, materialized by SPARQL CONSTRUCT rules to a fixpoint before querying; definitions as `rdfs:comment` | one SPARQL query over the materialized graph | 1 |

- Model: Anthropic's Haiku 4.5 (2025-10-01 snapshot; model ID set in `llm.py`), temperature 0, `max_tokens` 8192, sandbox and query timeout 60 s:
  identical to Experiment 1 (reused, unmodified `llm.py`, `sandbox.py`, `common.py`).
- API client timeout 120 s for every condition.
- Retry budget identical for all three: one retry, on error only (exception, timeout, parse failure, unmappable
  answer); a legitimately empty result is never retried.
- Questions carry **no definitions**. The definitions exp1 put in question text live only in the B+/B++ docs and
  in the C2 ontology, with the same wording (checked by `check_docs.py`). Each condition gets a one-sentence,
  definition-free data-format note saying how the failed region is marked.
- `helpers.py` and the C2 rules both reproduce `truth.py` exactly for every concept, node and scenario
  (`verify_defs.py`, with a negative control). Authoring effort is in `EFFORT.md`.

## Data and questions

- New seeds (2020, 2100, 2500) on exp1's generator configurations: 23, 121 and 559 nodes. 10 failure scenarios
  (2, 3, 5 regions). A scenario copy asserts the failed region as data; the question text never names it.
- 23 L4 questions per size over 13 kinds, quotas fixed per kind (`questions2.py: QUOTAS`), entities distinct
  within a kind. DEV/TEST split by seed: the first 6 of a seeded shuffle per size are DEV.
- **TEST: 51 L4 questions (17 per size) in 45 distinct question texts (clusters).** 34 are yes/no, 14 sets,
  3 numbers.
- DEV also has 3 "which region has failed?" checks (level `check`), not used in any test.
- Ground truth from `truth.py` (exp1's NetworkX code, unmodified) on the exp2 graphs.

## Primary analysis

- Metric: per-question F1 (set precision/recall; exact match for bool and number).
- Population: TEST L4 questions, all sizes pooled (n = 51, 45 clusters).
- Statistic: mean paired difference **F1(C2) − F1(B+)**.
- **Primary CI: cluster bootstrap over question texts.** Resample the 45 distinct texts with replacement; every
  question with a drawn text enters; statistic recomputed on the drawn questions. 10,000 resamples, numpy seed 0,
  95% percentile interval (`score2.cluster_bootstrap`). Clustering is needed because questions with the same text
  get the same prompt: for C2 across sizes and scenarios, for B+/B++ within a size, so their answers are
  correlated.
- **Secondary CI: per-question bootstrap**, Experiment 1's method (`score.paired_bootstrap`; 10,000 resamples,
  seed 0), questions resampled independently.
- Decision rules, applied to the **cluster** CI:
  - **Hypothesis supported** if the lower bound is above 0.
  - **Not supported** if the CI includes 0.
  - **Contradicted** if the upper bound is below 0.
- **If the two CIs disagree** (one excludes 0 and the other does not): the decision follows the cluster CI. Both
  intervals are reported, and the result is described as sensitive to the assumption that same-text questions
  are correlated. It is not reported as a clean positive or negative.

## Secondary analysis: C2 − B++

Same statistic and both CIs, on the same 51 questions.

- **Prediction: C2 and B++ tie** (CI includes 0, point estimate near 0). Both hand the model executable
  definitions; on DEV both scored 1.00 on L4 (ceiling).
- Interpretation fixed in advance:
  - **tie**: encoded, executable definitions help, and the ontology form adds nothing over equivalent code;
  - **C2 above B++**: the ontology form adds value beyond equivalent Python helpers;
  - **C2 below B++**: equivalent code beats the ontology form.
- A C2 win over B+ together with a C2/B++ tie is **not** evidence for ontologies over code; it is evidence for
  encoded definitions over prose, in either form.

## Reported but not used for any decision

- C2 − B+ and C2 − B++ per graph size and per question kind (exploratory, 5-6 questions per cell).
- Hallucination rate, parse rate, retry rate, C2 SPARQL validity (first try and after retry).
- Timeout counts per condition. If any condition times out on TEST, the primary analysis is repeated without
  those questions as a sensitivity check.
- Tokens, cost, and **median** latency per question (one DEV call hung for 42 minutes; the mean is not robust).
- Authoring effort for `helpers.py` and the rules (`EFFORT.md`: line and fix counts; wall-clock time is not a
  meaningful human-effort measure here and is not compared).

## Run protocol

- Each condition runs once on TEST, all sizes: B+ (exp2-docs), then B++, then C2. Scored once by
  `python exp2/score2.py test`.
- No change to prompts, docs, questions, rules, helpers, harness or scorer after TEST starts.
- If a run crashes, only the missing questions are re-run with the frozen code (completed calls come from the
  disk cache); any such event is recorded in `LOG.md`.
- Cost estimate: $0.56 from DEV per-question actuals; $1.11 from the dry-run estimator with the 1.6×
  correction. The run stops and asks before exceeding $5.

## What was known before TEST (DEV: 18 L4 questions, 14 clusters)

| | B+ (exp2-docs) | B++ (v2) | C2 |
|---|---|---|---|
| DEV F1, L4 | 0.889 | 1.000 | 1.000 |

C2 − B+: cluster +0.111 [0.000, +0.238]; per-question +0.111 [0.000, +0.278]. C2 − B++: 0.000 [0.000, 0.000].
All three found the failed region in all 3 checks. C2 SPARQL validity 21/21 on the first try. B++ retries fell from
3 to 0 after the v2 docs fix (logged). Tuning rounds used: 1 of 3.

## Known limitations

- **Ceiling.** B++ and C2 were perfect on DEV. If B+ is also near-perfect on TEST, the primary test cannot find
  a difference, and a "not supported" result would then reflect the questions' difficulty for this model as much
  as the definitions' form.
- **Yes/no-heavy.** 34 of 51 TEST questions are booleans, scored 0/1, with 50% chance accuracy for a guess.
- **Single author.** I wrote the definitions, rules, helpers, questions and ground truth;
  rules and helpers were each verified against `truth.py`, but the questions are shaped to the concepts both encode.
- **C2's executable layer is the rules, not OWL reasoning.** "Lost" needs closed-world negation, which OWL
  cannot express; it is a SPARQL rule. The OWL characteristics in `ontology2.ttl` (symmetric, transitive,
  reflexive) are declarative and are realized by the rules.
- **One model, one run, synthetic graphs**, as in Experiment 1.
- The authoring-effort comparison uses line and fix counts only; it has no time component.

## Frozen file hashes (sha256, first 16 hex chars)

Experiment 2 (`exp2/`):

```
8fea37c559c0100d gen2.py
d2800dfc39f94d41 helpers.py
572aa04cdf328d4b rules.py
a745701687391ad6 ontology2.ttl
bd4a14e9595bca9a docs.py
34eed0d76e238056 questions2.py
84fc2fbb8364b51d run2.py
1005a280ce8ca458 score2.py
ca3e7ea9dbb8acd4 verify_defs.py
59e9072fb6f20319 check_docs.py
95cc42b1fa1ff02d test_run2.py
909bff27253ca23e data/questions.json
46102045d4e91e7e data/answers.json
6b4a51a05a2094b0 data/graph_20.json
aa886f6ec8cf7876 data/graph_100.json
456a914488c61c91 data/graph_500.json
abfe4758b3c6f7b2 data/graph_20.ttl
ad88e4527b0ede04 data/graph_100.ttl
4e837ee6237d95e9 data/graph_500.ttl
```

Experiment 1 modules reused unmodified (hashes as in `PREREG.md`): `common.py` 5071ace7c1ccaa04, `llm.py`
6e3d94b1d34ced69, `sandbox.py` f226df5c6495747a, `run_B.py` 8f7208e43dfce33b, `run_C.py` 6902a017750e70ac,
`score.py` aac18966cf1a293b, `truth.py` 585c8cfd4bba8bc4, `gen.py` e9efe0998887de8a.
