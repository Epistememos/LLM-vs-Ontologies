# Experiment 1 addendum

**Dated 2026-10-16. Written after Experiment 1 was frozen (tag `exp1-final`).** This file adds context to
Experiment 1; it does not change its pre-registration ([PREREG.md](PREREG.md)), results or
[README.md](README.md), which stay exactly as frozen.

## What the ontology was asked to do

Experiment 1's ontology (`schema.ttl`) was a thin, typed graph: a class hierarchy (CustomerFacingService ⊂ Service ⊂
Component), domains and ranges, and `dependsOn` declared transitive. No reasoner ran, and no derived concept was
defined in it. Replica group, footprint, primary, lost, down and SLA breach existed only as prose in the question
text, which every condition received.

Everything the ontology stated could therefore be stated just as fully in the prose schema documentation that
condition B+ also received. The pre-registered tie between C and B+ (C − B+ = −0.005, 95% CI [−0.055, +0.055]) still
stands as measured. But it partly reflects how little the ontology was asked to do: the comparison was effectively
SPARQL plus a schema description against Python plus the same description, not ontological structure against prose.

## Follow-up

[Experiment 2](../exp2/README.md) addresses this directly. It moves the definitions out of the questions and into each
condition, and gives the ontology executable structure: rule-defined classes (`Primary`, `Lost`, `Down`,
`BreachedSLA`, ...) materialized to a fixpoint before querying, compared with the same definitions as prose (B+) and as
Python helpers (B++). Its pre-registered result: C2 − B+ = +0.026 [0.000, +0.071], not supported, and C2 − B++ = 0.000,
the predicted tie.

*Moved from the repo root to `exp1/ADDENDUM.md` on 2026-10-19 when Experiment 1 was gathered into `exp1/`; only this note and the Experiment 2 link path changed.*
