#!/usr/bin/env python3
"""
generate_slot.py — build one calendar slot
--------------------------------------------
    python3 analysis/distribution/generate_slot.py --slot 7th
    python3 analysis/distribution/generate_slot.py --slot 28th --date 2026-08-28
    python3 analysis/distribution/generate_slot.py --all --dry-run

One generator, five slots, ten categories (DISTRIBUTION_SPEC §4). Adding a slot is a
row in `CALENDAR`; adding a category is a selector in `SELECTORS`. Neither is a new
code path, which is the whole reason the categories are data and not functions scattered
across five renderers.

The run is self-gating in the newsletter's sense: the slate is validated before a byte
is written, and a failing slot produces no artifacts at all. It is also *honest* in the
§4 sense — if the primary category has nothing worth publishing, the fallback runs, and
if the fallback is empty too the slot is skipped and the skip is recorded. A missed slot
is cheaper than a thin post, and both are cheaper than a wrong one.
"""
import argparse
import sys
from datetime import date
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from distribution import categories as cats           # noqa: E402
from distribution import distribution_sources as src  # noqa: E402
from distribution import ledger as ledger_mod         # noqa: E402
from distribution import slot_render                  # noqa: E402
from distribution.validate_distribution import check_slate  # noqa: E402

OUT = ROOT / "analysis" / "distribution" / "output"

# §4. Primary, then fallback. The 1st always fires — levels always exist.
CALENDAR = {
    "1st":  {"primary": ["C1", "C5"], "fallback": None,
             "channel": "Newsletter (merged) + LinkedIn"},
    "7th":  {"primary": ["C2", "C3"], "fallback": ["C4"], "channel": "LinkedIn"},
    "14th": {"primary": ["C6", "C7"], "fallback": ["C4"], "channel": "Newsletter (deep read) + LinkedIn"},
    "21st": {"primary": ["C10"],      "fallback": ["C9"], "channel": "LinkedIn"},
    "28th": {"primary": ["C8"],       "fallback": ["C9"], "channel": "LinkedIn"},
}

# How many claims a slot carries. Enough to be worth a pager, few enough to have a point.
MAX_CLAIMS = 4
# The 28th post is "three things that could turn" — the opener says three, so send three.
WATCHLIST_N = 3


def select(category, ledger_entries, when, slot):
    """Claims for one category, or [] when the category has nothing to say this month.

    The empty return is a real result, not an error — the null results the compute layer
    emits by design (a stable ±3 pp pair gap, rotation mass under 0.5 pp) arrive here as
    an absence, and §4 says an absence means fall back or skip.
    """
    if category == "C1":
        # The monthly summary leads with the headline levels the newsletter already
        # leads with, then spreads across both pipelines rather than down one feed.
        claims = src.prioritise(src.cards_for_category("C1"), src.headline_ids())
    elif category in ("C2", "C3", "C4"):
        claims = src.cards_for_category(category)
    elif category == "C5":
        claims = src.turns()
    elif category == "C6":
        claims = src.opportunity_claims(cross_system=False)
    elif category == "C7":
        claims = src.opportunity_claims(cross_system=True)
    elif category == "C8":
        claims = src.watchlist(top_n=WATCHLIST_N)
        for c in claims:
            # A threshold is computed from the signal's own status rules, not stored in
            # signals.db — so the claim carries its derived numbers explicitly and the
            # gate checks against those four values rather than waving them through.
            p = c["proximity"]
            c["extra_numbers"] = [p["value"], p["threshold_value"], p["distance"],
                                  p["typical_move"], p["prev_value"]]
    elif category == "C9":
        claims = src.corrections(ledger_entries)
    elif category == "C10":
        claims = []          # authored from ai_pm_register.json — see §8, human-written
    else:
        raise ValueError(f"unknown category {category}")

    # §7: the ledger verifies the partition rather than deciding, so a recent reuse
    # drops that claim and lets the rest of the category stand.
    used = {sid for sid, _ in ledger_mod.overlaps(
        [s for c in claims for s in c.get("signal_ids", [])], when, slot)}
    if used:
        claims = [c for c in claims if not (set(c.get("signal_ids", [])) & used)]
    return src.diversify(claims, MAX_CLAIMS)


