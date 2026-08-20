#!/usr/bin/env python3
"""Claude first-pass annotation pipeline (2026-08-20).

  render <rid> <outdir>              render overview + per-decel detail figures
  write  <rid> <decisions.json>      build annotations/decel_manual/claude/rec_<rid>.json

Detail figures show objective features only — the detector's own typing is
deliberately withheld so the (Claude) annotator classifies blind, mirroring the
protocol the human annotator follows in the web tool. Event ids replicate the
web tool's prefill numbering exactly, so decisions and tool edits stay aligned.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
DATA = Path.home() / "Documents/git/ctg-analyzer/data"
ANN = HERE.parent.parent / "annotations" / "decel_manual" / "claude"


def load(rid):
    return json.loads((DATA / f"rec_{rid}.json").read_text())


def prefill_ids(rec):
    """Replicate annotator.html prefill(): shared counter over decels+contractions."""
    n = 0
    decels, cons = [], []
    for e in rec["events"]:
        if e["k"] == "deceleration":
            n += 1
            decels.append({"id": f"d{n}", "a": e["a"], "b": e["b"], "det": e.get("d")})
        elif e["k"] == "contraction":
            n += 1
            cons.append({"id": f"c{n}", "a": e["a"], "b": e["b"]})
    return decels, cons, n


def arrs(rec):
    s = rec["strip"]
    x = np.array(s["x"], float)
    fhr = np.array([np.nan if v is None else v for v in s["fhr"]], float)
    uc = np.array([np.nan if v is None else v for v in s["uc"]], float)
    base = np.array([np.nan if v is None else v for v in s["base"]], float)
    return x, fhr, uc, base


def feats(x, fhr, uc, base, cons, a, b):
    m = (x >= a) & (x <= b)
    f = np.where(m, fhr, np.nan)
    out = {"dur_s": (b - a) * 60}
    if np.all(np.isnan(f)):
        out.update(nadir=None, depth=None, o2n=None, rec_s=None)
    else:
        i = int(np.nanargmin(f))
        out["nadir"] = x[i]
        bl = base[i] if not np.isnan(base[i]) else np.nanmedian(base)
        out["depth"] = bl - fhr[i]
        out["o2n"] = (x[i] - a) * 60
        out["rec_s"] = (b - x[i]) * 60
    ov = [c for c in cons if c["b"] > a - 0.1 and c["a"] < b + 0.1]
    near = [c for c in cons if c["b"] > a - 1.5 and c["a"] < b + 1.5]
    link = ov[0] if ov else (near[0] if near else None)
    out["lag_s"] = None
    out["uc_peak"] = None
    if link is not None and out.get("nadir") is not None:
        mc = (x >= link["a"]) & (x <= link["b"])
        ucw = np.where(mc, uc, np.nan)
        if not np.all(np.isnan(ucw)):
            p = int(np.nanargmax(ucw))
            out["uc_peak"] = x[p]
            out["lag_s"] = (out["nadir"] - x[p]) * 60
    w = (x >= a - 1) & (x <= b + 1)
    out["uc_valid"] = float(np.mean(~np.isnan(uc[w]))) if w.any() else 0.0
    return out


def render(rid, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rec = load(rid)
    decels, cons, _ = prefill_ids(rec)
    x, fhr, uc, base = arrs(rec)
    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)

    # ---- overview ----
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(18, 6), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(x, fhr, "k", lw=.5)
    a1.plot(x, base, "b", lw=.6, alpha=.6)
    for d in decels:
        a1.axvspan(d["a"], d["b"], color="#ff9500", alpha=.25)
        a1.text((d["a"] + d["b"]) / 2, 205, d["id"], fontsize=6, ha="center", color="#b06000")
    if rec.get("ii_start") is not None:
        for ax in (a1, a2):
            ax.axvline(rec["ii_start"], color="#c9a227", ls="--", lw=.8)
    a1.set_ylim(50, 215); a1.set_ylabel("FHR")
    a1.set_title(f"rec {rid} · pH {rec.get('ph')} · overview")
    a2.plot(x, uc, color="#555", lw=.5)
    for c in cons:
        a2.axvspan(c["a"], c["b"], color="#c8a24b", alpha=.25)
        a2.text((c["a"] + c["b"]) / 2, a2.get_ylim()[1] * .9, c["id"],
                fontsize=5, ha="center", color="#7a6220")
    a2.set_ylabel("UC")
    a2.set_xlabel("min before delivery")
    fig.tight_layout()
    fig.savefig(outdir / f"rec{rid}_overview.png", dpi=110)
    plt.close(fig)

    # ---- detail grids: 4x4 cells, each cell = FHR over UC ----
    per = 16
    for gi in range(0, len(decels), per):
        chunk = decels[gi:gi + per]
        rows = (len(chunk) + 3) // 4
        fig = plt.figure(figsize=(19, 4.6 * rows))
        gs = fig.add_gridspec(rows * 2, 4, height_ratios=[2.2, 1] * rows,
                              hspace=.55, wspace=.25)
        for ci, d in enumerate(chunk):
            r, c = divmod(ci, 4)
            f = feats(x, fhr, uc, base, cons, d["a"], d["b"])
            pad = max(2.0, (d["b"] - d["a"]) * .6 + 1.0)
            w0, w1 = d["a"] - pad, d["b"] + pad
            m = (x >= w0) & (x <= w1)
            axF = fig.add_subplot(gs[r * 2, c])
            axU = fig.add_subplot(gs[r * 2 + 1, c], sharex=axF)
            axF.plot(x[m], fhr[m], "k", lw=.7)
            axF.plot(x[m], base[m], "b", lw=.7, alpha=.6)
            axF.axvspan(d["a"], d["b"], color="#ff9500", alpha=.2)
            if f["nadir"] is not None:
                axF.plot([f["nadir"]], [fhr[np.searchsorted(x, f["nadir"])]], "r.", ms=6)
            ylo = np.nanmin(fhr[m]) if not np.all(np.isnan(fhr[m])) else 60
            axF.set_ylim(min(60, ylo - 10), 200)
            axU.plot(x[m], uc[m], color="#555", lw=.7)
            for cc in cons:
                if cc["b"] > w0 and cc["a"] < w1:
                    axU.axvspan(cc["a"], cc["b"], color="#c8a24b", alpha=.25)
            if f["uc_peak"] is not None:
                axU.axvline(f["uc_peak"], color="#7a6220", lw=.8, ls=":")
                axF.axvline(f["uc_peak"], color="#7a6220", lw=.8, ls=":")
            if np.all(np.isnan(uc[m])):
                axU.text(.5, .5, "UC missing", transform=axU.transAxes,
                         ha="center", color="#999")
            lag = "—" if f["lag_s"] is None else f"{f['lag_s']:+.0f}s"
            dep = "—" if f["depth"] is None else f"{f['depth']:.0f}"
            o2n = "—" if f["o2n"] is None else f"{f['o2n']:.0f}s"
            rc = "—" if f["rec_s"] is None else f"{f['rec_s']:.0f}s"
            axF.set_title(f"{d['id']} · {f['dur_s']:.0f}s · o2n {o2n} · depth {dep} · "
                          f"nadir-lag {lag} · rec {rc} · UCok {f['uc_valid']:.0%}",
                          fontsize=7.5)
            axF.tick_params(labelsize=6); axU.tick_params(labelsize=6)
        fig.savefig(outdir / f"rec{rid}_detail_{gi // per + 1}.png", dpi=110)
        plt.close(fig)
    print(f"rendered rec {rid}: {len(decels)} decels, {len(cons)} contractions -> {outdir}")


def write(rid, decisions_path):
    rec = load(rid)
    decels, cons, n = prefill_ids(rec)
    dec = json.loads(Path(decisions_path).read_text())
    assert int(dec["record_id"]) == int(rid)
    dd = dec.get("decels", {})
    missing = [d["id"] for d in decels if d["id"] not in dd]
    assert not missing, f"no decision for: {missing}"
    unknown = [k for k in dd if k not in {d['id'] for d in decels}]
    assert not unknown, f"decisions for unknown ids: {unknown}"

    x, fhr, uc, base = arrs(rec)

    def nadir_of(a, b):
        m = (x >= a) & (x <= b)
        f = np.where(m, fhr, np.nan)
        if np.all(np.isnan(f)):
            return None
        return float(x[int(np.nanargmin(f))])

    out_d, deleted = [], []
    now = datetime.now(timezone.utc).isoformat()
    for d in decels:
        c = dd[d["id"]]
        base_ev = {"id": d["id"], "a": d["a"], "b": d["b"], "a0": d["a"], "b0": d["b"],
                   "origin": "detector", "det_type": d["det"]}
        if c.get("delete"):
            deleted.append({"list": "decels", **base_ev, "review": "deleted",
                            "type": None, "uc_unreadable": False,
                            "reason": c["delete"] if isinstance(c["delete"], str) else ""})
            continue
        a, b = c.get("a", d["a"]), c.get("b", d["b"])
        edited = abs(a - d["a"]) > 1e-9 or abs(b - d["b"]) > 1e-9
        out_d.append({**base_ev, "a": a, "b": b,
                      "review": "edited" if edited else "accepted",
                      "type": c.get("type"), "uc_unreadable": bool(c.get("uc", False)),
                      "nadir_min": nadir_of(a, b)})
    for add in dec.get("adds", []):
        n += 1
        out_d.append({"id": f"dm{n}", "a": add["a"], "b": add["b"], "a0": None, "b0": None,
                      "origin": "manual", "review": "added", "type": add.get("type"),
                      "uc_unreadable": bool(add.get("uc", False)), "det_type": None,
                      "nadir_min": nadir_of(add["a"], add["b"])})
    out_d.sort(key=lambda e: e["a"])
    bad = [e["id"] for e in out_d if not (e["type"] or e["uc_unreadable"])]
    assert not bad, f"untyped decels: {bad}"

    con_dec = dec.get("cons", "accept_all")
    out_c = [{"id": c0["id"], "a": c0["a"], "b": c0["b"], "a0": c0["a"], "b0": c0["b"],
              "origin": "detector", "review": "accepted"} for c0 in cons]
    for add in dec.get("con_adds", []):
        n += 1
        out_c.append({"id": f"cm{n}", "a": add["a"], "b": add["b"], "a0": None, "b0": None,
                      "origin": "manual", "review": "added"})
    out_c.sort(key=lambda e: e["a"])
    if isinstance(con_dec, dict):
        for cid, cc in con_dec.items():
            ev = next(e for e in out_c if e["id"] == cid)
            if cc.get("delete"):
                out_c.remove(ev)
                deleted.append({"list": "contractions", **ev, "review": "deleted"})
            else:
                if "a" in cc: ev["a"] = cc["a"]
                if "b" in cc: ev["b"] = cc["b"]
                if ev["a"] != ev["a0"] or ev["b"] != ev["b0"]:
                    ev["review"] = "edited"

    ann = {"schema": 1, "record_id": int(rid), "annotator": "claude",
           "status": dec.get("status", "done"), "notes": dec.get("notes", ""),
           "next_id": n + 1, "decels": out_d, "contractions": out_c,
           "deleted": deleted, "updated": now}
    ANN.mkdir(parents=True, exist_ok=True)
    dest = ANN / f"rec_{rid}.json"
    dest.write_text(json.dumps(ann, indent=1))
    t = {}
    for e in out_d:
        k = e["type"] or "uc_unreadable"
        t[k] = t.get(k, 0) + 1
    print(f"wrote {dest.name}: {len(out_d)} decels {t}, "
          f"{len(out_c)} cons, {len(deleted)} deleted")


def zoom(rid, t0, t1, outdir):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    rec = load(rid)
    decels, cons, _ = prefill_ids(rec)
    x, fhr, uc, base = arrs(rec)
    m = (x >= t0) & (x <= t1)
    fig, (a1, a2) = plt.subplots(2, 1, figsize=(16, 6), sharex=True,
                                 gridspec_kw={"height_ratios": [2, 1]})
    a1.plot(x[m], fhr[m], "k", lw=.8)
    a1.plot(x[m], base[m], "b", lw=.8, alpha=.6)
    for d in decels:
        if d["b"] > t0 and d["a"] < t1:
            a1.axvspan(d["a"], d["b"], color="#ff9500", alpha=.22)
            a1.text((d["a"] + d["b"]) / 2, 198, d["id"], fontsize=8, ha="center", color="#b06000")
    a1.set_ylim(50, 205); a1.set_ylabel("FHR"); a1.grid(True, lw=.3, alpha=.5)
    a1.xaxis.set_tick_params(labelbottom=True)
    a1.set_title(f"rec {rid} zoom {t0}..{t1}")
    a2.plot(x[m], uc[m], color="#555", lw=.8)
    for c in cons:
        if c["b"] > t0 and c["a"] < t1:
            a2.axvspan(c["a"], c["b"], color="#c8a24b", alpha=.25)
            a2.text((c["a"] + c["b"]) / 2, 1, c["id"], fontsize=7, ha="center", color="#7a6220")
    a2.grid(True, lw=.3, alpha=.5); a2.set_ylabel("UC"); a2.set_xlabel("min")
    fig.tight_layout()
    dest = Path(outdir) / f"rec{rid}_zoom_{t0}_{t1}.png"
    fig.savefig(dest, dpi=110)
    plt.close(fig)
    print(dest)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "render":
        render(int(sys.argv[2]), sys.argv[3])
    elif cmd == "zoom":
        zoom(int(sys.argv[2]), float(sys.argv[3]), float(sys.argv[4]), sys.argv[5])
    elif cmd == "write":
        write(int(sys.argv[2]), sys.argv[3])
    else:
        raise SystemExit("usage: claude_pass.py render|zoom|write ...")
