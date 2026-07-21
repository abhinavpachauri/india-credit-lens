#!/usr/bin/env python3
"""
validate_distribution.py — the one traceability gate for every channel
------------------------------------------------------------------------
DISTRIBUTION_SPEC §1: one gate covers all channels. This is the generalisation of
`newsletter/validate_newsletter.check_doc`, with the scope lesson from Check 4f taken
one step further.

Three rules, checked on a slate BEFORE anything is written:

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
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "analysis" / "newsletter"))

from core.traceability import DISTRIBUTION as POLICY, extract_numbers, matches  # noqa: E402
from signals.query import flat_numbers, signal_numbers                                 # noqa: E402
import newsletter_sources as ns                                                        # noqa: E402
from validate_newsletter import legit_card_texts, _DATE, _ISO                          # noqa: E402
from distribution import slot_render                                                   # noqa: E402

DB = ROOT / "analysis" / "signals" / "signals.db"


def signal_ground_truth(signal_ids):
    """Flat numbers of exactly these signals, at their pipeline's last two periods."""
    registry = ns.load_registry()
    conn = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    nums = []
    for sid in signal_ids:
        sig = registry.get(sid)
        if not sig:
            continue
        pl = sig["pipeline"]
        cur = ns.latest_period(pl)
        for period in [p for p in (cur, ns.prior_period(pl, cur)) if p]:
            nums += flat_numbers(signal_numbers(conn, sid, sig, pl, period))
    conn.close()
    return nums


def _strip_presentation(text, cards):
    text = _ISO.sub(" ", _DATE.sub(" ", text))
    for c in cards:
        if c in text:
            text = text.replace(c, " ")
    return text


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
            legit = signal_ground_truth(c.get("signal_ids", [])) + list(c.get("extra_numbers", []))
            failures += _ungrounded(text, legit, cards, f"claim {c['id']}")

    # The blurb is our own words throughout, so it is scoped to the union of what the
    # slate declared — still a handful of signals, never the period.
    declared = sorted({s for c in slate["claims"] for s in c.get("signal_ids", [])})
    extra = [n for c in slate["claims"] for n in c.get("extra_numbers", [])]
    legit = signal_ground_truth(declared) + extra
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
