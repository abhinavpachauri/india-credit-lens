#!/usr/bin/env python3
"""
planes.py — which of the three reader questions does this signal answer?
------------------------------------------------------------------------
The dashboard read-mode (DASHBOARD_SPEC.md) sorts every signal into one of three planes,
each answering a different reader question:

  read         "what changed this month?"  — the signal MOVED enough to be news.
  composition  "what's the structure?"     — the signal says the same thing every month
               ("Power is 57% of infrastructure"): true, worth showing once as a caption,
               never worth leading with.
  subject      "what's happening with X?"   — everything else. It moved a little, or it is a
               level nobody would call news, but it is still a real card the reader can open.

`read` is already decided elsewhere: is_news.score ≥ READ_FLOOR. This module owns the ONE
net-new judgement — is a signal *structural* (composition) — and the partition that follows
from it. Priority is read → composition → subject, so the three planes never overlap.

Why is_news / proximity could not answer this: they measure MOVEMENT. `categories.py` cannot
either — it answers *which question a signal asks*, not *does the answer change*: category C1
holds both `csv_sector_yoy` (pure delta) and `csv_sector_share` (pure structure). So the
composition rule is its own thing, and — per the standing AI PM rule — it ships with a measured
catch / false-rejection rate (`--measure`), not on prose.

The rule, in one line: a signal is structural when it has BARELY MOVED across the trailing year —
its spread sits inside a per-unit materiality band — and is not already a read.

The spec draft (§3) also asked the status to have held one regime. Measurement retired that half:
it dropped genuinely-still shares whose status LABEL wobbles on knife-edge noise (personal-loans
share sits at ~33% all year while its status ticks grow↔flat on sub-point moves). That wobble is
exactly the noise proximity.py names and discards; burying "personal loans are a third of advances"
out of the composition caption because of it was wrong. The read-first priority already removes
anything is_news calls news, so a still value that reaches this test is structure — the status
label says nothing a caption needs. `regime_held` is still computed and returned, for explaining a
card, but no longer gates the plane. (Catch 66.7%→90%, false-reject held at 0%.)

Deterministic, registry-driven, reads signals.db only. Lives in the signal layer beside
is_news.py and proximity.py — the classifier the dashboard uses is one every surface can reuse.

    python3 analysis/signals/planes.py --pipeline sibc      # per-signal plane table
    python3 analysis/signals/planes.py --measure            # catch / false-rejection
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from signals import is_news, proximity                          # noqa: E402

# How far back "the trailing year" reaches. Structure is a claim about the recent past, not
# all history — a share that was volatile two years ago but has settled is structural now.
WINDOW = 12

# The materiality band — how much a signal may move over the window and still count as "sitting
# still". Two families: rates and shares are read in their own points (a share within 3 pp over a
# year is flat, whether it is a 57% share or a 0.2% one — the point is the same size); everything
# else is judged RELATIVE to its own level, because 5% of a crore total and 5% of a card count are
# different absolute numbers but the same "barely moved".
BAND_ABS = 3.0                          # percentage points, for rates and shares
BAND_REL = 0.05                         # fraction of the signal's own median level, for the rest
ABS_UNITS = {"pct", "pp"}               # units already denominated in points

# A structural read needs enough history to be a claim about stability, not an accident of two
# points. Below this the signal is simply "subject" until it has a track record.
MIN_HISTORY = 4

# Momentum signals are never structural — a streak is a statement about change by construction.
MOMENTUM_UNITS = {"periods"}


def _window(values):
    return values[-WINDOW:] if len(values) > WINDOW else values


def _is_share(method):
    """A share of a total is denominated in percentage points — even when the registry left its
    unit blank — so it is judged in absolute points, never relative to its own (often tiny) level."""
    return method in is_news.STRUCTURAL_METHODS


def _band(unit, method, window_values):
    """The largest spread this signal may show over the window and still be 'still', in the
    signal's own units. Absolute points for rates and shares; a fraction of the level otherwise."""
    if unit in ABS_UNITS or _is_share(method):
        return BAND_ABS
    level = proximity.statistics.median([abs(v) for v in window_values]) if window_values else 0.0
    return BAND_REL * level if level else None


