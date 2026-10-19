"""questions3.py - Experiment 3 questions, answers from truth3 (canonical graph), DEV/TEST split by seed.

Cross-source questions need both exports: failure is named by a CMDB datacenter, dependencies come from both
exports, and SLAs and teams come from monitoring. Control questions need one export only. Answers use one
namespace per entity kind: services as CMDB CI IDs, SLAs as monitoring SLA IDs, teams as monitoring team names.
Each question records which wrong readings ('traps') would change its answer: ignoring the monitoring export,
keeping stale records, or trusting the non-authoritative source.

Writes exp3/data/questions.json (no answers) and exp3/data/hidden/answers.json. Run: python exp3/questions3.py
"""
import json
import random
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import truth3  # noqa: E402

SIZES = (20, 100, 500)
DEV_FRAC = 0.3
QUOTAS = {"is_down": 8, "down_by_team": 5, "breached_slas": 3, "sla_breached": 4, "count_down": 2,  # cross-source
          "cmdb_deps": 2, "mon_owner": 2}                                                         # single-source
CROSS = {"is_down", "down_by_team", "breached_slas", "sla_breached", "count_down"}
VARIANTS = ("cmdb_only", "keep_stale", "wrong_authority", "name_similarity")
LABEL = {"cmdb_only": "ignores the monitoring export", "keep_stale": "keeps stale records",
         "wrong_authority": "trusts the wrong source", "name_similarity": "matches entities by name similarity"}


def answers(t, key, kind, region, x):
    """Answer for one question on Truth t, in the answer namespaces."""
    cmdb = lambda c: key["entities"][c]["cmdb"] if c in key["entities"] else c
    svc = t.primaries(*truth3.truth.SERVICE_TYPES)
    down = set(t.down_services(region)) if region else set()
    return {
        "is_down": lambda: x in down,
        "down_by_team": lambda: sorted(cmdb(s) for s in svc if t.owner.get(s) == x and s in down),
        "breached_slas": lambda: sorted(key["slas"][s] for s in t.breached_slas(region)),
        "sla_breached": lambda: x in t.breached_slas(region),
        "count_down": lambda: sum(s in down for s in svc),
        "cmdb_deps": lambda: sorted(cmdb(d) for d in t.dependencies(x) if t.nodes[d]["type"] in truth3.truth.SERVICE_TYPES),
        "mon_owner": lambda: [key["teams"][t.owner[x]]["monitoring"]],
    }[kind]()


def candidates(n, rng):
    canon, key, _, _ = truth3.load(n)
    t = truth3.truth_for(n)
    ent, svc = key["entities"], t.primaries(*truth3.truth.SERVICE_TYPES)
    name = lambda x: rng.choice([ent[x]["display"]] + ent[x]["aliases"])  # monitoring vocabulary
    dc = lambda r: key["regions"][r]["cmdb"]                                # CMDB vocabulary
    c = {k: [] for k in QUOTAS}
    for r in t.ids("Region"):
        for s in svc:
            c["is_down"].append((r, s, f'If datacenter {dc(r)} fails, is "{name(s)}" down?', "bool"))
        for team in t.ids("Team"):
            c["down_by_team"].append((r, team, f"If datacenter {dc(r)} fails, which primary services owned by "
                                               f"{key['teams'][team]['monitoring']} are down? Give CMDB CI IDs.", "set"))
        c["breached_slas"].append((r, None, f"If datacenter {dc(r)} fails, which SLAs are breached? "
                                            f"Give monitoring SLA IDs.", "set"))
        for s in t.ids("SLA"):
            c["sla_breached"].append((r, s, f"If datacenter {dc(r)} fails, is {key['slas'][s]} breached?", "bool"))
        c["count_down"].append((r, None, f"If datacenter {dc(r)} fails, how many primary services are down?", "number"))
    for s in svc:
        if any(t.nodes[d]["type"] in truth3.truth.SERVICE_TYPES for d in t.dependencies(s)):
            c["cmdb_deps"].append((None, s, f"Which services does {ent[s]['cmdb']} transitively depend on? "
                                            f"Give CMDB CI IDs.", "set"))
        c["mon_owner"].append((None, s, f'Which team owns "{name(s)}"? Give the monitoring team name.', "set"))
    return t, key, c


def pick(rng, pool, k, t, key, kind):
    pool = rng.sample(pool, len(pool))
    if pool and pool[0][3] == "bool":  # balance true/false
        yes = [p for p in pool if answers(t, key, kind, p[0], p[1])]
        no = [p for p in pool if not answers(t, key, kind, p[0], p[1])]
        pool = [p for pair in zip(yes, no) for p in pair] + yes[len(no):] + no[len(yes):]
    out, seen = [], set()
    for p in pool:
        if p[2] not in seen:
            out.append(p)
            seen.add(p[2])
        if len(out) == k:
            break
    return out


def build():
    questions, ans = [], {}
    for n in SIZES:
        rng = random.Random(9000 + n)
        t, key, cands = candidates(n, rng)
        variants = {v: truth3.truth_for(n, truth3.rebuild(n, v)[0]) for v in VARIANTS}
        chosen = [(k, q) for k, quota in QUOTAS.items() for q in pick(rng, cands[k], quota, t, key, k)]
        rng.shuffle(chosen)
        n_dev = round(DEV_FRAC * len(chosen))
        for i, (kind, (region, x, text, atype)) in enumerate(chosen):
            qid = f"e3-{n}-{i:02d}"
            gold = answers(t, key, kind, region, x)
            traps = [v for v, tv in variants.items() if answers(tv, key, kind, region, x) != gold]
            questions.append(dict(qid=qid, size=n, scope="cross" if kind in CROSS else "control", kind=kind,
                                  answer_type=atype, split="dev" if i < n_dev else "test", text=text))
            ans[qid] = dict(answer=gold, region=region, entity=x, traps=traps)
    (truth3.DATA3 / "questions.json").write_bytes(json.dumps(questions, indent=1).encode())
    (truth3.HIDDEN / "answers.json").write_bytes(json.dumps(ans, indent=1).encode())
    return questions, ans


if __name__ == "__main__":
    import pandas as pd
    qs, ans = build()
    df = pd.DataFrame(qs)
    df["traps"] = df.qid.map(lambda q: len(ans[q]["traps"]))
    print(pd.crosstab([df["size"], df["split"]], df["scope"], margins=True))
    cross = df[df.scope == "cross"]
    print(f"\ncross-source questions with >= 1 active trap: {(cross.traps > 0).mean():.0%}")
    for v in VARIANTS:
        print(f"  answer changes if a model {LABEL[v]}: "
              f"{sum(v in ans[q]['traps'] for q in cross.qid)}/{len(cross)}")
    print("distinct texts:", df.text.nunique(), "of", len(df))
