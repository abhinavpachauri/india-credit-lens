"""
Context builder for LLM evaluation.

Pulls signal values, prior-period values, range stats, and entity distributions
from signals.db and formats them into a compact text payload per domain.
"""

from __future__ import annotations
import json
import sqlite3
import sys
from functools import lru_cache
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ANALYSIS


# ── Period label translation ──────────────────────────────────────────────────
# SIBC keys signals.db by `dataDate` (the RBI fortnightly *release* date), which
# can fall ~1 month after the data month it reports. The compute layer maps
# dataDate→csv_date to pull the right *value*, but the DB period key stays the
# release date. When we render a period as a human month for the LLM we must
# show the DATA month (csv_date), not the release month — otherwise the model
# (and every downstream narrative) is off by one. Other pipelines key on the
# true data date, so this is an identity no-op for them.

_TIMELINES: dict[str, Path] = {
    "sibc": ANALYSIS / "rbi_sibc" / "timeline.json",
}


@lru_cache(maxsize=None)
def _datadate_to_csvdate(pipeline: str) -> dict[str, str]:
    path = _TIMELINES.get(pipeline)
    if not path or not path.exists():
        return {}
    try:
        data = json.loads(path.read_text())
    except Exception:
        return {}
    return {
        p["dataDate"]: p["csv_date"]
        for p in data.get("periods", [])
        if p.get("dataDate") and p.get("csv_date")
    }


def display_date(period: str, pipeline: str) -> str:
    """Translate a stored DB period key (release date) to the data month-end
    that should be SHOWN. No-op when the period is not in the lag map."""
    return _datadate_to_csvdate(pipeline).get(period, period)


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


def _range_stats(vals: list[float]) -> tuple | None:
    """Compute (min, max, p25, p75, count) over a value list. Returns None when
    empty; p25/p75 are None when there are too few points for quartiles."""
    if not vals:
        return None
    s = sorted(vals)
    n = len(s)
    if n >= 4:
        import statistics
        q = statistics.quantiles(s, n=4)   # [p25, median, p75]
        return s[0], s[-1], q[0], q[2], n
    return s[0], s[-1], None, None, n


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
    from datetime import datetime

    # csv_category_share signals are stored under entity_type='bank_category'
    # keyed by the category name from the compute spec, not as aggregate/total
    compute  = sig.get("compute", {})
    method   = compute.get("method", "")
    if method == "csv_category_share":
        entity_type = "bank_category"
        entity_id   = compute.get("category", "total")
    else:
        entity_type = "aggregate"
        entity_id   = "total"

    row = conn.execute(
        """SELECT s.value, s.unit, s.status, s.period
           FROM signals s
           WHERE s.pipeline=? AND s.period=? AND s.metric_id=?
             AND s.entity_type=? AND s.entity_id=?""",
        (pipeline, period, sig_id, entity_type, entity_id)
    ).fetchone()

    if row is None or row[0] is None:
        return None

    value, unit, status, _ = row[0], row[1], row[2], row[3]

    # Period history THROUGH the eval period — never future periods. An eval is
    # a point-in-time view; when re-running an old period after newer data has
    # landed, an unbounded query would leak future values into the trajectory and
    # confuse which month is "current".
    history_rows = conn.execute(
        """SELECT period, value FROM signals
           WHERE pipeline=? AND metric_id=?
             AND entity_type=? AND entity_id=?
             AND value IS NOT NULL AND period <= ?
           ORDER BY period""",
        (pipeline, sig_id, entity_type, entity_id, period)
    ).fetchall()

    # Prior period value (still needed for delta)
    prior_value = None
    for i, (p, v) in enumerate(history_rows):
        if p == period and i > 0:
            prior_value = history_rows[i - 1][1]
            break

    delta = (value - prior_value) if prior_value is not None else None

    # Range stats — computed over the same period-bounded history, so the period
    # count and min/max/position reflect the eval period, not the global series.
    _hv = [v for _, v in history_rows if v is not None]
    rng = _range_stats(_hv)

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

    # Annual second-order metrics (e.g. FY acceleration) are period-invariant —
    # they only change at each March year-end, so a prior-period delta, a
    # per-period series, and a historical range are all meaningless and invite a
    # fabricated "jump" narrative. Surface the underlying component rates instead,
    # which make the value interpretable and traceable to its inputs.
    is_annual = bool(sig.get("compute", {}).get("annual"))

    if is_annual:
        comp = conn.execute(
            """SELECT entity_id, value FROM signals
               WHERE pipeline=? AND period=? AND metric_id=?
                 AND entity_type='fy_yoy' AND value IS NOT NULL
               ORDER BY entity_id""",
            (pipeline, period, sig_id)
        ).fetchall()
        if len(comp) >= 2:
            def _fy(d: str) -> str:
                try:    return datetime.strptime(d, "%Y-%m-%d").strftime("%b %Y")
                except: return d
            parts = ", ".join(f"year ending {_fy(d)} grew {v:.1f}%" for d, v in comp)
            lines.append(f"FY components: {parts} (acceleration = {value:+.1f}pp)")
        lines.append("Note: annual metric — set at each March year-end; it does NOT change month to month, so do not describe it as a per-period jump/surge/plateau.")
    else:
        lines.append(f"Prior period: {pvstr} | Change: {dstr}")

        # Full chronological series — lets the LLM write multi-period trajectories
        if len(history_rows) > 1:
            def _fmt_v(v: float) -> str:
                if unit == "pct":                   return f"{v:.1f}%"
                if unit in ("lcr_cr", "rs_thousands"): return f"{v:,.0f} {unit}"
                if unit == "pp":                    return f"{v:.1f}pp"
                if unit == "periods":               return f"{int(v)} periods"
                if unit == "count":                 return f"{v:,.0f}"
                if unit == "ratio":                 return f"{v:.1f}x"
                return f"{v:,.1f}"

            def _fmt_p(p: str) -> str:
                disp = display_date(p, pipeline)
                try:    return datetime.strptime(disp, "%Y-%m-%d").strftime("%b %Y")
                except: return disp

            series = " → ".join(
                f"{_fmt_p(p)}: {_fmt_v(v)}" for p, v in history_rows
            )
            lines.append(f"Series: {series}")

    if rng and not is_annual:
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

    # Full distribution — every entity value, so the narrative can cite any real
    # figure (and never has to invent one for a middle entity).
    all_str = "; ".join(f"{r[0]} {_fmt(r[1])}({r[2][0].upper()})" for r in rows)

    lines = [
        f"--- {sig_id} [type: {sig_type}] ---",
        f"Title: {title}",
        f"Distribution: {n} entities | {status_summary}",
        f"All entities (ranked, cite ONLY these values): {all_str}",
        f"Spread: {_fmt(spread)}",
    ]
    if changed:
        lines.append(f"Status shifts: {'; '.join(changed[:5])}")

    return "\n".join(lines)


