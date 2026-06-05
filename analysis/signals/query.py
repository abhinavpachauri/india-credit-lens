"""
Context builder for LLM evaluation.

Pulls signal values, prior-period values, range stats, and entity distributions
from signals.db and formats them into a compact text payload per domain.
"""

from __future__ import annotations
import sqlite3
from pathlib import Path


# ── Signal type → prompt type label ──────────────────────────────────────────

METHOD_TYPE: dict[str, str] = {
    # Layer 1a — aggregate scalars
    "series_yoy":              "yoy",
    "csv_total_yoy":           "yoy",
    "csv_category_yoy":        "yoy",
    "csv_sum_yoy":             "yoy",
    "csv_sector_yoy":          "yoy",
    "series_share":            "share",
    "multi_series_share":      "share",
    "csv_ratio_sum":           "share",
    "csv_category_share":      "share",
    "csv_sector_share":        "share",
    "series_abs":              "absolute",
    "csv_total_abs":           "absolute",
    "csv_sector_abs":          "absolute",
    "abs_undercount":          "absolute",
    "yoy_spread":              "spread",
    "yoy_spread_named":        "spread",
    "csv_sector_yoy_spread":   "spread",
    "csv_total_ratio":         "ratio",
    "count_positive_yoy":      "breadth",
    "csv_sector_count_positive_yoy": "breadth",
    "static_active":           "breadth",
    # Layer 1c — entity scans
    "section_scan_yoy":        "scan",
    "section_scan_share":      "scan",
    "csv_category_scan_share": "scan",
    "csv_sector_scan_yoy":     "scan",
    "csv_sector_scan_share":   "scan",
    "csv_psl_scan_yoy":        "scan",
    "csv_bank_scan":           "scan",
    # Layer 1d — multi-period
    "csv_streak":              "streak",
    "csv_sector_fy_acceleration": "acceleration",
    "csv_sector_fy_delta":     "absolute",
}

def _signal_type(sig: dict) -> str:
    method = sig.get("compute", {}).get("method", "")
    return METHOD_TYPE.get(method, "yoy")


def _range_position(value: float, p25: float | None, p75: float | None,
                    min_v: float | None, max_v: float | None) -> str:
    if p25 is None or p75 is None:
        return "insufficient history"
    if value >= (max_v or p75):
        return "at or near MAX"
    if value <= (min_v or p25):
        return "at or near MIN"
    if value >= p75:
        return "above p75 (upper range)"
    if value <= p25:
        return "below p25 (lower range)"
    return "near median"


# ── Scalar signal payload ─────────────────────────────────────────────────────

def _scalar_payload(conn: sqlite3.Connection, sig_id: str, sig: dict,
                    pipeline: str, period: str) -> str | None:
    """Build one-signal context block for scalar (non-scan) signals."""
    row = conn.execute(
        """SELECT s.value, s.unit, s.status, s.period
           FROM signals s
           WHERE s.pipeline=? AND s.period=? AND s.metric_id=?
             AND s.entity_type='aggregate' AND s.entity_id='total'""",
        (pipeline, period, sig_id)
    ).fetchone()

    if row is None or row[0] is None:
        return None

    value, unit, status, _ = row[0], row[1], row[2], row[3]

    # Prior period value
    prior_row = conn.execute(
        """SELECT s.value, s.period FROM signals s
           WHERE s.pipeline=? AND s.metric_id=?
             AND s.entity_type='aggregate' AND s.entity_id='total'
             AND s.period < ?
           ORDER BY s.period DESC LIMIT 1""",
        (pipeline, sig_id, period)
    ).fetchone()

    prior_value = prior_row[0] if prior_row else None
    delta = (value - prior_value) if prior_value is not None else None

    # Range stats
    rng = conn.execute(
        """SELECT min_value, max_value, p25_value, p75_value, period_count
           FROM metric_ranges
           WHERE metric_id=? AND pipeline=?
             AND entity_type='aggregate' AND entity_id='total'""",
        (sig_id, pipeline)
    ).fetchone()

    sig_type = _signal_type(sig)
    title    = sig.get("title", sig_id)

    lines = [
        f"--- {sig_id} [type: {sig_type}] ---",
        f"Title: {title}",
    ]

    # Format value
    if unit == "pct":
        vstr = f"{value:.2f}%"
        pvstr = f"{prior_value:.2f}%" if prior_value is not None else "n/a"
        dstr = f"{delta:+.2f}pp" if delta is not None else "n/a"
    elif unit in ("lcr_cr", "rs_thousands"):
        vstr = f"{value:,.0f} {unit}"
        pvstr = f"{prior_value:,.0f} {unit}" if prior_value is not None else "n/a"
        dstr = f"{delta:+,.0f}" if delta is not None else "n/a"
    elif unit == "ratio":
        vstr = f"{value:.1f}x"
        pvstr = f"{prior_value:.1f}x" if prior_value is not None else "n/a"
        dstr = f"{delta:+.2f}" if delta is not None else "n/a"
    elif unit == "pp":
        vstr = f"{value:.1f}pp"
        pvstr = f"{prior_value:.1f}pp" if prior_value is not None else "n/a"
        dstr = f"{delta:+.1f}pp" if delta is not None else "n/a"
    elif unit == "count":
        vstr = f"{value:.0f}"
        pvstr = f"{prior_value:.0f}" if prior_value is not None else "n/a"
        dstr = f"{delta:+.0f}" if delta is not None else "n/a"
    elif unit == "periods":
        vstr = f"{int(value)} consecutive period(s)"
        pvstr = f"{int(prior_value)}" if prior_value is not None else "n/a"
        dstr = f"{delta:+.0f}" if delta is not None else "n/a"
    else:
        vstr = f"{value:,.1f} {unit}"
        pvstr = f"{prior_value:,.1f} {unit}" if prior_value is not None else "n/a"
        dstr = f"{delta:+.1f}" if delta is not None else "n/a"

    lines.append(f"Value: {vstr} | Status: {status}")
    lines.append(f"Prior period: {pvstr} | Change: {dstr}")

    if rng:
        min_v, max_v, p25, p75, n = rng
        pos = _range_position(value, p25, p75, min_v, max_v)
        if unit == "pct":
            lines.append(
                f"Historical range: p25={p25:.1f}%, p75={p75:.1f}%, "
                f"current {pos} ({n} periods)"
            )
        else:
            lines.append(f"Historical range: {n} period(s), current {pos}")

    return "\n".join(lines)


