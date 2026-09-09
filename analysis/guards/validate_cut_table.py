#!/usr/bin/env python3
"""
validate_cut_table.py — every number in a Layer 1 table traces to that cut (§17.5)
──────────────────────────────────────────────────────────────────────────────────
The table is the densest published surface on the platform: forty cuts, two hundred rows,
seven numbers a row. Density is exactly why it needs a gate — nobody proofreads two
hundred rows, and a wrong cell looks identical to a right one.

SCOPE IS THE CHECK. Each row is validated against the signals of ITS OWN cut at THIS
period, not period-wide. The state-band measurement made the reason concrete: at history
width, four of twenty-three near-miss injections survived by colliding with the signal's
own past readings. A traceability gate that widens its scope to avoid false alarms has
quietly stopped being one.

    python3 analysis/guards/validate_cut_table.py --pipeline sibc
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core.traceability import DISTRIBUTION as POLICY, matches                  # noqa: E402
from core import table_rows                                                   # noqa: E402

DATA = ROOT / "web" / "public" / "data"
DB = ROOT / "analysis" / "signals" / "signals.db"
CELLS = ("size", "of_cut", "of_book", "growth", "pace", "new")


def column_truth(conn, pipeline, period, metric_id):
    """Every value this ONE signal stores at this period — the candidate set for a cell.

    Per COLUMN, not per cut. The cut-wide pool let a growth cell trace to a share and a
    pace cell trace to a size: six families in one candidate set is six chances to collide,
    and a traceability gate is its scope.
    """
    return [v for (v,) in conn.execute(
        "SELECT value FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
        "AND value IS NOT NULL", (pipeline, period, metric_id))]


def stored(conn, pipeline, metric_id, entity_id):
    """Every value this signal has ever stored for this entity — the series' candidate set.

    A cell's chart is history, so its scope is that entity's own history and nothing else.
    Widening it to the cut would let one part's past readings vouch for another's.
    """
    return [v for (v,) in conn.execute(
        "SELECT value FROM signals WHERE pipeline=? AND metric_id=? AND entity_id=? "
        "AND value IS NOT NULL", (pipeline, metric_id, entity_id))]


def fmt_for(col: str, unit: str):
    """The same formatter the builder used — imported, never re-implemented."""
    if col == "size":
        return table_rows.UNIT_FMT.get(unit, table_rows._count)
    return table_rows._pp if col == "pace" else table_rows._pct


def validate(pipeline: str) -> list[str]:
    doc = json.loads((DATA / f"{pipeline}_table.json").read_text())
    period = doc["_meta"]["period"]
    conn = sqlite3.connect(DB)
    findings = []
    try:
        reg = json.loads((ROOT / "analysis/signals/registry.json").read_text())["signals"]
        for stem, table in doc["cuts"].items():
            unit = reg.get(f"{stem}-size-scan", {}).get("compute", {}).get(
                "unit", "rs_cr" if pipeline == "sibc" else "count")
            cols, pcols = table["columns"], table.get("parent_columns", {})
            if not any(column_truth(conn, pipeline, period, m) for m in set(cols.values())):
                findings.append(f"{stem}: declares {sorted(set(cols.values()))} and none of them "
                                f"has a row at {period} — nothing to check against")
                continue
            rows = [(table["total"], "(the cut itself)", pcols, table.get("parent_periods", {}))]
            rows += [(p, p.get("entity"), cols, table.get("periods", {})) for p in table["parts"]]
            for row, who, colmap, periods in rows:
                for col in CELLS:
                    cell = row.get(col)
                    if not cell:
                        continue
                    metric = colmap.get(col)
                    if not metric:
                        findings.append(f"{stem} · {who} · {col}: drawn as '{cell['display']}' "
                                        f"with no signal declared behind the column")
                        continue
                    truth = column_truth(conn, pipeline, period, metric)
                    # A CELL IS NOT PROSE. It carries exactly one number, so the check is
                    # stronger than number-extraction: the raw value must be one this column
                    # stores, AND the string drawn must be that value rendered. Extracting
                    # numbers back out of "\u20b95.38L Cr" would have to undo the unit
                    # conversion to compare, and a check that re-implements the formatter
                    # is a second formatter that can disagree with the first.
                    if cell["sort"] is None:
                        findings.append(f"{stem} · {who} · {col}: drawn as '{cell['display']}' "
                                        f"with no value behind it")
                        continue
                    if not matches(cell["sort"], truth, POLICY):
                        findings.append(
                            f"{stem} · {who} · {col}: {cell['sort']} is not a value "
                            f"{metric} stores at {period}")
                        continue
                    want = fmt_for(col, unit)(cell["sort"])
                    if cell["display"] != want:
                        findings.append(
                            f"{stem} · {who} · {col}: drawn as '{cell['display']}' but "
                            f"{cell['sort']} renders as '{want}'")
                    findings += series_findings(conn, pipeline, stem, who, col, cell,
                                                metric, periods.get(col), row)
    finally:
        conn.close()
    return findings


def series_findings(conn, pipeline, stem, who, col, cell, metric, labels, row):
    """The chart behind a cell is published too (§20), so it is checked like the cell.

    Three ways a history can lie without any single number being wrong: a value that was
    never stored, a series that has slid out of step with its own axis, and a last reading
    that is not the cell sitting on top of it.
    """
    series = cell.get("series")
    if not series:
        return []
    out = []
    eid = row.get("entity") or "total"
    if labels is None or len(labels) != len(series):
        out.append(f"{stem} · {who} · {col}: {len(series)} readings against "
                   f"{len(labels or [])} period labels — the axis and the line disagree")
    truth = stored(conn, pipeline, metric, eid)
    unknown = [v for v in series if v is not None and not matches(v, truth, POLICY)]
    if unknown:
        out.append(f"{stem} · {who} · {col}: {len(unknown)} reading(s) in the chart "
                   f"({unknown[:3]}) are not values {metric} ever stored for {eid}")
    last = next((v for v in reversed(series) if v is not None), None)
    if last is not None and cell["sort"] is not None and not matches(cell["sort"], [last], POLICY):
        out.append(f"{stem} · {who} · {col}: the chart ends at {last} but the cell reads "
                   f"{cell['sort']} — the cell is not the top of its own series")
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", choices=("sibc", "atm_pos"), required=True)
    args = ap.parse_args()
    f = validate(args.pipeline)
    if f:
        print(f"  ✗ cut table traceability — {len(f)} finding(s)")
        for x in f[:12]:
            print(f"      {x}")
        return 1
    doc = json.loads((DATA / f"{args.pipeline}_table.json").read_text())
    rows = sum(len(t["parts"]) + 1 for t in doc["cuts"].values())
    readings = sum(len(c["series"]) for t in doc["cuts"].values()
                   for r in [t["total"], *t["parts"]]
                   for c in (r.get(k) for k in CELLS) if c and c.get("series"))
    print(f"  ✓ cut tables traceable — {len(doc['cuts'])} cut(s), {rows} row(s), "
          f"{readings} charted reading(s), every cell scoped to its own column")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
