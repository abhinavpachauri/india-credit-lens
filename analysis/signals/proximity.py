#!/usr/bin/env python3
"""
proximity.py — how close is each signal to changing its mind?
--------------------------------------------------------------
Every Layer-1 signal carries `compute.status_rules`: an ordered list of conditions over
`value` and `prev_value` that decide its status. The rules already say where the cliff
edges are. Nobody had ever asked how close each signal is standing to one.

This asks. For a signal at its latest period it finds the smallest move — up or down —
that would make NEXT period read as a different status. That distance is a property of
the signal, so it lives here in the signal layer rather than in whichever consumer
happened to want it first (DISTRIBUTION_SPEC §6). The distribution layer's C8 watchlist
is the first consumer; the dashboard and the reply desk are the next.

Two kinds of edge come out of this, and they are different stories with identical
arithmetic: a **level** sits a real distance away, while a **knife edge** is a momentum
rule whose threshold is today's own value — it turns on any step the wrong way. Only
levels belong on a watchlist, so that is what `ranked()` returns by default.

Ranking needs a common scale — 0.4 pp is a hair for one series and a lifetime for
another. So distance is divided by the signal's own typical monthly move (the median
absolute period-over-period change over its history), giving "moves away": how many
ordinary months of drift separate this signal from a different status.

Deterministic, registry-driven, no LLM, reads signals.db only.

    python3 analysis/signals/proximity.py                  # ranked table
    python3 analysis/signals/proximity.py --pipeline sibc --limit 10
"""
import argparse
import json
import sqlite3
import statistics
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

DB = ROOT / "analysis" / "signals" / "signals.db"
REGISTRY = ROOT / "analysis" / "signals" / "registry.json"

# Only total-level rows: a scan signal's per-entity rows roll up to one status, and a
# watchlist of 67 bank rows is noise, not a watchlist.
TOTAL_LEVELS = ("total", "aggregate")

# Search bounds for the flip point, as a multiple of the signal's typical move. Beyond
# this the signal is not "close to flipping" in any sense a reader would recognise.
MAX_MOVES_SEARCHED = 12.0
BISECT_STEPS = 40

# Below this many typical moves, the "threshold" is effectively today's value — a
# momentum rule that flips on any step the wrong way rather than a distance to travel.
KNIFE_EDGE_MOVES = 0.02


def load_registry():
    return json.loads(REGISTRY.read_text())["signals"]


def _con():
    return sqlite3.connect(f"file:{DB}?mode=ro", uri=True)


def eval_status(rules, value, prev_value):
    """Re-implementation of the compute layer's rule evaluation, on hypothetical values.

    Deliberately identical in behaviour to `compute.sibc._eval_status` — the same
    expressions, the same order, the same unknown fallback. It has to be a separate
    entry point because that one only ever sees values that actually happened, and the
    whole point here is to ask what would happen if the value were different.
    """
    if value is None:
        return "unknown"
    ctx = {"value": value, "prev_value": prev_value if prev_value is not None else value}
    for rule in rules:
        cond = rule["if"]
        if cond == "true":
            return rule["then"]
        try:
            if eval(cond, {"__builtins__": {}}, ctx):   # noqa: S307
                return rule["then"]
        except Exception:
            continue
    return "unknown"


def series(conn, pipeline, metric_id):
    """Chronological (period, value) for the signal's total-level row."""
    rows = conn.execute(
        "select period, value from signals where pipeline=? and metric_id=? "
        "  and (entity_type in ('total','aggregate') or entity_id='total') "
        "  and value is not null order by period", (pipeline, metric_id)).fetchall()
    return [(p, float(v)) for p, v in rows]


def typical_move(values):
    """Median absolute period-over-period change — the signal's own idea of a normal month."""
    steps = [abs(b - a) for a, b in zip(values, values[1:]) if a is not None and b is not None]
    steps = [s for s in steps if s > 0]
    return statistics.median(steps) if steps else None


def _flip_point(rules, value, prev_value, current, span, direction):
    """Smallest move in one direction that changes the status, or None within `span`.

    Coarse scan to bracket the change, then bisect — the rules are step functions, so a
    scan alone would report the grid resolution rather than the real edge.
    """
    step = span / 60.0
    lo = 0.0
    hi = None
    x = step
    while x <= span:
        if eval_status(rules, value + direction * x, prev_value) != current:
            hi = x
            break
        lo = x
        x += step
    if hi is None:
        return None
    for _ in range(BISECT_STEPS):
        mid = (lo + hi) / 2
        if eval_status(rules, value + direction * mid, prev_value) != current:
            hi = mid
        else:
            lo = mid
    return hi