# ── Scan signal payload ───────────────────────────────────────────────────────

def _scan_payload(conn: sqlite3.Connection, sig_id: str, sig: dict,
                  pipeline: str, period: str) -> str | None:
    """Build context block for 1c scan signals (full entity distributions)."""
    rows = conn.execute(
        """SELECT entity_id, value, status FROM signals
           WHERE pipeline=? AND period=? AND metric_id=?
             AND value IS NOT NULL
           ORDER BY value DESC""",
        (pipeline, period, sig_id)
    ).fetchall()

    if not rows:
        return None

    title    = sig.get("title", sig_id)
    sig_type = _signal_type(sig)
    n        = len(rows)

    # Status distribution
    status_counts: dict[str, int] = {}
    for r in rows:
        s = r[2] or "unknown"
        status_counts[s] = status_counts.get(s, 0) + 1
    status_summary = ", ".join(f"{v} {k}" for k, v in sorted(status_counts.items()))

    top3    = rows[:3]
    bottom3 = rows[-3:][::-1]   # worst first in the bottom group

    # Entities that changed status vs prior period
    prior_rows = conn.execute(
        """SELECT entity_id, status FROM signals
           WHERE pipeline=? AND metric_id=? AND entity_type NOT IN ('aggregate')
             AND period = (
               SELECT period FROM signals
               WHERE pipeline=? AND metric_id=? AND period < ?
               ORDER BY period DESC LIMIT 1
             )""",
        (pipeline, sig_id, pipeline, sig_id, period)
    ).fetchall()
    prior_status = {r[0]: r[1] for r in prior_rows}

    changed = []
    for r in rows:
        eid, _, cur_s = r
        prev_s = prior_status.get(eid)
        if prev_s and prev_s != cur_s:
            changed.append(f"{eid}: {prev_s}→{cur_s}")

    spread = rows[0][1] - rows[-1][1] if len(rows) >= 2 else 0

    unit_row = conn.execute(
        "SELECT unit FROM signals WHERE pipeline=? AND period=? AND metric_id=? LIMIT 1",
        (pipeline, period, sig_id)
    ).fetchone()
    unit = unit_row[0] if unit_row else "pct"

    def _fmt(v: float) -> str:
        return f"{v:.1f}%" if unit == "pct" else f"{v:,.0f}"

    top_str    = ", ".join(f"{r[0]} {_fmt(r[1])}({r[2][0].upper()})" for r in top3)
    bottom_str = ", ".join(f"{r[0]} {_fmt(r[1])}({r[2][0].upper()})" for r in bottom3)

    lines = [
        f"--- {sig_id} [type: {sig_type}] ---",
        f"Title: {title}",
        f"Distribution: {n} entities | {status_summary}",
        f"Top:    {top_str}",
        f"Bottom: {bottom_str}",
        f"Spread: {_fmt(spread)}",
    ]
    if changed:
        lines.append(f"Status shifts: {'; '.join(changed[:5])}")

    return "\n".join(lines)


# ── Domain payload ────────────────────────────────────────────────────────────

def build_domain_payload(conn: sqlite3.Connection, pipeline: str,
                          period: str, domain: str,
                          registry: dict) -> tuple[str, list[str]]:
    """
    Build the full signals_payload string for a domain evaluation call.
    Returns (payload_text, list_of_signal_ids_included).
    """
    domain_signals = [
        (sid, sig) for sid, sig in registry["signals"].items()
        if sig.get("pipeline") == pipeline
        and sig.get("layer") == 1
        and sig.get("domain") == domain
    ]

    blocks: list[str] = []
    included: list[str] = []

    for sid, sig in sorted(domain_signals):
        sig_type = _signal_type(sig)
        if sig_type == "scan":
            block = _scan_payload(conn, sid, sig, pipeline, period)
        else:
            block = _scalar_payload(conn, sid, sig, pipeline, period)

        if block:
            blocks.append(block)
            included.append(sid)

    return "\n\n".join(blocks), included
