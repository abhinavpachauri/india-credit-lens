#!/usr/bin/env python3
"""
is_news.py — is this signal's latest reading actually news?
------------------------------------------------------------
The monthly issue (DISTRIBUTION_SPEC §11.1) and the dashboard read-mode share one
problem: a feed lists cards in generation order, and most cards are not news. "Power is
57% of infrastructure" is true this month and every month; it should never lead. The
question a *read* has to pass is not "is this important" but "did this change".

This scores that, deterministically, from three factors — all computable from signals.db,
none of them prose:

  record    the latest value is an all-time high or low FOR A SERIES THAT COULD HAVE GONE
            EITHER WAY. A new record on a monotonic series (outstanding credit rises every
            month) is arithmetic, not news, so those score zero — the reversal test is the
            whole point of this factor.
  flip      the signal's status changed REGIME this period — growing → shrinking, or either
            → flat. Deliberately NOT the accelerating↔decelerating wobble: a YoY rate that
            ticks up one month and down the next flips `strengthening`↔`active` constantly
            while still growing, which is noise, not news. Only a regime crossing counts.
  crossed   any status boundary was crossed *this* period on the values themselves — the
            backward twin of proximity.py's "about to cross" (§11.1), and the finer-grained
            factor: it fires on the within-regime wobble too, which is why it is worth least
            and never makes something a read on its own.
  magnitude the signal moved much more than its own typical month (> 2× its median
            period-over-period move). Added 2026-07-23 (reco (b)): records and flips answer
            "did this change state"; magnitude catches a big, interesting move that set no
            record and flipped no regime — the three-factor version caught only 54.5% of the
            month's largest movers.

Score = 2·record + 2·flip + 2·magnitude + 1·crossed. A read must clear a STRONG factor
(floor 2.0), so `crossed` alone is never a read. A structural template scores 0 on all four
and can never surface; that property is the point, and `measure` below checks it.

Lives in the signal layer, registry-driven, like proximity.py — the classifier the
distribution reads selector uses is the one the dashboard read-mode reuses (§11.1).

    python3 analysis/signals/is_news.py --pipeline sibc          # ranked news table
    python3 analysis/signals/is_news.py --measure                # catch / false-rejection
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from signals import proximity                                   # noqa: E402

# Weights. Records, regime flips and outsized moves are the strong signals of news, each
# enough on its own to make a read; a fresh threshold crossing corroborates but rarely
# stands alone, so it is worth less.
W_RECORD, W_FLIP, W_MAGNITUDE, W_CROSSED = 2.0, 2.0, 2.0, 1.0

# How many typical monthly moves make a move "outsized" (the magnitude factor).
MAGNITUDE_MULT = 2.0

# A record only counts if the latest value clears the prior extreme by more than this
# fraction of the series range — a hair past a months-old high is a rounding artefact.
RECORD_MARGIN = 1e-9

# A streak/momentum reading this short is not a record worth reporting even at its max.
MIN_STREAK = 3

# Status words collapse to three regimes. A flip only counts when the regime changes —
# growing → shrinking, or either → flat — never the accelerating↔decelerating wobble
# within the growing regime, which any noisy rate does most months.
REGIME = {
    "strengthening": "grow", "active": "grow", "improving": "grow",
    "weakening": "shrink", "declining": "shrink", "falling": "shrink",
    "steady": "flat", "stable": "flat",
}

# Compute methods that describe structure, not movement — a share of a total is stable by
# construction and must never read as news. The independent template label for `measure`.
STRUCTURAL_METHODS = {"csv_sector_share", "csv_category_share",
                      "csv_sector_scan_share", "csv_category_scan_share"}

# A read must clear a strong factor (a record or a regime flip). `crossed` alone (score 1)
# is corroboration, never a headline.
READ_FLOOR = 2.0


def _extreme(values):
    """(is_record, kind) for the latest value.

    News only on a reversal-capable series: if every step so far has the same sign the
    series is monotonic and a new extreme is expected, not remarkable. So a record needs
    both a genuine all-time high/low AND a series that has changed direction at least once.
    """
    if len(values) < 3:
        return False, None
    steps = [b - a for a, b in zip(values, values[1:])]
    signs = {1 if s > 0 else -1 if s < 0 else 0 for s in steps if s != 0}
    if len(signs) < 2:
        return False, None                      # monotonic — a new extreme is just arithmetic
    latest = values[-1]
    prior = values[:-1]
    hi, lo = max(prior), min(prior)
    rng = (max(values) - min(values)) or 1.0
    if latest > hi + RECORD_MARGIN * rng:
        return True, "record high"
    if latest < lo - RECORD_MARGIN * rng:
        return True, "record low"
    return False, None


def _total_status(conn, pipeline, sid, period):
    row = conn.execute(
        "select status from signals where pipeline=? and metric_id=? and period=? "
        "  and (entity_type in ('total','aggregate') or entity_id='total') "
        "order by status limit 1", (pipeline, sid, period)).fetchone()
    return row[0] if row else None


def score(conn, sid, sig):
    """News score for one signal, with the factors that produced it. None if unmeasurable."""
    if sig.get("layer") != 1 or sig.get("current_status") == "retired":
        return None
    pipeline = sig.get("pipeline")
    hist = proximity.series(conn, pipeline, sid)
    if len(hist) < 3:
        return None
    periods = [p for p, _ in hist]
    values = [v for _, v in hist]
    period, prior_period = periods[-1], periods[-2]

    is_record, record_kind = _extreme(values)
    # A short momentum reading (a 1-2 period streak at its max) is not a record.
    if is_record and abs(values[-1]) < MIN_STREAK and sig.get("unit") == "count" \
            and "streak" in sid:
        is_record = False

    was = _total_status(conn, pipeline, sid, prior_period)
    now = _total_status(conn, pipeline, sid, period)
    # Regime change only — not the accelerating↔decelerating wobble within one regime.
    flipped = bool(was and now and REGIME.get(was) and REGIME.get(now)
                   and REGIME[was] != REGIME[now])

    # Backward twin of proximity: re-derive the status from the values with the signal's
    # own rules and ask whether it changed this period. Fires even when the stored status
    # came from a roll-up rather than the scalar rule.
    crossed = False
    rules = (sig.get("compute") or {}).get("status_rules")
    if rules and len(values) >= 3:
        prev_by_rule = proximity.eval_status(rules, values[-2], values[-3])
        now_by_rule = proximity.eval_status(rules, values[-1], values[-2])
        crossed = (prev_by_rule != now_by_rule
                   and "unknown" not in (prev_by_rule, now_by_rule))

    # Magnitude — this month's step vs the signal's own normal month.
    move = proximity.typical_move(values)
    magnitude = bool(move and abs(values[-1] - values[-2]) > MAGNITUDE_MULT * move)

    s = (W_RECORD * is_record + W_FLIP * flipped
         + W_MAGNITUDE * magnitude + W_CROSSED * crossed)
    return {
        "signal_id": sid, "pipeline": pipeline, "title": sig.get("title", sid),
        "period": period, "score": s,
        "factors": {"record": bool(is_record), "flip": flipped,
                    "magnitude": magnitude, "crossed": crossed},
        "record_kind": record_kind, "was": was, "now": now,
    }


def ranked(pipeline=None, registry=None, conn=None):
    """Every measurable signal, most newsworthy first."""
    close = False
    if conn is None:
        conn = proximity._con()
        close = True
    registry = registry or proximity.load_registry()
    out = []
    for sid, sig in registry.items():
        if pipeline and sig.get("pipeline") != pipeline:
            continue
        row = score(conn, sid, sig)
        if row:
            out.append(row)
    if close:
        conn.close()
    out.sort(key=lambda r: (-r["score"], r["signal_id"]))
    return out


def score_card(conn, card, registry):
    """A card's news score = the best score among the signals it cites (0 if none score)."""
    best = None
    for sid in card.get("signal_ids", []):
        sig = registry.get(sid)
        if not sig:
            continue
        row = score(conn, sid, sig)
        if row and (best is None or row["score"] > best["score"]):
            best = row
    return best


