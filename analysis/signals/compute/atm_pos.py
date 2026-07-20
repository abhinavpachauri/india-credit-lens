"""
ATM/POS compute methods — all algorithmic, no LLM input.
Source: web/public/data/atm_pos_consolidated.csv

Each method receives (params, period, df) and returns list[dict]:
  { entity_type, entity_id, value, status, unit }

Layer 1a methods (aggregate scalars from record_type='total' rows):
  csv_total_yoy      — YoY% for a single metric
  csv_total_ratio    — metric_a / metric_b
  csv_ratio_sum      — metric / (metric_1 + metric_2 + ...)  (% share of sum)
  csv_sum_yoy        — YoY% of (metric_1 + metric_2)

Layer 1b methods (bank-category level):
  csv_category_share — bank_category value / Total value for a metric
  csv_category_yoy   — YoY% for a specific bank_category

Layer 1c methods (entity scans — one row per entity, all entities):
  csv_category_scan_share — share for every bank_category
  csv_bank_scan           — value or YoY for every bank (full scan, no filtering)

Relational methods (cross-segment — spec: signals/README.md):
  csv_category_rotation   — Δshare_pp over an annual window per category + rotation mass
  csv_bank_divergence     — banks whose YoY contradicts their category (flagged only)
"""

from __future__ import annotations
import calendar
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO
CSV     = REPO / "web" / "public" / "data" / "atm_pos_consolidated.csv"

_df_cache: pd.DataFrame | None = None


def _load_df() -> pd.DataFrame:
    global _df_cache
    if _df_cache is None:
        df = pd.read_csv(CSV, parse_dates=["report_date"])
        df["report_date"] = df["report_date"].dt.strftime("%Y-%m-%d")
        # The hot path (_total_val/_category_val/scan/streak) filters by equality on these
        # string columns thousands of times over a 27k-row frame. As object dtype that runs
        # element-wise Python string comparison (the dominant gate cost); as `category` it
        # compares integer codes — same results, ~30× faster. value stays numeric.
        for col in ("report_date", "metric", "record_type", "bank_category", "bank_name"):
            if col in df.columns:
                df[col] = df[col].astype("category")
        _df_cache = df
    return _df_cache


def invalidate_cache() -> None:
    global _df_cache
    _df_cache = None


def _prior_year(period: str, available: set[str]) -> str | None:
    d = date.fromisoformat(period)
    py = d.year - 1
    last_day = calendar.monthrange(py, d.month)[1]
    candidate = f"{py}-{d.month:02d}-{last_day:02d}"
    return candidate if candidate in available else None


def _prior_period(period: str, available: set[str]) -> str | None:
    """Most recent period before `period` in available dates."""
    sorted_dates = sorted(available)
    try:
        idx = sorted_dates.index(period)
    except ValueError:
        return None
    return sorted_dates[idx - 1] if idx > 0 else None


def _total_val(df: pd.DataFrame, period: str, metric: str) -> float | None:
    rows = df[(df["report_date"] == period) &
              (df["metric"] == metric) &
              (df["record_type"] == "total")]["value"]
    return float(rows.iloc[0]) if not rows.empty else None


def _category_val(df: pd.DataFrame, period: str, metric: str, category: str) -> float | None:
    """
    Sum all bank rows for a given bank_category (CSV has one row per bank, no pre-aggregated
    category rows). Falls back to individual bank_name lookup for bank-level signals.
    """
    rows = df[(df["report_date"] == period) &
              (df["metric"] == metric) &
              (df["bank_category"] == category) &
              (df["record_type"] == "bank")]["value"].dropna()
    if not rows.empty:
        return float(rows.sum())
    # Fallback: individual bank lookup
    rows = df[(df["report_date"] == period) &
              (df["metric"] == metric) &
              (df["bank_name"] == category)]["value"].dropna()
    return float(rows.iloc[0]) if not rows.empty else None


def _eval_status(rules: list, value: float, prev: float) -> str:
    if value is None:
        return "unknown"
    ctx = {"value": value, "prev_value": prev if prev is not None else value}
    for rule in rules:
        cond = rule["if"]
        if cond == "true":
            return rule["then"]
        try:
            if eval(cond, {"__builtins__": {}}, ctx):   # noqa: S307
                return rule["then"]
        except Exception:
            continue
    return "unknown"


