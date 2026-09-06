"""Single-entity move dominance — the guard against a reporting artifact reading as a market signal.

An aggregate can lurch because one member's *reported* number jumped, not because the market moved.
The clearest case in this data: ATM/POS terminals printed -15.8% YoY in Jun 2026 — but ~98% of that
drop was one issuer's terminal count falling in a single month; across every other bank the fleet was
flat-to-up. Narrating that aggregate as "the network is in structural collapse" is false: it is a base
or reporting change at one entity.

This module answers, deterministically from the per-bank scan already in signals.db, one question:
*how much of a metric's recent move is a single entity, and what did the aggregate do without it?* A
consumer (the insight layer, a tile, a newsletter line) uses `dominant` to swap a market narrative for
a grounded caveat. Everything here traces to `{metric}-bank-scan` rows — no new stored signal, no LLM.
"""
from __future__ import annotations
import re
import sqlite3
from dataclasses import dataclass, asdict
from pathlib import Path

DB = Path(__file__).resolve().parent / "signals.db"

# Bank names arrive ALL-CAPS ("ICICI BANK LTD"); render them readably while keeping true acronyms
# upper so we print "ICICI Bank", not "Icici Bank".
_ACRONYMS = {"ICICI", "HDFC", "SBI", "RBL", "IDBI", "IDFC", "UCO", "PNB", "DBS", "AU", "YES", "SBM"}


def short_entity(name: str | None) -> str | None:
    if not name:
        return name
    name = re.sub(r"\s+(?:LTD|LIMITED|LTD\.)\.?$", "", name.strip(), flags=re.I)
    return " ".join(w if w in _ACRONYMS else w.capitalize() for w in name.split())

# An aggregate scalar signal → the per-bank scan that decomposes it. Only metrics whose level is a
# per-entity count/stock can suffer a single-entity reporting jump, so only those are mapped.
SCAN_FOR = {
    "pos-terminals-yoy":  "pos-bank-scan",
    "cc-outstanding-yoy": "cc-bank-scan",
    "dc-outstanding-yoy": "dc-bank-scan",
}

# A ratio inherits its denominator's artifact: if POS terminals lurch at one issuer, UPI-QR-per-POS
# lurches with them even though the numerator barely moved. Map ratio → the metric to actually test.
RATIO_DENOMINATOR = {
    "upi-qr-per-pos": "pos-terminals-yoy",
}

# A move is "dominated" when one entity is most of the latest month-on-month change AND that change is
# material. 0.70 keeps ordinary market leadership (a big bank moving the needle a bit) out of scope; the
# artifact we care about sits far above it (ICICI was 0.977). 3% MoM keeps noise out.
DOMINANCE_SHARE = 0.70
MATERIAL_MOM_PCT = 3.0


@dataclass
class Dominance:
    metric: str
    scan_metric: str
    dominant: bool
    top_entity: str | None
    top_move_share: float | None   # top entity's share of the latest MoM change (signed, 0..~1)
    mom_pct: float | None          # aggregate month-on-month % change
    ex_top_yoy_pct: float | None   # aggregate YoY % EXCLUDING the top entity — the "rest of the market"
    agg_value: float | None        # the aggregate metric's own value at `period` (the headline number)
    period: str
    via_denominator: bool = False  # True when the flag is inherited from a ratio's denominator
    window: str = "mom"            # which window the dominance was found in: "mom" or "yoy"

    def as_facts(self) -> dict:
        return asdict(self)


def _scan(conn, pipeline, scan_metric):
    """{period: {entity_id: value}} for a bank scan, all periods."""
    out: dict[str, dict[str, float]] = {}
    for period, ent, val in conn.execute(
        "SELECT period, entity_id, value FROM signals "
        "WHERE pipeline=? AND metric_id=? AND entity_type='bank'",
        (pipeline, scan_metric),
    ):
        out.setdefault(period, {})[ent] = val
    return out


def _year_ago(period: str, periods: list[str]) -> str | None:
    """The scan period ~12 months before `period` (same month, prior year), if present."""
    y, m, d = period.split("-")
    target = f"{int(y) - 1}-{m}"
    return next((p for p in periods if p.startswith(target)), None)


