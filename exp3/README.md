# Experiment 3: two conflicting sources, changing definitions

**Status: pre-registered and frozen; TEST not run yet.** See [PREREG_EXP3.md](PREREG_EXP3.md) for the design,
decision rules, DEV pilot and difficulty decision, [LOG3.md](LOG3.md) for every change, and
[EFFORT3.md](EFFORT3.md) for authoring effort.

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
| `score3.py`, `pilot3.py` | scoring and the DEV pilot report |
| `verify3.py`, `test_run3.py` | artifact verification against the key and ground truth; offline tests |
