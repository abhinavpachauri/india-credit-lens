#!/usr/bin/env python3
"""
validate_published_yoy.py — gate stage 1c: our arithmetic against RBI's own

NO OTHER PIPELINE HAS THIS. Every other check in this codebase compares our numbers to our
own stored numbers: traceability asks whether a sentence matches signals.db, freshness asks
whether signals.db matches the CSV. All of them would stay green if the CSV itself were
consistently wrong — a mis-parsed column, a row read off by one, a unit misread.

This source prints its OWN year-on-year columns beside the levels. So for the dates it
covers, RBI has published the answer to a sum we also compute, and the two must agree. It is
an EXTERNAL check on our reading of the file, and it costs one comparison per row.

    computed = 100 * (level[d] / level[d - 12 months] - 1)
    published = the release's own "Jul 2026 / Jul 2025" column

Tolerance is 1e-4 percentage points — the published values carry far more precision than a
rounding difference, so anything beyond that is a parse defect, not arithmetic.

    python3 analysis/pipelines/nbfc/validate_published_yoy.py
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import manifest                                              # noqa: E402

DATA_DIR = ROOT / "analysis" / "rbi_nbfc"
TOLERANCE_PP = 1e-4


def _year_before(iso: str, available: set[str]) -> str | None:
    y, m, _ = iso.split("-")
    want = f"{int(y) - 1}-{m}-"
    return next((d for d in sorted(available) if d.startswith(want)), None)


def main() -> int:
    csv_path = manifest.consolidated_csv("nbfc")
    if not csv_path.exists():
        print(f"✗ {csv_path.relative_to(ROOT)} does not exist — consolidate first")
        return 1

    levels: dict[tuple[str, str], float] = {}
    with csv_path.open() as fh:
        for r in csv.DictReader(fh):
            levels[(r["date"], r["code"])] = float(r["outstanding_cr"])
    dates = {d for d, _ in levels}

    checked, failures, uncovered = 0, [], []
    # Each way the check can pass without checking is its own count, and only one of them is
    # legitimate. A stage that printed ✓ over zero comparisons read exactly like one that had
    # compared ninety (absence review, 2026-09-26).
    unread, unprinted, new_codes = [], [], []
    for sections in sorted(DATA_DIR.glob("*/sections.json")):
        doc = json.loads(sections.read_text())
        for s in doc["sectors"]:
            printed = s.get("published_yoy") or {}
            if not printed:
                unprinted.append((sections.parent.name, s["code"]))
            for d, published in printed.items():
                prior = _year_before(d, dates)
                if prior is None:
                    uncovered.append((d, s["code"]))    # the oldest dates: no prior year exists
                    continue
                now, then = levels.get((d, s["code"])), levels.get((prior, s["code"]))
                if now is None:
                    unread.append((d, s["code"]))       # RBI printed a rate for a row we lack
                    continue
                if then is None or not then:
                    new_codes.append((d, s["code"]))    # the code is absent a year earlier
                    continue
                computed = 100.0 * (now / then - 1.0)
                checked += 1
                if abs(computed - published) > TOLERANCE_PP:
                    failures.append((d, s["code"], s["sector"], computed, published))

    for d, code, name, computed, published in failures[:10]:
        print(f"✗ {d} {code:<6} {name[:30]:<32} computed {computed:>9.5f}%  "
              f"published {published:>9.5f}%  Δ {computed - published:+.5f} pp")
    if failures:
        print(f"\n✗ {len(failures)} of {checked + len(failures)} YoY values disagree with the "
              f"figure RBI printed. Our reading of the file is wrong — a shifted column, a "
              f"mis-parsed row, or a date matched to the wrong prior year.")
        return 1
    if unread:
        print(f"✗ {len(unread)} published YoY value(s) have no level of ours at that date "
              f"(e.g. {unread[:3]}) — RBI printed a row we did not read")
        return 1
    if unprinted:
        print(f"✗ {len(unprinted)} sector(s) carry no published YoY at all (e.g. {unprinted[:3]}) "
              f"— the extractor stopped reading RBI's rate columns")
        return 1
    if checked == 0:
        print("✗ no published YoY value could be compared — the check checked nothing")
        return 1

    if uncovered:
        print(f"  ({len(uncovered)} published YoY value(s) have no prior year in the store — "
              f"expected for the oldest dates)")
    if new_codes:
        print(f"  ({len(new_codes)} value(s) for a code absent a year earlier: {new_codes[:3]})")
    print(f"✓ computed YoY matches RBI's own published figure on all {checked} values "
          f"(tolerance {TOLERANCE_PP} pp) — an external check on our reading of the source")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
