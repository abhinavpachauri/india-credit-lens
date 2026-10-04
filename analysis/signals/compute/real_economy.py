"""
compute/real_economy.py — 1f: a credit number measured against the real economy
───────────────────────────────────────────────────────────────────────────────
Two methods, one row per credit part per period (signals/README §1f, COMPOSITION_SPEC §24):

  csv_sector_real_growth    credit YoY net of the part's own price change at the same period:
                            100 × ((1 + g/100) / (1 + π/100) − 1)
  csv_sector_output_growth  growth of the part's real-economy counterpart over the trailing year:
                            IIP = last 12 months' mean index vs the 12 before;
                            NAS = last 4 quarters' constant-price sum vs the 4 before.

Neither method knows which MoSPI series measures which credit part. The concordance
(`ontology/concordance/{credit}__{reference}.json`) says so, so NBFC ↔ MoSPI later is a file, not
code. A credit pipeline reads a reference CSV only because its manifest declares `depends_on`.

Every row holds this period's operands or a reason, never an earlier period's value:
  * static reasons come from the concordance (`absent: weights_unsourced`, …);
  * per-period reasons are decided here, from a closed list in `core/absence.py`:
      credit_history_gap     the credit store lacks this period or the year before it,
      reference_history_gap  MoSPI's series on this base starts after a period we need,
      not_released           MoSPI's figure is not yet due (period + lag + grace > today).
Anything else RAISES (`ReferenceMissing`): a reference value past its due date and still missing
is an outage, and an outage must never read as a legitimate absence.
"""
from __future__ import annotations

import calendar
import csv
import json
from datetime import date, timedelta
from pathlib import Path

import pandas as pd

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import manifest, absence                                    # noqa: E402
from core.paths import ANALYSIS                                       # noqa: E402

from . import common

CONCORDANCE_DIR = ANALYSIS / "ontology" / "concordance"
OUTPUT_MEASURE = {"iip": "index", "nas": "constant_price"}
PRICE_MEASURE = {"wpi": "index", "cpi": "index"}
QUARTER_END_MONTHS = {3, 6, 9, 12}


class ReferenceMissing(LookupError):
    """A value the concordance needs is neither present nor legitimately absent.

    Re-raised by `csv_sector.compute` rather than swallowed into `_unknown()`, for the reason
    `ParentNotFound` is: a signal that silently emits nothing looks exactly like one with
    nothing to say.
    """


def today() -> date:
    """The run date `not_released` is judged against. A function, so tests can pin it."""
    return date.today()


# ── The inputs: the concordance and the reference CSV, read once ─────────────

_concordance_cache: dict[str, dict] = {}
_reference_cache: dict[str, "Reference"] = {}


def concordance(credit: str, reference: str) -> dict:
    key = f"{credit}__{reference}"
    if key not in _concordance_cache:
        f = CONCORDANCE_DIR / f"{key}.json"
        if not f.exists():
            raise ReferenceMissing(f"{credit}: no concordance {f.name} for reference {reference}")
        _concordance_cache[key] = json.loads(f.read_text())
    return _concordance_cache[key]


class Reference:
    """The reference pipeline's consolidated CSV as lookups, plus each dataset's calendar."""

    def __init__(self, pipeline: str):
        man = manifest.load(pipeline)
        self.datasets = man["datasets"]
        self.grace = int(man.get("grace_days", 0))
        self.values: dict[tuple, float] = {}
        self.first: dict[tuple, str] = {}
        with manifest.consolidated_csv(pipeline).open() as f:
            for r in csv.DictReader(f):
                k = (r["dataset"], r["code"], r["measure"])
                self.values[k + (r["period"],)] = float(r["value"])
                if k not in self.first or r["period"] < self.first[k]:
                    self.first[k] = r["period"]

    def value(self, series: str, measure: str, period: str) -> float | str:
        """The value, or the per-period reason it is legitimately absent. Raises otherwise."""
        ds, code = series.split("/", 1)
        k = (ds, code, measure)
        if k + (period,) in self.values:
            return self.values[k + (period,)]
        if k not in self.first:
            raise ReferenceMissing(f"{series} {measure}: not in the reference CSV at all")
        if period < self.first[k]:
            return "reference_history_gap"
        due = date.fromisoformat(period) + timedelta(days=self.datasets[ds]["expected_lag_days"] + self.grace)
        if due > today():
            return "not_released"
        raise ReferenceMissing(f"{series} {measure} {period}: due {due}, missing (overdue or a gap)")


def reference(pipeline: str) -> Reference:
    if pipeline not in _reference_cache:
        _reference_cache[pipeline] = Reference(pipeline)
    return _reference_cache[pipeline]


def invalidate_cache() -> None:
    _concordance_cache.clear()
    _reference_cache.clear()
    _credit_cache.clear()


# ── Period arithmetic ─────────────────────────────────────────────────────────

