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
Advisory until the §15.2 contract lands and cards carry derived cuts; `--strict`
turns findings into a gate failure. Same staging Check 4f used.

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
from core.manifest import path as _mpath, consolidated_csv  # noqa: E402


def _section_cuts(pipeline: str) -> dict:
    """Declared per pipeline and reached through the manifest — the path lives in
    one place, so source #3 declares its own and neither this file nor the gate
    learns a new name."""
    return json.loads(_mpath(pipeline, "section_cuts").read_text())


# ── the cut a signal was computed over ────────────────────────────────────────

def sibc_cut(compute: dict) -> dict | None:
    """A SIBC cut, read off the signal's own compute spec.

    `parent_code` + `child_level` is a decomposition; `denominator_code` names
    the total a share is measured against. A signal with neither is a `level`
    card — one entity's own series — which is the already-working case.
    """
    parent, level = compute.get("parent_code"), compute.get("child_level")
    if parent is None or level is None:
        return None
    return {
        "shape":       "share_of" if compute.get("denominator_code") else "decomposition",
        "parent_code": parent,
        "child_level": level,
        "statement":   compute.get("statement", "Statement 1"),
        "denominator": compute.get("denominator_code"),
    }


def atm_pos_cut(compute: dict) -> dict | None:
    """An ATM/POS cut: which metrics the claim is actually made out of.

    A share needs its whole denominator on the chart, and a pair needs both
    sides — quoting the distance between two lines while drawing one of them is
    the payments form of the same defect.
    """
    metrics, shape = set(), "level"
    if compute.get("metric"):
        metrics.add(compute["metric"])
    if compute.get("denominator_metrics"):
        metrics.update(compute["denominator_metrics"]); shape = "share_of"
    if compute.get("denominator_metric"):
        metrics.add(compute["denominator_metric"]);     shape = "pair"
    for side in ("a", "b"):
        if isinstance(compute.get(side), dict):
            metrics.update(compute[side].get("metrics", [])); shape = "pair"
    return {"shape": shape, "metrics": sorted(metrics)} if metrics else None


# ── what each section's chart renders ─────────────────────────────────────────

def sibc_section_series(cuts: dict, rows: list[dict]) -> dict[str, dict]:
    """Resolve each declared section cut to the codes its chart draws.

    Resolved from the CSV, so a section_cuts.json that no longer describes what
    buildSections() renders fails here instead of mis-charting a card quietly.
    """
    out = {}
    for sec, d in cuts["sections"].items():
        stmt = d["statement"]
        # Codes are only unique WITHIN a statement — 2.3 is "Large" in Statement 1 and
        # "Beverage and Tobacco" in Statement 2 — so every lookup is statement-scoped.
        scoped = [r for r in rows if r["statement"] == stmt]
        if d["kind"] == "codes":
            mine = [r for r in scoped if r["code"] in set(d["codes"])]
        elif d["kind"] == "psl":
            mine = [r for r in scoped if r["is_priority_sector_memo"] == "True"]
        else:
            mine = [r for r in scoped if r["parent_code"] == d["parent_code"]]

        # A section's rendered names: the CSV sector name, unless rbi_sibc.ts substitutes
        # a fixed map (bankCredit/mainSectors) or a display override.
        labels = {r["code"]: r["sector"] for r in mine}
        labels.update(d.get("labels", {}))
        labels.update(_overrides(sec))
        out[sec] = {**d, "codes": {r["code"] for r in mine}, "labels": labels}
    return out


def _overrides(section: str) -> dict:
    p = REPO / "web/lib/reports/rbi_sibc_label_overrides.json"
    return (json.loads(p.read_text()) if p.exists() else {}).get(section, {})


# ── the checks ────────────────────────────────────────────────────────────────

def check_sibc(strict: bool) -> list[str]:
    reg   = json.loads(REG.read_text())["signals"]
    cuts  = _section_cuts("sibc")
    rows  = list(csv.DictReader(open(consolidated_csv("sibc"))))
    feed  = json.loads((REPO / "web/public/data/sibc_l1_annotations.json").read_text())
    secs  = sibc_section_series(cuts, rows)
    found = []

    for sec, bucket in feed["sections"].items():
        chart = secs.get(sec)
        if chart is None:
            found.append(f"[C1:{sec}] section renders a chart no cut is declared for")
            continue
        for kind in ("insights", "gaps", "opportunities"):
            for card in bucket.get(kind, []):
                sig = reg.get(card["id"])
                if sig is None:
                    found.append(f"[C4:{sec}.{card['id']}] no registered signal — cut undeclarable")
                    continue
                cut = sibc_cut(sig.get("compute", {}))
                names = (card.get("effect") or {}).get("highlight") or []

                if cut is not None:
                    # C1 — is the card's cut the one this chart draws?
                    same = (cut["parent_code"] == chart.get("parent_code")
                            and cut["child_level"] == chart.get("child_level")
                            and cut["statement"]   == chart.get("statement"))
                    if not same:
                        found.append(
                            f"[C1:{sec}.{card['id']}] card is about "
                            f"{cut['parent_code']}/L{cut['child_level']}/{cut['statement']}; "
                            f"chart draws {chart.get('parent_code')}/L{chart.get('child_level')}"
                            f"/{chart.get('statement')} — different entities")
                    # C3 — a share measured against a total the chart does not imply
                    if cut["shape"] == "share_of" and not same:
                        found.append(
                            f"[C3:{sec}.{card['id']}] share is out of {cut['denominator']}; "
                            f"chart's total is {chart.get('parent_code')}")

                # C2 — every named series must be on this chart
                for n in names:
                    if n not in chart["labels"].values() and n not in _short_labels(sec):
                        found.append(f"[C2:{sec}.{card['id']}] names '{n}' — not a series on this chart")
    return found


def _short_labels(section: str) -> set[str]:
    """The aggregate 'Total' line every section can draw — not a CSV row, so it
    is never in the resolved cut, but it is a legitimate thing for a card to name."""
    return {"Total"}


def check_atm_pos(strict: bool) -> list[str]:
    reg    = json.loads(REG.read_text())["signals"]
    cuts   = _section_cuts("atm_pos")["sections"]
    series = json.loads((REPO / "web/public/data/atm_pos_chart_series.json").read_text())["series"]
    feed   = json.loads((REPO / "web/public/data/atm_pos_insights.json").read_text())
    cards  = feed["insights"] if isinstance(feed, dict) else feed
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
        sig = reg.get(card.get("eval_signal") or card["id"])
        if sig is None:
            found.append(f"[C4:{card['id']}] card-declared rule with no cut — §15.4 requires one")
            continue
        cut = atm_pos_cut(sig.get("compute", {}))
        if cut is None:
            continue
        missing = [m for m in cut["metrics"] if m not in chart["metrics"]]
        if missing:
            found.append(
                f"[{'C3' if cut['shape'] == 'share_of' else 'C1'}:{card['id']}] "
                f"{cut['shape']} claim needs {missing} — chart draws only {chart['metrics']}")
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
    print(f"\n  {len(found)} finding(s) — {'FAIL' if strict else 'advisory (§15.9 step 1)'}")
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
