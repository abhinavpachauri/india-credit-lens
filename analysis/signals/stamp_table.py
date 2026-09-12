#!/usr/bin/env python3
"""
stamp_table.py — ship every cut's Layer 1 table, precomputed (DASHBOARD_SPEC §17)
─────────────────────────────────────────────────────────────────────────────────
A sidecar, exactly like `stamp_planes` and `stamp_state`: the browser joins it by cut id
and draws what it is given. It formats nothing, because a browser that formats numbers is
a publishing surface no validator can see.

The cut list is DISCOVERED from the registry — every signal computed by a momentum method
IS a cut — rather than declared here. A second list would be the drift this project keeps
paying for, and it is how coverage came to be audited against MOVEMENT_CUTS (a table in
the card generator) while seven sub-cuts the dashboard draws went unchecked for a month.

    python3 analysis/signals/stamp_table.py --pipeline sibc
    python3 analysis/signals/stamp_table.py --pipeline sibc --check
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import table_rows                                            # noqa: E402

DATA = ROOT / "web" / "public" / "data"
DB = ROOT / "analysis" / "signals" / "signals.db"
REGISTRY = ROOT / "analysis" / "signals" / "registry.json"
SIDECAR = {p: DATA / f"{p}_table.json" for p in ("sibc", "atm_pos")}
MOMENTUM = ("csv_sector_momentum", "csv_category_momentum")


def parent_rates(pipeline: str) -> dict[str, str]:
    """{stem: the signal holding the PARENT's own growth} — read from the generator's own cut
    table, the single place that declares it (§16 uses the same field)."""
    if pipeline == "sibc":
        from pipelines.sibc.generate_analysis_report import MOVEMENT_CUTS
        prefix = "sibc-"
    else:
        from pipelines.atm_pos.generate_atm_pos_insights import MOVEMENT_CUTS, MOVEMENT_PREFIX
        prefix = None
    out = {}
    for c in MOVEMENT_CUTS:
        stem = f"{prefix}{c.slug}" if prefix else f"{MOVEMENT_PREFIX[c.section]}{c.slug}"
        if c.parent_yoy:
            out[stem] = c.parent_yoy
    return out


def cuts(pipeline: str) -> dict[str, str]:
    """{stem: unit} for every cut in this pipeline — discovered, never declared."""
    reg = json.loads(REGISTRY.read_text())["signals"]
    out = {}
    for sid, sig in reg.items():
        c = sig.get("compute", {})
        if sig.get("pipeline") != pipeline or c.get("method") not in MOMENTUM:
            continue
        stem = sid[: -len("-momentum")]
        # The unit the SIZE scan declares — the level's unit, not the momentum's.
        size = reg.get(f"{stem}-size-scan", {}).get("compute", {})
        out[stem] = size.get("unit", "rs_cr" if pipeline == "sibc" else "count")
    return out


def latest_period(conn, pipeline: str) -> str:
    return conn.execute("SELECT MAX(period) FROM signals WHERE pipeline=?", (pipeline,)).fetchone()[0]


def build(pipeline: str, period: str | None = None) -> dict:
    conn = sqlite3.connect(DB)
    try:
        period = period or latest_period(conn, pipeline)
        tables, rates = {}, parent_rates(pipeline)
        for stem, unit in sorted(cuts(pipeline).items()):
            t = table_rows.build(conn, pipeline, period, stem, unit, rates.get(stem))
            if t is not None:          # a cut without its 12-month window has no table yet
                tables[stem] = t
    finally:
        conn.close()
    return {
        "_meta": {
            "pipeline": pipeline,
            "period": period,
            "purpose": "One Layer 1 table per cut — every part of the cut with size, share, "
                       "growth, pace, the run of readings, and its share of the new money. "
                       "Numbers are rendered here and shipped as strings; `sort` orders and is "
                       "never drawn. Regenerated every gate; freshness-guarded with --check.",
            "spec": "analysis/DASHBOARD_SPEC.md §17",
        },
        "cuts": tables,
    }


def write(pipeline: str) -> dict:
    payload = build(pipeline)
    SIDECAR[pipeline].write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    return payload


def check(pipeline: str):
    if not SIDECAR[pipeline].exists():
        return False, "sidecar missing — run without --check"
    on_disk = json.loads(SIDECAR[pipeline].read_text()).get("cuts", {})
    fresh = build(pipeline)["cuts"]
    if on_disk == fresh:
        return True, None
    drift = {k for k in set(on_disk) | set(fresh) if on_disk.get(k) != fresh.get(k)}
    return False, f"{len(drift)} cut(s) drifted, e.g. {sorted(drift)[:4]}"


def main():
    ap = argparse.ArgumentParser(description="Precompute each cut's Layer 1 table into a sidecar")
    ap.add_argument("--pipeline", choices=list(SIDECAR), required=True)
    ap.add_argument("--check", action="store_true", help="fail on drift instead of writing")
    args = ap.parse_args()

    if args.check:
        ok, why = check(args.pipeline)
        print(f"table sidecar {'FRESH' if ok else 'STALE'}: {args.pipeline}" + (f" — {why}" if why else ""))
        return 0 if ok else 1

    p = write(args.pipeline)
    rows = sum(len(t["parts"]) for t in p["cuts"].values())
    print(f"stamped {len(p['cuts'])} {args.pipeline} cut table(s), {rows} rows "
          f"@ {p['_meta']['period']} → {SIDECAR[args.pipeline].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
