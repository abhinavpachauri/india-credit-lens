#!/usr/bin/env python3
"""
derive_opportunities.py — live opportunity/risk feed (COMPOSITION_SPEC §12.3)
----------------------------------------------------------------------------
Turns the model's opportunity/risk nodes from ad-hoc/hand-set into a DERIVED feed:
status (active|watch|closed) computed from whether each node's driver is firing in
S3 over the last 2 periods, with the signal evidence that decided it. Stamps the
surface/scope/refs fields the UI consumes (§12.2).

Status rule:
    driver fires in a period  := under force_check v3.1 (the pipeline's manifest): a force driver
                                 when its verdict is `working` (SYSTEM_MODEL_SPEC §16 Step 3); a
                                 LINE driver when it beats its group in the arrow's direction
                                 (force_check.line_verdict). Under v3.0: any of the driver's
                                 signals is non-flat (db status)
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
from pathlib import Path

# Bootstrap: put <repo>/analysis on sys.path so `from core import …` resolves from any
# cwd now that this script lives under core/. Move-safe via .git walk (see core/paths.py).
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs
from core import manifest  # noqa: E402
from core import force_check  # noqa: E402

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


def opportunity_status(fires_now: bool, fires_prior: bool, node_status: str | None = None,
                       unknown: bool = False) -> str:
    """The rule that decides whether an opportunity is live, and the only judgment this file makes.

    Two periods rather than one, deliberately: a single firing period is noise as often as it is
    a signal, so one period earns `watch` and two consecutive earn `active`.

    `retired` is a lifecycle decision made by a human in the model. Data must never resurrect it —
    a retired node whose driver starts firing again stays retired until someone says otherwise.
    """
    if node_status == "retired":
        return "retired"
    if fires_now and fires_prior:
        return "active"
    if fires_now or fires_prior:
        return "watch"
    # Nothing fired, but a driver could not be judged at all (a line with no group to compare
    # with): that is "we cannot tell", never "closed" (DECISIONS: absences stay visible).
    return "unassessable" if unknown else "closed"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", required=True, choices=manifest.model_pipelines())
    ap.add_argument("--period", required=True)
    args = ap.parse_args()

    cfg = gs.pipeline_cfg(args.pipeline)
    model = gs.load_json(cfg["model"])
    by_id = {n["id"]: n for n in model["nodes"]}
    fi_by_id = {f["id"]: f for f in model.get("force_instances", [])}
    urn_of = {n["id"]: n.get("urn") for n in model["nodes"] if n.get("tier") == "entity"}

    periods = periods_before(args.pipeline, args.period, 2)
    fire = {p: firing_signals(args.pipeline, p) for p in periods}
    cur, prior = (periods + [None, None])[0], (periods + [None, None])[1]

    # Under v3.1 a force fires when the data supports it, not when its signals merely move:
    # the same verdict S3 uses, recomputed for both periods from the same series.
    working = None
    if manifest.force_check(args.pipeline) == "v3.1":
        series, all_p = force_check.growth_series(args.pipeline, model), force_check.periods_of(args.pipeline)
        working = {p: {fid for fid, x in force_check.check(args.pipeline, model, p, series, all_p).items()
                       if x["verdict"] == "working"} for p in periods}
        dm = lambda q: force_check.resolve_csv_date(args.pipeline, q)  # noqa: E731

    # The arrow's polarity says which way the driver must move for the opportunity/risk to hold:
    # a line beating its group creates an opportunity (+), a line falling behind creates a risk (−).
    polarity = {(e["from"], e["to"]): (1 if e.get("polarity") == "+" else -1)
                for e in model["edges"] if e["type"] in ("creates_opportunity", "creates_risk")}

    unknown_drivers: dict[str, set] = {}

    def fires(driver_id, p, target=None):
        """Does this driver fire at period p, and on which of its signals?"""
        sigs = driver_signals(driver_id)
        if p is None:
            return False, set()
        if working is not None and driver_id in fi_by_id:
            on = driver_id in working[p]
            return on, (sigs & fire[p]) if on else set()
        if working is not None and driver_id in urn_of:
            # v3.1: a LINE fires when it beats its group in the arrow's direction, not whenever
            # any of its signals moved (which, like the old force check, could not fail).
            v = force_check.line_verdict(driver_id, polarity.get((driver_id, target), 1),
                                         model, series, all_p, p, dm)
            if v["verdict"] == "unassessable":
                unknown_drivers.setdefault(target, set()).add(driver_id)
            on = v["verdict"] == "working"
            return on, (sigs & fire.get(p, set())) if on else set()
        hit = sigs & fire.get(p, set())
        return bool(hit), hit

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
        now = [fires(d, cur, tid) for d in info["drivers"]]
        fires_now = any(on for on, _ in now)
        fires_prior = any(fires(d, prior, tid)[0] for d in info["drivers"])
        status = opportunity_status(fires_now, fires_prior, n.get("status"),
                                    unknown=bool(unknown_drivers.get(tid)))
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
            **({"unassessable_drivers": sorted(by_id[d]["label"] for d in unknown_drivers[tid])}
               if status == "unassessable" else {}),
            # evidence = the firing subset (drives STATUS); evidence_all = the driver's
            # full declared signal set (drives TRACEABILITY — a structural risk's numbers
            # trace to its signals even when the driver isn't currently firing).
            "evidence": sorted(set().union(set(), *[hit for _, hit in now])),
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
                  "periods_used": periods, "note": "status derived from S3 driver firing",
                  "force_rule": manifest.force_check(args.pipeline)},
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
