# Experiment 2: executable definitions, ontology rules vs Python helpers vs prose

Pre-registered in [PREREG_EXP2.md](PREREG_EXP2.md) before any TEST question was sent; every change is logged in
[LOG.md](LOG.md).

> **Hypothesis:** ontology-encoded executable definitions (footprint, lost, down, primary) outperform
> prose-described definitions on region-failure and constraint questions.

## Result

**The pre-registered test does not support the hypothesis.**

| Pre-registered test (TEST, L4, 51 questions in 45 text clusters) | Mean F1 difference | 95% CI | Decision |
|---|---|---|---|
| **Primary: C2 − B+, cluster bootstrap** | **+0.026** | **[0.000, +0.071]** | lower bound not above 0: **not supported** |
| C2 − B+, per-question bootstrap (secondary) | +0.026 | [0.000, +0.072] | agrees with the primary |
| **Secondary: C2 − B++** | **0.000** | **[0.000, 0.000]** | **tie, as predicted** |

The two bootstrap methods agree, so the pre-registered rule for disagreement does not come into play. C2 never
scored below B+ on any question and was right on the only two questions B+ got wrong, but two misses in 51 cannot
exclude a zero difference. C2 and B++ both answered all 51 questions correctly.

## Setup

| Condition | Definitions given as | Tool |
|---|---|---|
| **B+ (exp2-docs)** | prose docs: the definitions Experiment 1 carried in question text | Python sandbox over raw JSON |
| **B++** | the same prose plus `helpers.py`, executable Python (15 methods) | Python sandbox over raw JSON |
| **C2** | `ontology2.ttl`: rule-defined classes and properties, materialized by 16 SPARQL CONSTRUCT rules (8 strata, each to a fixpoint) before querying | one SPARQL query over the materialized graph |

- **Graphs:** exp1's generator with new seeds: 23, 121 and 559 nodes. 10 failure scenarios (one per region), each a
  copy of the graph with the failed region asserted as data. Question text never names the failed region and
  carries no definitions.
- **Questions:** 23 L4 questions per size over 13 kinds (region failure and the tier rule), quotas fixed per kind,
  DEV/TEST split by seed. TEST: 51 questions in 45 distinct texts; 34 yes/no, 14 sets, 3 numbers.
- **Unchanged from Experiment 1:** model (Haiku 4.5, temperature 0, 8192 output tokens), 60 s sandbox and query
  timeout, one retry on errors only.
- **Verification before any model call:** `helpers.py` and the rules both reproduce `truth.py` exactly, for every
  concept, node and scenario (`verify_defs.py`, with a negative control), and every definition is present in every
  condition's docs (`check_docs.py`).

## Descriptive findings (TEST)

**F1 on L4 by graph size**

| Nodes | B+ (exp2-docs) | B++ | C2 |
|---|---|---|---|
| 23 | 0.941 | 1.000 | 1.000 |
| 121 | 0.980 | 1.000 | 1.000 |
| 559 | 1.000 | 1.000 | 1.000 |
| **all** | **0.974** | **1.000** | **1.000** |

**B+'s only error type was "primary" applied in the wrong direction.** Both of its misses (`e2-20-L4-18`,
`e2-100-L4-15`) come from programs that treat a node that *has* replicas as non-primary, dropping every service with
a replica from the answer. This is the same inversion seen in Experiment 1. No condition ever failed to find the
failed region in the data: 0 flag-discovery failures in every condition. That split was exploratory, not
pre-registered; see the override entry in LOG.md.

**Efficiency and reliability**

| | B+ (exp2-docs) | B++ | C2 |
|---|---|---|---|
| Timeouts | 0 | 0 | 0 |
| Questions retried | 0 | 2 (3.9%), both `KeyError` on a node ID, fixed on retry | 0 |
| C2 valid SPARQL | | | 51/51, all first try |
| Median latency | 8.7 s | 1.6 s | 2.2 s |
| Mean input / output tokens | 1,376 / 941 | 1,791 / 175 | 1,769 / 217 |
| TEST cost (attributed) | $0.31 | $0.14 | $0.15 |
| Hallucinated IDs | 0 | 0 | 0 |

B+ writes the definitions out itself in every program: 4-5× the output tokens of B++ or C2, and 4-5× slower.

**Authoring effort** (from [EFFORT.md](EFFORT.md); both artifacts were written by an AI assistant, so no human hours
are reported)

| Artifact | Condition | Code lines | Fixes before matching ground truth |
|---|---|---|---|
| `helpers.py` | B++ | 88 | 0 |
| `rules.py` + `ontology2.ttl` | C2 | 72 + 50 | 1 |

## Interpretation

- **Executable definitions removed B+'s remaining error type.** Both encoded forms (Python helpers and ontology rules)
  took the "primary" inversion off the table and cut output tokens and latency sharply. On this question set that is a
  difference of 2 questions in 51, too small to pass the pre-registered test.
- **The ontology added nothing over equivalent Python helpers.** C2 and B++ tied exactly, as predicted. Where the
  definitions are executable, it made no difference whether they were SPARQL rules over RDF or Python functions over
  JSON. Writing them as rules took slightly more code and one fix.
- **The ceiling effect flagged in PREREG came true.** Prose definitions alone already scored 0.974. With this model
  and these questions, there was little room left for any encoding to show an advantage.

## Limitations

- **One clean source.** The data comes from a single, consistent source with one naming scheme. The situation where
  ontologies are usually argued to help, reconciling several sources, was not tested.
- **One model, one run** at temperature 0; no variance across seeds or models.
- **Synthetic graphs** from one generator, three sizes.
- **Ceiling on L4 difficulty.** Encoded conditions were perfect and prose nearly so, which limits how well the test can
  separate the conditions.
- **No multi-source integration and no change over time.** Nothing tested merging graphs, schema evolution, or keeping
  definitions in sync as the data changes, where maintaining definitions in one place might matter more.
- **B+ (exp2-docs) is not comparable to Experiment 1's B+.** Its docs carry the definitions that Experiment 1 put in
  question text, the questions differ, and the graphs come from new seeds.
- **Changes made during DEV**, all logged before freezing: a 120 s API client timeout (one DEV call hung for 42 minutes),
  a B++ docs fix stating that `g.region`, `g.owner` and `g.sla` are dicts (prompt version 2; removed 3 DEV retries),
  and question quotas raised from 14-15 to 23 per size for power.
- **Same author** for definitions, rules, helpers, questions and ground truth; the questions are shaped to the concepts
  both encodings implement.

## Possible Experiment 3 (not run)

A new pre-registered design that targets the setting where an ontology's mapping layer should matter: **two sources
describing the same infrastructure with conflicting names.**

- Two generated sources (for example a deployment inventory and an incident or SLA system) that use different
  identifiers and vocabulary for the same entities and relations (`svc-123` vs `checkout-api`, `deployedIn` vs
  `zone`), with some deliberate overlaps and gaps.
- Conditions: prose docs describing both sources and the correspondence (B+-style), Python helpers that merge them
  (B++-style), and an ontology with `owl:sameAs` / equivalence mappings plus the Experiment 2 rules (C2-style).
- Questions that can only be answered by joining both sources, for example region failure computed from one source and
  SLA ownership from the other.
- Fresh seeds, a DEV/TEST split by seed, the same model and retry budget, the cluster bootstrap as the primary test,
  and a pre-registered prediction before any TEST run.