def proximity(conn, sid, sig):
    """One signal's distance to its next status flip, or None if it isn't measurable.

    The question is forward-looking — *what could flip next month* — so the hypothetical
    is next period's reading: candidate values are tried against `prev_value = the value
    we have now`, which is what the rules will actually compare against next time.
    """
    rules = (sig.get("compute") or {}).get("status_rules")
    pipeline = sig.get("pipeline")
    if not rules or sig.get("layer") != 1 or sig.get("current_status") == "retired":
        return None

    hist = series(conn, pipeline, sid)
    if len(hist) < 3:
        return None
    period, value = hist[-1]
    move = typical_move([v for _, v in hist])
    if not move:
        return None

    # Next period's rules will compare against today's value; hold that fixed and move
    # the candidate. Status "now" is what a repeat of today's value would read as.
    current = eval_status(rules, value, value)
    if current == "unknown":
        return None

    span = move * MAX_MOVES_SEARCHED
    best = None
    for direction in (1, -1):
        dist = _flip_point(rules, value, value, current, span, direction)
        if dist is None:
            continue
        target = eval_status(rules, value + direction * dist, value)
        cand = {"distance": dist, "direction": direction, "target_status": target,
                "threshold_value": value + direction * dist}
        if best is None or cand["distance"] < best["distance"]:
            best = cand
    if best is None:
        return None

    moves_away = best["distance"] / move
    return {
        "signal_id": sid, "pipeline": pipeline, "title": sig.get("title", sid),
        "period": period, "value": value, "prev_value": hist[-2][1],
        "unit": sig.get("unit", ""), "current_status": current,
        "typical_move": move, "moves_away": moves_away,
        # Two different stories share the same arithmetic, so name them apart. A knife
        # edge is a momentum rule — its threshold IS today's value, so it turns on any
        # move the wrong way and says nothing about magnitude. A level is a real numeric
        # edge some distance away, which is the one worth a watchlist slot.
        "flip_kind": "knife_edge" if moves_away < KNIFE_EDGE_MOVES else "level",
        **best,
    }


def _unit_of(conn, pipeline, sid):
    """The unit of the row the distance was measured on — same entity filter as `series`.

    A pair-divergence signal stores its gap in pp at total level and each side's own rate
    in pct at `pair_side` level. Ask without the filter and the sides can win the race,
    which prints a percentage-point gap as a percent.
    """
    row = conn.execute(
        "select unit from signals where pipeline=? and metric_id=? and unit is not null "
        "  and (entity_type in ('total','aggregate') or entity_id='total') "
        "order by period desc limit 1", (pipeline, sid)).fetchone()
    return row[0] if row else ""


def ranked(pipeline=None, limit=None, kind="level"):
    """Measurable signals, nearest flip first.

    Defaults to `kind='level'` because that is what a watchlist means: signals with a
    real distance still to travel. Pass kind=None for everything including the knife
    edges, which are a different (and much shorter) story.
    """
    registry = load_registry()
    conn = _con()
    out = []
    for sid, sig in registry.items():
        if pipeline and sig.get("pipeline") != pipeline:
            continue
        row = proximity(conn, sid, sig)
        if row and (kind is None or row["flip_kind"] == kind):
            row["unit"] = _unit_of(conn, row["pipeline"], sid)
            out.append(row)
    conn.close()
    out.sort(key=lambda r: r["moves_away"])
    return out[:limit] if limit else out


STATUS_WORD = {"strengthening": "accelerating", "active": "growing steadily",
               "weakening": "slowing", "declining": "falling", "stable": "steady",
               "improving": "improving", "unknown": "no clear read"}


def _fmt(v, unit):
    if unit == "pct":
        return f"{v:.1f}%"
    if unit == "pp":
        # Space before the unit, matching core.relational_insights._pp: the traceability
        # extractors read "1.9 pp" as 1.9 but backtrack glued "1.9pp" to a bare 1, which
        # then fails to trace to anything and takes the whole slot down with it.
        return f"{v:.1f} pp"
    if unit == "count" and abs(v) >= 1e5:
        return f"{v / 1e5:.1f} lakh"
    return f"{v:,.1f}"


def sentence(row):
    """Plain-English watchlist line. Deterministic prose — this is the published text."""
    unit = row["unit"]
    move = "rise" if row["direction"] > 0 else "fall"
    return (f"{row['title']} is {_fmt(row['value'], unit)} and reads "
            f"{STATUS_WORD.get(row['current_status'], row['current_status'])}. "
            f"A {move} to {_fmt(row['threshold_value'], unit)} would change that reading to "
            f"{STATUS_WORD.get(row['target_status'], row['target_status'])} — "
            f"a move of {_fmt(row['distance'], unit)}, against a typical monthly move of "
            f"{_fmt(row['typical_move'], unit)}.")


def short_sentence(row):
    """The same fact in two short sentences — long enough for a pager, too long for a
    LinkedIn line, so the social copy gets its own shape rather than a truncation."""
    unit = row["unit"]
    move = "rise" if row["direction"] > 0 else "fall"
    return (f"{row['title']} is at {_fmt(row['value'], unit)}, reading "
            f"{STATUS_WORD.get(row['current_status'], row['current_status'])}. "
            f"A {move} of {_fmt(row['distance'], unit)} turns it "
            f"{STATUS_WORD.get(row['target_status'], row['target_status'])}")


def main():
    ap = argparse.ArgumentParser(description="Rank signals by distance to their next status flip")
    ap.add_argument("--pipeline", choices=["sibc", "atm_pos"])
    ap.add_argument("--limit", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--all-kinds", action="store_true", help="include knife-edge (momentum) flips")
    args = ap.parse_args()

    rows = ranked(args.pipeline, args.limit, kind=None if args.all_kinds else "level")
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    print(f"{'moves':>6}  {'signal':<38} {'now':<15} {'would become':<15} threshold")
    for r in rows:
        print(f"{r['moves_away']:6.2f}  {r['signal_id'][:38]:<38} "
              f"{r['current_status']:<15} {r['target_status']:<15} "
              f"{_fmt(r['threshold_value'], r['unit'])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
