#!/usr/bin/env python3
"""
table_rows.py — one cut's parts, side by side (DASHBOARD_SPEC §17)
──────────────────────────────────────────────────────────────────
The dashboard rendered Layer 1 as ninety-six cards in generation order. A reader asking
"what is happening in industry" got the answer spread over nine of them. This assembles
the other shape: every part of one cut on one line, with the six Layer 1 families as
columns — which is the shape the mix post that actually worked was written in.

Two properties are worth stating because they are structural rather than remembered:

  * **The pairing rule stops being a rule.** A share of new money cannot appear without
    that part's speed and acceleration, because they are cells in the same row. The
    movement card had to enforce that in its builder; a table enforces it by existing.

  * **Numbers are rendered HERE and shipped as strings.** A browser that formats numbers
    is a publishing surface no validator can see. Each cell carries `display` (drawn, and
    what the gate checks) and `sort` (ordering only, never shown).
"""
from __future__ import annotations

from dataclasses import dataclass, asdict

# The row types a cut's signals write ALONGSIDE its parts. Shared with movement_cards'
# _NON_MEMBER for the same reason: a member is whatever is left once the bookkeeping rows
# are removed, so a new bookkeeping row must be named in one place, not two.
from core.movement_cards import _NON_MEMBER


@dataclass(frozen=True)
class Cell:
    """One number as it will be read, plus the raw value for ordering only."""
    display: str
    sort: float | None

    @staticmethod
    def of(value: float | None, fmt) -> "Cell | None":
        return None if value is None else Cell(fmt(value), value)


def _rs(v: float) -> str:
    """Indian units. A level is quoted in lakh crore once it is one — 61.97L reads, and
    6,196,921 does not.

    Small values keep two decimals: cash withdrawn at POS terminals is Rs 1.16 crore, and
    rounding that to "Rs 1 Cr" throws away most of what the number says. A format that is
    right for the largest row is not automatically right for the smallest.
    """
    if abs(v) >= 1e5:
        return f"₹{v / 1e5:,.2f}L Cr"
    if abs(v) < 100:
        return f"₹{v:,.2f} Cr"
    return f"₹{v:,.0f} Cr"


def _count(v: float) -> str:
    for div, suf in ((1e7, " crore"), (1e5, " lakh")):
        if abs(v) >= div:
            return f"{v / div:,.2f}{suf}"
    return f"{v:,.0f}"


# Rs thousands -> Rs crore is v x 1000 / 1e7, i.e. v / 1e4. It shipped as v / 100 and drew
# monthly ATM withdrawals as Rs 219 LAKH CRORE — the size of the entire bank credit book,
# for one month of cash at ATMs. Caught by reading the rendered number for plausibility, not
# by any check: every gate here verifies a number against its stored value, and the stored
# value was right. A unit conversion is the one place traceability cannot help.
UNIT_FMT = {"rs_cr": _rs, "count": _count, "transactions": _count,
            "rs_thousands": lambda v: _rs(v / 1e4)}

_pct = lambda v: f"{v:.1f}%"
_pp  = lambda v: f"{v:+.2f} pp"


def _rows(conn, pipeline, period, metric_id, entity_type=None):
    q = ("SELECT entity_id, value, unit FROM signals WHERE pipeline=? AND period=? AND metric_id=?"
         + (" AND entity_type=?" if entity_type else ""))
    args = (pipeline, period, metric_id) + ((entity_type,) if entity_type else ())
    return {e: (v, u) for e, v, u in conn.execute(q, args)}


def _member_type(conn, pipeline, period, metric_id) -> str | None:
    """The entity type this cut's PARTS carry — discovered from the rows, not declared.

    Read off the data for the same reason movement_cards does it: SIBC declares
    `compute.entity_type` and payments does not, so trusting the declaration would mean
    trusting a description only one pipeline keeps true.
    """
    row = conn.execute(
        "SELECT entity_type FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
        f"AND entity_type NOT IN ({','.join('?' * len(_NON_MEMBER))}) LIMIT 1",
        (pipeline, period, metric_id, *_NON_MEMBER)).fetchone()
    return row[0] if row else None


def _series(conn, pipeline, metric_id, entity_id, entity_type, n=8):
    """The last n readings for one part — the Run column. Ordered by period, values only;
    the periods are implicit in the sparkline and explicit when the row opens."""
    return [v for _, v in conn.execute(
        "SELECT period, value FROM signals WHERE pipeline=? AND metric_id=? AND entity_id=? "
        "AND entity_type=? ORDER BY period", (pipeline, metric_id, entity_id, entity_type))][-n:]


