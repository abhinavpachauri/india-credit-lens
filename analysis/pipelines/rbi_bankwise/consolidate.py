#!/usr/bin/env python3
"""
consolidate.py — saved quarters → one long table, rebuilt locally (BANKWISE_SPEC.md §8, phase 1)
───────────────────────────────────────────────────────────────────────────────────────────────────
The record is the saved quarters (`releases/{quarter}/{saved}.json.gz`, committed, ~145 KB each).
The long table is ~2.8 million values for 2002 → 2026 (~140 MB), too big to commit, so it is a
local file rebuilt from the releases (user, 2026-11-14), git-ignored, like `signals.db` beside its
committed `.gz`. Rows follow the PAYMENTS shape (BANKWISE_SPEC §8a), so one per-bank compute module
serves both pipelines: report_date, bank_name (roster id), bank_category (the group RBI printed the
bank under that quarter), record_type (`bank`, or `total` for RBI's All SCBs row), metric
(`{sheet}.{column}`), value, unit, data_status. Group values are sums of their banks, as in
payments. A cell RBI left empty is not a row; the release keeps it as null. It also writes
`timeline.json`, the list of saved quarters that the freshness check iterates.

    python3 analysis/pipelines/rbi_bankwise/consolidate.py            # write
    python3 analysis/pipelines/rbi_bankwise/consolidate.py --check    # the file equals a rebuild
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / ".git").is_dir()) / "analysis"))
from core import manifest  # noqa: E402

PIPELINE = "rbi_bankwise"
FIELDS = ("report_date", "bank_name", "bank_category", "record_type", "metric", "value", "unit", "data_status")
GROUP_LABEL = {"group:psb": "Public Sector Banks", "group:pvt": "Private Sector Banks",
               "group:foreign": "Foreign Banks", "group:sfb": "Small Finance Banks",
               "group:sfb_ns": "Small Finance Banks (non-scheduled)", "group:lab": "Local Area Banks"}


def _unit(measure: str) -> str:
    import re
    return "pct" if ("%" in measure or re.search(r"\bratio\b|annualized|annualised", measure, re.I)
                     or measure.startswith(("yield", "cost_of", "return_on"))) else "crore"


def _fetch():
    import importlib.util
    name = "rbi_bankwise_fetch"
    if name not in sys.modules:
        spec = importlib.util.spec_from_file_location(name, HERE / "fetch.py")
        sys.modules[name] = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(sys.modules[name])
    return sys.modules[name]


def rows() -> list[tuple]:
    fetch = _fetch()
    out = []
    quarters = fetch.saved_quarters(manifest.path(PIPELINE, "releases"))
    if not quarters:
        raise SystemExit("✗ no saved quarters: nothing to consolidate (an empty table is not a result)")
    for quarter, path in sorted(quarters.items()):
        doc = fetch.load(path)
        for code, e in sorted(doc["banks"].items()):
            cat = GROUP_LABEL.get(e.get("group"), e.get("group") or "")
            for sheet, cols in sorted(e["sheets"].items()):
                for measure, v in sorted(cols.items()):
                    if v is not None:
                        out.append((quarter, code, cat, "bank", f"{sheet}.{measure}", repr(float(v)),
                                    _unit(measure), "final"))
        scb = doc["groups"].get("group:scb", {})
        for sheet, cols in sorted(scb.get("sheets", {}).items()):
            for measure, v in sorted(cols.items()):
                if v is not None:
                    out.append((quarter, "All Scheduled Commercial Banks", "", "total", f"{sheet}.{measure}",
                                repr(float(v)), _unit(measure), "final"))
    return out


def timeline(rs: list[tuple]) -> dict:
    import calendar
    qs = sorted({r[0] for r in rs})
    banks = {q: len({r[1] for r in rs if r[0] == q and r[3] == "bank"}) for q in qs}
    return {"report_id": "rbi_bankwise", "report_name": "RBI bank-wise quarterly variables of SCBs (DBIE)",
            "periods": [{"period": f"{calendar.month_name[int(q[5:7])]} {q[:4]}", "report_date": q,
                         "data_status": "final", "bank_count": banks[q]} for q in qs]}


def render(rs: list[tuple]) -> bytes:
    buf = io.StringIO()
    w = csv.writer(buf, lineterminator="\n")
    w.writerow(FIELDS)
    w.writerows(rs)
    return buf.getvalue().encode()


def main() -> int:
    ap = argparse.ArgumentParser(description="saved quarters → local long table")
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    target = manifest.consolidated_csv(PIPELINE)
    rs = rows()
    body = render(rs)
    quarters = len({r[0] for r in rs})
    tl = json.dumps(timeline(rs), indent=1) + "\n"
    tl_path = manifest.path(PIPELINE, "timeline")
    if a.check:
        if not tl_path.exists() or tl_path.read_text() != tl:
            print(f"  ✗ {tl_path.name} stale or missing; run consolidate")
            return 1
        if not target.exists():
            print(f"  ✗ {target.name} missing; run consolidate")
            return 1
        same = hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(body).digest()
        print(f"  {'✓' if same else '✗'} {target.name} {'fresh' if same else 'STALE'}: {len(rs):,} values, {quarters} quarters")
        return 0 if same else 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    tl_path.write_text(tl)
    print(f"  Wrote {target.relative_to(target.parents[2])}: {len(rs):,} values, {quarters} quarters "
          f"(local, rebuilt from the committed releases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
