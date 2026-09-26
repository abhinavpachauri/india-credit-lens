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
    """One number as it will be read, the raw value for ordering only, and the whole series
    it is the latest reading of.

    Every cell in this table is the top of a stored series — that is what the table IS, and
    it is why a cell can open its own chart. The history ships WITH the cell rather than
    being fetched per click: the browser already holds the file, and a second round trip to
    draw eleven numbers it could have been handed is a request nobody needs to make.

    `series` is aligned to the column's own period list, with null where a part has no
    reading — an entity that arrived late must not silently slide its history a month left.
    `series_display` is that same history rendered, because the panel a cell opens QUOTES its
    readings — in a tooltip and in the run of numbers under the line. A browser formatting
    those would be the second formatter this project keeps paying for; the strings compress
    to almost nothing over the wire and cost nothing to be right.
    """
    display: str
    sort: float | None
    series: list[float | None] | None = None
    series_display: list[str | None] | None = None

    @staticmethod
    def of(value: float | None, fmt, series: list[float | None] | None = None) -> "Cell | None":
        if value is None:
            return None
        shown = None if series is None else [None if v is None else fmt(v) for v in series]
        return Cell(fmt(value), value, series, shown)


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


def _history(conn, pipeline, metric_id, entity_type):
    """{entity_id: {period: value}} — every reading this signal holds, for every part.

    ONE query per column rather than one per cell: a cut has up to thirty parts and six
    columns, and a hundred and eighty round trips to SQLite to build one table is a cost
    paid on every gate run for no reason.
    """
    out: dict[str, dict[str, float]] = {}
    for eid, period, v in conn.execute(
            "SELECT entity_id, period, value FROM signals WHERE pipeline=? AND metric_id=? "
            "AND entity_type=? AND value IS NOT NULL ORDER BY period",
            (pipeline, metric_id, entity_type)):
        out.setdefault(eid, {})[period] = v
    return out


def _periods_of(hist: dict[str, dict[str, float]]) -> list[str]:
    """The column's own period list — the union over its parts, sorted.

    A column's depth is its OWN, not the table's: payments stores thirty-one readings of a
    level and nineteen of its YoY, because a year-on-year rate cannot exist until a year has
    passed. One axis for the whole table would have to either invent the missing readings or
    throw away the ones that exist.
    """
    return sorted({p for rows in hist.values() for p in rows})


def _label(period: str, pipeline: str) -> str:
    """The month a reading is ABOUT, as a chart axis will show it.

    SIBC keys the store by RBI's release date, which can fall a month after the data it
    reports; every other surface translates before showing it and so does this one. An axis
    tick is a published number like any other — rendered here, never in a browser.
    """
    from signals.query import display_date
    d = display_date(period, pipeline)
    return f"{_MONTH[int(d[5:7]) - 1]} {d[2:4]}" if len(d) >= 7 and d[5:7].isdigit() else d


_MONTH = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _aligned(hist, entity_id, periods):
    rows = hist.get(entity_id) or {}
    vals = [rows.get(p) for p in periods]
    return [None if v is None else round(v, 4) for v in vals] if any(v is not None for v in vals) else None


