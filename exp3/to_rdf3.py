"""to_rdf3.py - format-only conversion of the two exports to RDF (no resolution: that is the rules' job).

Every CMDB record and monitoring record becomes a node in the src: vocabulary with its fields as literals, the SLA
catalog becomes ex:SLA nodes, and the shared crosswalk tables (mapping_tables.json) become triples.
Writes exp3/data/rdf/raw_{n}.ttl. Run (from the repo root): python exp3/to_rdf3.py
"""
import json
from pathlib import Path

from rdflib import RDF, XSD, Graph, Literal, Namespace

HERE = Path(__file__).resolve().parent
EX = Namespace("http://example.org/br#")
SRC = Namespace("http://example.org/src#")
SIZES = (20, 100, 500)


def convert(n):
    cmdb = json.loads((HERE / "data" / f"cmdb_{n}.json").read_text())["records"]
    mon = json.loads((HERE / "data" / f"monitoring_{n}.json").read_text())
    tables = json.loads((HERE / "mapping_tables.json").read_text())[str(n)]
    g = Graph()
    g.bind("ex", EX)
    g.bind("src", SRC)
    for r in cmdb:
        c = SRC["cmdb-" + r["ci_id"]]
        g.add((c, RDF.type, SRC.CmdbRecord))
        for field, prop in (("ci_id", SRC.ciId), ("ci_name", SRC.ciName), ("ci_class", SRC.ciClass),
                            ("status", SRC.status), ("owner_group", SRC.ownerGroup), ("datacenter", SRC.datacenter)):
            g.add((c, prop, Literal(r[field])))
        if r["tier"] is not None:
            g.add((c, SRC.tier, Literal(r["tier"], datatype=XSD.integer)))
        if r["replica_of_ci"]:
            g.add((c, SRC.replicaOfCi, Literal(r["replica_of_ci"])))
        for d in r["depends_on_ci"]:
            g.add((c, SRC.dependsOnCi, Literal(d)))
    for r in mon["records"]:
        m = SRC["mon-" + r["component"].removeprefix("mon:")]
        g.add((m, RDF.type, SRC.MonRecord))
        for field, prop in (("component", SRC.component), ("display_name", SRC.displayName), ("kind", SRC.kind),
                            ("status", SRC.status), ("team", SRC.team), ("zone", SRC.zone)):
            g.add((m, prop, Literal(r[field])))
        for a in r["aliases"]:
            g.add((m, SRC.alias, Literal(a)))
        if r["sla"]:
            g.add((m, SRC.sla, Literal(r["sla"])))
        for u in r["upstream"]:
            g.add((m, SRC.upstream, Literal(u)))
    for s in mon["slas"]:
        g.add((EX[s["sla_id"]], RDF.type, EX.SLA))
        g.add((EX[s["sla_id"]], EX.availability, Literal(str(s["availability"]), datatype=XSD.decimal)))
    for og, team in tables["owner_group_to_team"].items():
        g.add((EX[team], EX.cmdbOwnerGroup, Literal(og)))
    for dc, zone in tables["datacenter_to_zone"].items():
        g.add((EX[dc], EX.monitoringZone, Literal(zone)))
    return g


if __name__ == "__main__":
    (HERE / "data" / "rdf").mkdir(exist_ok=True)
    for n in SIZES:
        g = convert(n)
        g.serialize(HERE / "data" / "rdf" / f"raw_{n}.ttl", format="turtle")
        print(f"  graph {n}: {len(g)} raw triples")
