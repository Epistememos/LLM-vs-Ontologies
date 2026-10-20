# Authoring effort, Experiment 3

What it cost to build each condition's artifact: entity resolution across the two exports, field mapping, the
authority and stale-record rules, and the definitions (footprint, lost, down, primary, SLA breach).
Counts are code lines (non-blank, excluding comments and docstrings), measured as in Experiment 2.

| Artifact | Condition | Code lines | Size | Fixes after the first verification run |
|---|---|---|---|---|
| `glue.py` | B3 | 83 | 13 public methods | 0 |
| `to_rdf3.py` | C3 | 52 | format-only conversion of both exports to RDF | 0 |
| `rules3.py` | C3 | 102 | 26 SPARQL CONSTRUCT rules in 14 strata | 0 |
| `ontology3.ttl` | C3 | 47 | canonical classes and properties, 7 derived concepts | 0 |
| **B3 total** | | **83** | | **0** |
| **C3 total** | | **201** | | **0** |
| shared: `derive_tables.py` | B3 and C3 | 25 | team and region crosswalks derived from the exports | 0 |
| shared: `docs3.py` | A3, B3, C3 | 51 | rules, definitions, answer format, per-condition notes | 0 |

- Both artifacts reproduced the mappings in the key and every fact and definition in `truth3.py` on the first
  verification run (`verify3.py`), so neither received a fix. One edit to `glue.py` happened before that first run:
  I removed an unused helper that guessed which crosswalk table to use (the harness passes a single-graph table).
- C3 needed about 2.4 times the code of B3 for the same behaviour: the conversion to RDF and the rule strata have no
  counterpart in the Python glue, which reads the JSON directly.

## Documentation fixes

One clarity iteration each for C3 and B3 (prompt version 2), both in `docs3.py`, logged with the exact text and evidence
in `LOG3.md`. They are documentation changes, not artifact fixes: `glue.py`, `to_rdf3.py`, `rules3.py` and
`ontology3.ttl` were frozen with 0 fixes each.

## Review time

| Date | Artifact | Hours | Notes |
|---|---|---|---|
| | `glue.py` | | |
| | `to_rdf3.py`, `rules3.py`, `ontology3.ttl` | | |
