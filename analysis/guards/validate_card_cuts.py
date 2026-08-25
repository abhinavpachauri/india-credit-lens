#!/usr/bin/env python3
"""
validate_card_cuts.py — the card↔chart cut check (DASHBOARD_SPEC.md §15.7)
──────────────────────────────────────────────────────────────────────────
Every other traceability gate here asks *is this number true?* — Check 2g and
Stage 4c trace each figure in a card back to signals.db, and they pass on the
defect this file exists for, because both numbers involved are true:

    card    Iron and Steel holds 69.0% of basic-metals credit   ← traces
    chart   Basic Metal and Metal Product — 11.2% of industry    ← also traces

The error is in the *relationship* between two individually-correct artifacts.
This check asks the question none of the others do: **is the chart under this
card an answer to the card's question?**

A card is generated from a signal computed over a CUT — a set of entities and,
where the figure is a share or a ratio, the total it is measured against. The
cut is recorded at compute time in the signal's own registry `compute` block.
The card then discards it and writes down the name of a series the chart
already happens to draw, which cannot express "the children of this parent" or
"the other side of this pair" — so it degrades to the nearest drawable
ancestor, and the reader is shown a different quantity from the one claimed.

What is checked, per card (§15.7):

  C1  the card's cut RESOLVES — the entities it is about are on the chart
  C2  every series the card names BELONGS to that cut
  C3  the denominator the chart implies is the one the signal computed against
  C4  the card DECLARES a cut at all

C4 is not pedantry. A card that declares nothing and a card that declares the
right thing are the same shape to every gate we own, so an undeclared cut reads
as compliance — the failure mode this project keeps meeting
([[feedback_failure_that_looks_like_absence]]).

Ground truth is the section's own declared cut (`section_cuts.json`, verified
against the CSV / chart-series artifact so it cannot drift from what the web
layer draws) — never the section's labels. Matching cuts by name is how the
first hand-audit of this produced a false positive.

Mode
────
STRICT in both gates since 2026-08-26, when §15.6 gave the charts the ability to
render every declared cut and the findings reached zero on both pipelines. It ran
advisory while that was built — the same staging Check 4f used — because a check
that reports defects nobody can yet fix is a check people learn to scroll past.

Usage:
    python3 analysis/guards/validate_card_cuts.py --pipeline sibc [--strict]
    python3 analysis/guards/validate_card_cuts.py --pipeline atm_pos [--strict]
    python3 analysis/guards/validate_card_cuts.py --all
"""
import argparse
import csv
import json
import sys
from pathlib import Path

ANALYSIS = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"
REPO     = ANALYSIS.parent
REG      = ANALYSIS / "signals" / "registry.json"

sys.path.insert(0, str(ANALYSIS))
from core.cuts import (                                      # noqa: E402
    Cut, sibc_cut, atm_pos_cut, sibc_sections, section_cuts, chart_label, AGGREGATE,
)




# The cut definitions and the section vocabulary live in core.cuts, shared with the
# generators that emit them. Two copies that agree today is exactly the drift this
# check exists to catch, so it does not keep its own.
def _cut_from(declared: dict) -> Cut:
    """A declared cut, back as the shared type. The card carries the wire form; every
    comparison below is against the same class the generators emitted from."""
    return Cut(shape=declared["shape"],
               codes=tuple(declared.get("codes", ())),
               parent_code=declared.get("parent_code"),
               child_level=declared.get("child_level"),
               statement=declared.get("statement"),
               denominator=declared.get("denominator"),
               metrics=tuple(declared.get("metrics", ())))


# ── the checks ────────────────────────────────────────────────────────────────