def build_slate(slot, when, category_ids, is_fallback):
    vintage = src.data_vintage()
    entries = ledger_mod.entries()
    claims = []
    for cat in category_ids:
        claims += select(cat, entries, when, slot)
    if not claims:
        return None
    # A two-category slot (C1+C5, C6+C7) must not come out as four claims of the first
    # one — diversify again across the pair, not only inside each.
    claims = src.diversify(claims, MAX_CLAIMS)
    primary_cat = category_ids[0]
    return {
        "slot": slot,
        "date": when,
        "category": primary_cat,
        "categories": category_ids,
        "channel": CALENDAR[slot]["channel"],
        "is_fallback": is_fallback,
        "vintage": vintage,
        "vintage_sentence": src.vintage_sentence(vintage),
        # The merged monthly summary is the one that spans both pipelines, so it is the
        # one that owes the reader the vintage out loud (§11.1). Never smoothed over.
        "vintage_note": src.vintage_sentence(vintage) if primary_cat == "C1" else None,
        "claims": claims[:MAX_CLAIMS],
        "pages": 1,
    }


def write_slot(slate, dry_run=False):
    folder = OUT / f"{slate['date']}_{slate['slot']}_{slate['category']}"
    prompt = slot_render.design_prompt(slate)
    blurb = slot_render.blurb(slate)
    if dry_run:
        return folder, prompt, blurb
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "design_prompt.md").write_text(prompt)
    (folder / "blurb.md").write_text(blurb)
    return folder, prompt, blurb


def run_slot(slot, when, dry_run=False):
    plan = CALENDAR[slot]
    for category_ids, is_fallback in ((plan["primary"], False),
                                      (plan["fallback"], True)):
        if not category_ids:
            continue
        slate = build_slate(slot, when, category_ids, is_fallback)
        if not slate:
            print(f"  {'+'.join(category_ids)}: nothing to publish")
            continue

        failures = check_slate(slate)
        if failures:
            print(f"  {'+'.join(category_ids)}: FAILED the gate — nothing written")
            for f in failures:
                print("    -", f)
            return 1

        folder, _, blurb = write_slot(slate, dry_run)
        label = " (fallback)" if is_fallback else ""
        print(f"  {'+'.join(category_ids)}{label}: {len(slate['claims'])} claims → "
              f"{folder.relative_to(ROOT)}{' [dry run]' if dry_run else ''}")
        if not dry_run:
            ledger_mod.record(
                slot, slate["category"], slate["claims"],
                src.current_statuses([s for c in slate["claims"]
                                      for s in c.get("signal_ids", [])]),
                artifacts=[str(folder.relative_to(ROOT) / "design_prompt.md"),
                           str(folder.relative_to(ROOT) / "blurb.md")],
                is_fallback=is_fallback, when=when)
        return 0

    reason = (f"primary {'+'.join(plan['primary'])} empty"
              + (f" and fallback {'+'.join(plan['fallback'])} empty" if plan["fallback"] else ""))
    print(f"  SKIPPED — {reason}")
    if not dry_run:
        ledger_mod.record_skip(slot, plan["primary"][0],
                               (plan["fallback"] or [None])[0], reason, when)
    return 0


def main():
    ap = argparse.ArgumentParser(description="Generate a distribution slot's design prompt + blurb")
    ap.add_argument("--slot", choices=list(CALENDAR))
    ap.add_argument("--all", action="store_true", help="run every slot (rehearsal)")
    ap.add_argument("--date", default=date.today().isoformat())
    ap.add_argument("--dry-run", action="store_true", help="render but write nothing")
    args = ap.parse_args()

    if not (args.slot or args.all):
        ap.error("pass --slot or --all")

    registry_gap = cats.unclassified_methods(src.load_registry())
    if registry_gap:
        print("FAIL: compute methods missing from the category partition: "
              + ", ".join(registry_gap))
        return 1

    rc = 0
    for slot in ([args.slot] if args.slot else list(CALENDAR)):
        # A whole-month rehearsal must land each slot on its own calendar day. Running
        # them all on one date collapses the reuse window and makes every slot look like
        # it is competing with the others for the same signals.
        when = args.date if args.slot else _slot_date(args.date, slot)
        print(f"{slot} — {CALENDAR[slot]['channel']}  [{when}]")
        rc |= run_slot(slot, when, args.dry_run)
    return rc


def _slot_date(anchor, slot):
    """The slot's own day in the anchor date's month — '7th' in 2026-08 is 2026-08-07."""
    return f"{anchor[:8]}{int(slot.rstrip('stndrh')):02d}"


if __name__ == "__main__":
    raise SystemExit(main())
