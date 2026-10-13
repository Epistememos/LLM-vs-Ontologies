"""questions2.py - Experiment 2 questions (L4: region failure and the tier rule), answers from truth.py.

Questions carry no definitions and never name the failed region: a scenario question is asked against a
scenario copy of the graph in which the failure is asserted as data. Most kinds are parameterised by an
entity, so question texts are distinct; parameter-free kinds appear once per graph size.
DEV additionally gets one "which region has failed?" check per size (level 'check', not scored as L4).

Writes exp2/data/questions.json (no answers) and exp2/data/answers.json. Run: python exp2/questions2.py
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
import truth  # noqa: E402

truth.DATA = HERE / "data"
SIZES = (20, 100, 500)
DEV_PER_SIZE = 6  # first 6 of the seeded shuffle per size; the rest is TEST
# kind -> quota per size, fixed before any run (parameterised kinds use distinct entities; parameter-free
# kinds appear once per size). A size gets fewer than the quota when it has too few distinct entities.
QUOTAS = {"is_down": 4, "is_lost": 3, "sla_breached": 3, "down_by_team": 2, "is_tier_risk": 2, "violates_edge": 2,
          "breached_slas": 1, "count_down": 1, "survivors": 1, "down_cfs": 1, "lost_dbs": 1,
          "violations": 1, "tier_risks": 1}


def candidates(t, rng):
    svc = t.primaries(*truth.SERVICE_TYPES)
    dbs = t.primaries("Database")
    cfs = t.primaries("CustomerFacingService")
    c = {k: [] for k in QUOTAS}
    for r in t.ids("Region"):
        down = set(t.down_services(r))
        for s in svc:
            c["is_down"].append((r, f"In this scenario, is {s} down?", "bool", s in down))
        for team in t.ids("Team"):
            owned = [s for s in svc if t.owner[s] == team]
            if owned:
                c["down_by_team"].append((r, f"In this scenario, which primary services owned by {team} are down?",
                                          "set", sorted(s for s in owned if s in down)))
        for d in dbs:
            c["is_lost"].append((r, f"In this scenario, is {d} lost?", "bool", t.lost(d, r)))
        for sla in t.ids("SLA"):
            c["sla_breached"].append((r, f"In this scenario, is {sla} breached?", "bool", sla in t.breached_slas(r)))
        c["breached_slas"].append((r, "In this scenario, which SLAs are breached?", "set", t.breached_slas(r)))
        c["count_down"].append((r, "In this scenario, how many primary services are down?", "number",
                                sum(s in down for s in svc)))
        c["survivors"].append((r, "In this scenario, which primary customer-facing services deployed in the failed "
                                  "region are not down?", "set",
                               sorted(x for x in cfs if t.region[x] == r and x not in down)))
        c["down_cfs"].append((r, "In this scenario, which primary customer-facing services are down?", "set",
                              sorted(x for x in cfs if x in down)))
        c["lost_dbs"].append((r, "In this scenario, which primary databases are lost?", "set",
                              sorted(d for d in dbs if t.lost(d, r))))
    c["violations"].append((None, "Which dependsOn edges violate the tier rule? Give each edge as 'SOURCE->TARGET'.",
                            "set", [f"{a}->{b}" for a, b in t.tier_violations()]))
    risks = sorted(s for s in t.ids(*truth.SERVICE_TYPES)
                   if t.tier(s) == 1 and any(t.tier(d) == 3 for d in t.dependencies(s)))
    c["tier_risks"].append((None, "Which services are tier risks?", "set", risks))
    for s in svc:
        if t.tier(s) == 1:
            c["is_tier_risk"].append((None, f"Is {s} a tier risk?", "bool", s in risks))
    bad = set(t.tier_violations())
    for a, b in t.dep.edges:
        if a in t.nodes and t.tier(a) and t.tier(b):
            c["violates_edge"].append((None, f"Does the dependsOn edge {a}->{b} violate the tier rule?", "bool",
                                       (a, b) in bad))
    return c


def pick(rng, pool, k):
    """Sample k; for bool kinds balance true/false; never repeat a text."""
    pool = rng.sample(pool, len(pool))
    if pool and pool[0][2] == "bool":
        yes = [p for p in pool if p[3]]
        no = [p for p in pool if not p[3]]
        pool = [p for pair in zip(yes, no) for p in pair] + yes[len(no):] + no[len(yes):]
    out, seen = [], set()
    for p in pool:
        if p[1] not in seen:
            out.append(p)
            seen.add(p[1])
        if len(out) == k:
            break
    return out


def build():
    questions, answers = [], {}
    for n in SIZES:
        t, rng = truth.Truth(n), random.Random(7000 + n)
        cands = candidates(t, rng)
        chosen = [(k, q) for k, quota in QUOTAS.items() for q in pick(rng, cands[k], quota)]
        rng.shuffle(chosen)
        for i, (kind, (scen, text, atype, ans)) in enumerate(chosen):
            qid = f"e2-{n}-L4-{i:02d}"
            questions.append(dict(qid=qid, size=n, level="L4", kind=kind, scenario=scen, answer_type=atype,
                                  split="dev" if i < DEV_PER_SIZE else "test", text=text))
            answers[qid] = ans
        r = rng.choice(t.ids("Region"))
        qid = f"e2-{n}-check-00"
        questions.append(dict(qid=qid, size=n, level="check", kind="failed_region", scenario=r, answer_type="set",
                              split="dev", text="In this scenario, which region has failed?"))
        answers[qid] = [r]
    (HERE / "data" / "questions.json").write_text(json.dumps(questions, indent=1))
    (HERE / "data" / "answers.json").write_text(json.dumps(answers, indent=1))
    return questions, answers


if __name__ == "__main__":
    import pandas as pd
    qs, ans = build()
    df = pd.DataFrame(qs)
    print(pd.crosstab([df["size"], df["split"]], df["level"], margins=True))
    print("\nkinds:", df.groupby("kind").size().to_dict())
    rep = df[df.level == "L4"].groupby("text").size()
    print(f"distinct L4 texts: {rep.size} of {int(rep.sum())}; texts repeated across sizes: "
          f"{sorted(rep[rep > 1].index)}")
    print("bool balance:", {k: f"{sum(ans[q] for q in g.qid)}/{len(g)} true"
                           for k, g in df[df.answer_type == "bool"].groupby("kind")})
    print("empty set answers:", sum(1 for q in qs if ans[q["qid"]] == []))
