"""run_h2.py - H2 change test runs: B3 and C3 on the TEST questions, one repeat, with the changed CMDB export.

Phase 'unchanged': the frozen artifacts and docs (exp3/glue.py, to_rdf3.py, rules3.py, ontology3.ttl, docs3.py).
Phase 'edited':    the copies in exp3/h2/artifacts/ with the minimal correct edits.
Each phase rebuilds C3's graph from the changed export with that phase's own conversion and rules. If the rebuild fails,
every C3 question on that graph is recorded as a loud failure with the error, and no model call is made.
Prompts, questions, split, harness logic and retry budget are exp3's, unchanged; only file paths are pointed at the
changed export and the phase's artifacts.
Run (from the repo root): python exp3/h2/run_h2.py {unchanged,edited} [--dry-run]
"""
import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP3 = HERE.parent
sys.path[:0] = [str(EXP3.parent / "exp1"), str(EXP3)]
import run3  # noqa: E402  (installs the hidden-data guard)
import common  # noqa: E402

H2_DATA = EXP3 / "data" / "h2"
ARTIFACTS = {"unchanged": EXP3, "edited": HERE / "artifacts"}


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def export_path(n, which):  # the changed CMDB export; monitoring is unchanged
    return H2_DATA / f"cmdb_{n}.json" if which == "cmdb" else EXP3 / "data" / f"monitoring_{n}.json"


def build_c3(phase, n):
    """Rebuild C3's materialized graph from the changed export with this phase's conversion and rules."""
    src = ARTIFACTS[phase]
    stage = HERE / "stage" / phase
    (stage / "data" / "rdf").mkdir(parents=True, exist_ok=True)
    shutil.copy(export_path(n, "cmdb"), stage / "data" / f"cmdb_{n}.json")
    shutil.copy(export_path(n, "monitoring"), stage / "data" / f"monitoring_{n}.json")
    shutil.copy(EXP3 / "mapping_tables.json", stage / "mapping_tables.json")
    out = stage / f"materialized_{n}.ttl"
    out.unlink(missing_ok=True)
    try:
        to_rdf = load_module(f"to_rdf3_{phase}", src / "to_rdf3.py")
        rules = load_module(f"rules3_{phase}", src / "rules3.py")
        to_rdf.HERE, rules.HERE, rules.ONTOLOGY = stage, stage, src / "ontology3.ttl"
        to_rdf.convert(n).serialize(stage / "data" / "rdf" / f"raw_{n}.ttl", format="turtle")
        g, _ = rules.load_materialized(n)
        g.serialize(out, format="turtle")
        return out, None
    except Exception as e:  # the artifact itself fails on the changed export
        return None, f"artifact build failed: {type(e).__name__}: {e}"


def configure(phase):
    """Point exp3's harness at the changed export and at this phase's artifacts and docs."""
    src = ARTIFACTS[phase]
    run3.export_path = export_path
    run3.GLUE, run3.ONTOLOGY = src / "glue.py", src / "ontology3.ttl"
    docs = load_module(f"docs3_{phase}", src / "docs3.py")
    run3.b3_doc, run3.c3_doc = docs.b3_doc, docs.c3_doc
    built = {n: build_c3(phase, n) for n in (20, 100, 500)}
    def runner_files(n):
        return {"runner.py": run3.GUARD + run3.sandbox.SPARQL_RUNNER, "data.ttl": built[n][0], "schema.ttl": run3.ONTOLOGY}
    run3.runner_files = runner_files
    return built


def run(phase, cond, q, built):
    if cond == "C3" and built[q["size"]][0] is None:
        return dict(condition=cond, qid=q["qid"], final=None, retries=0, timeouts=0, error=built[q["size"]][1],
                    build_failed=True, attempts=[], tokens_in=0, tokens_out=0, latency_s=0.0, cost_usd=0.0, cached=True)
    rec = common.solve_with_retry(f"e3h2-{phase}-{cond}", run3.system_prompt(cond, q["size"]), q,
                                  run3.execute_b3 if cond == "B3" else run3.execute_c3)
    rec["condition"], rec["build_failed"] = cond, False
    return rec


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("phase", choices=list(ARTIFACTS))
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args()
    built = configure(a.phase)
    for n, (path, err) in built.items():
        print(f"  C3 build, graph {n}: {'ok' if path else err}")
    qs = run3.load_questions((20, 100, 500), "test")
    for cond in ("B3", "C3"):
        live = [q for q in qs if cond == "B3" or built[q["size"]][0] is not None]
        print(f"{a.phase} {cond}: {len(qs)} questions, {len(live)} needing model calls")
        if live:
            common.estimate(live, lambda n: run3.system_prompt(cond, n), out_tokens=800 if cond == "B3" else 500,
                            calls_per_q=1.5 if a.phase == "unchanged" else 1.2)
    if not a.dry_run:
        (HERE / "results").mkdir(exist_ok=True)
        for cond in ("B3", "C3"):
            records = [run(a.phase, cond, q, built) for q in qs]
            path = HERE / "results" / f"{a.phase}_{cond}.jsonl"
            path.write_bytes("".join(json.dumps(r) + "\n" for r in records).encode())
            print(f"wrote {path.name} | spent ${sum(r['cost_usd'] for r in records if not r['cached']):.4f}")