# ── Ground-truth numbers (traceability) ───────────────────────────────────────

def signal_numbers(conn: sqlite3.Connection, sid: str, sig: dict,
                   pipeline: str, period: str) -> dict:
    """Return the numbers a signal legitimately produced for `period` — the
    ground truth an insight/chain may cite. Used both to attach source.values
    to an annotation and to validate that narrative text invents no figure.
    Mirrors the fetches in _scalar_payload / _scan_payload."""
    method = sig.get("compute", {}).get("method", "")
    stype  = _signal_type(sig)
    facts: dict = {"unit": None, "value": None, "prior": None, "status": None,
                   "series": [], "components": {}, "range": {}, "scan": []}

    if stype == "scan":
        rows = conn.execute(
            "SELECT entity_id, value FROM signals "
            "WHERE pipeline=? AND period=? AND metric_id=? AND value IS NOT NULL",
            (pipeline, period, sid)).fetchall()
        vals = [r[1] for r in rows]
        facts["scan"] = vals
        if len(vals) >= 2:
            facts["range"] = {"min": min(vals), "max": max(vals)}
            facts["spread"] = max(vals) - min(vals)
        ur = conn.execute(
            "SELECT unit FROM signals WHERE pipeline=? AND period=? AND metric_id=? LIMIT 1",
            (pipeline, period, sid)).fetchone()
        facts["unit"] = ur[0] if ur else None
        return facts

    if method == "csv_category_share":
        etype, eid = "bank_category", sig.get("compute", {}).get("category", "total")
    else:
        etype, eid = "aggregate", "total"

    row = conn.execute(
        "SELECT value, unit, status FROM signals "
        "WHERE pipeline=? AND period=? AND metric_id=? AND entity_type=? AND entity_id=?",
        (pipeline, period, sid, etype, eid)).fetchone()
    if row:
        facts["value"], facts["unit"], facts["status"] = row

    hist = conn.execute(
        "SELECT period, value FROM signals "
        "WHERE pipeline=? AND metric_id=? AND entity_type=? AND entity_id=? "
        "AND value IS NOT NULL AND period <= ? ORDER BY period",
        (pipeline, sid, etype, eid, period)).fetchall()
    facts["series"] = [v for _, v in hist]
    for i, (p, _v) in enumerate(hist):
        if p == period and i > 0:
            facts["prior"] = hist[i - 1][1]
            break
    rng = _range_stats([v for v in facts["series"] if v is not None])
    if rng:
        mn, mx, p25, p75, n = rng
        facts["range"] = {"min": mn, "max": mx, "p25": p25, "p75": p75, "count": n}

    # Component rows (e.g. the two fy_yoy rates behind an acceleration).
    for et, eid2, v in conn.execute(
        "SELECT entity_type, entity_id, value FROM signals "
        "WHERE pipeline=? AND period=? AND metric_id=? "
        "AND entity_type NOT IN ('aggregate','bank_category') AND value IS NOT NULL",
        (pipeline, period, sid)).fetchall():
        facts["components"][f"{et}:{eid2}"] = v
    return facts


