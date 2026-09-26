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
from concurrent.futures import ProcessPoolExecutor
from pathlib import Path

# Bootstrap: <repo>/analysis on sys.path so `from core…` / `from signals…` resolve from
# any cwd now that this guard lives under guards/. Move-safe via .git walk.
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT                        # noqa: E402
from core import manifest                          # noqa: E402
ANALYSIS = ROOT / "analysis"
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


def _one(task):
    """Recompute ONE (pipeline, period) into its own throwaway DB and return its rows.

    A worker, deliberately: `run_append` writes only to the connection it is handed and caches
    the source CSV per process, so periods are independent and the CSV is parsed once per
    worker rather than once per period.
    """
    pipeline, period, registry = task
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
    tmp.close()
    path = Path(tmp.name)
    try:
        scratch = init_db(path)
        with contextlib.redirect_stdout(io.StringIO()):   # silence per-append summaries
            run_append(pipeline, period, scratch, registry)
        data = _rows(scratch)
        scratch.close()
        return data
    finally:
        try:
            os.unlink(path)
        except OSError:
            pass


def _recompute(registry, periods_by_pipeline, workers=None):
    """Recompute the given (pipeline -> {periods}) set from current sources; return the same
    {key: (value,status,unit)} mapping the committed DB is read into.

    PARALLEL BY PERIOD, and the guarantee is unchanged by it: every period is still recomputed
    from the CSV and compared row by row. Nothing is skipped, cached or trusted — the work is
    simply spread over cores instead of done one period at a time.

    This is deliberately NOT the other available speed-up. Fingerprinting the inputs and
    skipping when they are unchanged would be far faster still, and it would stop catching a
    hand-edited signals.db — a capability used four times in one day for negative tests, and the
    thing that makes this check evidence rather than bookkeeping.

    Falls back to serial on any pool failure: a guard that cannot run is worse than a slow one.
    """
    tasks = [(pl, per, registry)
             for pl, periods in sorted(periods_by_pipeline.items())
             for per in sorted(periods)]
    out: dict = {}
    if len(tasks) > 1:
        try:
            with ProcessPoolExecutor(max_workers=workers or min(os.cpu_count() or 1, 8)) as pool:
                for part in pool.map(_one, tasks):
                    out.update(part)
            return out
        except Exception as e:                            # noqa: BLE001
            print(f"  · parallel recompute unavailable ({e}); falling back to serial",
                  file=sys.stderr)
            out = {}
    for t in tasks:
        out.update(_one(t))
    return out


def _declared_periods() -> dict[str, set]:
    """{pipeline: periods the timeline says have been ingested}.

    The timeline is each pipeline's own record of what it has taken in — the only statement of
    what the signal store OUGHT to contain that does not come from the signal store itself.

    Both the pipelines and where each one keeps its timeline are read off the manifests. This was
    a hand-written pair of (sibc, atm_pos) until 2026-09-26, so NBFC, added later, fell back to the
    period set in the database: the exact circularity this function exists to remove, re-opened
    by the next pipeline. A reviewer found it cold. A pipeline that declares a timeline which is
    missing, or no `period_key`, now fails the check instead of silently dropping out of it.
    """
    out: dict[str, set] = {}
    for pl in manifest.discover_pipeline_ids():
        key = manifest.load(pl).get("period_key")
        if not key:
            raise SystemExit(f"✗ {pl}: manifest declares no period_key — freshness cannot tell "
                             f"which periods its timeline says were ingested")
        f = manifest.path(pl, "timeline")
        if not f.exists():
            raise SystemExit(f"✗ {pl}: declared timeline {f} is missing — "
                             f"refusing to fall back to the database's own list of periods")
        doc = json.loads(f.read_text())
        rows = doc["periods"] if isinstance(doc, dict) else doc
        periods = {r.get(key) for r in rows}
        periods.discard(None)
        if not periods:
            raise SystemExit(f"✗ {pl}: timeline has no '{key}' values — wrong period_key?")
        out[pl] = periods
    return out


def _fmt(triple) -> str:
    val, st, un = triple
    vs = "None" if val is None else f"{val:g}"
    return f"value={vs} status={st} unit={un}"


def check(pipeline_filter=None, quiet=False) -> int:
    if not DB_PATH.exists():
        print("  ✗ signals.db not found — run core/generate_signal_history.py append first", file=sys.stderr)
        return 1

    registry = json.loads(REG.read_text())

    conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True)
    committed = _rows(conn, pipeline_filter)
    conn.close()

    if not committed:
        print(f"  ✗ no committed rows for pipeline filter {pipeline_filter!r}", file=sys.stderr)
        return 1

    # The population is the TIMELINE, not the database.
    #
    # This read the period set off the committed rows, which means a period with NO rows was
    # never in the set, never recomputed and never compared. Deleting an entire month left the
    # check reporting "fresh — 46,013 rows match (sibc:10p)". Stale VALUES were caught; an
    # absent PERIOD was not — and an absent period is the June failure's own shape.
    #
    # timeline.json is the declared record of what has been ingested, so it is what the DB
    # should be measured against. A period declared and not appended now surfaces as
    # MISSING_IN_DB instead of silently shrinking the thing being checked.
    periods_by_pipeline: dict[str, set] = {}
    for (pl, per, *_rest) in committed:
        periods_by_pipeline.setdefault(pl, set()).add(per)
    for pl, declared in _declared_periods().items():
        if pipeline_filter and pl != pipeline_filter:
            continue
        if pl in periods_by_pipeline or not pipeline_filter:
            periods_by_pipeline.setdefault(pl, set()).update(declared)

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
              "    python3 analysis/core/generate_signal_history.py append --pipeline <name> --period <YYYY-MM-DD>\n"
              "  (run for all periods, not just the latest — that is the whole point of this check)",
              file=sys.stderr)
        return 1

    if not quiet:
        print(f"  ✓ signals.db fresh — {checked} rows match recompute ({pls})")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Verify signals.db matches a fresh recompute from source CSVs.")
    ap.add_argument("--pipeline", choices=manifest.PIPELINE_IDS, default=None,
                    help="Limit the check to one pipeline (default: all present in DB).")
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    return check(args.pipeline, args.quiet)


if __name__ == "__main__":
    sys.exit(main())
