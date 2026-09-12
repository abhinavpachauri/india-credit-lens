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


def ground_truth(conn, pipeline, period, source_signals):
    """Every value this cut stores this period — the candidate set a cell may draw from."""
    vals = []
    for sid in source_signals:
        vals += [v for (v,) in conn.execute(
            "SELECT value FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
            "AND value IS NOT NULL", (pipeline, period, sid))]
    return vals


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
        units = {}
        import json as _j
        reg = _j.loads((ROOT / "analysis/signals/registry.json").read_text())["signals"]
        for stem, table in doc["cuts"].items():
            unit = reg.get(f"{stem}-size-scan", {}).get("compute", {}).get(
                "unit", "rs_cr" if pipeline == "sibc" else "count")
            truth = ground_truth(conn, pipeline, period, table["source_signals"])
            if not truth:
                findings.append(f"{stem}: declares {table['source_signals']} and none of them "
                                f"has a row at {period} — nothing to check against")
                continue
            for row in [table["total"], *table["parts"]]:
                who = row.get("entity") or "(the cut itself)"
                for col in CELLS:
                    cell = row.get(col)
                    if not cell:
                        continue
                    # A CELL IS NOT PROSE. It carries exactly one number, so the check is
                    # stronger than number-extraction: the raw value must be one this cut
                    # stores, AND the string drawn must be that value rendered. Extracting
                    # numbers back out of "\u20b95.38L Cr" would have to undo the unit
                    # conversion to compare, and a check that re-implements the formatter
                    # is a second formatter that can disagree with the first.
                    if cell["sort"] is None:
                        findings.append(f"{stem} · {who} · {col}: drawn as '{cell['display']}' "
                                        f"with no value behind it")
                    elif not matches(cell["sort"], truth, POLICY):
                        findings.append(
                            f"{stem} · {who} · {col}: {cell['sort']} is not a value this cut "
                            f"stores at {period}")
                    else:
                        want = fmt_for(col, unit)(cell["sort"])
                        if cell["display"] != want:
                            findings.append(
                                f"{stem} · {who} · {col}: drawn as '{cell['display']}' but "
                                f"{cell['sort']} renders as '{want}'")
    finally:
        conn.close()
    return findings


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
    print(f"  ✓ cut tables traceable — {len(doc['cuts'])} cut(s), {rows} row(s), "
          f"every cell scoped to its own cut")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