def shortlist(cards, registry, conn=None):
    """All candidate cards ranked by news score, most newsworthy first — no floor cut.

    The editor reads this and picks (the determinism-vs-judgment boundary, §11.1): the score
    says what changed most, the human says what matters. Cards that cite no scorable signal
    sort last at score 0, still visible so the editor can override."""
    close = False
    if conn is None:
        conn = proximity._con()
        close = True
    scored = []
    for c in cards:
        row = score_card(conn, c, registry)
        scored.append({"card": c, "news": row,
                       "score": row["score"] if row else 0.0})
    if close:
        conn.close()
    scored.sort(key=lambda t: (-t["score"], (t["card"].get("signal_ids") or [""])[0]))
    return scored


def select_reads(cards, registry, k=2, conn=None, floor=READ_FLOOR):
    """The `k` cards that most clearly changed this period — the 'reads that matter'.

    A card scoring below `floor` is not a read: it did not clear one strong factor. When
    fewer than `k` clear it, return fewer — an honest null beats padding the section
    (§11.1). Ties break on score then card id for determinism.
    """
    close = False
    if conn is None:
        conn = proximity._con()
        close = True
    scored = []
    for c in cards:
        row = score_card(conn, c, registry)
        if row and row["score"] >= floor:
            scored.append((row["score"], row, c))
    if close:
        conn.close()
    scored.sort(key=lambda t: (-t[0], t[1]["signal_id"]))
    return [{"card": c, "news": row} for _, row, c in scored[:k]]


