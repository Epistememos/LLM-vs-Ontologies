"""make_h2.py - the two pre-registered H2 changes, applied to data only (no artifact is touched here).

1. Schema change: the CMDB export renames `datacenter` to `site` (values and field order unchanged).
   Writes exp3/data/h2/cmdb_{n}.json; the monitoring export is unchanged.
2. Definition change ("lost"): a non-database component is lost if its footprint contains only the failed region;
   a database is lost if fewer than two of its footprint regions lie outside the failed region.
   Writes the new answer key exp3/data/hidden/h2_answers.json from the canonical ground truth (truth3 / NetworkX),
   independently of B3's glue and C3's rules.
Run (from the repo root): python exp3/h2/make_h2.py
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
EXP3 = HERE.parent
sys.path[:0] = [str(EXP3.parent / "exp1"), str(EXP3)]
import questions3  # noqa: E402
import truth3  # noqa: E402

H2_DATA = EXP3 / "data" / "h2"


class NewLostTruth:
    """Canonical ground truth under the changed "lost" definition (wraps exp1's Truth)."""

    def __init__(self, t):
        self.t = t

    def __getattr__(self, name):
        return getattr(self.t, name)

    def lost(self, x, r):
        fp = self.t.footprint(x)
        if self.t.nodes[x]["type"] == "Database":
            return len(fp - {r}) < 2
        return fp <= {r}

    def down_services(self, r):
        services = self.t.ids(*truth3.truth.SERVICE_TYPES)
        return sorted(s for s in services if self.lost(s, r) or any(self.lost(d, r) for d in self.t.dependencies(s)))

    def breached_slas(self, r):
        return sorted({self.t.sla[s] for s in self.down_services(r) if s in self.t.sla})


def rename_field(n):
    cmdb = json.loads((EXP3 / "data" / f"cmdb_{n}.json").read_text())
    cmdb["records"] = [{("site" if k == "datacenter" else k): v for k, v in r.items()} for r in cmdb["records"]]
    H2_DATA.mkdir(parents=True, exist_ok=True)
    (H2_DATA / f"cmdb_{n}.json").write_bytes(json.dumps(cmdb, indent=1).encode())


def new_answers():
    qs = json.loads((EXP3 / "data" / "questions.json").read_text())
    old = json.loads((truth3.HIDDEN / "answers.json").read_text())
    new = {}
    for n in (20, 100, 500):
        t = NewLostTruth(truth3.truth_for(n))
        _, key, _, _ = truth3.load(n)
        for q in (q for q in qs if q["size"] == n):
            a = old[q["qid"]]
            new[q["qid"]] = dict(answer=questions3.answers(t, key, q["kind"], a["region"], a["entity"]),
                                 region=a["region"], entity=a["entity"])
    (truth3.HIDDEN / "h2_answers.json").write_bytes(json.dumps(new, indent=1).encode())
    return qs, old, new


if __name__ == "__main__":
    for n in (20, 100, 500):
        rename_field(n)
    qs, old, new = new_answers()
    test = [q for q in qs if q["split"] == "test"]
    changed = [q for q in test if new[q["qid"]]["answer"] != old[q["qid"]]["answer"]]
    print(f"renamed datacenter -> site in 3 CMDB exports; new answer key: {len(changed)}/{len(test)} TEST answers change "
          f"(cross-source {sum(q['scope'] == 'cross' for q in changed)}, controls {sum(q['scope'] == 'control' for q in changed)})")