def _status_series(conn, pipeline, sid, periods):
    """The total-level status at each of these periods — the raw material for 'has the regime
    held'. One query, filtered to the same total/aggregate row `series` reads its values from."""
    rows = conn.execute(
        "select period, status from signals where pipeline=? and metric_id=? "
        "  and (entity_type in ('total','aggregate') or entity_id='total') "
        "  and status is not null order by period", (pipeline, sid)).fetchall()
    want = set(periods)
    return [st for p, st in rows if p in want]


def _one_regime(statuses):
    """True when every known status collapses to a single regime (grow / shrink / flat).
    Unknowns don't break a run — they are silence, not a change of mind."""
    regimes = {is_news.REGIME[s] for s in statuses if s in is_news.REGIME}
    return len(regimes) <= 1


def is_structural(conn, sid, sig):
    """Has this signal said the same thing all year? Returns the judgement plus the numbers
    behind it (for explainability and for `measure`), or None if it can't be judged."""
    if sig.get("layer") != 1 or sig.get("current_status") == "retired":
        return None
    unit = sig.get("unit", "")
    if unit in MOMENTUM_UNITS or "streak" in sid:
        return {"structural": False, "reason": "momentum signal — change by construction"}

    pipeline = sig.get("pipeline")
    hist = proximity.series(conn, pipeline, sid)
    if len(hist) < MIN_HISTORY:
        return None
    win = _window([v for _, v in hist])
    win_periods = [p for p, _ in hist][-len(win):]

    spread = max(win) - min(win)
    band = _band(unit, (sig.get("compute") or {}).get("method"), win)
    if band is None:                    # level is ~0 (a YoY hovering at zero) — relative band undefined
        return {"structural": False, "reason": "level ~0, materiality band undefined",
                "spread": spread}

    still = spread <= band
    regime_held = _one_regime(_status_series(conn, pipeline, sid, win_periods))
    return {
        "structural": bool(still),      # read-first priority already excluded the movers
        "spread": spread, "band": band, "unit": unit,
        "still": still, "regime_held": regime_held,
        "window": len(win),
    }


# ── The partition ─────────────────────────────────────────────────────────────────────────

READ, COMPOSITION, SUBJECT = "read", "composition", "subject"


def plane(conn, sid, sig):
    """The plane one signal belongs to, with the evidence for it. read wins over composition wins
    over subject, so the result is a clean partition — a mover is never also filed as structure.
    Both the news score and the structural read are always returned (a subject still has a score,
    just below the read floor — the accordion uses it to say how close it came)."""
    news = is_news.score(conn, sid, sig)
    struct = is_structural(conn, sid, sig)
    if news and news["score"] >= is_news.READ_FLOOR:
        p = READ
    elif struct and struct.get("structural"):
        p = COMPOSITION
    else:
        p = SUBJECT
    return {"plane": p, "news": news, "structural": struct}


def classify(pipeline=None, registry=None, conn=None):
    """Every measurable signal with its plane. Order: reads first (by news score), then
    composition, then subjects — the reading order of the page itself."""
    close = False
    if conn is None:
        conn = proximity._con()
        close = True
    registry = registry or proximity.load_registry()
    out = []
    for sid, sig in registry.items():
        if pipeline and sig.get("pipeline") != pipeline:
            continue
        if sig.get("layer") != 1 or sig.get("current_status") == "retired":
            continue
        p = plane(conn, sid, sig)
        out.append({"signal_id": sid, "pipeline": sig.get("pipeline"),
                    "title": sig.get("title", sid), **p})
    if close:
        conn.close()
    rank = {READ: 0, COMPOSITION: 1, SUBJECT: 2}
    out.sort(key=lambda r: (rank[r["plane"]],
                            -(r.get("news") or {}).get("score", 0.0),
                            r["signal_id"]))
    return out


def plane_card(conn, card, registry):
    """A card's plane, from the signals it cites. A card is a read if ANY cited signal is news;
    composition only if EVERY cited signal is structural (one dynamic member makes it a subject);
    otherwise subject. Matches how the reader would file the card, not the signal."""
    planes = []
    for sid in card.get("signal_ids", []):
        sig = registry.get(sid)
        if sig:
            planes.append(plane(conn, sid, sig)["plane"])
    if not planes:
        return SUBJECT
    if READ in planes:
        return READ
    if all(p == COMPOSITION for p in planes):
        return COMPOSITION
    return SUBJECT