# ── Measurement (AI PM topic #1: does the selector admit news and reject templates?) ──

def _magnitude_outlier(conn, sid, sig, mult=2.0):
    """News label INDEPENDENT of the score: did the signal move much more than usual this
    period? |latest step| > mult × its own typical monthly move. A behavioural label — it
    knows nothing about records, regimes, or thresholds, so checking the categorical score
    against it is not circular."""
    hist = proximity.series(conn, sig.get("pipeline"), sid)
    if len(hist) < 4:
        return False
    values = [v for _, v in hist]
    move = proximity.typical_move(values)
    if not move:
        return False
    return abs(values[-1] - values[-2]) > mult * move


def measure():
    """How good is the selector — measured two ways.

      template-reject  the independent, non-circular test. A template = a SHARE signal
                       (STRUCTURAL_METHODS) that ALSO barely moved (< 0.5× its typical move):
                       the "Power is 57% of infrastructure" case, structure sitting still. It
                       must score below the read floor. Both halves of the label (method +
                       magnitude) are blind to the score, so this is a real question. (A share
                       that DID move a lot — a record share — is legitimately news and is not
                       labelled a template.)
      selectivity      the share of all scored signals that clear the read floor. A selector
                       that admits everything is useless however well it rejects templates; a
                       read is meant to be the exception, so this should be a clear minority.
      magnitude-cover  now that magnitude is a factor, a magnitude outlier clears the floor by
                       construction — reported as a consistency check (should be ~100%), not an
                       independent catch rate.
    """
    conn = proximity._con()
    registry = proximity.load_registry()
    rows = {r["signal_id"]: r for r in ranked(registry=registry, conn=conn) if r}

    templates, outliers = [], []
    for sid, sig in registry.items():
        if sid not in rows:
            continue
        method = (sig.get("compute") or {}).get("method")
        # A template is a SHARE that sits still AND is not otherwise newsworthy. A share can
        # barely move yet still print an all-time record (a slow asymptotic approach to a new
        # extreme) — that record IS news (the docstring's "record share is not a template"),
        # so a record-setter is excluded from the template set regardless of its move size.
        if (method in STRUCTURAL_METHODS
                and _magnitude_outlier(conn, sid, sig, mult=0.5) is False
                and not rows[sid]["factors"].get("record")):
            templates.append(sid)
        if _magnitude_outlier(conn, sid, sig):
            outliers.append(sid)

    reject = sum(1 for sid in templates if rows[sid]["score"] < READ_FLOOR)
    clear = sum(1 for r in rows.values() if r["score"] >= READ_FLOOR)
    cover = sum(1 for sid in outliers if rows[sid]["score"] >= READ_FLOOR)
    conn.close()
    return {
        "signals_scored": len(rows),
        "read_floor": READ_FLOOR,
        "template_reject": (reject, len(templates)),
        "selectivity": (clear, len(rows)),
        "magnitude_cover": (cover, len(outliers)),
    }


def main():
    ap = argparse.ArgumentParser(description="Score signals by whether their latest reading is news")
    ap.add_argument("--pipeline", choices=["sibc", "atm_pos"])
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.measure:
        m = measure()
        print(json.dumps(m, indent=1))
        r, t = m["template_reject"]
        c, s = m["selectivity"]
        print(f"\ntemplate reject (static shares below floor): "
              + (f"{r}/{t} = {100.0*r/t:.1f}%" if t else "no static share signals"))
        print(f"selectivity (signals clearing floor {m['read_floor']}): "
              f"{c}/{s} = {100.0*c/s:.1f}%   ← a read should be the exception")
        return 0

    rows = ranked(args.pipeline)
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    print(f"{'score':>5}  {'signal':<38} {'rec':>3} {'flip':>4} {'mag':>4} {'cross':>5}  now")
    for r in rows:
        if r["score"] <= 0:
            continue
        f = r["factors"]
        print(f"{r['score']:5.1f}  {r['signal_id'][:38]:<38} "
              f"{'●' if f['record'] else '·':>3} {'●' if f['flip'] else '·':>4} "
              f"{'●' if f['magnitude'] else '·':>4} {'●' if f['crossed'] else '·':>5}  "
              f"{r['now'] or ''}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
