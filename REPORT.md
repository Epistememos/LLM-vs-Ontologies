# Blast Radius: consolidated report on three pre-registered experiments

Experiments 1-3 are complete and frozen. This report brings them together; each experiment's own write-up, log and
pre-registration remain the authority for its details: [Experiment 1](exp1/README.md), [Experiment 2](exp2/README.md),
[Experiment 3](exp3/README.md).

## Summary

| Experiment | Pre-registered primary test | Mean F1 difference [95% CI] | Decision |
|---|---|---|---|
| 1. Ontology vs documented code | C − B+ | **−0.005** [−0.055, +0.055] | not supported |
| 2. Executable definitions: ontology rules vs prose | C2 − B+ | **+0.026** [0.000, +0.071] | not supported |
| 3. Two conflicting sources: resolving ontology vs resolving Python | C3 − B3 | **0.000** [0.000, 0.000] | not supported (ceiling) |

Across three experiments, an ontology never beat code that carried the same knowledge. What did make a large
difference was doing the knowledge work before the model sees anything: grounding with a tool and a schema
(Experiment 1: C − A = +0.163), executable definitions (Experiment 2: B+'s only error type disappeared in both encoded
forms), and resolving two conflicting sources (Experiment 3: +0.532 over the model alone). Python and RDF/OWL did that
work equally well, and the Python versions were smaller.

## 1. Thesis and why I tested it

> "LLMs grounded in an ontology are better at reasoning about system topology than LLMs alone."

Answering "what breaks if this datacenter fails?" means following dependency chains, replicas and ownership across a
company's whole infrastructure. Ontologies are widely promoted as the way to make language models reliable at this
kind of reasoning, and they are expensive to build. I wanted to know whether the ontology itself, as opposed to the
knowledge it carries or the tool used to query it, makes the difference.

Every experiment used the same discipline: synthetic infrastructure graphs with exact ground truth computed by
NetworkX, independent of every harness; a DEV/TEST split fixed by seed; prompts frozen and the analysis pre-registered,
with file hashes, before any TEST question was sent; one model (Haiku 4.5, temperature 0, 8192 output tokens); the same
retry budget for every tool-using condition; and every change logged with its evidence.

## 2. The three pre-registered tests

### Experiment 1: does an ontology beat plain data and code?

**Design.** Four conditions answered 131 questions (DEV 40 / TEST 91) on graphs of 24, 117 and 553 nodes: A, the
LLM alone with the graph in its prompt; B, Python over raw JSON; B+, Python plus prose schema documentation; C, one
SPARQL query against an RDF graph described by an RDFS/OWL schema (`schema.ttl`), given the same prose documentation.
B+ separates "knowing the schema" from "having a formal ontology". Definitions such as "lost" and "down" were given as
prose in the question text to every condition.

**Primary result.** C − B+ on TEST levels L2-L4 (n = 61), paired bootstrap: **−0.005 [−0.055, +0.055]**.

**Decision.** Not supported. The interval is narrow and centred on zero: a tie. Grounding of either kind beat the LLM
alone (C − A = +0.163 [+0.083, +0.250]), and that gap grew with graph size. C's main weakness was region-failure logic
it had to write in SPARQL: 9 of its 12 non-survivor region-failure questions were valid queries with the wrong logic.

### Experiment 2: what if the ontology carries executable definitions?

**Design.** Definitions moved out of the questions and into each condition: B+ (prose docs), B++ (the same prose plus
`helpers.py`, 15 Python methods), and C2 (`ontology2.ttl` with rule-defined classes, materialized by 16 SPARQL CONSTRUCT
rules in 8 strata before querying). Both encodings reproduced the ground truth exactly before any model call. New
graphs of 23, 121 and 559 nodes; the failed region was asserted as data, never named in the question.

**Primary result.** C2 − B+ on 51 TEST L4 questions, cluster bootstrap over 45 question texts: **+0.026
[0.000, +0.071]**. Secondary, as predicted: C2 − B++ = **0.000 [0.000, 0.000]**.

**Decision.** Not supported. C2 and B++ both answered all 51 questions correctly; B+ scored 0.974, missing 2, both from
reading "primary" in the wrong direction. Two misses in 51 cannot exclude a zero difference.

### Experiment 3: two conflicting sources, changing definitions

