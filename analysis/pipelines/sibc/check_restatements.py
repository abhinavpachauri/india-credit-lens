#!/usr/bin/env python3
"""
check_restatements.py — did the latest release reprint a line on a new basis nobody has declared?
──────────────────────────────────────────────────────────────────────────────────────────────────
Spec: signals/README.md, "Series breaks". A reprint that relabels loans changes which months can be
compared, and the data still looks fine, so nothing downstream would notice. Only the latest release
is judged: "typical" moves as history grows, and an old release must not start failing a later gate.

    python3 analysis/pipelines/sibc/check_restatements.py          # the gate stage
    python3 analysis/pipelines/sibc/check_restatements.py --all    # every release, for measuring
"""
from __future__ import annotations

import argparse
import contextlib
import csv
import io
import json
import sys
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ANALYSIS))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core import manifest, series_breaks as sb  # noqa: E402
import update_web_data as u  # noqa: E402

PIPELINE = "sibc"


def vintages() -> dict:
    """release -> {(statement, code, date): value}, each release read alone so none hides another."""
    sys.path.insert(0, str(u.RBI_SIBC_LIB))
    from consolidate import consolidate

    out: dict = {}
    for f in sorted((ANALYSIS / "rbi_sibc").glob("*/raw/*.xlsx")):
        with contextlib.redirect_stdout(io.StringIO()):
            df = u.normalize_to_period_end(u.load_and_apply_overrides(consolidate([f])))
        release = out.setdefault(f.parts[-3], {})
        for r in df.sort_values("date").itertuples():
            if r.outstanding_cr == r.outstanding_cr:
                release[(r.statement, str(r.code), r.date[:10])] = float(r.outstanding_cr)
    return out


def typical_by_line() -> dict:
    series: dict = {}
    with open(manifest.consolidated_csv(PIPELINE)) as f:
        for r in sorted(csv.DictReader(f), key=lambda r: r["date"]):
            series.setdefault((r["statement"], r["code"]), []).append(float(r["outstanding_cr"]))
    return {k: sb.typical_change_pct(v) for k, v in series.items()}


def flagged(all_vintages: dict, typical: dict) -> dict:
    """release -> {(statement, code): [% each reprinted month moved against its previous print]}."""
    seen: dict = {}
    out: dict = {}
    for release in sorted(all_vintages):
        reprints: dict = {}
        for (st, code, date), value in all_vintages[release].items():
            before = seen.get((st, code, date))
            if before:
                reprints.setdefault((st, code), []).append((value / before - 1) * 100)
        out[release] = {k: p for k, p in reprints.items() if sb.is_restatement(p, typical.get(k))}
        for key, value in all_vintages[release].items():
            seen[key] = value
    return out


def declared(release: str) -> set:
    path = ANALYSIS / "rbi_sibc" / "series_breaks.json"
    return {(l["statement"], l["code"])
            for r in json.loads(path.read_text()).get("restatements", [])
            if r["release"] == release for l in r["lines"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--all", action="store_true", help="list what the rule flags in every release")
    args = ap.parse_args()

    found = flagged(vintages(), typical_by_line())
    if args.all:
        for release, lines in found.items():
            if lines:
                print(release, {k: [round(x, 1) for x in v] for k, v in lines.items()})
        print(f"{sum(map(len, found.values()))} flagged across {len(found)} releases")
        return 0

    latest = max(found)
    missing = sorted(set(found[latest]) - declared(latest))
    if missing:
        print(f"✗ {latest} reprinted {len(missing)} line(s) on what looks like a new basis, undeclared:",
              file=sys.stderr)
        for key in missing:
            print(f"    {key[0]} {key[1]}: {[round(x, 1) for x in found[latest][key]]} % against earlier prints",
                  file=sys.stderr)
        print("  Review, then declare in analysis/rbi_sibc/series_breaks.json (signals/README.md, "
              "\"Series breaks\").", file=sys.stderr)
        return 1
    print(f"restatements: {latest} reprints nothing undeclared ({len(found[latest])} declared line(s) flagged)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
