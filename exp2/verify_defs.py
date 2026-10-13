"""verify_defs.py - check that helpers.py (B++) and the materialized ontology rules (C2) reproduce
truth.py exactly, for every concept, every node and every failure scenario.
Run (from the repo root): python exp2/verify_defs.py
"""
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path[:0] = [str(HERE.parent), str(HERE)]
import truth  # noqa: E402  exp1 ground truth, used as a library on exp2 data
from helpers import Infra  # noqa: E402
from rules import EX, load_materialized  # noqa: E402

truth.DATA = HERE / "data"
SCEN = HERE / "data" / "scenarios"
loc = lambda u: str(u).removeprefix(str(EX))


def rule_facts(g):
    q = lambda s: [tuple(loc(v) for v in row) for row in g.query(s)]
    members = lambda cls: {x for (x,) in q(f"SELECT ?x WHERE {{ ?x a <{EX[cls]}> }}")}
    pairs = lambda prop: q(f"SELECT ?a ?b WHERE {{ ?a <{EX[prop]}> ?b }}")
    def grouped(prop):
        out = {}
        for a, b in pairs(prop):
            out.setdefault(a, set()).add(b)
        return out
    return dict(primary=members("Primary"), lost=members("Lost"), down=members("Down"),
                breached=members("BreachedSLA"), tier_risk=members("TierRiskService"),
                violations=set(pairs("violatesTierRule")), group=grouped("inReplicaGroupWith"),
                footprint=grouped("hasFootprintRegion"), deps=grouped("dependsOnTransitively"))


def truth_facts(t, r):
    comps = t.ids(*truth.INFRA_TYPES)
    return dict(primary=set(t.primaries(*truth.INFRA_TYPES)),
                lost={x for x in comps if t.lost(x, r)},
                down=set(t.down_services(r)),
                breached=set(t.breached_slas(r)),
                tier_risk={s for s in t.ids(*truth.SERVICE_TYPES)
                           if t.tier(s) == 1 and any(t.tier(d) == 3 for d in t.dependencies(s))},
                violations=set(t.tier_violations()),
                group={x: set(t.replica_group(x)) for x in comps},
                footprint={x: t.footprint(x) for x in comps},
                deps={x: set(t.dependencies(x)) for x in comps if t.dependencies(x)})


def helper_facts(h):
    comps = h.components()
    return dict(primary=set(h.primaries()), lost=set(h.lost_components()), down=set(h.down_services()),
                breached=set(h.breached_slas()), tier_risk=set(h.tier_risk_services()),
                violations=set(h.tier_violations()),
                group={x: h.replica_group(x) for x in comps},
                footprint={x: h.footprint(x) for x in comps},
                deps={x: h.transitive_dependencies(x) for x in comps if h.transitive_dependencies(x)})


def main():
    all_ok, rows = True, []
    for n in (20, 100, 500):
        t = truth.Truth(n)
        for r in t.ids("Region"):
            ref = truth_facts(t, r)
            h = helper_facts(Infra(SCEN / f"graph_{n}_{r}.json"))
            t0 = time.time()
            g, stats = load_materialized(SCEN / f"graph_{n}_{r}.ttl")
            secs = time.time() - t0
            c = rule_facts(g)
            bad_h = [k for k in ref if h[k] != ref[k]]
            bad_c = [k for k in ref if c[k] != ref[k]]
            all_ok &= not bad_h and not bad_c
            rows.append((n, r, len(ref["lost"]), len(ref["down"]), len(ref["breached"]),
                         "OK" if not bad_h else f"FAIL {bad_h}", "OK" if not bad_c else f"FAIL {bad_c}",
                         f"{secs:.1f}s", sum(a for _, a in stats.values()),
                         max(rd for rd, _ in stats.values())))
    print(f"{'size':>4} {'region':6} {'lost':>4} {'down':>4} {'SLAs':>4}  {'helpers.py':10} {'rules':10} "
          f"{'materialize':>11} {'derived':>8} {'max rounds':>10}")
    for row in rows:
        print("{:>4} {:6} {:>4} {:>4} {:>4}  {:10} {:10} {:>11} {:>8} {:>10}".format(*row))
    print(f"\nconcepts checked per scenario: {', '.join(truth_facts(truth.Truth(20), 'reg-1'))}")
    print("ALL MATCH truth.py" if all_ok else "MISMATCH")
    return all_ok


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
