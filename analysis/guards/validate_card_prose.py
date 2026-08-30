#!/usr/bin/env python3
"""
validate_card_prose.py — the voice gate for dashboard cards
────────────────────────────────────────────────────────────
`core.voice` has linted the distribution surfaces for a year: no advice, no
forecasts, no consultant register, lakh and crore rather than millions. The
dashboard — the surface most people actually read — was linted by nothing, and
it showed. A card told the reader to *"Move everything to UPI QR"* and that
*"there is no viable future for Bharat QR"*; another opened with *"Lenders can
lean into Jute Textiles (21.4%)"*, a sector holding 1.7% of textiles credit.

Who a hit belongs to decides whether it stops the gate (DISTRIBUTION_SPEC §5.3 —
the rule attaches to the risk, not the surface):

  deterministic   our own sentences, in a generator we control  → HARD FAIL
  llm             the eval's narration, fixable only in the      → WARN, and it
                  prompt; hand-editing a validated artifact is     belongs on the
                  the thing this project does not do               next prompt's fix list

SEBI/compliance hits WARN in both cases. The matcher is a substring list that
trips on ordinary English — "what shopkeepers sell" is not investment advice —
and DISTRIBUTION_SPEC §5.3 says precision-fix-first, measured, before it is
allowed to fail anything.

Usage:
    python3 analysis/guards/validate_card_prose.py --pipeline {sibc|atm_pos} [--strict]
"""
import argparse
import json
import re
import sys
from pathlib import Path

ANALYSIS = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"
REPO     = ANALYSIS.parent
sys.path.insert(0, str(ANALYSIS))
from core import residuals, voice   # noqa: E402

FIELDS = ("title", "body", "implication")


def _cards(pipeline: str):
    if pipeline == "sibc":
        feed = json.loads((REPO / "web/public/data/sibc_l1_annotations.json").read_text())
        for section, bucket in feed["sections"].items():
            for kind in bucket:
                for card in bucket[kind]:
                    yield section, card
    else:
        feed = json.loads((REPO / "web/public/data/atm_pos_insights.json").read_text())
        for card in (feed["insights"] if isinstance(feed, dict) else feed):
            yield card.get("group", ""), card


def _residual_problems(card: dict, pipeline: str) -> list[str]:
    """A remainder read as a sector.

    `core.residuals` states the rule the old name-list could not enforce: RBI's
    "Other…" buckets are what it did not classify, so a card may name one but must
    never HEADLINE one. "Other Textiles is the biggest slice of textiles credit at
    45.5%" was live — the exact sentence `_is_residual`'s docstring forbade, missed
    because the bucket is called "Other Textiles" and not "Others".

    Only the title is checked. A remainder in the body is usually the disclosure
    itself ("A further 45.5% sits in Other Textiles, which RBI does not break down"),
    and failing that would push the generator back toward hiding it.
    """
    title = card.get("title") or ""
    out = []
    for name in residuals.catch_alls(pipeline):
        # "biggest / largest / fastest <name>" — a superlative attached to a bucket.
        # "rotating toward X" and "X took N% of all new credit" are headline claims too —
        # they name a destination, and a remainder is not a destination anyone chose.
        if re.search(r"\b(?:biggest|largest|fastest|leads?|leading|top|towards?)\b[^.]{0,40}"
                     + re.escape(name), title, re.I) or \
           re.search(re.escape(name) + r"[^.]{0,30}\b(?:is the (?:biggest|largest|fastest)|leads|took)\b",
                     title, re.I):
            out.append(f"headlines {name!r}, which RBI does not break down — "
                       "a remainder is not a block (core.residuals)")
    return out


def check(pipeline: str) -> tuple[list[str], list[str]]:
    """(hard failures, warnings)."""
    fails, warns = [], []
    for where, card in _cards(pipeline):
        # Absent means nobody declared it. Treated as ours — the stricter reading, so a
        # new generator cannot opt out of the voice rules by forgetting a field.
        ours = card.get("representation", "deterministic") != "llm"
        for problem in _residual_problems(card, pipeline):
            line = f"[{where}.{card['id']}] title: {problem}"
            (fails if ours else warns).append(line)
        for field in FIELDS:
            for problem in voice.lint(card.get(field) or ""):
                line = f"[{where}.{card['id']}] {field}: {problem}"
                (fails if ours and not problem.startswith("SEBI") else warns).append(line)
    return fails, warns


def run(pipeline: str, strict: bool) -> int:
    fails, warns = check(pipeline)
    print(f"\n  {pipeline} — card prose voice (core.voice)")
    for w in warns:
        print(f"  ⚠  {w}")
    for f in fails:
        print(f"  {'✗' if strict else '⚠'}  {f}")
    if not fails and not warns:
        print("  ✅  every card reads as an observation, in lakh and crore")
    elif not fails:
        print(f"  ✅  no problems in our own prose ({len(warns)} warning(s) — eval prompt / SEBI precision)")
    else:
        print(f"\n  {len(fails)} problem(s) in prose we generate — {'FAIL' if strict else 'advisory'}")
    return 1 if (fails and strict) else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", choices=["sibc", "atm_pos"], default="sibc")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    if a.all:
        sys.exit(max(run("sibc", a.strict), run("atm_pos", a.strict)))
    sys.exit(run(a.pipeline, a.strict))
