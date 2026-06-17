"""
SIBC compute methods — reads from rbi_sibc_consolidated.csv.

Single source of truth: same file used by the live dashboard.
Source: web/public/data/rbi_sibc_consolidated.csv

Each method receives (params, period, df) and returns list[dict]:
  { entity_type, entity_id, value, status, unit }

period: YYYY-MM-DD matching the CSV date column (e.g. "2026-03-31").
No timeline.json lookup needed — period resolves directly from CSV dates.

Layer 1a methods (aggregate scalars):
  csv_sector_yoy              — YoY% for a single sector code
  csv_sector_abs              — Absolute level for a single sector code
  csv_sector_share            — Sector share of parent
  csv_sector_yoy_spread       — YoY spread between two sector codes
  csv_sector_count_positive_yoy — Count of named codes with positive YoY

Layer 1b methods (named sub-group scalars):
  Same methods as 1a — different code/parent_code params

Layer 1c methods (entity scans — one row per child):
  csv_sector_scan_yoy         — YoY for every child of a parent code
  csv_sector_scan_share       — Share for every child of a parent code
  csv_psl_scan_yoy            — YoY for all PSL memo items

YoY momentum: status rules compare current YoY to prior-period YoY,
both computed inline from the CSV. No external state required.
"""

from __future__ import annotations

import calendar
from datetime import date
from pathlib import Path

import pandas as pd

REPO     = Path(__file__).resolve().parent.parent.parent.parent
CSV      = REPO / "web" / "public" / "data" / "rbi_sibc_consolidated.csv"
TIMELINE = REPO / "analysis" / "rbi_sibc" / "timeline.json"

_df_cache: pd.DataFrame | None = None


def resolve_csv_date(data_date: str) -> str | None:
    """
    Map a report dataDate (e.g. '2026-04-30') → csv_date ('2026-03-31').
    Returns the input unchanged if no matching entry found (allows direct
    csv_date pass-through when no translation is needed).
    """
    import json as _json
    try:
        tl = _json.loads(TIMELINE.read_text())
        for entry in tl.get("periods", []):
            if entry.get("dataDate") == data_date:
                return entry.get("csv_date", data_date)
    except Exception:
        pass
    return data_date


def _load_df() -> pd.DataFrame:
    global _df_cache
    if _df_cache is None:
        _df_cache = pd.read_csv(CSV, dtype={"code": str, "parent_code": str})
        _df_cache["date"] = pd.to_datetime(_df_cache["date"]).dt.strftime("%Y-%m-%d")
        _df_cache["code"]        = _df_cache["code"].fillna("").str.strip()
        _df_cache["parent_code"] = _df_cache["parent_code"].fillna("").str.strip()
    return _df_cache


def invalidate_cache() -> None:
    global _df_cache
    _df_cache = None


# ── Date helpers ──────────────────────────────────────────────────────────────

def _prior_year(period: str, available: set[str]) -> str | None:
    """Same month, one year prior — returns None if not in available dates."""
    d = date.fromisoformat(period)
    py = d.year - 1
    last_day = calendar.monthrange(py, d.month)[1]
    candidate = f"{py}-{d.month:02d}-{last_day:02d}"
    return candidate if candidate in available else None


def _prior_period(period: str, available: set[str]) -> str | None:
    """Most recent date before period in available set."""
    sorted_dates = sorted(available)
    try:
        idx = sorted_dates.index(period)
        return sorted_dates[idx - 1] if idx > 0 else None
    except ValueError:
        return None


# ── Value lookup ──────────────────────────────────────────────────────────────

def _val(df: pd.DataFrame, date_str: str, code: str,
         statement: str = "Statement 1", is_psl: bool = False) -> float | None:
    q = df[(df["date"] == date_str) & (df["code"] == str(code))]
    if is_psl:
        q = q[q["is_priority_sector_memo"] == True]   # noqa: E712
    else:
        q = q[q["statement"] == statement]
    rows = q["outstanding_cr"]
    return float(rows.iloc[0]) if not rows.empty else None


