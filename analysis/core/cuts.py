#!/usr/bin/env python3
"""
cuts.py — what a card is a claim about (DASHBOARD_SPEC §15)
────────────────────────────────────────────────────────────
A card is generated from a signal computed over a **cut**: a set of entities
and, where the figure is a share or a ratio, the total it is measured against.
The signal records the cut when it computes — `parent_code`, `child_level`,
`denominator_code` on SIBC; `metric`, `denominator_metrics`, the two sides of a
pair on payments. Until now the card threw that away and wrote down the name of
a series the chart already drew, which is why 25 cards render a chart answering
a different question from the one they ask.

This module is the single definition of a cut. The generators emit from it and
the gate checks against it, so "the card declares X" and "the check expects X"
cannot drift into two descriptions that merely agree today.

Two things it deliberately owns together:

  the CUT     which entities, out of which total   (§15.3)
  the LABEL   what the chart calls them            (§15.5)

They belong together because most of the defects were the second, not the
first: a card naming "Education Loans" where the chart draws "Education", or
the full CSV name where the chart shows an override. A card must speak the
chart's vocabulary, and the only way to guarantee that is to look it up rather
than type it.
"""
from __future__ import annotations

import csv
import json
from dataclasses import dataclass
from pathlib import Path

from core.manifest import path as _mpath, consolidated_csv

ANALYSIS = Path(__file__).resolve().parent.parent
REPO     = ANALYSIS.parent


# ── the cut ───────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class Cut:
    """What a card is about. `shape` is the §15.3 vocabulary.

    level          one entity's own series — the case that always worked
    decomposition  the children of one parent
    share_of       a part against a named total
    pair           two named sides compared
    """
    shape:       str
    codes:       tuple = ()          # SIBC: explicit entity codes, when known
    parent_code: str | None = None
    child_level: int | None = None
    statement:   str | None = None
    denominator: str | None = None
    metrics:     tuple = ()          # payments: the metrics the claim is made of
    # A pair's two sides, each a bundle with the name the card's own prose uses
    # ("value transacted at POS" is CC POS value + DC POS value). Flattening the
    # sides into one metric list drew three unlabelled lines for a two-sided claim.
    sides:       tuple = ()

    def as_json(self) -> dict:
        """The wire form carried on a card's `effect.cut`. Omits what does not
        apply so a level card does not carry four nulls."""
        d = {"shape": self.shape}
        for k in ("parent_code", "child_level", "statement", "denominator"):
            if getattr(self, k) is not None:
                d[k] = getattr(self, k)
        if self.codes:   d["codes"]   = list(self.codes)
        if self.metrics: d["metrics"] = list(self.metrics)
        # Sides are stored as sorted tuples so the Cut stays hashable; JSON needs lists,
        # and a tuple left in here compares unequal to the list that round-trips back
        # through the feed — which C5 correctly reported as drift.
        if self.sides:
            d["sides"] = [{"label": dict(s)["label"], "metrics": list(dict(s)["metrics"])}
                          for s in self.sides]
        return d


def sibc_cut(compute: dict) -> Cut:
    """The cut a SIBC signal was computed over.

    `parent_code` + `child_level` is a decomposition; a `denominator_code`
    alongside makes it a share of that parent. A signal naming a single `code`
    is a level card — one entity's own series — which is not a defect and must
    never be reported as one.
    """
    stmt = compute.get("statement", "Statement 1")
    parent, level = compute.get("parent_code"), compute.get("child_level")
    if parent is not None and level is not None:
        return Cut(shape="share_of" if compute.get("denominator_code") else "decomposition",
                   parent_code=parent, child_level=level, statement=stmt,
                   denominator=compute.get("denominator_code"))
    # A spread names two entities and quotes the distance between them — the same
    # claim shape as a payments pair, on the entity axis instead of the metric axis.
    # §15.3 said SIBC had no pair; deriving the cuts is what disproved it, because a
    # hand-typed chart_series had been carrying both names all along.
    if compute.get("code_a") and compute.get("code_b"):
        return Cut(shape="pair", codes=(compute["code_a"], compute["code_b"]), statement=stmt)
    # A named set — "how many of these four grew" is about all four.
    if compute.get("child_codes"):
        return Cut(shape="level", codes=tuple(compute["child_codes"]), statement=stmt)
    if compute.get("code") is not None:
        return Cut(shape="level", codes=(compute["code"],), statement=stmt)
    return Cut(shape="level", statement=stmt)


def atm_pos_cut(compute: dict) -> Cut:
    """The cut an ATM/POS signal was computed over — which metrics the claim is
    actually made out of. A share needs its whole denominator; a pair needs both
    sides, because the gap a pair card quotes is the distance between two lines.
    """
    metrics, shape, sides = set(), "level", []
    if compute.get("metric"):
        metrics.add(compute["metric"])
    if compute.get("denominator_metrics"):
        metrics.update(compute["denominator_metrics"]); shape = "share_of"
    if compute.get("denominator_metric"):
        # A ratio is a two-sided claim whose sides are single metrics.
        metrics.add(compute["denominator_metric"]); shape = "pair"
        sides = [_side(None, [compute["metric"]]), _side(None, [compute["denominator_metric"]])]
    for key in ("a", "b"):
        side = compute.get(key)
        if isinstance(side, dict):
            metrics.update(side.get("metrics", [])); shape = "pair"
            sides.append(_side(side.get("label"), side.get("metrics", [])))
    return Cut(shape=shape, metrics=tuple(sorted(metrics)),
               sides=tuple(sides) if shape == "pair" else ())