def scan_distribution(conn: sqlite3.Connection, sid: str,
                      pipeline: str, period: str) -> list[tuple]:
    """Full ranked distribution for a scan signal: [(entity_id, value, status)]
    sorted high→low. Source for deterministic scan insight generation."""
    return [(r[0], r[1], r[2]) for r in conn.execute(
        "SELECT entity_id, value, status FROM signals "
        "WHERE pipeline=? AND period=? AND metric_id=? AND value IS NOT NULL "
        "ORDER BY value DESC", (pipeline, period, sid)).fetchall()]


def flat_numbers(facts: dict) -> list[float]:
    """All legitimate numbers from signal_numbers(), including the common derived
    values an insight may legitimately state (period delta; pairwise component
    differences such as fy_latest - fy_prior = acceleration).

    Unit-aware: lcr_cr values are stored raw (crore) but always displayed in lakh
    crore (÷1e5), so monetary numbers are emitted at the display scale. Component
    rates (their own unit, e.g. pct) and the period count are dimensionless here
    and are not scaled."""
    scale = 1e5 if facts.get("unit") == "lcr_cr" else 1.0

    mono: list[float] = []   # numbers in the signal's own (monetary/level) unit
    for k in ("value", "prior"):
        if facts.get(k) is not None:
            mono.append(float(facts[k]))
    mono += [float(v) for v in facts.get("series", []) if v is not None]
    mono += [float(v) for v in facts.get("scan", [])]
    # Scan distribution derived values an insight may legitimately state:
    #   cumulative top-k sums ("top N hold X%"), entity counts ("4 sub-sectors"),
    #   and the mean ("averaging around X%").
    sc = sorted((float(v) for v in facts.get("scan", [])), reverse=True)
    cum = 0.0
    for v in sc:
        cum += v
        mono.append(cum)
    if sc:
        mono += [float(i) for i in range(1, len(sc) + 1)]   # counts of entities
        mono.append(sum(sc) / len(sc))                      # mean
    r = facts.get("range", {})
    mono += [float(v) for v in (r.get("min"), r.get("max"), r.get("p25"), r.get("p75")) if v is not None]
    if "spread" in facts:
        mono.append(float(facts["spread"]))
    if facts.get("value") is not None and facts.get("prior") is not None:
        d = float(facts["value"]) - float(facts["prior"])
        mono += [d, abs(d)]

    nums = [m / scale for m in mono]

    comps = [float(v) for v in facts.get("components", {}).values()]   # own unit (e.g. pct)
    nums += comps
    for i in range(len(comps)):
        for j in range(len(comps)):
            if i != j:
                nums.append(comps[i] - comps[j])

    if r.get("count"):                       # dimensionless period count
        nums.append(float(r["count"]))
    return nums


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


def build_chunk_payload(signal_ids: list[str], full_payload: str,
                        chunk_size: int) -> list[tuple[str, list[str]]]:
    """
    Split a full domain payload (already built by build_domain_payload) into
    chunks of at most chunk_size signal blocks, preserving block boundaries.

    Each block starts with '--- <signal_id> [type: ...] ---'.
    Returns list of (chunk_payload_text, chunk_signal_ids).
    """
    if not signal_ids:
        return []

    # Split payload back into individual blocks
    import re
    raw_blocks = re.split(r'\n(?=--- )', full_payload)

    # Map each block to its signal_id (first line prefix)
    id_to_block: dict[str, str] = {}
    for block in raw_blocks:
        first_line = block.split("\n")[0]
        # extract signal_id from '--- sibc-xxx [type: yyy] ---'
        m = re.match(r'^--- (\S+) \[', first_line)
        if m:
            id_to_block[m.group(1)] = block

    # Build chunks in the order signal_ids were provided
    chunks: list[tuple[str, list[str]]] = []
    for i in range(0, len(signal_ids), chunk_size):
        chunk_ids = signal_ids[i : i + chunk_size]
        chunk_blocks = [id_to_block[sid] for sid in chunk_ids if sid in id_to_block]
        if chunk_blocks:
            chunks.append(("\n\n".join(chunk_blocks), chunk_ids))

    return chunks if chunks else [(full_payload, signal_ids)]