**Design.** One hidden canonical graph per size (22, 120 and 567 nodes) exported twice, as a CMDB-style export and a
monitoring-style export with different identifiers, aliases, stale ghost records and contradictory facts, plus a fixed
rulebook saying which export is authoritative for what. A3: the LLM alone with both raw exports (22- and 120-node graphs
only). B3: Python glue (`glue.py`) that resolves entities and implements the rules and definitions. C3: the same
resolution and definitions as an RDF conversion, 26 CONSTRUCT rules in 14 strata, and an ontology, queried with SPARQL.
Both artifacts reproduced the hidden resolution key and the ground truth before any model call. 53 TEST questions (44
cross-source, 9 single-source controls), each asked 3 times.

**Primary result (H1).** C3 − B3 on the 44 cross-source questions, cluster bootstrap by question text × graph seed:
**0.000 [0.000, 0.000]**. Both conditions scored 1.000 on every cross-source question in every repeat.

**Decision.** Not supported, on ceiling grounds that were pre-registered: in the DEV pilot both conditions were above
the 0.90 ceiling in both rounds, and raising the noise could not move them, because both resolve the noise before the
model sees it.

**Descriptive contrast.** Against the LLM alone, on the two smaller graphs (30 cross-source questions): B3 − A3 =
C3 − A3 = **+0.532 [+0.377, +0.687]**. A3 scored 0.468 (0.287 on the 22-node graph, 0.649 on the 120-node graph);
half of its 60 wrong answers across repeats matched a planted integration trap.

**H2, change test (exploratory; two pre-specified changes, n = 1 each).** The CMDB field `datacenter` was renamed to
`site`, and the definition of "lost" changed for databases (29 of 53 TEST answers change).

| | Phase (a): unchanged artifacts, loud / silent / unaffected | Phase (b): code lines changed | Phase (b): mean F1 |
|---|---|---|---|
| B3 | 28 / 18 / 7 (F1 0.221) | 4 (`glue.py` +2/−2) | 0.981 |
| C3 | 53 / 0 / 0 (F1 0.000) | 4 (`to_rdf3.py` +1/−1, `rules3.py` +2/−0); 6 with an ontology comment | 1.000 |

C3's graph build failed before any model call, so all of its failures were loud. B3's glue failed with the same error,
but inside a sandbox: on retry, 25 programs worked around the rename and answered with the old definition, 18 of them
wrongly. The difference comes from where validation runs, not from the ontology. A changed definition raised no error
in either artifact. The edits run were smaller than the ones I first approved, with identical output on all three
graphs; the deviation is logged in `exp3/LOG3.md`.

## 3. What each experiment ruled out

| Possible explanation for "ontologies help" | Tested by | Outcome |
|---|---|---|
| **Tools vs ontology.** The ontology condition wins only because it has a query tool and the others do not. | Exp 1: B+ got a tool and the same schema documentation as C | C tied B+. Grounding beat the LLM alone, but the formal ontology added nothing over documented code. |
| **Thin ontology.** Experiment 1's ontology was a typed graph with no derived concepts, so it was never asked to do ontology work. | Exp 2: rule-defined classes materialized before querying | C2 tied equivalent Python helpers exactly (0.000). |
| **Prose vs executable definitions.** The ontology's value is encoding definitions so they can be executed, not merely described. | Exp 2: B+ (prose) vs B++ (Python) vs C2 (rules) | Executable definitions in either form removed B+'s only error type, but the effect (2 of 51 questions) did not pass the test, and the form made no difference. |
| **Single source.** Ontologies pay off when several sources disagree and must be reconciled. | Exp 3, H1: two conflicting exports | Resolving the sources mattered a great deal (+0.532 over the LLM alone); doing it in an ontology rather than Python did not (0.000). |
| **Static definitions.** Ontologies pay off when the data and definitions change. | Exp 3, H2: a field rename and a definition change | Same edit size (4 code lines each). The ontology broke loudly and the code silently, because of where validation ran, which code can also do. Exploratory, n = 1 per change. |

## 4. What the results do not show

- **One model.** Every result comes from Haiku 4.5 at temperature 0. A stronger or weaker model could behave
  differently, in particular on the ceilinged tests.
- **Synthetic data.** All graphs come from one generator, with noise planted by a program. Real infrastructure is
  messier in ways a generator does not imitate.