# ── Status evaluation ─────────────────────────────────────────────────────────

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
    return {
        "entity_type": entity_type,
        "entity_id":   entity_id,
        "value":       round(float(value), 4) if value is not None else None,
        "status":      status,
        "unit":        unit,
    }


def _unknown() -> list[dict]:
    return [_row("aggregate", "total", None, "unknown", "")]


# ── YoY helper (current + prior-period YoY for momentum) ─────────────────────

def _compute_yoy(df: pd.DataFrame, period: str, code: str,
                 statement: str, avail: set[str],
                 is_psl: bool = False) -> tuple[float | None, float | None]:
    """
    Returns (yoy, prev_yoy) where prev_yoy is the prior period's YoY —
    used by status rules to assess acceleration/deceleration.
    Both computed from CSV without external state.
    """
    prior_yr = _prior_year(period, avail)
    if not prior_yr:
        return None, None
    v  = _val(df, period,   code, statement, is_psl)
    pv = _val(df, prior_yr, code, statement, is_psl)
    if v is None or pv is None or pv == 0:
        return None, None
    yoy = (v - pv) / pv * 100

    prev_pd = _prior_period(period, avail)
    prev_yoy = yoy
    if prev_pd:
        prev_yr2 = _prior_year(prev_pd, avail)
        if prev_yr2:
            v2  = _val(df, prev_pd,  code, statement, is_psl)
            pv2 = _val(df, prev_yr2, code, statement, is_psl)
            if v2 and pv2 and pv2 != 0:
                prev_yoy = (v2 - pv2) / pv2 * 100
    return yoy, prev_yoy


# ── Layer 1a / 1b scalar methods ──────────────────────────────────────────────