def build(conn, pipeline: str, period: str, stem: str, unit: str = "rs_cr",
          parent_yoy: str | None = None, sub_cuts: dict[str, str] | None = None,
          signals: dict[str, str] | None = None) -> dict | None:
    """One cut's table, or None when the cut has nothing to show this period.

    None is a real answer: a cut whose 12-month window is not yet available has no
    allocation rows, and a table of blanks is worse than no table.

    `signals` DECLARES which signal fills which column, for a cut whose ids do not follow the
    stem convention — a bank breakout, whose scan has been called `{metric}-bank-scan` since
    the first ingestion. Deriving an id from a stem is a spelling rule, and a spelling rule is
    what hid three payments tables from the dashboard this week; a cut that can declare is
    better than a cut that must be spelled correctly.
    """
    sid = lambda col, default: (signals or {}).get(col, default)
    size_id = sid("size", f"{stem}-size-scan")
    etype = _member_type(conn, pipeline, period, size_id)
    if not etype:
        return None
    size = _rows(conn, pipeline, period, size_id, etype)
    if not size:
        return None

    growth_id = sid("growth",  f"{stem}-yoy-scan")
    book_id   = sid("of_book", f"{stem}-share-of-credit-scan")
    accel_id  = sid("pace",    f"{stem}-acceleration")
    alloc_id  = sid("alloc",   f"{stem}-allocation")
    g_type = _member_type(conn, pipeline, period, growth_id) or etype
    a_type = _member_type(conn, pipeline, period, accel_id) or etype
    b_type = _member_type(conn, pipeline, period, book_id) or etype

    # ── Each column, with its whole history ──────────────────────────────────────────
    # (metric, entity_type, the aggregate row that belongs to the parent). A column is read
    # once, for every part and every period it holds; the latest reading is the cell and the
    # rest is what the cell opens into.
    COLS = {
        "size":    (size_id,  etype,        ("aggregate", "total")),
        # `of_cut` is normally the allocation's `weight_now` — the share over the SUM of the
        # parts, which is what makes the Mix reading like-for-like. A cut that has no
        # allocation (a bank breakout has no 12-month movement window) declares a share scan
        # instead, whose denominator is the published total; the two answer the same question
        # over different denominators, which is why the source is declared and not assumed.
        "of_cut":  ((signals or {}).get("of_cut", alloc_id),
                    "bank" if (signals or {}).get("of_cut") else "weight_now", None),
        "of_book": (book_id,  b_type,       ("aggregate", "total")),
        "growth":  (growth_id, g_type,      None),
        "pace":    (accel_id, a_type,       ("aggregate", "total")),
        "new":     (alloc_id, "alloc",      None),
    }
    for c, (mid, et, agg) in list(COLS.items()):
        if et == "bank":                     # a declared share scan carries the member type
            COLS[c] = (mid, _member_type(conn, pipeline, period, mid) or et, agg)
    hist    = {c: _history(conn, pipeline, mid, et) for c, (mid, et, _) in COLS.items()}
    periods = {c: _periods_of(h) for c, h in hist.items()}
    # The parent's growth is NOT one of this cut's signals — it belongs to the level above,
    # which the cut declares (the same field the state band reads).
    # The parent of a BANK breakout is the metric's own total, which no bank scan stores —
    # sixty-four banks are the parts, and the whole is published separately. Declared, so the
    # parent row reads the same total the category table's parent row reads.
    agg_size_id = sid("total_size", size_id)
    par_hist = {
        "growth":  _history(conn, pipeline, parent_yoy, "aggregate") if parent_yoy else {},
        "size":    _history(conn, pipeline, agg_size_id, "aggregate"),
        "pace":    _history(conn, pipeline, accel_id, "aggregate"),
        "of_book": _history(conn, pipeline, book_id,  "aggregate"),
    }
    par_periods = {c: _periods_of(h) for c, h in par_hist.items()}

    fmt = UNIT_FMT.get(unit, _count)
    FMT = {"size": fmt, "of_cut": _pct, "of_book": _pct,
           "growth": _pct, "pace": _pp, "new": _pct}
    def at(col, name):
        return hist[col].get(name, {}).get(period)

    parts = []
    for name in sorted(size, key=lambda k: -size[k][0]):
        sz, gr = at("size", name), at("growth", name)
        # THE PAIRING RULE, enforced here rather than remembered. A share of the new money is
        # never drawn without the speed that explains it: alone, "took 25% of the growth" reads
        # as a verdict on the entity when it may only mean its peers grew faster. The one
        # exemption is a part with NO SIZE — Payment Banks holds zero cards since Paytm exited,
        # so there is no rate to pair with and a share of nothing asserts nothing.
        drop_new = not (gr is not None or not sz)
        row = {
            "entity":  name,
            # The cut this part decomposes into, when it has one (§19). Resolved HERE — code to
            # CSV name to row entity is a mapping the compute layer already holds, and doing it
            # again in a browser would be a second implementation of it.
            "sub_cut": (sub_cuts or {}).get(name),
        }
        for col in COLS:
            v = None if (col == "new" and drop_new) else at(col, name)
            row[col] = Cell.of(v, FMT[col], _aligned(hist[col], name, periods[col]))
        parts.append(row)

    # The cut's own row: its total summed from the parts (the denominator `of_cut` uses), the
    # parent's own growth, pace and — since this build — its share of the book. A cut whose
    # parent has no published rate loses those cells rather than borrowing a part's.
    # The pinned row IS the parent, so its size is the parent's own published row wherever the
    # scan stores one. The sum of the parts (`total`) is only the parent on a cut whose parts
    # are the whole; on an "of which" cut it put ₹7.38L Cr beside a pinned "NBFCs" that the
    # table one level up shows at ₹21.28L Cr, next to a share and a growth that were NBFCs'.
    # Each pinned cell declares the row it came from, so the gate checks that row and no other.
    own = "parent" if par_hist["size"].get("parent", {}).get(period) is not None else "total"
    parent_entities = {c: "total" for c in COLS}
    parent_entities["size"] = own
    total = {"entity": None}
    for col in COLS:
        agg = COLS[col][2]
        if not agg or col not in par_hist:
            # NOT "100%" for of_cut: that is the definition of the denominator, not a measured
            # value, and a cell whose number traces to nothing is what every gate here stops.
            total[col] = None
            continue
        h, eid = par_hist[col], parent_entities[col]
        total[col] = Cell.of(h.get(eid, {}).get(period), FMT[col],
                             _aligned(h, eid, par_periods[col]))
    total["growth"] = Cell.of(
        par_hist["growth"].get("total", {}).get(period), _pct,
        _aligned(par_hist["growth"], "total", par_periods["growth"])) if parent_yoy else None

    # What the `new` column MEANS depends on the sign of the net: a share of the growth, or a
    # share of the contraction. The band already says "took 25% of the contraction"; a column
    # headed "New" over the same rows contradicts it. Five debit-card categories shrank this
    # period under a header saying New.
    net = next((v for (v,) in conn.execute(
        "SELECT value FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
        "AND entity_type='aggregate' AND entity_id='total'",
        (pipeline, period, f"{stem}-momentum"))), None)
    flow_label = "Of fall" if (net is not None and net < 0) else "New"

    # COVERAGE — what fraction of this cut the parts RBI actually names add up to. Shipped so
    # the table can SAY it: without the line, four rows under a heading imply a complete
    # decomposition, and on an "of which" cut they are not one. The number is the stored
    # `coverage` row (signals/README.md, the denominator rule), never recomputed here and
    # never typed into a component — SIBC's main table carried a hand-written "95.1%" in the
    # browser, which is a published number no gate could see.
    coverage = next((v for (v,) in conn.execute(
        "SELECT value FROM signals WHERE pipeline=? AND period=? AND metric_id=? "
        "AND entity_type='coverage' AND entity_id='total'",
        (pipeline, period, f"{stem}-allocation"))), None)

    declared = sorted({size_id, growth_id, accel_id, alloc_id, book_id, COLS["of_cut"][0]}
                      | ({parent_yoy} if parent_yoy else set()))
    cells = lambda r: {k: (asdict(v) if isinstance(v, Cell) else v) for k, v in r.items()}
    return {
        "cut": stem,
        "flow_label": flow_label,
        # None when the parts ARE the whole — a line saying "these are 100.0% of the cut"
        # every month is noise, and its absence is the honest signal that nothing is missing.
        "coverage": None if coverage is None else round(coverage, 1),
        "parts": [cells(p) for p in parts],
        "total": cells(total),
        # WHICH SIGNAL EACH COLUMN IS, declared for the gate. Scoping a growth cell to the
        # union of the cut's signals would let a share pass as a rate; scoping it to the
        # growth signal is the check §17.5 was asking for and did not have.
        # Only the columns that actually carry a cell: a declared cut names the signals it
        # has, and listing one it does not would be a mapping to nothing.
        "columns": {c: COLS[c][0] for c in COLS
                    if total.get(c) or any(p.get(c) for p in parts)},
        "parent_columns": {c: (parent_yoy if c == "growth"
                               else agg_size_id if c == "size" else COLS[c][0])
                           for c in ("size", "pace", "of_book", "growth") if total.get(c)},
        "parent_entities": {c: parent_entities[c] for c in ("size", "pace", "of_book", "growth")
                            if total.get(c)},
        # The x-axis of every cell chart, rendered here like every other string. Per column,
        # because a column's depth is its own; `parent` where the parent row's history runs
        # over a different period set than the parts'.
        "periods": {c: [_label(p, pipeline) for p in ps] for c, ps in periods.items() if ps},
        "parent_periods": {c: [_label(p, pipeline) for p in ps]
                           for c, ps in par_periods.items() if ps and total.get(c)},
        # Declared reads, so the gate scopes to this cut at this period rather than falling
        # back to period-wide — the fallback is how a traceability gate quietly dies.
        "source_signals": declared,
    }
