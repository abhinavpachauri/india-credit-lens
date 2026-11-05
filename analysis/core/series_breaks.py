"""
core/series_breaks.py — does this comparison span a break in the published series?
─────────────────────────────────────────────────────────────────────────────────
The one place the question is asked (signals/README.md, "Series breaks"). A break is declared per
pipeline in `{data_dir}/series_breaks.json`: when it took effect, why, RBI's own words, and which
lines it touched. A comparison spans a break when one of its dates is before the effective month
and the other is on or after it; on a marked line such a reading is not growth, it is the break.

A restatement is the other kind: RBI reprints a line on a new classification for only the months
that release prints, so the new basis is a set of months rather than a date. Its months are read
from the consolidated CSV, never listed, and a comparison spans it when exactly one date is on it.

A pipeline with no file has no breaks. A file that names a reason outside core/absence.py raises.
"""
from __future__ import annotations

import csv
import json
from functools import lru_cache
from statistics import median

from core import absence, manifest
from core.paths import ROOT


class SeriesBreak(Exception):
    """A comparison crosses a declared break on a marked line. Carries the reason code."""
    def __init__(self, reason: str, line: str):
        super().__init__(f"{line}: comparison spans a series break ({reason})")
        self.reason = reason


@lru_cache(maxsize=None)
def _breaks(pipeline: str) -> tuple:
    # A frame tied to no pipeline (a unit test's synthetic frame) has no declared breaks. Every
    # production frame names its pipeline (csv_sector._load_df sets df.attrs["pipeline"]).
    if not pipeline:
        return ()
    path = ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "series_breaks.json"
    if not path.exists():
        return ()
    out = []
    for b in json.loads(path.read_text())["breaks"]:
        if b["reason"] not in absence.PER_PERIOD:
            raise ValueError(f"{path}: break {b['id']} names reason {b['reason']!r}, "
                             f"which core/absence.py does not define")
        out.append((b["effective"], b["reason"],
                    frozenset((l["statement"], l["code"]) for l in b["lines"])))
    return tuple(out)


@lru_cache(maxsize=None)
def _restatements(pipeline: str) -> tuple:
    if not pipeline:
        return ()
    path = ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "series_breaks.json"
    if not path.exists():
        return ()
    out = []
    for r in json.loads(path.read_text()).get("restatements", []):
        if r["reason"] not in absence.PER_PERIOD:
            raise ValueError(f"{path}: restatement {r['id']} names reason {r['reason']!r}, "
                             f"which core/absence.py does not define")
        out.append((r["release"], r["reason"],
                    frozenset((l["statement"], l["code"]) for l in r["lines"])))
    return tuple(out)


@lru_cache(maxsize=None)
def _printed_by(pipeline: str) -> dict:
    """(statement, code) -> {date: the release whose figure the CSV holds for that date}."""
    out: dict = {}
    with open(manifest.consolidated_csv(pipeline)) as f:
        for r in csv.DictReader(f):
            out.setdefault((r["statement"], r["code"]), {})[r["date"][:10]] = r["report_date"][:10]
    return out


def restated_months(pipeline: str, statement: str | None, code: str) -> frozenset:
    """The months of this line printed on its restated basis; empty for a line with no restatement."""
    key = (statement, str(code))
    months: set = set()
    for release, _reason, lines in _restatements(pipeline):
        if key in lines:
            months |= {d for d, rel in _printed_by(pipeline).get(key, {}).items() if rel >= release}
    return frozenset(months)


def spans(pipeline: str, statement: str | None, code: str, a: str, b: str) -> str | None:
    """The reason a comparison of this line between dates a and b crosses a break, or None."""
    lo, hi = sorted((a[:10], b[:10]))
    for effective, reason, lines in _breaks(pipeline):
        if (statement, str(code)) in lines and lo < effective <= hi:
            return reason
    for release, reason, lines in _restatements(pipeline):
        if (statement, str(code)) in lines:
            months = restated_months(pipeline, statement, code)
            if (lo in months) != (hi in months):
                return reason
    return None


def restated_months_of_node(model: dict, node: dict) -> frozenset:
    """restated_months for a system-model node, whose model names its report, not its pipeline."""
    report = model.get("_meta", {}).get("report_id")
    for pipeline in manifest.discover_pipeline_ids():
        if report and manifest.load(pipeline)["paths"]["data_dir"].endswith(report):
            return restated_months(pipeline, node.get("statement"), node.get("code"))
    return frozenset()


# How far a reprint must move a line to count as a change of basis: the same bar as a move
# (DECISIONS, "a move is a change > 3x the line's typical month-to-month change).
RESTATEMENT_FACTOR = 3
RESTATEMENT_MIN_REPRINTS = 2


def is_restatement(reprint_pcts: list[float], typical_pct: float | None) -> bool:
    """Every month this release reprinted moved the same way, each by more than the bar.

    One month moving is a revision. Revisions go both ways and vary month to month; a relabelling
    moves every reprinted month the same way."""
    if not typical_pct or len(reprint_pcts) < RESTATEMENT_MIN_REPRINTS:
        return False
    same_way = all(p > 0 for p in reprint_pcts) or all(p < 0 for p in reprint_pcts)
    return same_way and min(abs(p) for p in reprint_pcts) > RESTATEMENT_FACTOR * typical_pct


def typical_change_pct(values: list[float]) -> float | None:
    """A line's median absolute month-to-month change, in percent, over values in date order."""
    changes = [abs(b / a - 1) * 100 for a, b in zip(values, values[1:]) if a > 0 and b > 0]
    return median(changes) if changes else None


def check(pipeline: str, statement: str | None, code: str, a: str, b: str) -> None:
    """Raise SeriesBreak when the comparison spans a break; return otherwise."""
    reason = spans(pipeline, statement, code, a, b)
    if reason:
        raise SeriesBreak(reason, f"{pipeline} {statement} {code} {a}..{b}")
