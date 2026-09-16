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
from core import manifest                          # noqa: E402

DATA = ROOT / "web" / "public" / "data"
DB = ROOT / "analysis" / "signals" / "signals.db"
REGISTRY = ROOT / "analysis" / "signals" / "registry.json"
SIDECAR = {p: DATA / f"{p}_table.json" for p in manifest.PIPELINE_IDS}
# A bank breakout ships as its own file, fetched when the reader opens it. Twenty-six of them
# inline would be an eight-megabyte artifact every visitor downloads to look at one: sixty-four
# banks, three columns, thirty-one readings each. Compute once, ship compact, and ship only the
# part that was asked for.
BANK_DIR = {p: DATA / f"{p}_banks" for p in manifest.PIPELINE_IDS}
MOMENTUM = ("csv_sector_momentum", "csv_category_momentum")
# A bank breakout's parent rate: the metric's own total YoY, which belongs to the level above
# the banks exactly as a credit cut's parent rate belongs to the level above its parts.
TOTAL_YOY = {"credit_cards": "cc-outstanding-yoy", "debit_cards": "dc-outstanding-yoy",
             "pos_terminals": "pos-terminals-yoy"}


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


def measured_metric(pipeline: str) -> dict[str, str]:
    """{stem: the CSV metric this cut measures} — payments only.

    A payments cut's stem and the metric it measures are named independently: the credit-card
    fleet is metric `credit_cards` and cut `cc-category`. The dashboard adapter had been
    RECONSTRUCTING the stem from the metric name ("credit_cards" -> "credit-cards-category"),
    which is right for twenty-three cuts and wrong for the three that matter most — the two
    card fleets and the POS fleet, every group's anchor. All three were computed, gated,
    shipped and reachable from nothing.

    So the join is declared here, out of the registry that knows both names, and the browser
    matches on the metric instead of guessing at a spelling.
    """
    if pipeline == "sibc":
        return {}
    reg = json.loads(REGISTRY.read_text())["signals"]
    out = {}
    for sid, sig in reg.items():
        c = sig.get("compute", {})
        if sig.get("pipeline") != pipeline or not sid.endswith("-size-scan"):
            continue
        if c.get("metric"):
            out[sid[: -len("-size-scan")]] = c["metric"]
    return out


def bank_cuts(pipeline: str) -> dict[str, dict]:
    """The per-bank breakout of a metric, as its own cut (§20 `break out by bank`).

    Sixty-four banks have been in the store since the first ingestion and no surface could
    show one of them beside its own growth: the bank scan was consumed only by concentration
    cards. A breakout is not a drilldown into a category — it is the SAME table at a different
    level, which is why it is a cut and not a nested row.

    Discovered by METHOD and METRIC, never by name: `cc-bank-scan` does not follow the stem
    convention and never will, and matching on a spelling is what hid three payments tables
    from the dashboard this week.
    """
    if pipeline != "atm_pos":
        return {}                    # SIBC is sector-level; RBI publishes no per-bank credit
    reg = json.loads(REGISTRY.read_text())["signals"]
    by_metric: dict[str, dict[str, str]] = {}
    for sid, sig in reg.items():
        c = sig.get("compute", {})
        if sig.get("pipeline") != pipeline or not c.get("metric"):
            continue
        m = c["metric"]
        if c.get("method") == "csv_bank_scan":
            by_metric.setdefault(m, {})["growth" if c.get("value_type") == "yoy" else "size"] = sid
        elif c.get("method") == "csv_bank_scan_share":
            by_metric.setdefault(m, {})["of_cut"] = sid
    out = {}
    for metric, cols in by_metric.items():
        if "size" not in cols:       # a rate with no level is not a table
            continue
        # The breakout's parent row is the metric's own total, which the CATEGORY cut of the
        # same metric already stores. Same number in both tables, from one signal.
        for stem2, sig2 in reg.items():
            c2 = sig2.get("compute", {})
            if c2.get("metric") == metric and c2.get("method") == "csv_category_scan_abs":
                cols["total_size"] = stem2
                break
        out[f"{metric.replace('_', '-')}-banks"] = {"metric": metric, "signals": cols}
    return out


def sub_cut_map(pipeline: str) -> dict[str, str]:
    """{parent entity name: the cut it decomposes into} (§19).

    A sub-cut declares the CODE of its parent; a table row is keyed by the parent's NAME. The
    consolidated CSV is the one place both are known, so the join happens here and the browser
    is handed the answer.
    """
    if pipeline != "sibc":
        return {}                    # payments has one level of bank categories, no sub-cuts
    import pandas as pd
    from core.manifest import consolidated_csv
    reg = json.loads(REGISTRY.read_text())["signals"]
    df = pd.read_csv(consolidated_csv(pipeline))
    out = {}
    for sid, sig in reg.items():
        c = sig.get("compute", {})
        if c.get("method") not in MOMENTUM or c.get("child_level") != 3:
            continue
        rows = df[(df["code"].astype(str) == str(c.get("parent_code")))
                  & (df["statement"] == c.get("statement"))]["sector"]
        if len(rows):
            out[rows.iloc[0]] = sid[: -len("-momentum")]
    return out


