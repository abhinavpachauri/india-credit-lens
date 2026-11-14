#!/usr/bin/env python3
"""
consolidate.py — saved quarters → one long table, rebuilt locally (BANKWISE_SPEC.md §8, phase 1)
───────────────────────────────────────────────────────────────────────────────────────────────────
The record is the saved quarters (`releases/{quarter}/{saved}.json.gz`, committed, ~145 KB each).
The long table is ~2.8 million values for 2002 → 2026 (~140 MB), too big to commit, so it is a
local file rebuilt from the releases (user, 2026-11-14), git-ignored, like `signals.db` beside its
committed `.gz`. Rows follow the reference-pipeline schema (dataset, base_year, period, code,
measure, value, status): dataset = sheet, code = bank or group id, measure = column id,
status = "bank" or "group". A cell RBI left empty is not a row; the release keeps it as null.

    python3 analysis/pipelines/rbi_bankwise/consolidate.py            # write
    python3 analysis/pipelines/rbi_bankwise/consolidate.py --check    # the file equals a rebuild
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / ".git").is_dir()) / "analysis"))
from core import manifest  # noqa: E402

PIPELINE = "rbi_bankwise"
FIELDS = ("dataset", "base_year", "period", "code", "measure", "value", "status")


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
        for kind, ents in (("bank", doc["banks"]), ("group", doc["groups"])):
            for code, e in sorted(ents.items()):
                for sheet, cols in sorted(e["sheets"].items()):
                    for measure, v in sorted(cols.items()):
                        if v is not None:
                            out.append((sheet, "", quarter, code, measure, repr(float(v)), kind))
    return out


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
    quarters = len({r[2] for r in rs})
    if a.check:
        if not target.exists():
            print(f"  ✗ {target.name} missing; run consolidate")
            return 1
        same = hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(body).digest()
        print(f"  {'✓' if same else '✗'} {target.name} {'fresh' if same else 'STALE'}: {len(rs):,} values, {quarters} quarters")
        return 0 if same else 1
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(body)
    print(f"  Wrote {target.relative_to(target.parents[2])}: {len(rs):,} values, {quarters} quarters "
          f"(local, rebuilt from the committed releases)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