def _side(label: str | None, metrics: list) -> tuple:
    """One side of a pair, as sorted key/value pairs so the Cut stays hashable."""
    return tuple(sorted({"label": label or "", "metrics": tuple(metrics)}.items()))


def cut_of(pipeline: str, compute: dict) -> Cut:
    return sibc_cut(compute) if pipeline == "sibc" else atm_pos_cut(compute)


# ── what each section's chart renders ─────────────────────────────────────────

def section_cuts(pipeline: str) -> dict:
    """Declared per pipeline, reached through the manifest.

    Declared and not inferred: the first hand-audit of this matched a cut to a
    section by NAME and threw a false positive off `PSL` vs `psl`.
    """
    return json.loads(_mpath(pipeline, "section_cuts").read_text())["sections"]


def _overrides(section: str) -> dict:
    p = REPO / "web/lib/reports/rbi_sibc_label_overrides.json"
    return (json.loads(p.read_text()) if p.exists() else {}).get(section, {})


def sibc_sections(rows: list[dict] | None = None) -> dict[str, dict]:
    """Each SIBC section resolved to the codes and display names its chart draws.

    Resolved from the CSV, so a `section_cuts.json` that has stopped describing
    what `buildSections()` renders fails a gate instead of mis-charting quietly.
    """
    rows = rows if rows is not None else list(csv.DictReader(open(consolidated_csv("sibc"))))
    out = {}
    for sec, d in section_cuts("sibc").items():
        stmt = d["statement"]
        # Codes are unique only WITHIN a statement — 2.3 is "Large" in Statement 1
        # and "Beverage and Tobacco" in Statement 2. An unscoped lookup mislabels a
        # whole section, and did: it flagged 20 correct cards on this check's first run.
        scoped = [r for r in rows if r["statement"] == stmt]
        if d["kind"] == "codes":
            mine = [r for r in scoped if r["code"] in set(d["codes"])]
        elif d["kind"] == "psl":
            mine = [r for r in scoped if r["is_priority_sector_memo"] == "True"]
        else:
            mine = [r for r in scoped if r["parent_code"] == d["parent_code"]]
        # `csv_names` is kept beside `labels` because a renamed series has TWO
        # names and callers arrive with either: the compute layer works in raw CSV
        # names ("Non-Banking Financial Companies (NBFCs)"), the chart draws the
        # override ("NBFCs"). Dropping the raw name is what made the allocation
        # cards highlight a series the chart does not have.
        csv_names = {r["sector"]: r["code"] for r in mine}
        labels = {r["code"]: r["sector"] for r in mine}
        labels.update(d.get("labels", {}))     # rbi_sibc.ts fixed maps (bankCredit, mainSectors)
        labels.update(_overrides(sec))         # display overrides (NBFCs, Housing, …)
        # The sub-cuts this section's chart can also draw (§15.6a): every code in it
        # that RBI breaks down further. `buildSubCuts` in rbi_sibc.ts builds exactly
        # this set from the same rule, so the check's model of the chart tracks the
        # chart. Without it, cards the chart now renders correctly would keep being
        # reported — and a gate that reports fixed defects is a gate people learn to
        # ignore.
        kids = {}
        for code in {r["code"] for r in mine}:
            children = [r for r in scoped if r["parent_code"] == code]
            if children:
                kids[code] = {"parent_code": code,
                              "child_level": int(children[0]["level"]),
                              "statement":   stmt}
        out[sec] = {**d, "codes": {r["code"] for r in mine},
                    "labels": labels, "csv_names": csv_names, "sub_cuts": kids}
    return out


# ── speaking the chart's vocabulary ───────────────────────────────────────────

AGGREGATE = "Total"   # every section can draw its parent total; not a CSV row


def chart_label(sections: dict, section: str, code_or_name: str) -> str | None:
    """The name this section's chart uses for an entity, given its code or its
    raw CSV name. `None` when the chart cannot draw it at all — which is the
    honest answer, and the one a hand-typed name could never give.
    """
    sec = sections.get(section)
    if sec is None:
        return None
    if code_or_name in sec["labels"]:
        return sec["labels"][code_or_name]
    if code_or_name in sec["labels"].values() or code_or_name == AGGREGATE:
        return code_or_name
    # a raw CSV name the section renames — go back through the code it belongs to
    code = sec["csv_names"].get(code_or_name)
    return sec["labels"].get(code) if code else None


def highlight_for(sections: dict, section: str, cut: Cut, lead: str | None = None) -> list[str]:
    """The series a card should highlight, in the chart's own vocabulary.

    Derived, never authored. Authoring it by hand is what produced seven
    highlights that render nothing — 'Power' (on no chart), 'Education Loans'
    (the chart says 'Education'), and the full CSV names where the chart shows
    an override.
    """
    if lead is not None:
        label = chart_label(sections, section, lead)
        return [label] if label else []
    if cut.shape == "level":
        labels = [chart_label(sections, section, c) for c in cut.codes]
        return [l for l in labels if l]
    return []