def _metric_unit(conn, pipeline: str, period: str, size_id: str) -> str:
    """The unit the size rows themselves carry — a bank scan takes its unit from the CSV
    rather than declaring one, so read it back rather than assuming a count."""
    row = conn.execute("SELECT unit FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
                       "LIMIT 1", (pipeline, period, size_id)).fetchone()
    return row[0] if row and row[0] else "count"


def latest_period(conn, pipeline: str) -> str:
    return conn.execute("SELECT MAX(period) FROM signals WHERE pipeline=?", (pipeline,)).fetchone()[0]


def build(pipeline: str, period: str | None = None) -> dict:
    conn = sqlite3.connect(DB)
    try:
        period = period or latest_period(conn, pipeline)
        tables, rates, subs = {}, parent_rates(pipeline), sub_cut_map(pipeline)
        metrics = measured_metric(pipeline)
        banks = {}
        for stem, spec in sorted(bank_cuts(pipeline).items()):
            unit = json.loads(REGISTRY.read_text())["signals"].get(
                spec["signals"]["size"], {}).get("compute", {}).get("unit")
            t = table_rows.build(conn, pipeline, period, stem,
                                 unit or _metric_unit(conn, pipeline, period, spec["signals"]["size"]),
                                 TOTAL_YOY.get(spec["metric"]), None, signals=spec["signals"])
            if t is not None:
                t["metric"] = spec["metric"]
                t["level"] = "bank"
                banks[stem] = t
        for stem, unit in sorted(cuts(pipeline).items()):
            t = table_rows.build(conn, pipeline, period, stem, unit, rates.get(stem), subs)
            if t is not None:          # a cut without its 12-month window has no table yet
                if stem in metrics:
                    t["metric"] = metrics[stem]
                tables[stem] = t
    finally:
        conn.close()
    return {
        # The index of bank breakouts: which measure has one, how many banks it holds, and the
        # file to fetch. The browser needs to know a breakout EXISTS before the reader asks for
        # it — an absent toggle is honest, a toggle that opens nothing is not.
        "_banks": {t["metric"]: {"cut": stem, "parts": len(t["parts"]),
                                 "file": f"{pipeline}_banks/{stem}.json"}
                   for stem, t in banks.items()},
        "_bank_tables": banks,           # written out separately, never into this file
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


def _split(payload: dict) -> tuple[dict, dict]:
    """The main sidecar, and the bank tables that ship beside it one file each."""
    banks = payload.pop("_bank_tables", {})
    return payload, banks


def write(pipeline: str) -> dict:
    payload, banks = _split(build(pipeline))
    SIDECAR[pipeline].write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    d = BANK_DIR[pipeline]
    d.mkdir(parents=True, exist_ok=True)
    live = set()
    for stem, table in banks.items():
        (d / f"{stem}.json").write_text(json.dumps(table, indent=1, ensure_ascii=False) + "\n")
        live.add(f"{stem}.json")
    # A breakout that stops being computed must stop being SERVED: a stale file left behind
    # would answer a fetch with last month's table and nothing would say so.
    for old in d.glob("*.json"):
        if old.name not in live:
            old.unlink()
    payload["_bank_tables"] = banks          # returned for the caller's counts, not written
    return payload


def check(pipeline: str):
    if not SIDECAR[pipeline].exists():
        return False, "sidecar missing — run without --check"
    fresh_all = build(pipeline)
    fresh_banks = fresh_all.pop("_bank_tables", {})
    on_disk = json.loads(SIDECAR[pipeline].read_text()).get("cuts", {})
    drift = {k for k in set(on_disk) | set(fresh_all["cuts"])
             if on_disk.get(k) != fresh_all["cuts"].get(k)}
    for stem, table in fresh_banks.items():
        f = BANK_DIR[pipeline] / f"{stem}.json"
        if not f.exists() or json.loads(f.read_text()) != table:
            drift.add(stem)
    stale = {f.stem for f in BANK_DIR[pipeline].glob("*.json")} - set(fresh_banks)
    drift |= stale
    if not drift:
        return True, None
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
    banks = p.get("_bank_tables", {})
    rows = sum(len(t["parts"]) for t in p["cuts"].values())
    brows = sum(len(t["parts"]) for t in banks.values())
    print(f"stamped {len(p['cuts'])} {args.pipeline} cut table(s), {rows} rows "
          f"@ {p['_meta']['period']} → {SIDECAR[args.pipeline].name}"
          + (f"; {len(banks)} bank breakout(s), {brows} bank rows → {BANK_DIR[args.pipeline].name}/"
             if banks else ""))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