def csv_sector_yoy(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """YoY% for a single sector code. Set is_psl=true in params for PSL memo items."""
    code   = str(params["code"])
    stmt   = params.get("statement", "Statement 1")
    is_psl = bool(params.get("is_psl", False))
    avail  = set(df["date"].unique())
    yoy, prev_yoy = _compute_yoy(df, period, code, stmt, avail, is_psl=is_psl)
    if yoy is None:
        return _unknown()
    return [_row("aggregate", "total", yoy,
                 _eval_status(params.get("status_rules", []), yoy, prev_yoy),
                 "pct")]


def csv_sector_abs(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Absolute outstanding credit for a single sector code."""
    code   = str(params["code"])
    stmt   = params.get("statement", "Statement 1")
    is_psl = bool(params.get("is_psl", False))
    avail  = set(df["date"].unique())
    v      = _val(df, period, code, stmt, is_psl=is_psl)
    if v is None:
        return _unknown()
    prior = _prior_period(period, avail)
    pv    = _val(df, prior, code, stmt, is_psl=is_psl) if prior else v
    unit  = params.get("unit", "rs_cr")
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, pv if pv else v),
                 unit)]


def csv_sector_share(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Sector share of parent sector (%)."""
    code        = str(params["code"])
    parent_code = str(params["parent_code"])
    stmt        = params.get("statement", "Statement 1")
    avail       = set(df["date"].unique())
    v   = _val(df, period, code,        stmt)
    den = _val(df, period, parent_code, stmt)
    if v is None or den is None or den == 0:
        return _unknown()
    share  = v / den * 100
    prior  = _prior_period(period, avail)
    pshare = share
    if prior:
        pv  = _val(df, prior, code,        stmt)
        pdn = _val(df, prior, parent_code, stmt)
        if pv is not None and pdn and pdn != 0:
            pshare = pv / pdn * 100
    return [_row("aggregate", "total", share,
                 _eval_status(params.get("status_rules", []), share, pshare),
                 "pct")]


def csv_sector_yoy_spread(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """YoY spread: code_a growth minus code_b growth (pp)."""
    code_a = str(params["code_a"])
    code_b = str(params["code_b"])
    stmt   = params.get("statement", "Statement 1")
    avail  = set(df["date"].unique())
    yoy_a, _ = _compute_yoy(df, period, code_a, stmt, avail)
    yoy_b, _ = _compute_yoy(df, period, code_b, stmt, avail)
    if yoy_a is None or yoy_b is None:
        return _unknown()
    spread = yoy_a - yoy_b
    prior  = _prior_period(period, avail)
    pspread = spread
    if prior:
        pa, _ = _compute_yoy(df, prior, code_a, stmt, avail)
        pb, _ = _compute_yoy(df, prior, code_b, stmt, avail)
        if pa is not None and pb is not None:
            pspread = pa - pb
    return [_row("aggregate", "total", spread,
                 _eval_status(params.get("status_rules", []), spread, pspread),
                 "pp")]


def csv_sector_count_positive_yoy(params: dict, period: str,
                                   df: pd.DataFrame) -> list[dict]:
    """Count of named sector codes with positive YoY growth."""
    codes = [str(c) for c in params["child_codes"]]
    stmt  = params.get("statement", "Statement 1")
    avail = set(df["date"].unique())
    prior = _prior_period(period, avail)

    count  = sum(1 for c in codes
                 if (_compute_yoy(df, period, c, stmt, avail)[0] or 0) > 0)
    pcount = count
    if prior:
        pcount = sum(1 for c in codes
                     if (_compute_yoy(df, prior, c, stmt, avail)[0] or 0) > 0)
    return [_row("aggregate", "total", count,
                 _eval_status(params.get("status_rules", []), count, pcount),
                 "count")]


# ── Layer 1c scan methods ──────────────────────────────────────────────────────

def csv_sector_scan_yoy(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """YoY for every child of parent_code at child_level."""
    parent_code = str(params["parent_code"])
    stmt        = params.get("statement", "Statement 1")
    child_level = params.get("child_level", 2)
    entity_type = params.get("entity_type", "sector")
    avail       = set(df["date"].unique())
    exclude     = {str(c) for c in params.get("exclude_codes", [])}

    children = df[
        (df["date"] == period) &
        (df["statement"] == stmt) &
        (df["parent_code"] == parent_code) &
        (df["level"] == child_level)
    ]
    out = []
    for _, row in children.iterrows():
        code = str(row["code"])
        if code in exclude:
            continue
        yoy, prev_yoy = _compute_yoy(df, period, code, stmt, avail)
        if yoy is None:
            continue
        out.append(_row(entity_type, row["sector"], yoy,
                        _eval_status(params.get("status_rules", []), yoy, prev_yoy),
                        "pct"))
    return sorted(out, key=lambda r: r["value"] if r["value"] is not None else -999,
                  reverse=True)


def csv_sector_scan_share(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """Share of parent for every child of parent_code at child_level."""
    parent_code      = str(params["parent_code"])
    stmt             = params.get("statement", "Statement 1")
    # Denominator may differ from structural parent (e.g. Statement 2 types → Statement 1 total)
    denom_code       = str(params.get("denominator_code", parent_code))
    denom_stmt       = params.get("denominator_statement", stmt)
    child_level      = params.get("child_level", 2)
    entity_type      = params.get("entity_type", "sector")
    avail            = set(df["date"].unique())
    exclude          = {str(c) for c in params.get("exclude_codes", [])}

    parent_val = _val(df, period, denom_code, denom_stmt)
    if parent_val is None or parent_val == 0:
        return []

    prior       = _prior_period(period, avail)
    prior_denom = _val(df, prior, denom_code, denom_stmt) if prior else None

    children = df[
        (df["date"] == period) &
        (df["statement"] == stmt) &
        (df["parent_code"] == parent_code) &
        (df["level"] == child_level)
    ]
    out = []
    for _, row in children.iterrows():
        code = str(row["code"])
        if code in exclude:
            continue
        v = _val(df, period, code, stmt)
        if v is None:
            continue
        share  = v / parent_val * 100
        pshare = share
        if prior and prior_denom and prior_denom != 0:
            pv = _val(df, prior, code, stmt)
            if pv is not None:
                pshare = pv / prior_denom * 100
        out.append(_row(entity_type, row["sector"], share,
                        _eval_status(params.get("status_rules", []), share, pshare),
                        "pct"))
    return sorted(out, key=lambda r: r["value"] if r["value"] is not None else -999,
                  reverse=True)


def csv_psl_scan_yoy(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """YoY for all Priority Sector Lending memo items."""
    entity_type = params.get("entity_type", "psl_category")
    avail       = set(df["date"].unique())
    exclude     = {str(c) for c in params.get("exclude_codes", [])}

    psl_rows = df[
        (df["date"] == period) &
        (df["is_priority_sector_memo"] == True)   # noqa: E712
    ]
    out = []
    for _, row in psl_rows.iterrows():
        code = str(row["code"])
        if code in exclude:
            continue
        yoy, prev_yoy = _compute_yoy(df, period, code, "Statement 1", avail,
                                      is_psl=True)
        if yoy is None:
            continue
        out.append(_row(entity_type, row["sector"], yoy,
                        _eval_status(params.get("status_rules", []), yoy, prev_yoy),
                        "pct"))
    return sorted(out, key=lambda r: r["value"] if r["value"] is not None else -999,
                  reverse=True)


# ── 1d: Multi-period compute methods ─────────────────────────────────────────

def _fy_end_dates(avail: set[str]) -> list[str]:
    """Return sorted list of March 31 dates present in the CSV."""
    return sorted(d for d in avail if d.endswith("-03-31"))


def csv_streak(params: dict, period: str, df: pd.DataFrame) -> list[dict]:
    """
    Count consecutive periods (going back from current) where a YoY
    condition holds.

    params:
      code       — sector code
      statement  — default "Statement 1"
      is_psl     — default False
      condition  — "positive" | "negative" | "above:{n}" | "below:{n}"
                   e.g. "negative" → yoy < 0, "above:20" → yoy > 20
    """
    code      = str(params["code"])
    stmt      = params.get("statement", "Statement 1")
    is_psl    = bool(params.get("is_psl", False))
    condition = params.get("condition", "positive")
    avail     = set(df["date"].unique())

    def _meets(yoy: float | None) -> bool:
        if yoy is None:
            return False
        if condition == "positive":
            return yoy > 0
        if condition == "negative":
            return yoy < 0
        if condition.startswith("above:"):
            return yoy > float(condition.split(":")[1])
        if condition.startswith("below:"):
            return yoy < float(condition.split(":")[1])
        return False

    sorted_dates = sorted(avail)
    try:
        idx = sorted_dates.index(period)
    except ValueError:
        return _unknown()

    streak = 0
    for d in reversed(sorted_dates[: idx + 1]):
        yoy, _ = _compute_yoy(df, d, code, stmt, avail, is_psl=is_psl)
        if _meets(yoy):
            streak += 1
        else:
            break

    if streak == 0:
        return _unknown()

    prev_streak = 0
    if idx > 0:
        for d in reversed(sorted_dates[: idx]):
            yoy, _ = _compute_yoy(df, d, code, stmt, avail, is_psl=is_psl)
            if _meets(yoy):
                prev_streak += 1
            else:
                break

    return [_row("aggregate", "total", streak,
                 _eval_status(params.get("status_rules", []), streak, prev_streak),
                 "periods")]


def csv_sector_fy_acceleration(params: dict, period: str,
                                df: pd.DataFrame) -> list[dict]:
    """
    YoY acceleration between the two most recent FY-end (March 31) dates.
    Returns (latest_fy_yoy - prior_fy_yoy) in percentage points.

    params:
      code      — sector code
      statement — default "Statement 1"
      is_psl    — default False
    """
    code   = str(params["code"])
    stmt   = params.get("statement", "Statement 1")
    is_psl = bool(params.get("is_psl", False))
    avail  = set(df["date"].unique())

    fy_dates = _fy_end_dates(avail)
    if len(fy_dates) < 2:
        return _unknown()

    latest_fy = fy_dates[-1]
    prior_fy  = fy_dates[-2]

    yoy_latest, _ = _compute_yoy(df, latest_fy, code, stmt, avail, is_psl=is_psl)
    yoy_prior,  _ = _compute_yoy(df, prior_fy,  code, stmt, avail, is_psl=is_psl)

    if yoy_latest is None or yoy_prior is None:
        return _unknown()

    accel = yoy_latest - yoy_prior

    # prev_value: acceleration from second-to-last vs third-to-last FY (if available)
    prev_accel = accel
    if len(fy_dates) >= 3:
        prior2_fy = fy_dates[-3]
        yoy_prior2, _ = _compute_yoy(df, prior2_fy, code, stmt, avail, is_psl=is_psl)
        if yoy_prior2 is not None:
            prev_accel = yoy_prior - yoy_prior2

    # Acceleration is a second-order scalar (difference of two FY-end YoY rates)
    # and is period-invariant — it depends only on the FY-ends, not the eval
    # period. Emit its two component rates as well, keyed by FY-end date, so the
    # value is interpretable and traceable back to its inputs (year to Mar YYYY
    # grew X%). entity_type='fy_yoy' keeps these out of the aggregate/total
    # status-sync and scalar-history paths.
    return [
        _row("aggregate", "total", accel,
             _eval_status(params.get("status_rules", []), accel, prev_accel), "pp"),
        _row("fy_yoy", prior_fy,  yoy_prior,  "active", "pct"),
        _row("fy_yoy", latest_fy, yoy_latest, "active", "pct"),
    ]


def csv_sector_fy_delta(params: dict, period: str,
                         df: pd.DataFrame) -> list[dict]:
    """
    Absolute credit add (₹L Cr) between the two most recent FY-end dates.

    params:
      code      — sector code
      statement — default "Statement 1"
      unit      — default "lcr_cr"
    """
    code  = str(params["code"])
    stmt  = params.get("statement", "Statement 1")
    unit  = params.get("unit", "lcr_cr")
    avail = set(df["date"].unique())

    fy_dates = _fy_end_dates(avail)
    if len(fy_dates) < 2:
        return _unknown()

    latest_fy = fy_dates[-1]
    prior_fy  = fy_dates[-2]

    v_latest = _val(df, latest_fy, code, stmt)
    v_prior  = _val(df, prior_fy,  code, stmt)

    if v_latest is None or v_prior is None:
        return _unknown()

    delta = v_latest - v_prior

    prev_delta = delta
    if len(fy_dates) >= 3:
        prior2_fy = fy_dates[-3]
        v_prior2  = _val(df, prior2_fy, code, stmt)
        if v_prior2 is not None:
            prev_delta = v_prior - v_prior2

    return [_row("aggregate", "total", delta,
                 _eval_status(params.get("status_rules", []), delta, prev_delta),
                 unit)]


# ── dispatch ──────────────────────────────────────────────────────────────────

METHODS: dict = {
    "csv_sector_yoy":               csv_sector_yoy,
    "csv_sector_abs":               csv_sector_abs,
    "csv_sector_share":             csv_sector_share,
    "csv_sector_yoy_spread":        csv_sector_yoy_spread,
    "csv_sector_count_positive_yoy": csv_sector_count_positive_yoy,
    "csv_sector_scan_yoy":          csv_sector_scan_yoy,
    "csv_sector_scan_share":        csv_sector_scan_share,
    "csv_psl_scan_yoy":             csv_psl_scan_yoy,
    # 1d — multi-period
    "csv_streak":                   csv_streak,
    "csv_sector_fy_acceleration":   csv_sector_fy_acceleration,
    "csv_sector_fy_delta":          csv_sector_fy_delta,
}


def compute(metric_id: str, params: dict, period: str,
            df: pd.DataFrame) -> list[dict]:
    fn = METHODS.get(params.get("method", ""))
    if fn is None:
        return _unknown()
    try:
        return fn(params, period, df) or _unknown()
    except Exception:
        return _unknown()
