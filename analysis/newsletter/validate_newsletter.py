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
     flip lines, basis lines) must trace to the flat numbers of the signals THAT
     BLOCK declared. Exact card titles quoted inside template text (e.g. the H1)
     are stripped first.

Negative-tested: an invented number in template text fails; a reworded card fails.

## Why rule 2 says "that block" (rescoped 2026-07-21)

It used to say "the signals the generator declared", pooled across the whole issue,
matched with the SIBC card policy and its ratio grounding. Measured, that gate caught
**0%** of injected numbers — it passed 9.1%, 47.3% and 812.6% into a paragraph and
only tripped on a five-figure absurdity. The reason was never tolerance: a release
read declares ~21 signals, which is 735 values, and ratio grounding turns any pool
that size into a net that catches nothing. The check was real; its ground truth was
not discriminating.

Two changes fixed it, in this order of importance:

  scope      each block is checked against the signals it is actually about, so a
             flip line is judged by that flip's own values (~10) rather than by
             everything the issue mentions. Blocks that state no numbers declare
             none, which correctly makes any number in them ungrounded.
  tolerance  `core.traceability.DISTRIBUTION` — rounding width, no ratio grounding.
             The newsletter quotes computed values; it never derives one in prose.

This is the same lesson as Check 4f's `evidence_all` rescoping and the distribution
gate's, arriving for the third time. Measure gates: `analysis/measure_groundedness.py`.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from core.traceability import DISTRIBUTION as POLICY, extract_numbers, matches  # noqa: E402
from signals.query import flat_numbers, signal_numbers                                 # noqa: E402
import newsletter_sources as src                                                       # noqa: E402

DB = ROOT / "analysis" / "signals" / "signals.db"
DATA = ROOT / "web" / "public" / "data"

# Presentation-only tokens that are not data claims.
_DATE = re.compile(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* 20\d\d\b")
_ISO = re.compile(r"\b20\d\d-\d\d-\d\d\b")

# "₹2.9L Cr" is one token to a reader and two to the extractor: a decimal glued to a
# letter backtracks to its integer part, so 2.9 arrives as a meaningless 2. Unglue the
# magnitude suffix before reading. Validator-side only — the rendered issue is
# unchanged, because "₹2.9 L Cr" is not how anyone writes it.
_GLUED_MAGNITUDE = re.compile(r"(\d)(L Cr|L|Cr)\b")


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


def _units_of(conn, pipeline, metric_id):
    return [u for (u,) in conn.execute(
        "select distinct unit from signals where pipeline=? and metric_id=? "
        "  and unit is not null", (pipeline, metric_id))]


def _as_rendered(values, units):
    """The same values as the newsletter prints them.

    The db stores ₹ crore and raw counts; the issue says "₹2.9L Cr" and "12.0 crore",
    because `fmt_value` scales for the reader. Those are the same fact in the unit a
    person reads, so the gate has to accept them — and the honest way to do that is to
    put each value through the very renderer the issue used, then read it back with the
    very extractor the check uses. Anything else is a tolerance guess.

    (The old gate never hit this: ratio grounding was quietly accepting the scaled
    forms as a/b of two other values, which is also why it accepted everything else.)
    """
    out = []
    for v in values:
        for unit in units:
            out += extract_numbers(src.fmt_value(v, unit), POLICY)
    return out


def declared_ground_truth(declared_ids):
    """Flat numbers of the declared signals at their pipeline's last two periods,
    plus those values as rendered for the reader."""
    registry = src.load_registry()
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    nums = []
    for sid in declared_ids:
        sig = registry.get(sid)
        if not sig:
            continue
        pl = sig["pipeline"]
        cur = src.latest_period(pl)
        raw = []
        for period in [p for p in (cur, src.prior_period(pl, cur)) if p]:
            raw += flat_numbers(signal_numbers(conn, sid, sig, pl, period))
        nums += raw + _as_rendered(raw, _units_of(conn, pl, sid))
    conn.close()
    return nums


def _scoped(block_signals, cache):
    """Ground truth for one block: exactly the signals that block declared.

    A block that declares nothing grounds nothing — so any number appearing in the
    template's connective prose is a failure, which is correct: those paragraphs are
    written to carry no figures.

    There is deliberately NO fall-back to the issue-wide declaration. That fallback
    looked like prudence and measured like a hole: the intro paragraph inherited all
    735 values the issue declares, and the catch rate on injections into it went from
    91.9% to 42.4%. A default that quietly widens scope is the whole failure mode this
    rescoping exists to remove.
    """
    key = tuple(block_signals or ())
    if key not in cache:
        cache[key] = declared_ground_truth(block_signals or [])
    return cache[key]


def check_doc(doc, declared_ids, label="newsletter"):
    """Return list of failure strings; empty = the issue is publishable."""
    cards = legit_card_texts()
    cache = {}
    failures = []

    def strip_presentation(text):
        for c in cards:                       # card titles quoted in template text (e.g. H1)
            if c in text:
                text = text.replace(c, " ")
        # Unglue AFTER removing card text, never before: rewriting "₹215.2L Cr" to
        # "₹215.2 L Cr" first stops the card title matching as a substring, and the
        # headline's quoted card then reads as an ungrounded claim of the template's own.
        text = _GLUED_MAGNITUDE.sub(r"\1 \2", text)
        return _ISO.sub(" ", _DATE.sub(" ", text))

    for b in doc:
        # Blocks that count the document rather than describe the data ("…and 10 more
        # on the dashboard"). Marked explicitly at the point of authorship, so the
        # exemption is auditable instead of an exempt-this-block-type rule.
        if b.get("meta"):
            continue
        if b["type"] == "card":
            for k in ("title", "body", "implication"):
                v = b.get(k)
                if v and v not in cards:
                    failures.append(f"{label}: card {k} not found verbatim in any "
                                    f"validated feed: {v[:80]!r}")
            continue
        if b["type"] == "chart":
            continue            # placeholder recipe — series names only, never numbers

        # A statgrid is many claims in one block: each stat is checked against its own
        # signal, so a headline number cannot be justified by a neighbouring stat.
        if b["type"] == "statgrid":
            parts = [(f"{it.get('value', '')} {it.get('label', '')} {it.get('note', '')}",
                      [it["signal"]] if it.get("signal") else b.get("signals"))
                     for it in b.get("items", [])]  # each stat judged by its own signal
        else:
            text = b.get("text") or b.get("label") or ""
            if b.get("label"):
                text = f"{b['label']} {b.get('text', '')}"
            parts = [(text, b.get("signals"))]

        for text, block_signals in parts:
            legit = _scoped(block_signals, cache)
            for num in extract_numbers(strip_presentation(text), POLICY):
                if not matches(num, legit, POLICY):
                    failures.append(f"{label}: ungrounded number {num} in {b['type']!r} "
                                    f"block: {text[:70]!r}")
    return failures