def _row(entity_type: str, entity_id: str, value, status: str, unit: str) -> dict:
    return {"entity_type": entity_type, "entity_id": entity_id,
            "value": round(float(value), 4) if value is not None else None,
            "status": status, "unit": unit}


def _unknown() -> list[dict]:
    return [_row("aggregate", "total", None, "unknown", "")]


# ── Layer 1a ──────────────────────────────────────────────────────────────────

def csv_total_abs(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Absolute value for the total row — status compares to prior period (MoM)."""
    metric = params["metric"]
    v = _total_val(df, period, metric)
    if v is None:
        return _unknown()
    avail = set(df["report_date"].unique())
    prior = _prior_period(period, avail)
    pv    = _total_val(df, prior, metric) if prior else v
    unit_rows = df[(df["report_date"] == period) & (df["metric"] == metric)]["unit"]
    unit = params.get("unit") or (unit_rows.iloc[0] if not unit_rows.empty else "count")
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, pv), unit)]


def csv_total_yoy(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    metric  = params["metric"]
    avail   = set(df["report_date"].unique())
    prior   = _prior_year(period, avail)
    v       = _total_val(df, period, metric)
    pv      = _total_val(df, prior,  metric) if prior else None
    if v is None:
        return _unknown()
    yoy = ((v - pv) / pv * 100) if pv else None
    status = _eval_status(params.get("status_rules", []), yoy,
                          None) if yoy is not None else "unknown"
    return [_row("aggregate", "total", yoy, status, "pct")]


def csv_total_ratio(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Ratio of two metrics — status compares to prior period (MoM)."""
    num = _total_val(df, period, params["metric"])
    den = _total_val(df, period, params["denominator_metric"])
    if num is None or den is None or den == 0:
        return _unknown()
    v     = num / den
    avail = set(df["report_date"].unique())
    prior = _prior_period(period, avail)
    pnum  = _total_val(df, prior, params["metric"])             if prior else None
    pden  = _total_val(df, prior, params["denominator_metric"]) if prior else None
    pv    = (pnum / pden) if (pnum and pden and pden != 0) else v
    unit  = params.get("unit", "ratio")
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, pv), unit)]


def csv_ratio_sum(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """metric / (metric_1 + metric_2 + ...) × 100 — status compares to prior period (MoM)."""
    metric = params["metric"]
    denom_metrics = params["denominator_metrics"]
    num = _total_val(df, period, metric)
    den = sum((_total_val(df, period, m) or 0) for m in denom_metrics)
    if num is None or den == 0:
        return _unknown()
    v     = num / den * 100
    avail = set(df["report_date"].unique())
    prior = _prior_period(period, avail)
    if prior:
        pnum = _total_val(df, prior, metric)
        pden = sum((_total_val(df, prior, m) or 0) for m in denom_metrics)
        pv   = (pnum / pden * 100) if pnum and pden else v
    else:
        pv = v
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, pv), "pct")]