- **Entity resolution was solved for both conditions.** In Experiment 3, B3 and C3 both resolved every entity correctly
  by construction, verified against the hidden key. Imperfect resolution, the hard part in practice and where an
  ontology's mapping layer might matter, was not tested.
- **Ceilings in Experiments 2 and 3.** C2 and B++ were perfect, B+ nearly so (0.974); B3 and C3 were perfect. A ceiling
  limits how well a test can separate conditions, so these ties are ties at the top, not evidence of equivalence on
  harder questions.
- **H2 is n = 1 per change.** Two changes, one run each: case studies, not estimates, and descriptive only.
- **Ontology construction cost beyond line counts was not measured.** I counted code lines and fixes; I did not
  measure authoring or review time in hours, and nothing here captures the cost of modelling a real business.
- **Small numbers.** 61, 51 and 44 questions in the three primary tests; every per-size, per-level or per-trap breakdown
  is exploratory.

## 5. Authoring effort and cost

**Authoring effort** (code lines: non-blank, excluding comments and docstrings; fixes needed after writing, before
matching the ground truth)

| Experiment | Code / helpers | Lines | Fixes | Ontology / rules | Lines | Fixes |
|---|---|---|---|---|---|---|
| 2 | `helpers.py` (B++) | 88 | 0 | `rules.py` + `ontology2.ttl` (C2) | 72 + 50 = 122 | 1 |
| 3 | `glue.py` (B3) | 83 | 0 | `to_rdf3.py` + `rules3.py` + `ontology3.ttl` (C3) | 52 + 102 + 47 = 201 | 0 |
| 3, H2 edits | `glue.py` | 4 changed | 0 | `to_rdf3.py`, `rules3.py` (+ ontology comment) | 4 changed (6) | 0 |

Experiment 1 had no executable artifacts to compare: its ontology was a schema, and the code conditions wrote their
programs per question. In Experiments 2 and 3 the ontology version needed 1.4 and 2.4 times the code of the Python
version for identical behaviour.

**API cost** (Haiku 4.5, all DEV and TEST calls)

| | Spent |
|---|---|
| Experiment 1 | $3.08 |
| Experiment 2 | $0.84 |
| Experiment 3 (DEV pilot $0.68, TEST $2.22, H2 $1.17) | $4.07 |
| **Total** | **$7.99** |

The total is the sum of the per-phase figures; the model-call cache totals $7.98, the difference being rounding.

## 6. Next steps

- **Cross-model re-run of the frozen TEST sets.** Re-run Experiments 1-3 on their frozen TEST questions, prompts and
  artifacts with other models, to test whether the ties and the ceilings hold. Which models, the number of repeats, the
  analysis and the budget would be pre-registered before any call. Nothing in the frozen experiments would change; the
  re-run would be reported as its own pre-registered study.
- **A possible Experiment 4 on messy real data.** The open question these experiments leave is whether an ontology's
  mapping layer helps when entity resolution is imperfect, as it always is with real systems. A next design would use
  real or realistically messy exports, where no artifact can resolve every entity by construction, and measure both
  accuracy and how resolution errors propagate to answers. It would need its own pre-registration before any run.

## Sources

| Experiment | Write-up | Pre-registration | Log | Effort |
|---|---|---|---|---|
| 1 | [exp1/README.md](exp1/README.md), [exp1/ADDENDUM.md](exp1/ADDENDUM.md) | [exp1/PREREG.md](exp1/PREREG.md) | [exp1/PROMPT_LOG.md](exp1/PROMPT_LOG.md) | n/a |
| 2 | [exp2/README.md](exp2/README.md) | [exp2/PREREG_EXP2.md](exp2/PREREG_EXP2.md) | [exp2/LOG.md](exp2/LOG.md) | [exp2/EFFORT.md](exp2/EFFORT.md) |
| 3 | [exp3/README.md](exp3/README.md) | [exp3/PREREG_EXP3.md](exp3/PREREG_EXP3.md) | [exp3/LOG3.md](exp3/LOG3.md) | [exp3/EFFORT3.md](exp3/EFFORT3.md) |

Frozen files are checked with `python tools/verify_frozen.py`; [PROGRESS.md](PROGRESS.md) lists every commit and the
decisions behind it.
