"""verify_h2.py - check the edited artifacts against the H2 ground truth (test-only; reads data/hidden/).

On the changed export, B3's edited glue and C3's edited conversion + rules must reproduce, for every datacenter
failure, the lost components, down services and breached SLAs of the changed "lost" definition, plus every region
assignment. Ground truth comes from make_h2.NewLostTruth (canonical graph, NetworkX), independent of both artifacts.
Run (from the repo root): python exp3/h2/verify_h2.py
"""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP3 = HERE.parent
sys.path[:0] = [str(EXP3.parent / "exp1"), str(EXP3), str(HERE)]
import truth3  # noqa: E402
from make_h2 import NewLostTruth  # noqa: E402

COMP = truth3.truth.INFRA_TYPES


def reference():
    """Everything from data/hidden/, computed before the guarded harness is imported."""
    ref = {}
    for n in (20, 100, 500):
        t = NewLostTruth(truth3.truth_for(n))
        _, key, _, _ = truth3.load(n)
        ci = lambda x: key["entities"][x]["cmdb"]
        dc = {r: v["cmdb"] for r, v in key["regions"].items()}
        comps = t.ids(*COMP)
        f = {"region": {ci(x): dc[t.region[x]] for x in comps}}
        for r in t.ids("Region"):
            f[f"lost@{dc[r]}"] = sorted(ci(x) for x in comps if t.lost(x, r))
            f[f"down@{dc[r]}"] = sorted(ci(s) for s in t.down_services(r))
            f[f"breached@{dc[r]}"] = sorted(key["slas"][s] for s in t.breached_slas(r))
        ref[n] = (f, list(dc.values()))
    return ref


REF = reference()
import run_h2  # noqa: E402  (installs the hidden-data guard from here on)
from rdflib import Graph  # noqa: E402

EX = "http://example.org/br#"


def from_glue(n, dcs):
    glue = run_h2.load_module("glue_edited", HERE / "artifacts" / "glue.py")
    g = glue.Infra3(run_h2.export_path(n, "cmdb"), run_h2.export_path(n, "monitoring"), EXP3 / "mapping_tables.json", n)
    f = {"region": dict(g.region)}
    for d in dcs:
        f[f"lost@{d}"] = sorted(x for x in g.components() if g.is_lost(x, d))
        f[f"down@{d}"] = sorted(g.down_services(d))
        f[f"breached@{d}"] = g.breached_slas(d)
    return f


def from_rules(n, dcs):
    path, err = run_h2.build_c3("edited", n)
    if err:
        return {"build": err}
    g = Graph().parse(path)
    pairs = lambda p: [(str(a).removeprefix(EX), str(b).removeprefix(EX)) for a, b in g.subject_objects(g.namespace_manager.expand_curie(f"ex:{p}"))]
    f = {"region": dict(pairs("deployedIn"))}
    for d in dcs:
        for prop, label in (("lostIn", "lost"), ("downIn", "down"), ("breachedIn", "breached")):
            f[f"{label}@{d}"] = sorted(x for x, r in pairs(prop) if r == d)
    return f


def main():
    ok = True
    for n, (ref, dcs) in REF.items():
        for label, facts in (("B3 edited glue", from_glue(n, dcs)), ("C3 edited rules", from_rules(n, dcs))):
            bad = [k for k in ref if facts.get(k) != ref[k]]
            ok &= not bad
            print(f"  graph {n:>3} {label:16} {len(ref) - len(bad)}/{len(ref)} match {bad[:4] if bad else ''}")
    print("ALL MATCH the H2 ground truth" if ok else "MISMATCH")
    return ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