def months_back(period: str, n: int) -> str:
    d = date.fromisoformat(period)
    y, m = divmod(d.year * 12 + d.month - 1 - n, 12)
    return f"{y}-{m + 1:02d}-{calendar.monthrange(y, m + 1)[1]:02d}"


def window(period: str, n: int, step: int) -> list[str]:
    """n periods ending at `period`, `step` months apart, oldest first."""
    return [months_back(period, step * i) for i in range(n - 1, -1, -1)]


# ── Combining several series into one (the concordance's `combine`) ──────────

class Absent(Exception):
    """A per-period reason surfaced from deep inside a computation; carries the code."""
    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason


def _get(ref: Reference, series: str, measure: str, period: str) -> float:
    v = ref.value(series, measure, period)
    if isinstance(v, str):
        raise Absent(v)
    return v


def combined(ref: Reference, spec: dict, measure: str, period: str) -> float:
    """One number for a part at one period: a single series, a NAS sum, or a weighted index.

    A combined series needs EVERY component for the period: if one is absent the whole is, and
    the weights are never renormalised over the components present."""
    series = spec["series"]
    vals = [_get(ref, s, measure, period) for s in series]
    if len(series) == 1:
        return vals[0]
    how = spec.get("combine")
    if how == "sum":
        return sum(vals)
    if how == "weighted":
        w = [spec["weights"][s] for s in series]
        return sum(wi * vi for wi, vi in zip(w, vals)) / sum(w)
    raise ReferenceMissing(f"{series}: {len(series)} series with no declared combine")


def implicit_deflator(ref: Reference, series: list[str], period: str) -> float:
    """NAS current ÷ constant prices, each summed over the series as published."""
    cur = sum(_get(ref, s, "current_price", period) for s in series)
    con = sum(_get(ref, s, "constant_price", period) for s in series)
    return cur / con


# ── The credit side ───────────────────────────────────────────────────────────

class Credit:
    """The credit CSV's values by (urn, date), and each URN's name at a date."""

    def __init__(self, df: pd.DataFrame):
        self.pipeline = df.attrs["pipeline"]
        sch = df.attrs.get("schema", {})
        scope = sch.get("scope_column")
        self.value: dict[tuple, float] = {}
        self.name: dict[tuple, str] = {}
        self.children: dict[tuple, list[str]] = {}
        for r in df[["date", "code", "parent_code", "sector", "outstanding_cr"] + ([scope] if scope else [])] \
                .itertuples(index=False):
            st = getattr(r, scope) if scope else ""
            if not r.code:
                continue
            u = urn(self.pipeline, str(st), str(r.code))
            self.value[(u, str(r.date))] = float(r.outstanding_cr)
            self.name[(u, str(r.date))] = r.sector
            self.children.setdefault((str(st), str(r.parent_code), str(r.date)), []).append(u)

    def yoy(self, u: str, period: str) -> tuple[float, float, float]:
        cur, prior = self.value.get((u, period)), self.value.get((u, months_back(period, 12)))
        if cur is None or prior is None or prior == 0:
            raise Absent("credit_history_gap")
        return (cur / prior - 1) * 100, cur, prior


def urn(pipeline: str, statement: str, code: str) -> str:
    return f"icl:{pipeline}/{statement.replace(' ', '')}/{code}"


_credit_cache: dict[int, Credit] = {}


def credit(df: pd.DataFrame) -> Credit:
    if id(df) not in _credit_cache:
        _credit_cache[id(df)] = Credit(df)
    return _credit_cache[id(df)]


# ── Which parts a cut emits ───────────────────────────────────────────────────

def parts_of(doc: dict, stem: str, cred: Credit, period: str) -> list[tuple[str, bool]]:
    """[(urn, is_parent)] this cut emits at `period`.

    The children are the parent's children IN THE CREDIT CSV at this period (COMPOSITION_SPEC
    §24.3), never a list typed here. The parent row is emitted only by a cut it is not a child
    of: Industry is the total of the industry-by-type table but a part of the main table, so it
    is computed once, on the main table, at the main table's cadence.
    """
    cut = doc["cuts"][stem]
    st, parent = cut["statement"], cut["parent_code"]
    kids = cred.children.get((st, parent, period), [])
    if not kids:
        raise ReferenceMissing(f"cut {stem}: no children of {parent} in {st} at {period}")
    parent_urn = cut.get("parent_urn") or urn(cred.pipeline, st, parent)
    child_of_another = any(
        parent_urn in cred.children.get((c["statement"], c["parent_code"], period), [])
        for s, c in doc["cuts"].items() if s != stem)
    out = [(u, False) for u in kids]
    if not child_of_another:
        out.insert(0, (parent_urn, True))
    for u, _ in out:
        if u not in doc["parts"]:
            raise ReferenceMissing(f"cut {stem}: {u} is a part at {period} but not in the concordance")
    return out


# ── The two methods ───────────────────────────────────────────────────────────

