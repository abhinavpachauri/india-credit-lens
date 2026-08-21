#!/usr/bin/env python3
"""
stamp_planes.py — ship each dashboard card's plane, precomputed.
----------------------------------------------------------------
The dashboard read-mode (DASHBOARD_SPEC.md) files every card into a plane — read /
composition / subject — decided by `planes.py` in the signal layer. The browser must never
re-derive that (compute-once-ship-compact): it would need signals.db, the registry, and the
whole classifier client-side. So this stamps the answer into a compact sidecar the web joins
onto the cards by id.

A SIDECAR, not a rewrite of the card JSON: the insight generators (SIBC Stage 5.5, ATM/POS
Stage 4b) own `sibc_l1_annotations.json` / `atm_pos_insights.json` and are freshness-guarded on
them. The plane is DERIVED from those cards + signals.db, so it lives in its own derived file,
regenerated every gate and checkable with `--check` — one source of truth per artifact, no
parallel copy that "agrees today but could drift".

Card → registry signal is ONE rule for both pipelines: the card's registry signal is its
`eval_signal` (an ATM/POS anchored card names the signal it borrows its prose from) or its `id`
(every SIBC card, and the ATM/POS relational cards, IS a signal), whichever the registry knows.
Composed and gap cards resolve to nothing and are subjects — correct: they are neither news-scored
nor structural at the signal level.

    python3 analysis/signals/stamp_planes.py --pipeline sibc        # write the sidecar
    python3 analysis/signals/stamp_planes.py --pipeline sibc --check # fail on drift (freshness)
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from signals import planes, proximity                             # noqa: E402

DATA = ROOT / "web" / "public" / "data"
CARD_FILE = {"sibc": DATA / "sibc_l1_annotations.json",
             "atm_pos": DATA / "atm_pos_insights.json"}
SIDECAR = {p: DATA / f"{p}_planes.json" for p in CARD_FILE}


def _cards(pipeline, doc):
    """Every card in the pipeline's artifact, uniformly — (card, subject) pairs. Subject is the
    chart series the card drives (SIBC `effect.highlight`, ATM/POS `effect.focusCard`), carried
    through so the web groups the accordion without re-resolving it."""
    if pipeline == "sibc":
        for section in doc["sections"].values():
            for kind in ("insights", "gaps", "opportunities"):
                for card in section.get(kind, []):
                    subj = (card.get("effect", {}).get("highlight") or [None])[0]
                    yield card, subj
    else:
        for card in doc:
            eff = card.get("effect", {})
            subj = eff.get("focusCard") or (eff.get("highlight") or [None])[0]
            yield card, subj


def _signal_ids(card, registry):
    """The registry signals a card stands on — eval_signal, its own id, and any it declares.

    `sourceSignals` is added because a card may legitimately rest on more than the signal
    it is named after: the SIBC movement card is filed under its allocation signal but
    reads momentum, acceleration and speed alongside it, and its news lives in the
    momentum row. Scoring it on its id alone buried a record-setting card in the subject
    plane. Entries that are not registry ids are ignored, so the ATM/POS convention of
    naming dot-paths into signals.json passes through harmlessly."""
    declared = card.get("sourceSignals") or []
    return [sid for sid in (card.get("eval_signal"), card.get("id"), *declared)
            if sid and sid in registry]


# The reason a read surfaced, one word, in priority order — this is the read card's chip.
# A record beats a reversal beats an outsized move beats a threshold crossing (the is_news
# weighting), so the strongest true factor wins.
def _reason(news):
    f = news.get("factors", {})
    if f.get("record"):
        return "record"
    if f.get("flip"):
        return "reversal"
    if f.get("magnitude"):
        return "surge"
    if f.get("crossed"):
        return "shift"
    return None


def _direction(conn, pipeline, sid):
    """Which way the latest reading moved — for the ▲/▼ glyph on the read card."""
    hist = proximity.series(conn, pipeline, sid)
    if len(hist) < 2:
        return None
    prev, latest = hist[-2][1], hist[-1][1]
    return "up" if latest > prev else "down" if latest < prev else "flat"


def build(pipeline, conn=None, registry=None):
    """The sidecar payload: per-card plane + news score + subject, keyed by card id."""
    close = conn is None
    conn = conn or proximity._con()
    registry = registry or proximity.load_registry()
    doc = json.loads(CARD_FILE[pipeline].read_text())

    out = {}
    for card, subject in _cards(pipeline, doc):
        cid = card.get("id")
        if not cid:
            continue
        sids = _signal_ids(card, registry)
        card_plane, best_news, best_sid = planes.SUBJECT, None, None
        for sid in sids:
            p = planes.plane(conn, sid, registry[sid])
            news = p.get("news")
            if p["plane"] == planes.READ:
                card_plane = planes.READ
            elif card_plane != planes.READ and p["plane"] == planes.COMPOSITION:
                card_plane = planes.COMPOSITION
            if news and (best_news is None or news["score"] > best_news["score"]):
                best_news, best_sid = news, sid
        entry = {"plane": card_plane,
                 "news_score": best_news["score"] if best_news else None,
                 "subject": subject}
        # A read card carries WHY it surfaced (record/reversal/surge/shift) + which way it
        # moved — the chip and glyph. Only reads need it; subjects/composition stay lean.
        if card_plane == planes.READ and best_news:
            entry["reason"] = _reason(best_news)
            entry["direction"] = _direction(conn, pipeline, best_sid)
        out[cid] = entry
    if close:
        conn.close()
    return {
        "_meta": {
            "pipeline": pipeline,
            "purpose": "Per-card read/composition/subject plane for the dashboard read-mode. "
                       "Derived from the card artifact + signals.db by planes.py — join on card id. "
                       "Regenerated every gate; freshness-guarded with --check.",
            "spec": "analysis/DASHBOARD_SPEC.md",
            "classifier": "analysis/signals/planes.py",
        },
        "planes": out,
    }


def write(pipeline):
    payload = build(pipeline)
    SIDECAR[pipeline].write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    return payload


def check(pipeline):
    """True when the on-disk sidecar equals a fresh recompute — the freshness guard. Compares the
    `planes` map only, so a doc comment can change without tripping it."""
    if not SIDECAR[pipeline].exists():
        return False, "sidecar missing — run without --check"
    on_disk = json.loads(SIDECAR[pipeline].read_text()).get("planes", {})
    fresh = build(pipeline)["planes"]
    if on_disk == fresh:
        return True, None
    drift = {k for k in set(on_disk) | set(fresh) if on_disk.get(k) != fresh.get(k)}
    return False, f"{len(drift)} card(s) drifted, e.g. {sorted(drift)[:5]}"


def main():
    ap = argparse.ArgumentParser(description="Precompute each dashboard card's plane into a sidecar")
    ap.add_argument("--pipeline", choices=list(CARD_FILE), required=True)
    ap.add_argument("--check", action="store_true", help="fail on drift instead of writing")
    args = ap.parse_args()

    if args.check:
        ok, why = check(args.pipeline)
        print(f"planes sidecar {'FRESH' if ok else 'STALE'}: {args.pipeline}"
              + (f" — {why}" if why else ""))
        return 0 if ok else 1

    payload = write(args.pipeline)
    from collections import Counter
    dist = Counter(v["plane"] for v in payload["planes"].values())
    print(f"stamped {len(payload['planes'])} {args.pipeline} cards → {SIDECAR[args.pipeline].name}"
          f"  {dict(dist)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