def move_dominance(pipeline: str, agg_metric: str, period: str, conn=None) -> Dominance | None:
    """How concentrated is `agg_metric`'s recent move in a single entity, and what did the rest do?
    Returns None when the metric has no per-bank scan (nothing to decompose) or the history is too
    short to judge.

    Two windows are tested, because a guard only protects the window it measures. The original
    check was month-on-month, which flags the month a single issuer lurches — but a YoY metric
    carries that lurch for another eleven months. ICICI's POS reclassification landed in Jun 2026
    (97.7% of that month's move); by Jul 2026 the MoM move was an ordinary +1.1% while the headline
    still read -15.8% YoY, and the card published it as a market trend with no attribution. So the
    year window is tested too, and `window` records which test fired.
    """
    via_denominator = agg_metric in RATIO_DENOMINATOR
    base_metric = RATIO_DENOMINATOR.get(agg_metric, agg_metric)
    scan_metric = SCAN_FOR.get(base_metric)
    if not scan_metric:
        return None
    own = conn or sqlite3.connect(DB)
    try:
        scan = _scan(own, pipeline, scan_metric)
        periods = sorted(scan)
        if period not in scan or periods.index(period) == 0:
            return None
        cur = scan[period]
        prev = scan[periods[periods.index(period) - 1]]
        prev_total = sum(prev.values())
        if not prev_total:
            return None
        mom_pct = 100 * (sum(cur.values()) - prev_total) / prev_total

        def _top_of(base_scan):
            """The biggest mover between `base_scan` and `cur`, and its share of that move."""
            move = sum(cur.values()) - sum(base_scan.values())
            if not move:
                return None, None
            deltas = {b: cur.get(b, 0) - base_scan.get(b, 0) for b in set(cur) | set(base_scan)}
            t = max(deltas, key=lambda b: abs(deltas[b]))
            return t, deltas[t] / move

        # MoM window — the month of the lurch.
        mom_top, mom_share = _top_of(prev)
        mom_hit = (mom_share is not None and abs(mom_share) >= DOMINANCE_SHARE
                   and abs(mom_pct) >= MATERIAL_MOM_PCT)

        # YoY window — the eleven months in which the lurch keeps distorting the headline.
        ya = _year_ago(period, periods)
        yoy_top = yoy_share = yoy_pct = None
        if ya:
            base_total = sum(scan[ya].values())
            yoy_top, yoy_share = _top_of(scan[ya])
            if base_total:
                yoy_pct = 100 * (sum(cur.values()) - base_total) / base_total
        yoy_hit = (yoy_share is not None and abs(yoy_share) >= DOMINANCE_SHARE
                   and yoy_pct is not None and abs(yoy_pct) >= MATERIAL_MOM_PCT)

        # The month of the lurch reports as "mom" — the sharper, more local story. The trailing
        # months report as "yoy": same artifact, still in the headline, no longer in this month.
        if mom_hit:
            window, top, top_share, dominant = "mom", mom_top, mom_share, True
        elif yoy_hit:
            window, top, top_share, dominant = "yoy", yoy_top, yoy_share, True
        else:
            window, top, top_share, dominant = "mom", mom_top, mom_share, False

        ex_top_yoy = None
        if ya and top is not None:
            base = sum(v for b, v in scan[ya].items() if b != top)
            now = sum(v for b, v in cur.items() if b != top)
            if base:
                ex_top_yoy = 100 * (now / base - 1)
        agg_row = own.execute(
            "SELECT value FROM signals WHERE pipeline=? AND metric_id=? AND period=? "
            "AND entity_type IN ('aggregate','total') LIMIT 1", (pipeline, agg_metric, period)).fetchone()
        agg_value = agg_row[0] if agg_row else None
        return Dominance(agg_metric, scan_metric, dominant, top if dominant else None,
                         round(top_share, 4) if dominant and top_share is not None else None,
                         round(mom_pct, 2), round(ex_top_yoy, 2) if ex_top_yoy is not None else None,
                         round(agg_value, 2) if agg_value is not None else None, period,
                         via_denominator, window)
    finally:
        if conn is None:
            own.close()
