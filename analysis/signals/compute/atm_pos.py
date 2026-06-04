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
"""

from __future__ import annotations
import calendar
from datetime import date
from pathlib import Path
from typing import Any

import pandas as pd

REPO    = Path(__file__).resolve().parent.parent.parent.parent
CSV     = REPO / "web" / "public" / "data" / "atm_pos_consolidated.csv"

_df_cache: pd.DataFrame | None = None


def _load_df() -> pd.DataFrame:
    global _df_cache
    if _df_cache is None:
        _df_cache = pd.read_csv(CSV, parse_dates=["report_date"])
        _df_cache["report_date"] = _df_cache["report_date"].dt.strftime("%Y-%m-%d")
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


def _total_val(df: pd.DataFrame, period: str, metric: str) -> float | None:
    rows = df[(df["report_date"] == period) &
              (df["metric"] == metric) &
              (df["record_type"] == "total")]["value"]
    return float(rows.iloc[0]) if not rows.empty else None


def _category_val(df: pd.DataFrame, period: str, metric: str, category: str) -> float | None:
    rows = df[(df["report_date"] == period) &
              (df["metric"] == metric) &
              (df["bank_category"] == category) &
              (df["record_type"] == "bank")]["value"]
    if rows.empty:
        rows = df[(df["report_date"] == period) &
                  (df["metric"] == metric) &
                  (df["bank_name"] == category)]["value"]
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
    num = _total_val(df, period, params["metric"])
    den = _total_val(df, period, params["denominator_metric"])
    if num is None or den is None or den == 0:
        return _unknown()
    v   = num / den
    avail = set(df["report_date"].unique())
    prior = _prior_year(period, avail)
    pnum = _total_val(df, prior, params["metric"])          if prior else None
    pden = _total_val(df, prior, params["denominator_metric"]) if prior else None
    pv   = (pnum / pden) if (pnum and pden and pden != 0) else v
    unit = params.get("unit", "ratio")
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, pv), unit)]


def csv_ratio_sum(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """metric / (metric_1 + metric_2 + ...) × 100."""
    metric = params["metric"]
    denom_metrics = params["denominator_metrics"]
    num = _total_val(df, period, metric)
    den = sum((_total_val(df, period, m) or 0) for m in denom_metrics)
    if num is None or den == 0:
        return _unknown()
    v = num / den * 100
    avail = set(df["report_date"].unique())
    prior = _prior_year(period, avail)
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
    """bank_category value / Total value for a metric."""
    metric   = params["metric"]
    category = params["category"]
    cat_v    = _category_val(df, period, metric, category)
    total_v  = _total_val(df,   period, metric)
    if cat_v is None or total_v is None or total_v == 0:
        return _unknown()
    v = cat_v / total_v * 100
    avail = set(df["report_date"].unique())
    prior = _prior_year(period, avail)
    pv = v
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
    """Share of total for every bank_category. One row per category."""
    metric  = params["metric"]
    total_v = _total_val(df, period, metric)
    if total_v is None or total_v == 0:
        return []
    avail = set(df["report_date"].unique())
    prior = _prior_year(period, avail)
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


# ── dispatch ──────────────────────────────────────────────────────────────────

METHODS: dict = {
    "csv_total_yoy":           csv_total_yoy,
    "csv_total_ratio":         csv_total_ratio,
    "csv_ratio_sum":           csv_ratio_sum,
    "csv_sum_yoy":             csv_sum_yoy,
    "csv_category_share":      csv_category_share,
    "csv_category_yoy":        csv_category_yoy,
    "csv_category_scan_share": csv_category_scan_share,
    "csv_bank_scan":           csv_bank_scan,
}


def compute(metric_id: str, params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    fn = METHODS.get(params.get("method", ""))
    if fn is None:
        return _unknown()
    try:
        return fn(params, period, df) or _unknown()
    except Exception:
        return _unknown()