def build(conn, pipeline: str, period: str, stem: str, unit: str = "rs_cr",
          parent_yoy: str | None = None) -> dict | None:
    """One cut's table, or None when the cut has nothing to show this period.

    None is a real answer: a cut whose 12-month window is not yet available has no
    allocation rows, and a table of blanks is worse than no table.
    """
    size_id = f"{stem}-size-scan"
    etype = _member_type(conn, pipeline, period, size_id)
    if not etype:
        return None
    size = _rows(conn, pipeline, period, size_id, etype)
    if not size:
        return None

    growth_id = f"{stem}-yoy-scan"
    g_type = _member_type(conn, pipeline, period, growth_id) or etype
    growth = _rows(conn, pipeline, period, growth_id, g_type)
    pace   = _rows(conn, pipeline, period, f"{stem}-acceleration",
                   _member_type(conn, pipeline, period, f"{stem}-acceleration") or etype)
    alloc  = _rows(conn, pipeline, period, f"{stem}-allocation", "alloc")
    ofcut  = _rows(conn, pipeline, period, f"{stem}-allocation", "weight_now")
    ofbook = _rows(conn, pipeline, period, f"{stem}-share-of-credit-scan",
                   _member_type(conn, pipeline, period, f"{stem}-share-of-credit-scan") or etype)

    fmt = UNIT_FMT.get(unit, _count)
    val = lambda d, k: d[k][0] if k in d else None

    parts = []
    for name in sorted(size, key=lambda k: -size[k][0]):
        sz, gr = val(size, name), val(growth, name)
        # THE PAIRING RULE, enforced here rather than remembered. A share of the new money is
        # never drawn without the speed that explains it: alone, "took 25% of the growth" reads
        # as a verdict on the entity when it may only mean its peers grew faster. The one
        # exemption is a part with NO SIZE — Payment Banks holds zero cards since Paytm exited,
        # so there is no rate to pair with and a share of nothing asserts nothing.
        share = val(alloc, name) if (gr is not None or not sz) else None
        parts.append({
            "entity":  name,
            "size":    Cell.of(sz, fmt),
            "of_cut":  Cell.of(val(ofcut, name), _pct),
            "of_book": Cell.of(val(ofbook, name), _pct),
            "growth":  Cell.of(gr, _pct),
            "pace":    Cell.of(val(pace, name), _pp),
            "new":     Cell.of(share, _pct),
            "run":     [round(v, 4) for v in _series(conn, pipeline, growth_id, name, g_type)],
        })

    # The cut's own row: its total summed from the parts (the denominator `of_cut` uses),
    # and the parent's own growth and pace, which the cut's signals already store as
    # `aggregate`/`total`. A cut whose parent has no published rate loses those cells
    # rather than borrowing a part's.
    agg_size  = _rows(conn, pipeline, period, size_id, "aggregate").get("total")
    agg_pace  = _rows(conn, pipeline, period, f"{stem}-acceleration", "aggregate").get("total")
    # The parent's own growth is NOT one of the cut's signals — it belongs to the level above,
    # and the cut declares which signal that is (the same field the state band reads). Without
    # it the parent row shows a dash for Growth directly beneath a band stating the number,
    # which reads as broken rather than as absent.
    agg_growth = _rows(conn, pipeline, period, parent_yoy, "aggregate").get("total") if parent_yoy else None
    total = {
        "entity": None,
        "size":   Cell.of(agg_size[0] if agg_size else None, fmt),
        # NOT "100%": that is the definition of the denominator, not a measured value, and
        # a cell whose number traces to nothing is the thing every gate here exists to stop.
        "of_cut": None,
        "of_book": None,
        "growth": Cell.of(agg_growth[0] if agg_growth else None, _pct),
        "pace":   Cell.of(agg_pace[0] if agg_pace else None, _pp),
        "new": None, "run": [],
    }

    # What the `new` column MEANS depends on the sign of the net: a share of the growth, or a
    # share of the contraction. The band already says "took 25% of the contraction"; a column
    # headed "New" over the same rows contradicts it. Five debit-card categories shrank this
    # period under a header saying New.
    net = next((v for (v,) in conn.execute(
        "SELECT value FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
        "AND entity_type='aggregate' AND entity_id='total'",
        (pipeline, period, f"{stem}-momentum"))), None)
    flow_label = "Of fall" if (net is not None and net < 0) else "New"

    declared = [size_id, growth_id, f"{stem}-acceleration", f"{stem}-allocation",
                f"{stem}-share-of-credit-scan"] + ([parent_yoy] if parent_yoy else [])
    return {
        "cut": stem,
        "flow_label": flow_label,
        "parts": [{k: (asdict(v) if isinstance(v, Cell) else v) for k, v in p.items()} for p in parts],
        "total": {k: (asdict(v) if isinstance(v, Cell) else v) for k, v in total.items()},
        # Declared reads, so the gate scopes to this cut at this period rather than falling
        # back to period-wide — the fallback is how a traceability gate quietly dies.
        "source_signals": declared,
    }
