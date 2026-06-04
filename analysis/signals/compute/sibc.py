"""
SIBC compute methods — all algorithmic, no LLM input.
Source: analysis/rbi_sibc/merged/sections_merged.json

Each method receives (params: dict, period_label: str) and returns list[dict]:
  { entity_type, entity_id, value, status, unit }

period_label is the sections_merged.json date label for the target period
(e.g. "Jan 2026", "Feb 2026", "Mar 2026"). The engine resolves this from
the dataDate using _build_label_index().

Layer 1a methods (aggregate scalars):
  static_active, series_yoy, series_abs, series_share, multi_series_share,
  count_positive_yoy, is_max_series, abs_undercount, yoy_spread, yoy_spread_named

Layer 1b methods (cross-series scalars within a section):
  (same methods as 1a, just different params — series_share with section totals, etc.)

Layer 1c methods (entity-level scans — return one row per entity):
  section_scan_yoy, section_scan_share
"""

from __future__ import annotations
import json
from pathlib import Path

REPO            = Path(__file__).resolve().parent.parent.parent.parent
SECTIONS_MERGED = REPO / "analysis" / "rbi_sibc" / "merged" / "sections_merged.json"
TIMELINE        = REPO / "analysis" / "rbi_sibc" / "timeline.json"

_cache: dict | None = None
_label_map: dict[str, str] | None = None   # dataDate → period_label


def _load() -> dict:
    global _cache
    if _cache is None:
        with open(SECTIONS_MERGED) as f:
            _cache = json.load(f)
    return _cache


def invalidate_cache() -> None:
    global _cache, _label_map
    _cache = None
    _label_map = None


def build_label_map() -> dict[str, str]:
    """Return {dataDate: period_label} from timeline.json."""
    global _label_map
    if _label_map is None:
        with open(TIMELINE) as f:
            tl = json.load(f)
        _label_map = {
            p["dataDate"]: p["period"]
            for p in tl.get("periods", [])
            if p.get("dataDate") and p.get("period")
        }
    return _label_map


def _section(section_id: str) -> dict | None:
    return next((s for s in _load().get("sections", []) if s["id"] == section_id), None)


def _find_idx(data: list[dict], label: str) -> int | None:
    """Return the index in data[] whose 'date' matches label (exact or prefix)."""
    for i, row in enumerate(data):
        if row.get("date") == label:
            return i
        # handle provisional marks like "Feb 2025*"
        if row.get("date", "").rstrip("*") == label.rstrip("*"):
            return i
    return None


def _eval_status(rules: list, value: float, prev: float) -> str:
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


def _get_rows(data: list[dict], label: str) -> tuple[dict, dict]:
    """
    Return (current_row, prev_row) for the given label.
    Falls back to last row if label not found.
    """
    idx = _find_idx(data, label)
    if idx is None:
        # label not in data — use latest available
        idx = len(data) - 1
    cur  = data[idx]
    prev = data[idx - 1] if idx > 0 else cur
    return cur, prev


# ── Layer 1a / 1b scalar methods ──────────────────────────────────────────────

def static_active(params: dict, period_label: str) -> list[dict]:
    return [_row("aggregate", "total", 1.0, "active", "index")]


def series_yoy(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    gd = sec.get("growthData", [])
    if not gd:
        return _unknown()
    s = params["series"]
    cur, prev = _get_rows(gd, period_label)
    v = cur.get(s)
    p = prev.get(s)
    if v is None:
        return _unknown()
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, p if p is not None else v),
                 "pct")]


def series_abs(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    ad = sec.get("absoluteData", [])
    if not ad:
        return _unknown()
    s = params["series"]
    cur, prev = _get_rows(ad, period_label)
    v = cur.get(s)
    p = prev.get(s)
    if v is None:
        return _unknown()
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, p if p is not None else v),
                 params.get("unit", "lcr_cr"))]


def series_share(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    ad = sec.get("absoluteData", [])
    if not ad:
        return _unknown()
    s    = params["series"]
    dnom = params.get("denominator_series")
    cur, prev = _get_rows(ad, period_label)

    def _share(row):
        num = row.get(s, 0) or 0
        den = (row.get(dnom, 0) or 0) if dnom else \
              sum(v for k, v in row.items() if k != "date" and isinstance(v, (int, float)))
        return (num / den * 100) if den else None

    v = _share(cur)
    p = _share(prev)
    if v is None:
        return _unknown()
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, p if p is not None else v),
                 "pct")]