# ── Measurement (AI PM topic #1: does the classifier demote structure and only structure?) ──

# The independent "truly still" label: a SHARE signal whose spread over its WHOLE history is under
# a point. Deliberately tighter than the classifier's 3 pp band and computed on raw values with no
# status logic, so agreement is a real question — "Power is 57% every month" is the archetype.
TRULY_STILL_PP = 1.0


def _truly_still(conn, sid, sig):
    if (sig.get("compute") or {}).get("method") not in is_news.STRUCTURAL_METHODS:
        return False
    hist = proximity.series(conn, sig.get("pipeline"), sid)
    if len(hist) < MIN_HISTORY:
        return False
    values = [v for _, v in hist]
    return (max(values) - min(values)) <= TRULY_STILL_PP


def measure():
    """How good is the composition rule — two non-circular numbers plus the partition shape.

      catch          of signals that are TRULY STILL (a share flat to within 1 pp over all history
                     — an independent label, blind to the classifier's band) AND not news this
                     period, the fraction filed as `composition`. A truly-still share that IS news
                     this month is correctly a read, not a miss, so it leaves the denominator
                     (reported separately as `still_but_news`). A real miss is structure left as an
                     un-flagged `subject` card the reader would still meet in a carousel.
      false-reject   of MAGNITUDE OUTLIERS (moved > 2× their own typical move this period — the
                     opposite of structure, is_news's independent behavioural label), the fraction
                     WRONGLY filed as `composition`. Must be ~0: the whole risk of a stillness rule
                     is calling a big mover 'structure'.
      partition      how many signals land in each plane — a sanity shape, not a score. Composition
                     is meant to be a real slice (the 'not news' residue), reads a clear minority.
    """
    conn = proximity._con()
    registry = proximity.load_registry()
    rows = {r["signal_id"]: r for r in classify(registry=registry, conn=conn)}

    still, movers = [], []
    for sid, sig in registry.items():
        if sid not in rows:
            continue
        if _truly_still(conn, sid, sig):
            still.append(sid)
        if is_news._magnitude_outlier(conn, sid, sig):
            movers.append(sid)

    still_news = [sid for sid in still if rows[sid]["plane"] == READ]
    still_scored = [sid for sid in still if sid not in still_news]
    caught = sum(1 for sid in still_scored if rows[sid]["plane"] == COMPOSITION)
    wrong = sum(1 for sid in movers if rows[sid]["plane"] == COMPOSITION)
    from collections import Counter
    partition = Counter(r["plane"] for r in rows.values())
    conn.close()
    return {
        "signals": len(rows),
        "catch": (caught, len(still_scored)),
        "still_but_news": len(still_news),
        "false_reject": (wrong, len(movers)),
        "partition": dict(partition),
    }


def main():
    ap = argparse.ArgumentParser(description="Sort signals into read / composition / subject planes")
    ap.add_argument("--pipeline", choices=["sibc", "atm_pos"])
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()

    if args.measure:
        m = measure()
        if args.json:
            print(json.dumps(m, indent=1))
            return 0
        c, ct = m["catch"]
        w, wt = m["false_reject"]
        print(f"signals scored     {m['signals']}")
        print(f"catch (structural) {c}/{ct}  = {100 * c / ct:.1f}%" if ct else "catch  n/a")
        print(f"  still-but-news   {m['still_but_news']}  (correctly reads this period, not misses)")
        print(f"false-reject       {w}/{wt}  = {100 * w / wt:.1f}%" if wt else "false-reject  n/a")
        print(f"partition          {m['partition']}")
        return 0

    rows = classify(args.pipeline)
    if args.json:
        print(json.dumps(rows, indent=1))
        return 0
    print(f"{'plane':<12} {'score':>5}  signal")
    for r in rows:
        sc = (r.get("news") or {}).get("score")
        print(f"{r['plane']:<12} {sc if sc is not None else '':>5}  {r['signal_id']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
