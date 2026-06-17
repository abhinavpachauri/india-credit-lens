#!/usr/bin/env python3
"""
check_signal_freshness.py — deterministic freshness guard for signals.db
------------------------------------------------------------------------
signals.db is a DETERMINISTIC function of the consolidated CSVs + the registry
compute specs. If a CSV is corrected (e.g. date normalisation) without
re-appending EVERY period, historical rows go stale while only the latest stays
fresh — which silently fabricates trends. This was the root cause of the
FY-acceleration "phantom 5.1 -> 7.1 jump" (2026-06): only the latest period had
been re-appended after a CSV fix, so a period-invariant metric looked like it
moved month to month.

check_derived_fresh.py guards the deterministic S1->S3 chain but EXCLUDES
signals.db (it is binary; a raw git-diff churns on computed_at timestamps). This
guard closes that gap at the VALUE level: it recomputes every (pipeline, period)
present in the committed DB from current sources into a throwaway DB and fails on
any drift in value / status / unit, or any missing / orphaned row.

The LLM evaluation layer (evaluations/*.json) is non-deterministic and is NOT
checked here — but it reads from this DB, so a fresh DB is the deterministic
guarantee that matters.

Usage:
    python3 analysis/check_signal_freshness.py                 # all pipelines
    python3 analysis/check_signal_freshness.py --pipeline sibc
    python3 analysis/check_signal_freshness.py --quiet
"""
import argparse
import contextlib
import io
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parent
REG = ANALYSIS / "signals" / "registry.json"

from signals.db import init_db, DB_PATH           # noqa: E402
from signals.compute.engine import run_append     # noqa: E402

# Both compute paths round values to 4 dp via _row(); tolerance guards float noise.
VALUE_TOL = 1e-4


def _rows(conn, pipeline=None):
    """Return {(pipeline,period,metric_id,entity_type,entity_id): (value,status,unit)}."""
    q = ("SELECT pipeline,period,metric_id,entity_type,entity_id,value,status,unit "
         "FROM signals")
    args: tuple = ()
    if pipeline:
        q += " WHERE pipeline=?"
        args = (pipeline,)
    return {(r[0], r[1], r[2], r[3], r[4]): (r[5], r[6], r[7])
            for r in conn.execute(q, args).fetchall()}


def _recompute(registry, periods_by_pipeline):
    """Recompute the given (pipeline -> {periods}) set from current sources into a
    throwaway DB; return the same {key: (value,status,unit)} mapping."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    try:
        scratch = init_db(path)
        with contextlib.redirect_stdout(io.StringIO()):   # silence per-append summaries
            for pipeline, periods in periods_by_pipeline.items():
                for period in sorted(periods):
                    run_append(pipeline, period, scratch, registry)
        data = _rows(scratch)
        scratch.close()
        return data
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _fmt(triple) -> str:
    val, st, un = triple
    vs = "None" if val is None else f"{val:g}"
    return f"value={vs} status={st} unit={un}"


def check(pipeline_filter=None, quiet=False) -> int:
    if not DB_PATH.exists():
        print("  ✗ signals.db not found — run generate_signal_history.py append first", file=sys.stderr)
        return 1

    registry = json.loads(REG.read_text())

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    committed = _rows(conn, pipeline_filter)
    conn.close()

    if not committed:
        print(f"  ✗ no committed rows for pipeline filter {pipeline_filter!r}", file=sys.stderr)
        return 1

    # Recompute exactly the (pipeline, period) set present in the committed DB.
    periods_by_pipeline: dict[str, set] = {}
    for (pl, per, *_rest) in committed:
        periods_by_pipeline.setdefault(pl, set()).add(per)

    expected = _recompute(registry, periods_by_pipeline)

    drift = []
    for k in sorted(set(committed) | set(expected)):
        c, e = committed.get(k), expected.get(k)
        if c is None:
            drift.append(("MISSING_IN_DB (stale: not appended)", k, e))
            continue
        if e is None:
            drift.append(("ORPHAN_IN_DB (stale: no longer computed)", k, c))
            continue
        cv, cs, cu = c
        ev, es, eu = e
        vbad = ((cv is None) != (ev is None)) or \
               (cv is not None and ev is not None and abs(cv - ev) > VALUE_TOL)
        if vbad or cs != es or cu != eu:
            drift.append(("DRIFT", k, (c, e)))

    checked = len(set(committed) | set(expected))
    pls = ", ".join(f"{p}:{len(s)}p" for p, s in sorted(periods_by_pipeline.items()))

    if drift:
        print(f"  ✗ signals.db STALE — {len(drift)} of {checked} rows differ from a fresh "
              f"recompute from the current CSV ({pls}):", file=sys.stderr)
        for kind, key, detail in drift[:25]:
            ks = "/".join(str(x) for x in key)
            if kind == "DRIFT":
                c, e = detail
                print(f"    {kind}  {ks}", file=sys.stderr)
                print(f"        committed: {_fmt(c)}", file=sys.stderr)
                print(f"        expected:  {_fmt(e)}", file=sys.stderr)
            else:
                print(f"    {kind}  {ks}  ({_fmt(detail)})", file=sys.stderr)
        if len(drift) > 25:
            print(f"    ... and {len(drift) - 25} more", file=sys.stderr)
        print("\n  Fix: re-append EVERY period for the affected pipeline, e.g.\n"
              "    python3 analysis/generate_signal_history.py append --pipeline <name> --period <YYYY-MM-DD>\n"
              "  (run for all periods, not just the latest — that is the whole point of this check)",
              file=sys.stderr)
        return 1

    if not quiet:
        print(f"  ✓ signals.db fresh — {checked} rows match recompute ({pls})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify signals.db matches a fresh recompute from source CSVs.")
    ap.add_argument("--pipeline", choices=["sibc", "atm_pos"], default=None,
                    help="Limit the check to one pipeline (default: all present in DB).")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    return check(args.pipeline, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