def multi_series_share(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    ad = sec.get("absoluteData", [])
    if not ad:
        return _unknown()
    series_list = params["series"]
    dnom        = params.get("denominator_series")
    cur, prev   = _get_rows(ad, period_label)

    def _share(row):
        num = sum(row.get(s, 0) or 0 for s in series_list)
        den = (row.get(dnom, 0) or 0) if dnom else \
              sum(v for k, v in row.items() if k != "date" and isinstance(v, (int, float)))
        return (num / den * 100) if den else None

    v = _share(cur)
    p = _share(prev)
    if v is None:
        return _unknown()
    return [_row("aggregate", "total", v,
                 _eval_status(params.get("status_rules", []), v, p if p is not None else v),
                 "pct")]


def count_positive_yoy(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    gd = sec.get("growthData", [])
    if not gd:
        return _unknown()
    cur, prev = _get_rows(gd, period_label)
    count = sum(1 for k, v in cur.items()  if k != "date" and isinstance(v, (int, float)) and v > 0)
    pcount= sum(1 for k, v in prev.items() if k != "date" and isinstance(v, (int, float)) and v > 0)
    return [_row("aggregate", "total", count,
                 _eval_status(params.get("status_rules", []), count, pcount),
                 "count")]


def is_max_series(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    ad = sec.get("absoluteData", [])
    if not ad:
        return _unknown()
    s = params["series"]
    cur, _ = _get_rows(ad, period_label)
    vals   = {k: v for k, v in cur.items() if k != "date" and isinstance(v, (int, float))}
    if not vals or s not in vals:
        return _unknown()
    is_max = 1 if vals[s] == max(vals.values()) else 0
    return [_row("aggregate", "total", is_max,
                 _eval_status(params.get("status_rules", []), is_max, is_max),
                 "index")]


def abs_undercount(params: dict, period_label: str) -> list[dict]:
    num_sec = _section(params["numerator_section"])
    den_sec = _section(params["denominator_section"])
    if not num_sec or not den_sec:
        return _unknown()
    num_ad = num_sec.get("absoluteData", [])
    den_ad = den_sec.get("absoluteData", [])
    if not num_ad or not den_ad:
        return _unknown()
    ns = params["numerator_series"]
    num_cur, num_prev = _get_rows(num_ad, period_label)
    den_cur, den_prev = _get_rows(den_ad, period_label)
    numer = num_cur.get(ns)
    if numer is None:
        return _unknown()
    den   = sum(v for k, v in den_cur.items() if k != "date" and isinstance(v, (int, float)))
    gap   = numer - den
    pn    = num_prev.get(ns, 0) or 0
    pd    = sum(v for k, v in den_prev.items() if k != "date" and isinstance(v, (int, float)))
    pgap  = pn - pd
    return [_row("aggregate", "total", gap,
                 _eval_status(params.get("status_rules", []), gap, pgap),
                 "lcr_cr")]


def yoy_spread(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    gd = sec.get("growthData", [])
    if not gd:
        return _unknown()
    cur, prev = _get_rows(gd, period_label)
    vals  = [v for k, v in cur.items()  if k != "date" and isinstance(v, (int, float))]
    pvals = [v for k, v in prev.items() if k != "date" and isinstance(v, (int, float))]
    if len(vals) < 2:
        return _unknown()
    spread  = max(vals)  - min(vals)
    pspread = (max(pvals) - min(pvals)) if len(pvals) >= 2 else spread
    return [_row("aggregate", "total", spread,
                 _eval_status(params.get("status_rules", []), spread, pspread),
                 "pp")]


def yoy_spread_named(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return _unknown()
    gd = sec.get("growthData", [])
    if not gd:
        return _unknown()
    a = params["series_a"]
    b = params["series_b"]
    cur, prev = _get_rows(gd, period_label)
    va = cur.get(a)
    vb = cur.get(b)
    if va is None or vb is None:
        return _unknown()
    spread = va - vb
    pa = prev.get(a) or va
    pb = prev.get(b) or vb
    return [_row("aggregate", "total", spread,
                 _eval_status(params.get("status_rules", []), spread, pa - pb),
                 "pp")]


# ── Layer 1c scan methods ─────────────────────────────────────────────────────

def section_scan_yoy(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return []
    gd = sec.get("growthData", [])
    if not gd:
        return []
    cur, prev = _get_rows(gd, period_label)
    rules   = params.get("status_rules", [])
    exclude = set(params.get("exclude_series", []))
    entity_type = params.get("entity_type", "section_series")
    out = []
    for k, v in cur.items():
        if k == "date" or k in exclude or not isinstance(v, (int, float)):
            continue
        pv = prev.get(k, v)
        out.append(_row(entity_type, k, v,
                        _eval_status(rules, v, pv if pv is not None else v),
                        "pct"))
    return sorted(out, key=lambda r: r["value"] if r["value"] is not None else -999, reverse=True)


def section_scan_share(params: dict, period_label: str) -> list[dict]:
    sec = _section(params["section"])
    if not sec:
        return []
    ad = sec.get("absoluteData", [])
    if not ad:
        return []
    cur, prev = _get_rows(ad, period_label)
    rules   = params.get("status_rules", [])
    exclude = set(params.get("exclude_series", []))
    entity_type = params.get("entity_type", "section_series")

    total  = sum(v for k, v in cur.items()  if k != "date" and k not in exclude and isinstance(v, (int, float)))
    ptotal = sum(v for k, v in prev.items() if k != "date" and k not in exclude and isinstance(v, (int, float)))
    out = []
    for k, v in cur.items():
        if k == "date" or k in exclude or not isinstance(v, (int, float)):
            continue
        share  = (v / total * 100) if total else None
        pv     = prev.get(k, 0) or 0
        pshare = (pv / ptotal * 100) if ptotal else share
        out.append(_row(entity_type, k, share,
                        _eval_status(rules, share, pshare) if share is not None else "unknown",
                        "pct"))
    return sorted(out, key=lambda r: r["value"] if r["value"] is not None else -999, reverse=True)


# ── dispatch ──────────────────────────────────────────────────────────────────

METHODS: dict = {
    "static_active":       static_active,
    "series_yoy":          series_yoy,
    "series_abs":          series_abs,
    "series_share":        series_share,
    "multi_series_share":  multi_series_share,
    "count_positive_yoy":  count_positive_yoy,
    "is_max_series":       is_max_series,
    "abs_undercount":      abs_undercount,
    "yoy_spread":          yoy_spread,
    "yoy_spread_named":    yoy_spread_named,
    "section_scan_yoy":    section_scan_yoy,
    "section_scan_share":  section_scan_share,
}


def compute(metric_id: str, params: dict, period_label: str = "") -> list[dict]:
    fn = METHODS.get(params.get("method", ""))
    if fn is None:
        return _unknown()
    try:
        return fn(params, period_label) or _unknown()
    except Exception:
        return _unknown()