def check_sibc(strict: bool = False, feed: dict | None = None) -> list[str]:
    reg   = json.loads(REG.read_text())["signals"]
    # `feed` is injectable so the checks can be driven with a card that does not
    # exist in the live feed. A check tested only by the defects it once found
    # stops being tested the moment they are fixed.
    feed  = feed or json.loads((REPO / "web/public/data/sibc_l1_annotations.json").read_text())
    secs  = sibc_sections()
    found = []

    for sec, bucket in feed["sections"].items():
        chart = secs.get(sec)
        if chart is None:
            found.append(f"[C1:{sec}] section renders a chart no cut is declared for")
            continue
        for kind in ("insights", "gaps", "opportunities"):
            for card in bucket.get(kind, []):
                # C2 first, and unconditionally: a card can name a series the chart
                # does not draw whether or not it declares a cut, and skipping the
                # name check on an undeclared card would hide the louder defect
                # behind the quieter one.
                rendered = set(chart["labels"].values()) | {AGGREGATE}
                for n in (card.get("effect") or {}).get("highlight") or []:
                    if n in rendered:
                        continue
                    fix = chart_label(secs, sec, n)
                    found.append(
                        f"[C2:{sec}.{card['id']}] names '{n}' — not a series on this chart"
                        + (f"; the chart draws it as '{fix}'" if fix else ""))

                declared = (card.get("effect") or {}).get("cut")
                if not declared:
                    found.append(f"[C4:{sec}.{card['id']}] declares no cut")
                    continue
                # The declaration is the contract; the registry is the cross-check.
                # They are derived from one definition in core.cuts, so a disagreement
                # means the emitted feed is stale — the drift this check exists to see.
                sig = reg.get(card["id"])
                if sig is not None:
                    computed = sibc_cut(sig.get("compute", {})).as_json()
                    if computed != declared:
                        found.append(f"[C5:{sec}.{card['id']}] declares {declared}; "
                                     f"its signal computed {computed} — regenerate the feed")
                cut = _cut_from(declared)

                # C1/C3 read differently per shape (§15.3): a decomposition is
                # right when the chart draws that parent's children; a pair or a
                # named set is right when the chart can draw every entity it names.
                if cut.shape in ("decomposition", "share_of"):
                    drawable = [chart, *chart.get("sub_cuts", {}).values()]
                    same = any(cut.parent_code == c.get("parent_code")
                               and cut.child_level == c.get("child_level")
                               and cut.statement   == c.get("statement")
                               for c in drawable)
                    if not same:
                        found.append(
                            f"[C1:{sec}.{card['id']}] card is about "
                            f"{cut.parent_code}/L{cut.child_level}/{cut.statement}; "
                            f"chart draws {chart.get('parent_code')}/L{chart.get('child_level')}"
                            f"/{chart.get('statement')} — different entities")
                    if cut.shape == "share_of" and not same:
                        found.append(
                            f"[C3:{sec}.{card['id']}] share is out of {cut.denominator}; "
                            f"chart's total is {chart.get('parent_code')}")
                elif cut.codes:
                    absent = [c for c in cut.codes if chart_label(secs, sec, c) is None]
                    if absent:
                        found.append(
                            f"[C1:{sec}.{card['id']}] {cut.shape} claim names {absent} — "
                            f"not drawable on this chart")

    return found


def check_atm_pos(strict: bool = False, cards: list | None = None) -> list[str]:
    reg    = json.loads(REG.read_text())["signals"]
    cuts   = section_cuts("atm_pos")
    series = json.loads((REPO / "web/public/data/atm_pos_chart_series.json").read_text())["series"]
    feed   = json.loads((REPO / "web/public/data/atm_pos_insights.json").read_text())
    cards  = cards if cards is not None else (feed["insights"] if isinstance(feed, dict) else feed)
    found  = []

    # the declaration must describe the artifact the chart is actually drawn from
    for sec, d in cuts.items():
        for m in d["metrics"]:
            if m not in series:
                found.append(f"[C1:{sec}] declared metric '{m}' is not in atm_pos_chart_series.json")

    for card in cards:
        focus = (card.get("effect") or {}).get("focusCard")
        chart = cuts.get(focus)
        if chart is None:
            found.append(f"[C1:{card['id']}] focusCard '{focus}' is not a section that renders a chart")
            continue
        declared = (card.get("effect") or {}).get("cut")
        if not declared:
            found.append(f"[C4:{card['id']}] declares no cut")
            continue
        sig = reg.get(card.get("eval_signal") or card["id"])
        if sig is not None and sig.get("compute"):
            computed = atm_pos_cut(sig["compute"]).as_json()
            if computed != declared:
                found.append(f"[C5:{card['id']}] declares {declared}; "
                             f"its signal computed {computed} — regenerate the feed")
        cut = _cut_from(declared)
        # §15.6 b/c: a share or a pair whose metrics reach beyond the section is now
        # rendered on its own metrics (buildShareData / buildPairData in AtmReadMode),
        # so the section's metric list is not the only thing the chart can draw. A
        # `level` claim has no such builder and must still sit on its own section.
        renders_own_metrics = cut.shape in ("share_of", "pair")
        missing = [m for m in cut.metrics if m not in chart["metrics"]]
        if missing and not renders_own_metrics:
            found.append(
                f"[C1:{card['id']}] {cut.shape} claim needs {missing} — "
                f"chart draws only {chart['metrics']}")
    return found


# ── main ──────────────────────────────────────────────────────────────────────

def run(pipeline: str, strict: bool) -> int:
    found = check_sibc(strict) if pipeline == "sibc" else check_atm_pos(strict)
    print(f"\n  {pipeline} — card↔chart cut check (DASHBOARD_SPEC §15.7)")
    if not found:
        print("  ✅  every card's chart answers the card's question")
        return 0
    for f in found:
        print(f"  {'✗' if strict else '⚠'}  {f}")
    print(f"\n  {len(found)} finding(s) — {'FAIL' if strict else 'advisory'}")
    return 1 if strict else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--pipeline", choices=["sibc", "atm_pos"])
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--strict", action="store_true")
    a = ap.parse_args()
    if a.all:
        sys.exit(max(run("sibc", a.strict), run("atm_pos", a.strict)))
    sys.exit(run(a.pipeline or "sibc", a.strict))
