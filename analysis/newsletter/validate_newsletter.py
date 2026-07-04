#!/usr/bin/env python3
"""
validate_newsletter.py — newsletter traceability gate (v2)
-----------------------------------------------------------
The newsletter promise is "every number is machine-checked against the source".
This makes it true, with the same scoping lesson as Check 4f: a period-wide
ground truth is vacuous (thousands of mixed-magnitude values match anything),
so the check scopes to what the issue actually declares.

Two rules, checked on the composed document BEFORE anything is written:

  1. CARD blocks (title/body/implication) must appear VERBATIM in a validated
     feed (sibc_l1_annotations / atm_pos_insights / opportunities_feed) — the
     newsletter may curate gate-validated prose, never alter it.
  2. Every number in NON-card blocks (the template's own words: headline stats,
     flip lines, basis lines) must trace to the flat numbers of the signals the
     generator DECLARED it used — small set, meaningful matching. Exact card
     titles quoted inside template text (e.g. the H1) are stripped first.

Negative-tested: an invented number in template text fails; a reworded card fails.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.traceability import SIBC as POLICY, extract_numbers, matches, ratio_matches  # noqa: E402
from signals.query import flat_numbers, signal_numbers                                 # noqa: E402
import newsletter_sources as src                                                       # noqa: E402

DB = ROOT / "analysis" / "signals" / "signals.db"
DATA = ROOT / "web" / "public" / "data"

# Presentation-only tokens that are not data claims.
_DATE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* 20\d\d\b")
_ISO = re.compile(r"\b20\d\d-\d\d-\d\d\b")


def legit_card_texts():
    """Every title/body/implication string a validated feed currently carries."""
    texts = set()

    def add(item):
        for k in ("title", "body", "implication"):
            v = item.get(k)
            if v:
                texts.add(v)

    sibc = json.loads((DATA / "sibc_l1_annotations.json").read_text())
    for bucket in sibc["sections"].values():
        for kind in ("insights", "gaps", "opportunities"):
            for it in bucket.get(kind, []):
                add(it)
    for it in json.loads((DATA / "atm_pos_insights.json").read_text()):
        add(it)
    feed = json.loads((DATA / "opportunities_feed.json").read_text())
    for it in feed.get("cross_system", []) + [x for v in feed.get("pipelines", {}).values() for x in v]:
        add(it)
    return texts


def declared_ground_truth(declared_ids):
    """Flat numbers of the declared signals at their pipeline's last two periods."""
    registry = src.load_registry()
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    nums = []
    for sid in declared_ids:
        sig = registry.get(sid)
        if not sig:
            continue
        pl = sig["pipeline"]
        cur = src.latest_period(pl)
        for period in [p for p in (cur, src.prior_period(pl, cur)) if p]:
            nums += flat_numbers(signal_numbers(conn, sid, sig, pl, period))
    conn.close()
    return nums


def check_doc(doc, declared_ids, label="newsletter"):
    """Return list of failure strings; empty = the issue is publishable."""
    cards = legit_card_texts()
    legit_nums = declared_ground_truth(declared_ids)
    failures = []

    def strip_presentation(text):
        text = _ISO.sub(" ", _DATE.sub(" ", text))
        for c in cards:                       # card titles quoted in template text (e.g. H1)
            if c in text:
                text = text.replace(c, " ")
        return text

    for b in doc:
        if b["type"] == "card":
            for k in ("title", "body", "implication"):
                v = b.get(k)
                if v and v not in cards:
                    failures.append(f"{label}: card {k} not found verbatim in any "
                                    f"validated feed: {v[:80]!r}")
            continue
        if b["type"] == "chart":
            continue            # placeholder recipe — series names only, never numbers
        if b["type"] == "statgrid":
            text = " ".join(f"{it.get('value', '')} {it.get('label', '')} {it.get('note', '')}"
                            for it in b.get("items", []))
        else:
            text = b.get("text") or b.get("label") or ""
            if b.get("label"):
                text = f"{b['label']} {b.get('text', '')}"
        for num in extract_numbers(strip_presentation(text), POLICY):
            if not matches(num, legit_nums, POLICY) and not ratio_matches(num, legit_nums, POLICY):
                failures.append(f"{label}: ungrounded number {num} in {b['type']!r} "
                                f"block: {text[:70]!r}")
    return failures
