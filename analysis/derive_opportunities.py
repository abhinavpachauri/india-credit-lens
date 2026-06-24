#!/usr/bin/env python3
"""
derive_opportunities.py — live opportunity/risk feed (COMPOSITION_SPEC §12.3)
----------------------------------------------------------------------------
Turns the model's opportunity/risk nodes from ad-hoc/hand-set into a DERIVED feed:
status (active|watch|closed) computed from whether each node's driver is firing in
S3 over the last 2 periods, with the signal evidence that decided it. Stamps the
surface/scope/refs fields the UI consumes (§12.2).

Status rule:
    driver fires in a period  := any of its signal_evidence / signal_ids is non-flat (db status)
    active  — driver fires in the current AND prior period
    watch   — driver fires in exactly one of the two
    closed  — driver fires in neither

Output: analysis/{pipeline}/merged/opportunities_{period}.json

Usage:
    python3 analysis/derive_opportunities.py --pipeline sibc --period 2026-05-29
"""
import argparse
import json
import sqlite3
import sys

from core import generate_skeleton as gs

DB = gs.ANALYSIS / "signals" / "signals.db"
NONFLAT = {"strengthening", "weakening", "declining", "active"}


def periods_before(pipeline, period, n=2):
    con = sqlite3.connect(DB)
    ps = [r[0] for r in con.execute(
        "select distinct period from signals where pipeline=? and period<=? order by period desc",
        (pipeline, period)).fetchall()]
    con.close()
    return ps[:n]


def firing_signals(pipeline, period):
    con = sqlite3.connect(DB)
    rows = con.execute("select metric_id, status from signals where pipeline=? and period=?",
                       (pipeline, period)).fetchall()
    con.close()
    return {m for m, s in rows if s in NONFLAT}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", required=True, choices=list(gs.PIPELINES))
    ap.add_argument("--period", required=True)
    args = ap.parse_args()

    cfg = gs.PIPELINES[args.pipeline]
    model = gs.load_json(cfg["model"])
    by_id = {n["id"]: n for n in model["nodes"]}
    fi_by_id = {f["id"]: f for f in model.get("force_instances", [])}
    urn_of = {n["id"]: n.get("urn") for n in model["nodes"] if n.get("tier") == "entity"}

    periods = periods_before(args.pipeline, args.period, 2)
    fire = {p: firing_signals(args.pipeline, p) for p in periods}
    cur, prior = (periods + [None, None])[0], (periods + [None, None])[1]

    # driver → its evidence signal set
    def driver_signals(driver_id):
        if driver_id in fi_by_id:
            return set(fi_by_id[driver_id].get("signal_evidence") or [])
        if driver_id in by_id and by_id[driver_id].get("tier") == "entity":
            return set(by_id[driver_id].get("signal_ids") or [])
        return set()

    # collect drivers per opportunity/risk
    targets = {n["id"]: {"node": n, "drivers": []} for n in model["nodes"]
               if n.get("tier") in ("opportunity", "risk")}
    for e in model["edges"]:
        if e["type"] in ("creates_opportunity", "creates_risk") and e["to"] in targets:
            targets[e["to"]]["drivers"].append(e["from"])

    feed = []
    for tid, info in targets.items():
        n = info["node"]
        sigs = set().union(*[driver_signals(d) for d in info["drivers"]]) if info["drivers"] else set()
        fires_now = bool(sigs & fire.get(cur, set())) if cur else False
        fires_prior = bool(sigs & fire.get(prior, set())) if prior else False
        if n.get("status") == "retired":
            status = "retired"          # lifecycle decision — never data-resurrected
        elif fires_now and fires_prior:
            status = "active"
        elif fires_now or fires_prior:
            status = "watch"
        else:
            status = "closed"
        # references for the UI (§12.2)
        entity_refs, instance_refs, channel_refs = [], [], []
        for d in info["drivers"]:
            if d in fi_by_id:
                instance_refs.append(d)
                channel_refs.append(fi_by_id[d].get("instance_of"))
                entity_refs += fi_by_id[d].get("scope_entities", [])
            elif d in urn_of:
                entity_refs.append(urn_of[d])
        feed.append({
            "id": tid, "tier": n["tier"], "label": n["label"],
            "surface": "opportunities" if n["tier"] == "opportunity" else args.pipeline,
            "scope": "pipeline",
            "status": status,
            "authored_status": n.get("status"),
            # evidence = the firing subset (drives STATUS); evidence_all = the driver's
            # full declared signal set (drives TRACEABILITY — a structural risk's numbers
            # trace to its signals even when the driver isn't currently firing).
            "evidence": sorted(sigs & fire.get(cur, set())),
            "evidence_all": sorted(sigs),
            "refs": {
                "entities": sorted(set(entity_refs)),
                "instances": sorted(set(instance_refs)),
                "channels": sorted(set(c for c in channel_refs if c)),
            },
        })

    out = {
        "_meta": {"pipeline": args.pipeline, "period": args.period,
                  "spec_ref": "analysis/COMPOSITION_SPEC.md §12",
                  "periods_used": periods, "note": "status derived from S3 driver firing"},
        "items": sorted(feed, key=lambda x: (x["tier"], x["id"])),
    }
    out_path = cfg["model"].parent / f"opportunities_{args.period}.json"
    out_path.write_text(json.dumps(out, indent=2, ensure_ascii=False))

    from collections import Counter
    byst = Counter(f"{i['tier']}:{i['status']}" for i in feed)
    print(f"[{args.pipeline} {args.period}] derived {len(feed)} opportunity/risk items over periods {periods}")
    for k, v in sorted(byst.items()):
        print(f"    {k:24s} {v}")
    for i in feed:
        if i["status"] != "active":
            continue
        print(f"  ✓ {i['status']:6s} {i['tier']:11s} {i['label'][:46]}")
    print(f"  → wrote {out_path.relative_to(gs.ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
