#!/usr/bin/env python3
"""
validate_distribution.py — the one traceability gate for every channel
------------------------------------------------------------------------
DISTRIBUTION_SPEC §1: one gate covers all channels — the LinkedIn slots via `check_slate`
and the long-form Substack issues via `check_doc`. It absorbed the newsletter's separate
gate on 2026-07-21; they had converged on the same policy, so keeping two was just two
places to drift.

`check_slate` — three rules, checked BEFORE anything is written:

  1. **Verbatim claims stay verbatim.** A claim lifted from a validated feed must match
     that feed's wording exactly. Distribution curates gate-validated prose; it never
     rewords it, because rewording is where a hedge quietly becomes a assertion.

  2. **Our own words are scoped per claim.** Numbers in text this layer wrote (turns,
     watchlist, corrections, the blurb) must trace to the signals THAT claim declares —
     not to a period-wide pool. A period-wide pool is vacuous: thousands of
     mixed-magnitude values match nearly anything, which is how a fabricated +9.99 pp
     once passed a check that looked strict.

  3. **Derived numbers must be declared.** A watchlist threshold is not in signals.db —
     it is computed deterministically from the signal's own status rules. Such numbers
     are legitimate only when the claim carries them explicitly in `extra_numbers`,
     which keeps the scope four numbers wide instead of open-ended.

Plus the machine-checkable half of the §10 voice rules on the blurb.

Negative-tested in `analysis/tests/test_distribution.py`: an invented number in a
generated line fails, a reworded feed card fails, and an undeclared threshold fails.
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core.traceability import DISTRIBUTION as POLICY, extract_numbers, matches  # noqa: E402
from signals.query import flat_numbers, signal_numbers                          # noqa: E402
from distribution import distribution_sources as ns                             # noqa: E402
from distribution import slot_render                                            # noqa: E402
from distribution.distribution_sources import (DATA, fmt_value, latest_period,   # noqa: E402
                                               load_registry, prior_period)

DB = ROOT / "analysis" / "signals" / "signals.db"


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
            out += extract_numbers(fmt_value(v, unit), POLICY)
    return out


def declared_ground_truth(declared_ids):
    """Flat numbers of the declared signals at their pipeline's last two periods,
    plus those values as rendered for the reader."""
    registry = load_registry()
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    nums = []
    for sid in declared_ids:
        sig = registry.get(sid)
        if not sig:
            continue
        pl = sig["pipeline"]
        cur = latest_period(pl)
        raw = []
        for period in [p for p in (cur, prior_period(pl, cur)) if p]:
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


def _strip_presentation(text, cards):
    for c in cards:
        if c in text:
            text = text.replace(c, " ")
    text = _GLUED_MAGNITUDE.sub(r"\1 \2", text)
    return _ISO.sub(" ", _DATE.sub(" ", text))


def _ungrounded(text, legit, cards, where):
    """Numbers in `text` that no declared value accounts for.

    Deliberately does NOT accept `ratio_matches`. The insight validators allow a number
    to be grounded as a ratio of two grounded values, because a card may legitimately
    say "X is 3× Y". This layer never computes anything in prose — it quotes values that
    already exist — so allowing ratios would only widen the net: a 29-value pool spawns
    some 800 candidate ratios, and a pool that size matches almost any number you put in
    front of it. That is the vacuous-scope failure from Check 4f wearing a different hat.
    """
    out = []
    for num in extract_numbers(_strip_presentation(text, cards), POLICY):
        if not matches(num, legit, POLICY):
            out.append(f"{where}: ungrounded number {num} in {text[:70]!r}")
    return out


def check_slate(slate):
    """Return a list of failure strings. Empty means the slot is publishable."""
    cards = legit_card_texts()
    failures = []

    # 1 + 2 + 3 — claims, each scoped to what it declares.
    for c in slate["claims"]:
        text = " ".join(x for x in (c["title"], c["body"], c.get("implication", "")) if x)
        if c.get("verbatim"):
            for field in ("title", "body", "implication"):
                v = c.get(field)
                if v and v not in cards:
                    failures.append(
                        f"claim {c['id']}: {field} is not verbatim in any validated feed: "
                        f"{v[:80]!r}")
        else:
            legit = declared_ground_truth(c.get("signal_ids", [])) + list(c.get("extra_numbers", []))
            failures += _ungrounded(text, legit, cards, f"claim {c['id']}")

    # The blurb is our own words throughout, so it is scoped to the union of what the
    # slate declared — still a handful of signals, never the period.
    declared = sorted({s for c in slate["claims"] for s in c.get("signal_ids", [])})
    extra = [n for c in slate["claims"] for n in c.get("extra_numbers", [])]
    legit = declared_ground_truth(declared) + extra
    text = slot_render.blurb(slate)
    failures += _ungrounded(text, legit, cards, "blurb")
    failures += [f"blurb voice: {p}" for p in slot_render.lint_blurb(text)]

    # The design prompt leaves the gate and becomes a public pager, so the compliance
    # guardrail follows it out. Card prose is validated for *numbers* upstream; nobody
    # was checking it for advice language on the way to a design session.
    failures += [f"design prompt: {p}"
                 for p in slot_render.lint_compliance(slot_render.design_prompt(slate))]

    return failures


def main():
    print("validate_distribution is a library — run generate_slot.py, which self-gates.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