def real(g: float, pi: float) -> float:
    """Credit growth g% net of price growth pi%, both in percent. Plugged in unconverted the
    formula gives 3.2 for Industry Q1 FY27 instead of 14.83: inside the normal range and
    invisible to any scale check, so a unit test pins it (plausibility review, 2026-09-26)."""
    return 100 * ((1 + g / 100) / (1 + pi / 100) - 1)


def _real_growth(part: dict, ref: Reference, cred: Credit, u: str, period: str) -> tuple[float, dict]:
    g, cur, prior = cred.yoy(u, period)
    spec = part["deflator"]
    year_ago = months_back(period, 12)
    if "implicit" in spec:
        now, then = (implicit_deflator(ref, spec["implicit"], p) for p in (period, year_ago))
        series, kind = spec["implicit"], "implicit"
    else:
        ds = spec["series"][0].split("/", 1)[0]
        now, then = (combined(ref, spec, PRICE_MEASURE[ds], p) for p in (period, year_ago))
        series, kind = spec["series"], "index"
    pi = (now / then - 1) * 100
    value = real(g, pi)
    return value, {"credit_yoy": g, "credit": [cur, prior], "deflator_yoy": pi,
                   "deflator": {"kind": kind, "series": series, "values": [now, then],
                                "periods": [period, year_ago]}}


def _output_growth(part: dict, ref: Reference, cred: Credit, u: str, period: str) -> tuple[float, dict]:
    spec = part["output"]
    ds = spec["series"][0].split("/", 1)[0]
    measure = OUTPUT_MEASURE[ds]
    step = 3 if ref.datasets[ds]["cadence"] == "quarterly" else 1
    n = 12 // step
    recent, before = window(period, n, step), window(months_back(period, 12), n, step)
    agg = sum if ds == "nas" else (lambda xs: sum(xs) / len(xs))
    now = agg([combined(ref, spec, measure, p) for p in recent])
    then = agg([combined(ref, spec, measure, p) for p in before])
    return (now / then - 1) * 100, {"series": spec["series"], "measure": measure,
                                    "trailing": [now, then], "window": [before[0], recent[-1]]}


ROLE = {"csv_sector_real_growth": ("deflator", _real_growth),
        "csv_sector_output_growth": ("output", _output_growth)}


def _one_part(method: str, part: dict, ref: Reference, cred: Credit, u: str, period: str):
    """(value, reason, operands) for one part at one period."""
    role, fn = ROLE[method]
    spec = part[role]
    if "absent" in spec:
        return None, spec["absent"], None
    try:
        value, ops = fn(part, ref, cred, u, period)
    except Absent as a:
        return None, a.reason, None
    if part.get("approximate"):
        ops["approximate"] = part["approximate"]
    return value, None, ops


def _rows(method: str, params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    cred = credit(df)
    ref_pl = params["reference"]
    if ref_pl not in (manifest.load(cred.pipeline).get("depends_on") or []):
        raise ReferenceMissing(f"{cred.pipeline} reads {ref_pl} but its manifest does not declare "
                               f"depends_on: [{ref_pl}]")
    doc, ref = concordance(cred.pipeline, ref_pl), reference(ref_pl)
    stem = params["cut"]
    cadence = doc["cuts"][stem]["cadence"]
    if cadence == "quarterly" and date.fromisoformat(period).month not in QUARTER_END_MONTHS:
        return []                     # not a period of this signal: its value cannot change here
    step = 3 if cadence == "quarterly" else 1
    out = []
    for u, is_parent in parts_of(doc, stem, cred, period):
        part = doc["parts"][u]
        value, reason, ops = _one_part(method, part, ref, cred, u, period)
        if reason is not None and reason not in absence.STATIC and reason not in absence.PER_PERIOD:
            raise ReferenceMissing(f"{u}: reason {reason!r} is not in core/absence.py")
        if value is None:
            status = "absent"
        else:
            prev = None
            try:
                prev, _, _ = _one_part(method, part, ref, cred, u, months_back(period, step))
            except ReferenceMissing:
                prev = None           # the prior period is history, not this period's outage
            status = common.eval_status(params.get("status_rules", []), value, prev)
        row = common.row("aggregate" if is_parent else params.get("entity_type", "sector"),
                         "total" if is_parent else cred.name[(u, period)], value, status, "pct")
        row["reason"] = reason
        row["operands"] = json.dumps(_rounded(ops), sort_keys=True) if ops else None
        out.append(row)
    return out


def _rounded(x):
    if isinstance(x, float):
        return round(x, 4)
    if isinstance(x, dict):
        return {k: _rounded(v) for k, v in x.items()}
    if isinstance(x, list):
        return [_rounded(v) for v in x]
    return x


def csv_sector_real_growth(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Credit YoY net of the part's own price change (signals/README §1f)."""
    return _rows("csv_sector_real_growth", params, period, df)


def csv_sector_output_growth(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Growth of the part's real-economy counterpart over the trailing year (signals/README §1f)."""
    return _rows("csv_sector_output_growth", params, period, df)


METHODS = {"csv_sector_real_growth": csv_sector_real_growth,
           "csv_sector_output_growth": csv_sector_output_growth}
