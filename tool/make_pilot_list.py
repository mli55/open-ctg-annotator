#!/usr/bin/env python3
"""Select the pilot subset (~25 records) for manual decel annotation.

Criteria (2026-08-20, confirmed with user):
- always include rec 1180 / 1485 (the two exemplar records in decel_analysis)
- prioritise records with expert late decels and high algo-expert label
  disagreement (late recall is the known pain point)
- stratify hypoxia vs normal roughly half/half
- add a few low-decel records as clean controls

Reads research_log/tables/decel_analysis/, writes pilot.json next to this file.
"""
import csv
import json
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
TABLES = HERE.parent.parent / "tables" / "decel_analysis"

N_TOTAL = 25
N_CONTROLS = 3
SEEDS = [1180, 1485]


def read_csv(name):
    with open(TABLES / name, newline="") as f:
        return list(csv.DictReader(f))


def main():
    recs = {int(r["record_id"]): r for r in read_csv("records_algo.csv")}

    n_late = defaultdict(int)
    for r in read_csv("decel_events_expert.csv"):
        if r["label"] == "late":
            n_late[int(r["record_id"])] += 1

    n_match = defaultdict(int)
    n_disagree = defaultdict(int)
    for r in read_csv("algo_expert_matches.csv"):
        rid = int(r["record_id"])
        n_match[rid] += 1
        if r["algo_label"] != r["expert_label"]:
            n_disagree[rid] += 1

    scored = []
    for rid, r in recs.items():
        scored.append({
            "id": rid,
            "hypoxia": int(r["hypoxia"]),
            "ph": float(r["ph"]) if r["ph"] else None,
            "dur_min": float(r["dur_min"]),
            "n_decel": int(r["n_decel"]),
            "n_contraction": int(r["n_contraction"]),
            "n_expert_late": n_late[rid],
            "n_disagree": n_disagree[rid],
            "n_match": n_match[rid],
            "score": n_disagree[rid] + 2 * n_late[rid],
        })
    by_id = {s["id"]: s for s in scored}

    picked, reasons = [], {}

    def pick(rid, reason):
        if rid in picked:
            return
        picked.append(rid)
        reasons[rid] = reason

    for rid in SEEDS:
        if rid in by_id:
            pick(rid, "exemplar (decel_analysis §0)")

    # main picks: alternate strata, score-descending, need enough events to be informative
    pools = {
        1: sorted((s for s in scored if s["hypoxia"] == 1 and s["n_decel"] >= 8),
                  key=lambda s: -s["score"]),
        0: sorted((s for s in scored if s["hypoxia"] == 0 and s["n_decel"] >= 8),
                  key=lambda s: -s["score"]),
    }
    turn = 1
    while len(picked) < N_TOTAL - N_CONTROLS and (pools[0] or pools[1]):
        pool = pools[turn] if pools[turn] else pools[1 - turn]
        s = pool.pop(0)
        pick(s["id"], f"{'hypoxia' if s['hypoxia'] else 'normal'}, "
                      f"{s['n_expert_late']} expert late, {s['n_disagree']} label disagreements")
        turn = 1 - turn

    # controls: few decels, one per outcome first
    controls = sorted((s for s in scored if s["n_decel"] <= 5 and s["id"] not in picked),
                      key=lambda s: (s["n_decel"], s["id"]))
    got = {0: 0, 1: 0}
    for s in controls:
        if len(picked) >= N_TOTAL:
            break
        if got[s["hypoxia"]] >= 2 and got[1 - s["hypoxia"]] == 0:
            continue
        pick(s["id"], f"control ({s['n_decel']} decels, "
                      f"{'hypoxia' if s['hypoxia'] else 'normal'})")
        got[s["hypoxia"]] += 1

    out = []
    for rid in sorted(picked):
        s = by_id[rid]
        out.append({k: s[k] for k in ("id", "hypoxia", "ph", "dur_min",
                                      "n_decel", "n_contraction",
                                      "n_expert_late", "n_disagree")}
                   | {"reason": reasons[rid]})

    dest = HERE / "pilot.json"
    with open(dest, "w") as f:
        json.dump({"generated": "make_pilot_list.py", "n": len(out), "records": out},
                  f, indent=1)
    n_hyp = sum(1 for s in out if s["hypoxia"])
    n_ev = sum(s["n_decel"] + s["n_contraction"] for s in out)
    print(f"pilot.json: {len(out)} records ({n_hyp} hypoxia / {len(out)-n_hyp} normal), "
          f"{sum(s['n_decel'] for s in out)} detector decels, {n_ev} total events to review")
    for s in out:
        print(f"  rec {s['id']:>4}  pH {s['ph']:<5} decels {s['n_decel']:>2}  "
              f"lates {s['n_expert_late']:>2}  disagree {s['n_disagree']:>2}  — {s['reason']}")


if __name__ == "__main__":
    main()
