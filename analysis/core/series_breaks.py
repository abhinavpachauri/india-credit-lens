"""
core/series_breaks.py — does this comparison span a break in the published series?
─────────────────────────────────────────────────────────────────────────────────
The one place the question is asked (signals/README.md, "Series breaks"). A break is declared per
pipeline in `{data_dir}/series_breaks.json`: when it took effect, why, RBI's own words, and which
lines it touched. A comparison spans a break when one of its dates is before the effective month
and the other is on or after it; on a marked line such a reading is not growth, it is the break.

A pipeline with no file has no breaks. A file that names a reason outside core/absence.py raises.
"""
from __future__ import annotations

import json
from functools import lru_cache

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


def spans(pipeline: str, statement: str | None, code: str, a: str, b: str) -> str | None:
    """The reason a comparison of this line between dates a and b crosses a break, or None."""
    lo, hi = sorted((a[:10], b[:10]))
    for effective, reason, lines in _breaks(pipeline):
        if (statement, str(code)) in lines and lo < effective <= hi:
            return reason
    return None


def check(pipeline: str, statement: str | None, code: str, a: str, b: str) -> None:
    """Raise SeriesBreak when the comparison spans a break; return otherwise."""
    reason = spans(pipeline, statement, code, a, b)
    if reason:
        raise SeriesBreak(reason, f"{pipeline} {statement} {code} {a}..{b}")
