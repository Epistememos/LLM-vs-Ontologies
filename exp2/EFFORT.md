# Authoring effort, Experiment 2

What it cost to encode the definitions (replica group, footprint, primary, lost, down, SLA breach, tier
rule) as executable artifacts, for B++ (Python helpers) and C2 (ontology + materialization rules).

| Artifact | Condition | Code lines (non-blank, no comments/docstrings) | Size | Fixes needed before matching truth.py |
|---|---|---|---|---|
| `helpers.py` | B++ | 88 (130 total) | 15 methods | 0 |
| `rules.py` | C2 | 72 (corrected 2026-10-16, see note) | 16 SPARQL CONSTRUCT rules in 8 strata | 1 (see below) |
| `ontology2.ttl` | C2 | 50 non-blank (20 for the derived concepts) | 6 derived classes, 4 derived properties | 0 |
| C2 total | C2 | 122 (corrected 2026-10-16, was 113) | | 1 |

**Correction, 2026-10-16 (post-run):** `rules.py` has 72 code lines, not 63. The 63 was counted before the
precompute block (`if __name__ == "__main__":`, which writes the materialized graphs to `data/materialized/`) was
added on 2026-10-13, before freezing. Those 9 lines account for the whole difference; the 16 rules and 8 strata
did not change. The C2 total changes from 113 to 122 accordingly.

Fix to the rules: type inheritance (`rdfs:subClassOf`) ran only in the first stratum, before the derived classes
existed, so instances of `Lost`, `Down`, `Primary` etc. did not get their superclass types. Added a final
type-closure stratum. Found by reading the rules, before the first verification run.

## Time

Wall-clock timestamps were recorded (start 2026-10-13 12:46:36; helpers written 12:48:02; rules and
ontology written 12:48:17), but **they are not a meaningful measure of human authoring effort**: both artifacts
were written by an AI coding assistant, and most of the drafting happens before the file-write timestamps. Do not
compare them with human hours. The comparable proxies are the line counts and fix counts above. If a human
reviews or re-derives either artifact, log that time here:

| Date | Who | Artifact | Hours | Notes |
|---|---|---|---|---|
| | | | | |

## Verification

`python exp2/verify_defs.py` checks both artifacts against `truth.py` for every concept, every node and every
failure scenario (3 graphs, 10 failed-region scenarios). Both match exactly. A negative control (exp1's
per-member footprint bug planted in the rules; a direct-dependency-only bug planted in the helpers) is caught
in 10/10 and 9/10 scenarios respectively; the one helper miss is a 20-node scenario with no multi-hop loss.
