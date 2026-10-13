"""exp2/gen2.py - Experiment 2 graphs: exp1's generator (imported, unmodified) with new seeds,
written to exp2/data/, plus one failed-region scenario copy per (size, region).

A scenario copy is the base graph with the failure asserted as data:
  JSON: the region node gets "failed": true
  RDF:  ex:<region> a ex:FailedRegion
Run (from the repo root): python exp2/gen2.py
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
import gen  # noqa: E402  exp1 generator, used as a library

from rdflib import RDF, Graph  # noqa: E402

DATA2 = Path(__file__).resolve().parent / "data"
SEEDS = {20: 2020, 100: 2100, 500: 2500}  # new seeds; sizes and configs as exp1 (24/117/553-node scale)


def scenario_json(n, region):
    g = json.loads((DATA2 / f"graph_{n}.json").read_text())
    g = copy.deepcopy(g)
    node = next(v for v in g["nodes"] if v["id"] == region)
    assert node["type"] == "Region"
    node["failed"] = True
    return g


def write_scenario(n, region):
    out = DATA2 / "scenarios"
    out.mkdir(exist_ok=True)
    (out / f"graph_{n}_{region}.json").write_text(json.dumps(scenario_json(n, region), indent=1))
    g = Graph().parse(DATA2 / f"graph_{n}.ttl")
    g.bind("ex", gen.EX)
    g.add((gen.EX[region], RDF.type, gen.EX.FailedRegion))
    g.serialize(out / f"graph_{n}_{region}.ttl", format="turtle")


if __name__ == "__main__":
    gen.DATA = DATA2  # redirect exp1's writer to exp2/data (module attribute, file untouched)
    for n, cfg in gen.SIZES.items():
        nodes, edges, planted = gen.build(cfg | {"seed": SEEDS[n]})
        gen.write(n, nodes, edges, planted)
        assert gen.verify_roundtrip(n)
        regions = sorted(k for k, v in nodes.items() if v["type"] == "Region")
        for r in regions:
            write_scenario(n, r)
        print(f"  size {n}: {len(nodes)} nodes, {len(regions)} failure scenarios")
