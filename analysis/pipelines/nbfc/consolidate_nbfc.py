#!/usr/bin/env python3
"""
consolidate_nbfc.py — every extracted release → one consolidated CSV + timeline

THE POINT OF THIS PIPELINE'S CONSOLIDATION IS THE OVERLAP. Each release carries five dated
columns, so three releases hold ELEVEN distinct dates and most of those dates appear in more
than one release. That is a gift and a hazard in the same fact:

  * the gift — eleven dates from three files, seven of them able to compute a YoY on day
    one. SIBC ingested 11 of its 24 available dates and paid for the rest in a separate
    backfill session; there is no reason to repeat that.

  * the hazard — two releases can disagree about the same date. LAST RELEASE WINS, which is
    the same single-source-of-truth rule SIBC applies to RBI's historical revisions. Any
    disagreement is REPORTED rather than silently absorbed, because a revision that nobody
    saw is indistinguishable from a parsing bug.

The column names are not ours to choose: `signals/compute/csv_sector.py` requires
date · code · parent_code · level · sector · outstanding_cr, verifies them on load, and means
the same thing by them in every source. `release_date` rides along as provenance.

    python3 analysis/pipelines/nbfc/consolidate_nbfc.py
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import date
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import manifest                                              # noqa: E402

DATA_DIR = ROOT / "analysis" / "rbi_nbfc"
TIMELINE = DATA_DIR / "timeline.json"
COLUMNS = ["date", "code", "sector", "level", "parent_code", "outstanding_cr", "release_date"]

MONTHS = ["", "January", "February", "March", "April", "May", "June",
          "July", "August", "September", "October", "November", "December"]


def _label(iso: str) -> str:
    y, m, _ = iso.split("-")
    return f"{MONTHS[int(m)]} {y}"


def _year_before(iso: str) -> str:
    y, m, d = (int(x) for x in iso.split("-"))
    prev = date(y - 1, m, 1)
    # month-end a year back; the source only ever publishes month-ends
    nxt = date(prev.year + (prev.month // 12), prev.month % 12 + 1, 1)
    return (nxt - (nxt - prev).__class__(days=1)).isoformat()


def load_releases() -> list[dict]:
    docs = []
    for f in sorted(DATA_DIR.glob("*/sections.json")):
        docs.append(json.loads(f.read_text()))
    if not docs:
        raise SystemExit(f"no extracted releases under {DATA_DIR.relative_to(ROOT)} — "
                         f"run extract_nbfc.py first")
    return sorted(docs, key=lambda d: d["period"])


def consolidate(docs: list[dict]) -> tuple[list[dict], list[str]]:
    """(rows, revisions). Later releases overwrite earlier ones for the same (date, code)."""
    cell: dict[tuple[str, str], dict] = {}
    revisions: list[str] = []
    for doc in docs:
        for s in doc["sectors"]:
            for d, v in s["values"].items():
                key = (d, s["code"])
                prev = cell.get(key)
                if prev is not None and abs(prev["outstanding_cr"] - v) > 0.01:
                    revisions.append(
                        f"{d} {s['code']:<6} {s['sector'][:28]:<30} "
                        f"{prev['outstanding_cr']:>14,.2f} → {v:>14,.2f}  "
                        f"({prev['release_date']} → {doc['period']})")
                cell[key] = {
                    "date": d, "code": s["code"], "sector": s["sector"],
                    "level": s["level"], "parent_code": s["parent_code"],
                    "outstanding_cr": v, "release_date": doc["period"],
                }
    rows = sorted(cell.values(), key=lambda r: (r["date"], r["level"], r["code"]))
    return rows, revisions


def build_timeline(docs: list[dict], rows: list[dict]) -> dict:
    dates = sorted({r["date"] for r in rows})
    released = {d["period"]: d for d in docs}
    total = {r["date"]: r["outstanding_cr"] for r in rows if r["code"] == "T"}
    periods = []
    for d in dates:
        doc = released.get(d)
        prior = _year_before(d)
        supplier = d if doc else next((x["period"] for x in docs if d in x["dates"]), None)
        # A date with no prior year IN THE STORE can carry a level and nothing else. Recorded
        # rather than left to be rediscovered: an absent rate must be legible as legitimate.
        level_only = _year_before(d) not in dates
        periods.append({
            "period": _label(d),
            "dataDate": d,
            # No remapping exists for this source — the column header IS the data date — so
            # the two are equal by construction rather than by a rule someone has to apply.
            "csv_date": d,
            "is_fy_end": d.endswith("-03-31"),
            "level_only": level_only,
            "released": doc is not None,
            "source_file": doc["source_file"] if doc else None,
            # Which release supplied a date nobody published on its own.
            "backfilled_from": None if doc else supplier,
            "total_credit_lcr": round(total[d] / 1e5, 2) if d in total else None,
            "yoy_growth_pct": (round(100.0 * (total[d] / total[prior] - 1), 2)
                               if prior in total and total.get(prior) else None),
            # A backfilled date has no sections.json of its own — it arrived inside another
            # release's five columns — so this points at the file that actually carries it.
            # "Where do I find this date?" has an answer for every date, not just released ones.
            "paths": {"sections": f"rbi_nbfc/{supplier}/sections.json"} if supplier else {},
        })
    return {
        "report_id": "rbi_nbfc",
        "report_name": "RBI — Sectoral Deployment of Outstanding Credit by NBFCs (incl. HFCs)",
        "periods": periods,
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true",
                    help="recompute and fail if the committed CSV or timeline would change")
    a = ap.parse_args()

    docs = load_releases()
    rows, revisions = consolidate(docs)
    timeline = build_timeline(docs, rows)
    csv_path = manifest.consolidated_csv("nbfc")

    body = []
    body.append(",".join(COLUMNS))
    for r in rows:
        body.append(",".join(str(r[c]) for c in COLUMNS))
    text = "\n".join(body) + "\n"

    if a.check:
        stale = []
        if not csv_path.exists() or csv_path.read_text() != text:
            stale.append(csv_path.relative_to(ROOT))
        if not TIMELINE.exists() or json.loads(TIMELINE.read_text()) != timeline:
            stale.append(TIMELINE.relative_to(ROOT))
        if stale:
            print("✗ consolidated artifacts are stale:", *[f"\n    {s}" for s in stale])
            return 1
        print(f"✓ consolidated CSV + timeline fresh — {len(rows)} rows, "
              f"{len(timeline['periods'])} dates")
        return 0

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.write_text(text)
    TIMELINE.write_text(json.dumps(timeline, indent=2) + "\n")

    dates = [p["dataDate"] for p in timeline["periods"]]
    lvl = [p["dataDate"] for p in timeline["periods"] if p["level_only"]]
    print(f"✓ Wrote {len(rows)} rows over {len(dates)} dates from {len(docs)} release(s)")
    print(f"  dates      : {dates[0]} … {dates[-1]}")
    print(f"  level-only : {len(lvl)} ({', '.join(lvl)}) — no prior year in the store, so "
          f"every rate is legitimately absent")
    print(f"  released   : {', '.join(d['period'] for d in docs)}")
    if revisions:
        print(f"  ⚠ {len(revisions)} value(s) revised between releases (last release wins):")
        for line in revisions[:10]:
            print("     ", line)
    else:
        print("  revisions  : none — every overlapping date agrees across releases")
    print(f"  → {csv_path.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
