#!/usr/bin/env python3
"""
validate_csv.py — MoSPI stage 1b: the consolidated CSV, and the release calendar
───────────────────────────────────────────────────────────────────────────────
Structure, every run:
  * the key (dataset, base_year, period, code, measure) is unique;
  * one base per dataset, and it is the declared one (a YoY is never linked across bases);
  * every (dataset, code) in labels.json has rows: the population is the manifest × the map,
    never the CSV's own keys, so a truncated CSV cannot agree with itself;
  * no gap inside a series at its cadence: a missing month in the middle is not "no data".

The release calendar (signals/README, "when missing means overdue"). Each dataset declares its
expected lag; after `period end + lag + grace_days`, the period must be here. If it is not, that
FAILS as overdue, whatever the cause (the fetch, the source, a PDF nobody downloaded). Before that
date its absence is legitimate (`not_released`), and the summary says when the next one is due.
Without this, a pipeline that stopped fetching would look exactly like one waiting for MoSPI.

    python3 analysis/pipelines/mospi/validate_csv.py [--today 2026-09-28]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import releases as R                                          # noqa: E402
import consolidate as C                                       # noqa: E402
from core import manifest                                     # noqa: E402

STEP_MONTHS = {"monthly": 1, "quarterly": 3}


def next_period(p: str, months: int) -> str:
    y, m = int(p[:4]), int(p[5:7]) + months
    y, m = y + (m - 1) // 12, (m - 1) % 12 + 1
    return R.month_end(y, m)


def due_date(period: str, lag: int, grace: int) -> date:
    return date.fromisoformat(period) + timedelta(days=lag + grace)


def expected_latest(latest: str, cadence: str, lag: int, grace: int, today: date) -> str:
    """The newest period whose due date has passed, walking forward from what we hold."""
    step, p = STEP_MONTHS[cadence], latest
    while due_date(next_period(p, step), lag, grace) <= today:
        p = next_period(p, step)
    return p


def check(rows: list[dict], man: dict, lab: dict, today: date) -> tuple[list[str], list[str]]:
    errs, notes = [], []
    seen = set()
    for r in rows:
        k = (r["dataset"], r["base_year"], r["period"], r["code"], r["measure"])
        if k in seen:
            errs.append(f"duplicate key {k}")
        seen.add(k)
    grace = man.get("grace_days", 0)
    for name, ds in man["datasets"].items():
        mine = [r for r in rows if r["dataset"] == name]
        bases = {r["base_year"] for r in mine}
        if bases != {ds["base_year"]}:
            errs.append(f"{name}: base years {sorted(bases)}, declared {ds['base_year']!r}")
        if not mine:
            errs.append(f"{name}: no rows")
            continue
        codes = set(lab[name].values())
        have = {r["code"] for r in mine}
        for c in sorted(codes - have):
            errs.append(f"{name}: {c} is mapped in labels.json but has no rows")
        for c in sorted(have - codes):
            errs.append(f"{name}: {c} has rows but no label maps to it")
        expected = set()
        for lk, code in lab[name].items():
            row = dict(zip(ds["label_fields"], lk.split(" › ")))
            for measure in C.measures_for(ds, row, ds["label_fields"]):
                expected.add((code, measure))
        step = STEP_MONTHS[ds["cadence"]]
        series = {}
        for r in mine:
            series.setdefault((r["code"], r["measure"]), set()).add(r["period"])
        for (code, measure), periods in sorted(series.items()):
            ps = sorted(periods)
            for a, b in zip(ps, ps[1:]):
                if next_period(a, step) != b:
                    errs.append(f"{name}: {code}/{measure} has a gap between {a} and {b}")
                    break
        latest = max(r["period"] for r in mine)
        # Per series, not per dataset: a measure that vanished (or stopped early) must not hide
        # behind another measure of the same code that is still current.
        for code, measure in sorted(expected):
            ps = series.get((code, measure))
            if not ps:
                errs.append(f"{name}: {code}/{measure} is declared but has no rows")
            elif max(ps) != latest:
                errs.append(f"{name}: {code}/{measure} ends {max(ps)}, the dataset's latest is {latest}")
        want = expected_latest(latest, ds["cadence"], ds["expected_lag_days"], grace, today)
        if want > latest:
            errs.append(f"{name}: OVERDUE: {want} was due by "
                        f"{due_date(want, ds['expected_lag_days'], grace)}; latest held is {latest}")
        else:
            nxt = next_period(latest, step)
            notes.append(f"{name}: latest {latest} (next, {nxt}, due by "
                         f"{due_date(nxt, ds['expected_lag_days'], grace)})")
    return errs, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--today", type=date.fromisoformat, default=date.today())
    args = ap.parse_args()
    path = manifest.path(R.PIPELINE, "consolidated_csv")
    if not path.exists():
        print(f"  ✗ {path} is missing; run consolidate.py", file=sys.stderr)
        return 1
    with path.open() as f:
        rows = list(csv.DictReader(f))
    errs, notes = check(rows, R.load_manifest(), C.labels(), args.today)
    for n in notes:
        print(f"  · {n}")
    for e in errs:
        print(f"  ✗ {e}", file=sys.stderr)
    if errs:
        return 1
    n_series = len({(r['dataset'], r['code'], r['measure']) for r in rows})
    print(f"  ✓ {len(rows)} rows, {n_series} series: unique, one base, no gaps, none overdue")
    return 0


if __name__ == "__main__":
    sys.exit(main())
