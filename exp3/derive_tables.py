"""derive_tables.py - derive the team and region crosswalks from the two exports (never from data/hidden/).

For each CMDB owner group, the monitoring team most often recorded for the same components (majority vote over
non-stale records); likewise datacenter -> zone. Contradictions are a minority, so the majority is the mapping.
Both B3 (glue.py) and C3 (to_rdf3.py) use the resulting file, so their crosswalks are identical by construction.
Writes exp3/mapping_tables.json. Run (from the repo root): python exp3/derive_tables.py
"""
import json
import re
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
SIZES = (20, 100, 500)


def mon_id(ci_name):
    """CMDB name -> monitoring component ID (identity rule shared by glue.py and rules3.py)."""
    return "mon:" + re.sub(r"_(svc|db|q)$", "", ci_name).replace("_", "-")


def derive(n):
    cmdb = json.loads((HERE / "data" / f"cmdb_{n}.json").read_text())["records"]
    mon = {r["component"]: r for r in json.loads((HERE / "data" / f"monitoring_{n}.json").read_text())["records"]}
    teams, regions = defaultdict(Counter), defaultdict(Counter)
    for r in cmdb:
        m = mon.get(mon_id(r["ci_name"]))
        if r["status"] == "decommissioned" or m is None or m["status"] == "retired":
            continue
        teams[r["owner_group"]][m["team"]] += 1
        regions[r["datacenter"]][m["zone"]] += 1
    pick = lambda votes: {k: c.most_common(1)[0][0] for k, c in sorted(votes.items())}
    return {"owner_group_to_team": pick(teams), "datacenter_to_zone": pick(regions)}


if __name__ == "__main__":
    tables = {str(n): derive(n) for n in SIZES}
    (HERE / "mapping_tables.json").write_bytes(json.dumps(tables, indent=1).encode())
    for n, t in tables.items():
        print(f"  graph {n}: {len(t['owner_group_to_team'])} team mappings, {len(t['datacenter_to_zone'])} region mappings")