def csv_sum_yoy(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """YoY% of (metric_1 + metric_2 + ...)."""
    metrics = params["metrics"]
    avail   = set(df["report_date"].unique())
    prior   = _prior_year(period, avail)
    v  = sum((_total_val(df, period, m) or 0) for m in metrics)
    pv = sum((_total_val(df, prior,  m) or 0) for m in metrics) if prior else None
    if not v:
        return _unknown()
    yoy = ((v - pv) / pv * 100) if pv else None
    status = _eval_status(params.get("status_rules", []), yoy, None) if yoy is not None else "unknown"
    return [_row("aggregate", "total", yoy, status, "pct")]


# ── Layer 1b ──────────────────────────────────────────────────────────────────

def csv_category_share(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """bank_category / Total for a metric — status compares to prior period (MoM)."""
    metric   = params["metric"]
    category = params["category"]
    cat_v    = _category_val(df, period, metric, category)
    total_v  = _total_val(df,   period, metric)
    if cat_v is None or total_v is None or total_v == 0:
        return _unknown()
    v     = cat_v / total_v * 100
    avail = set(df["report_date"].unique())
    prior = _prior_period(period, avail)
    pv    = v
    if prior:
        pc = _category_val(df, prior, metric, category)
        pt = _total_val(df,   prior, metric)
        if pc and pt and pt != 0:
            pv = pc / pt * 100
    return [_row("bank_category", category, v,
                 _eval_status(params.get("status_rules", []), v, pv), "pct")]


def csv_category_yoy(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """YoY% for a specific bank_category."""
    metric   = params["metric"]
    category = params["category"]
    avail    = set(df["report_date"].unique())
    prior    = _prior_year(period, avail)
    v  = _category_val(df, period, metric, category)
    pv = _category_val(df, prior,  metric, category) if prior else None
    if v is None:
        return _unknown()
    yoy = ((v - pv) / pv * 100) if pv else None
    status = _eval_status(params.get("status_rules", []), yoy, None) if yoy is not None else "unknown"
    return [_row("bank_category", category, yoy, status, "pct")]


# ── Layer 1c ──────────────────────────────────────────────────────────────────

def csv_category_scan_share(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Share of total for every bank_category — status compares to prior period (MoM)."""
    metric  = params["metric"]
    total_v = _total_val(df, period, metric)
    if total_v is None or total_v == 0:
        return []
    avail = set(df["report_date"].unique())
    prior = _prior_period(period, avail)
    rules = params.get("status_rules", [])
    cats  = df[(df["report_date"] == period) &
               (df["metric"] == metric) &
               (df["record_type"] == "bank")]["bank_category"].unique()
    out   = []
    for cat in cats:
        cv = _category_val(df, period, metric, cat)
        if cv is None:
            continue
        share = cv / total_v * 100
        pv    = share
        if prior:
            pc = _category_val(df, prior, metric, cat)
            pt = _total_val(df, prior, metric)
            if pc and pt and pt != 0:
                pv = pc / pt * 100
        out.append(_row("bank_category", cat, share,
                        _eval_status(rules, share, pv), "pct"))
    return sorted(out, key=lambda r: r["value"] if r["value"] is not None else -999, reverse=True)


def csv_bank_scan(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """
    Compute value or YoY for EVERY bank for a metric. One row per bank.
    value_type: "value" (absolute) | "yoy" (year-on-year %)
    No filtering — the full set of banks is stored; analysis layer extracts insights.
    """
    metric     = params["metric"]
    value_type = params.get("value_type", "value")
    rules      = params.get("status_rules", [])

    bank_rows = df[(df["report_date"] == period) &
                   (df["metric"] == metric) &
                   (df["record_type"] == "bank")][["bank_name", "value"]].dropna()
    if bank_rows.empty:
        return []

    unit = params.get("unit")
    if not unit:
        unit_rows = df[(df["report_date"] == period) & (df["metric"] == metric)]["unit"]
        unit = unit_rows.iloc[0] if not unit_rows.empty else "count"

    if value_type == "yoy":
        avail = set(df["report_date"].unique())
        prior = _prior_year(period, avail)
        if not prior:
            return []
        prev_rows = df[(df["report_date"] == prior) &
                       (df["metric"] == metric) &
                       (df["record_type"] == "bank")][["bank_name", "value"]].dropna()
        merged = bank_rows.merge(prev_rows, on="bank_name", suffixes=("_cur", "_prev"))
        merged = merged[merged["value_prev"] > 0].copy()
        merged["yoy"] = (merged["value_cur"] - merged["value_prev"]) / merged["value_prev"] * 100
        out = []
        for _, row in merged.iterrows():
            v = row["yoy"]
            out.append(_row("bank", row["bank_name"], v,
                            _eval_status(rules, v, v) if rules else "active", "pct"))
        return out
    else:
        # absolute value for each bank
        total_v = _total_val(df, period, metric)
        avail   = set(df["report_date"].unique())
        prior   = _prior_year(period, avail)
        out = []
        for _, row in bank_rows.iterrows():
            v  = row["value"]
            pv = v
            if prior:
                prow = df[(df["report_date"] == prior) &
                          (df["metric"] == metric) &
                          (df["bank_name"] == row["bank_name"]) &
                          (df["record_type"] == "bank")]["value"]
                if not prow.empty:
                    pv = float(prow.iloc[0])
            status = _eval_status(rules, v, pv) if rules else "active"
            out.append(_row("bank", row["bank_name"], v, status, unit))
        return out


# ── Layer 1d ──────────────────────────────────────────────────────────────────

def csv_streak(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """
    Count consecutive periods (going backwards from current) where a
    month-over-month condition holds on the total metric value.

    params:
      metric    — metric name in the CSV
      condition — 'value > prev_value' (default, growth streak)
                  'value < prev_value' (contraction streak)
    """
    metric    = params["metric"]
    condition = params.get("condition", "value > prev_value")
    avail     = sorted(df["report_date"].unique())

    if period not in avail:
        return _unknown()

    idx = avail.index(period)

    def _meets(v: float | None, pv: float | None) -> bool:
        if v is None or pv is None:
            return False
        if condition == "value > prev_value":
            return v > pv
        if condition == "value < prev_value":
            return v < pv
        return False

    # Count streak ending at current period
    streak = 0
    for i in range(idx, -1, -1):
        v  = _total_val(df, avail[i],          metric)
        pv = _total_val(df, avail[i - 1], metric) if i > 0 else None
        if _meets(v, pv):
            streak += 1
        else:
            break

    # streak=0 means condition not met for current period — still a valid result (declining)
    # Only return unknown when there is no prior period to compare at all
    if streak == 0 and idx == 0:
        return _unknown()

    # Count streak ending at prior period (for status comparison)
    prev_streak = 0
    if idx > 0:
        for i in range(idx - 1, -1, -1):
            v  = _total_val(df, avail[i],          metric)
            pv = _total_val(df, avail[i - 1], metric) if i > 0 else None
            if _meets(v, pv):
                prev_streak += 1
            else:
                break

    return [_row("aggregate", "total", streak,
                 _eval_status(params.get("status_rules", []), streak, prev_streak),
                 "periods")]


# ── Relational methods — rotation & divergence (spec: signals/README.md) ──────

def _month_back(period: str, months: int, available: set[str]) -> str | None:
    """Month-end date `months` calendar months before period — None if absent
    from available dates. Calendar-based so the annual window is honest even if
    the consolidated CSV ever has coverage gaps (same rule as the SIBC module)."""
    d = date.fromisoformat(period)
    total = d.year * 12 + (d.month - 1) - months
    y, m = divmod(total, 12)
    m += 1
    candidate = f"{y}-{m:02d}-{calendar.monthrange(y, m)[1]:02d}"
    return candidate if candidate in available else None


ROTATION_DEFAULT_RULES = [
    {"if": "value > 0.15",  "then": "strengthening"},
    {"if": "value < -0.15", "then": "weakening"},
    {"if": "true",          "then": "stable"},
]


def _rotation_rows(cur_shares: list[dict], prior_shares: list[dict],
                   rules: list) -> list[dict]:
    """Shared rotation math: Δshare_pp per entity from two share-scan snapshots,
    plus the aggregate 'rotation mass' row (Σ|Δ|/2 = pp of the mix that moved).
    Entities must appear in both snapshots to rotate. Mirror of sibc._rotation_rows."""
    prior = {r["entity_id"]: r["value"] for r in prior_shares
             if r["value"] is not None}
    out = []
    for r in cur_shares:
        eid = r["entity_id"]
        if r["value"] is None or eid not in prior:
            continue
        delta = r["value"] - prior[eid]
        out.append(_row(r["entity_type"], eid, delta,
                        _eval_status(rules, delta, delta), "pp"))
    if not out:
        return []
    out.sort(key=lambda r: r["value"], reverse=True)
    mass = sum(abs(r["value"]) for r in out) / 2
    out.append(_row("aggregate", "total", mass, "active", "pp"))
    return out


def csv_category_rotation(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """
    Δshare_pp over an annual window for every bank_category on a metric — who is
    gaining/losing ground in the mix. Share basis reuses csv_category_scan_share
    at the two endpoint dates (no parallel math).

    params: as csv_category_scan_share, plus
      window — calendar months back for the comparison date (default 12)
    Emits one row per category (value = Δshare_pp, sorted desc) + one
    aggregate/total 'rotation mass' row (Σ|Δ|/2). First `window` months emit no rows.
    """
    avail  = set(df["report_date"].unique())
    window = int(params.get("window", 12))
    prior_date = _month_back(period, window, avail)
    if prior_date is None:
        return []
    return _rotation_rows(csv_category_scan_share(params, period, df),
                          csv_category_scan_share(params, prior_date, df),
                          params.get("status_rules") or ROTATION_DEFAULT_RULES)


def csv_bank_divergence(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """
    Banks whose YoY on a metric contradicts their bank_category's YoY — flagged
    banks only (anomaly-surfaced by construction; no flags → no rows). The
    hierarchy operator: structurally identical to a SIBC sub-sector diverging
    from its sector.

    Flag rule: opposite YoY signs AND |bank_yoy| ≥ min_abs (default 2.0)
    AND |bank_yoy − category_yoy| ≥ min_gap (default 5.0).

    params:
      metric   — metric name in the CSV
      min_abs, min_gap — flag thresholds (pp)
      min_base — both the bank's current and prior-year value must be ≥ this
                 (default 1; excludes structural zeros — never flag structure)
    value = bank_yoy − category_yoy (pp, signed — sign carries direction).
    """
    metric   = params["metric"]
    min_abs  = float(params.get("min_abs", 2.0))
    min_gap  = float(params.get("min_gap", 5.0))
    min_base = float(params.get("min_base", 1))
    avail    = set(df["report_date"].unique())
    prior_yr = _prior_year(period, avail)
    if prior_yr is None:
        return []

    cur_rows = df[(df["report_date"] == period) &
                  (df["metric"] == metric) &
                  (df["record_type"] == "bank")][["bank_name", "bank_category", "value"]].dropna(subset=["value"])
    prev_rows = df[(df["report_date"] == prior_yr) &
                   (df["metric"] == metric) &
                   (df["record_type"] == "bank")][["bank_name", "value"]].dropna(subset=["value"])
    if cur_rows.empty or prev_rows.empty:
        return []

    merged = cur_rows.merge(prev_rows, on="bank_name", suffixes=("_cur", "_prev"))
    merged = merged[(merged["value_cur"] >= min_base) &
                    (merged["value_prev"] >= min_base)]

    # Category YoY per bank_category, from the same summed-bank basis as
    # csv_category_yoy (no parallel math beyond the reuse of _category_val).
    cat_yoy: dict[str, float] = {}
    for cat in merged["bank_category"].unique():
        cv = _category_val(df, period,   metric, cat)
        pv = _category_val(df, prior_yr, metric, cat)
        if cv is not None and pv:
            cat_yoy[str(cat)] = (cv - pv) / pv * 100

    out = []
    for _, row in merged.iterrows():
        cat = str(row["bank_category"])
        if cat not in cat_yoy:
            continue
        bank_yoy = (row["value_cur"] - row["value_prev"]) / row["value_prev"] * 100
        c_yoy    = cat_yoy[cat]
        opposite = (bank_yoy > 0 > c_yoy) or (bank_yoy < 0 < c_yoy)
        if (opposite and abs(bank_yoy) >= min_abs
                and abs(bank_yoy - c_yoy) >= min_gap):
            out.append(_row("bank", row["bank_name"],
                            bank_yoy - c_yoy, "active", "pp"))
    return sorted(out, key=lambda r: r["value"], reverse=True)


# ── dispatch ──────────────────────────────────────────────────────────────────

METHODS: dict = {
    "csv_total_abs":           csv_total_abs,
    "csv_total_yoy":           csv_total_yoy,
    "csv_total_ratio":         csv_total_ratio,
    "csv_ratio_sum":           csv_ratio_sum,
    "csv_sum_yoy":             csv_sum_yoy,
    "csv_category_share":      csv_category_share,
    "csv_category_yoy":        csv_category_yoy,
    "csv_category_scan_share": csv_category_scan_share,
    "csv_bank_scan":           csv_bank_scan,
    "csv_streak":              csv_streak,
    # relational — cross-segment (spec: signals/README.md)
    "csv_category_rotation":   csv_category_rotation,
    "csv_bank_divergence":     csv_bank_divergence,
}


def compute(metric_id: str, params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    fn = METHODS.get(params.get("method", ""))
    if fn is None:
        return _unknown()
    try:
        return fn(params, period, df) or _unknown()
    except Exception:
        return _unknown()
