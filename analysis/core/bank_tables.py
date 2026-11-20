"""
core/bank_tables.py — what a per-bank table needs beyond the cut table itself
──────────────────────────────────────────────────────────────────────────────
A per-bank pipeline (payments, bank-wise credit) ships tables whose parts are banks. Four things
apply to those tables and no other, and each is one generic mechanism keyed by what a pipeline
declares, never by its name (BANKWISE_SPEC §8b, DECISIONS 2026-11-20):

  * small_base — a bank ranks by growth only off a base of ≥ MIN_BASE_SHARE of the total a year
    earlier. Below it the growth still shows, marked, and sorts last. A selection rule, not a
    signal, so it lives here and nothing is stored.
  * flags — a (quarter, bank, metric) where RBI's own figures fail its own check is left out of
    every reading it feeds, with its reason (`{data_dir}/inconsistencies.json`).
  * markers — a declared merger (`series_breaks.json`, statement `bank`) is named on the chart
    where its growth gap is, so a gap never reads as broken.
  * books — each bank's own credit, line by line, as a table of its own fetched when its row
    opens (`{pipeline}_banks/book/{bank}.json`), for a pipeline whose cuts module declares BOOK.

    Every function takes the table dict the stamp built and edits it in place.
"""
from __future__ import annotations

import json
from datetime import date

from core import absence, manifest, table_rows
from core.paths import ROOT

MIN_BASE_SHARE = 0.25            # % of the total a year earlier (user, 2026-11-20)
SMALL_BASE_NOTE = (f"·sb small base: growth off under {MIN_BASE_SHARE}% of the total a year "
                   f"earlier. Shown, sorted last.")
LEVEL_COLS = ("size", "of_cut", "of_book", "gnpa")     # a reading of one quarter
CHANGE_COLS = ("growth", "new")                          # a comparison with a year earlier
_MON = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")


def _year_before(period: str) -> str:
    """The month-end a year before a month-end (a quarter-end stays a quarter-end)."""
    y, m, _ = (int(x) for x in period.split("-"))
    from calendar import monthrange
    return f"{y - 1}-{m:02d}-{monthrange(y - 1, m)[1]:02d}"


def _long(d: str) -> str:
    return f"{_MON[int(d[5:7]) - 1]} {d[:4]}"


# ── small base ────────────────────────────────────────────────────────────────────────────────

def mark_small_base(conn, pipeline: str, period: str, t: dict, signals: dict) -> None:
    """Mark each bank whose book a year earlier was under MIN_BASE_SHARE of the total.

    The total a year earlier is the metric's published total (the same row the table's pinned
    size reads); the sum of the banks stands in only where none is stored. A bank with no
    reading a year earlier has no growth to rank, so it is never marked.
    """
    prior = _year_before(period)
    size = table_rows._history(conn, pipeline, signals["size"], "bank")
    base = {e: rows.get(prior) for e, rows in size.items()}
    total = None
    if signals.get("total_size"):
        total = table_rows._history(conn, pipeline, signals["total_size"], "aggregate") \
            .get("total", {}).get(prior)
    total = total or sum(v for v in base.values() if v)
    if not total:
        return
    marked = 0
    for p in t["parts"]:
        b = base.get(p["entity"])
        if b and 100.0 * b / total < MIN_BASE_SHARE and (p.get("growth") or p.get("pace")):
            p["small_base"] = True
            marked += 1
    t.pop("unsortable", None)                      # the rule exists, so growth sorts again
    if marked:
        t["notes"] = [*t.get("notes", []), SMALL_BASE_NOTE]


# ── flags ─────────────────────────────────────────────────────────────────────────────────────

def _flag_index(pipeline: str) -> dict[tuple[str, str], set[str]]:
    """{(bank, metric): {quarter}} for every bank-level flag; empty where none is declared."""
    paths = manifest.load(pipeline).get("paths", {})
    if "inconsistencies" not in paths:
        return {}
    out: dict[tuple[str, str], set[str]] = {}
    for f in json.loads((ROOT / paths["inconsistencies"]).read_text())["flags"]:
        if f["entity"].startswith("group:") or " " not in f["column"]:
            continue
        metric = f["column"].replace(" ", ".", 1)
        out.setdefault((f["entity"], metric), set()).add(f["quarter"])
    return out


def is_flagged(pipeline: str, bank: str, metric: str, quarter: str) -> bool:
    """For the gate: does the declared record list this cell?"""
    return quarter in _flag_index(pipeline).get((bank, metric), set())


def _touched(q: str, col: str, dates: list[str]) -> set[str]:
    """The readings in `col` a flagged quarter feeds. A level is that quarter; a change compares
    two dates a year apart, so it is the quarter and the one a year on; a pace is a change and
    the change before it, so each of those and the period after."""
    if col in LEVEL_COLS:
        return {q}
    later = next((d for d in dates if d[:7] == f"{int(q[:4]) + 1}{q[4:7]}"), None)
    ends = {q} | ({later} if later else set())
    if col in CHANGE_COLS:
        return ends
    nxt = {dates[dates.index(e) + 1] for e in ends if e in dates and dates.index(e) + 1 < len(dates)}
    return ends | nxt


def apply_flags(conn, pipeline: str, period: str, t: dict, metric: str,
                denominator: str | None) -> None:
    """Leave flagged readings out of a bank table: nulled in each history, and the latest cell
    shown as "—" with its reason. A flag on the denominator (a bank's whole book) touches only
    the share of that book."""
    idx = _flag_index(pipeline)
    if not idx:
        return
    for p in t["parts"]:
        own = idx.get((p["entity"], metric), set())
        den = idx.get((p["entity"], denominator), set()) if denominator else set()
        if not own and not den:
            continue
        for col, sid in (t.get("columns") or {}).items():
            cell = p.get(col)
            qs = own | (den if col == "of_book" else set())
            if not cell or not qs:
                continue
            et = table_rows._member_type(conn, pipeline, period, sid) or "bank"
            dates = table_rows._periods_of(table_rows._history(conn, pipeline, sid, et))
            hit = set().union(*(_touched(q, col, dates) for q in qs))
            series = cell.get("series") or []
            for i, d in enumerate(dates[:len(series)]):
                if d in hit:
                    series[i] = None
                    if cell.get("series_display"):
                        cell["series_display"][i] = None
            if period in hit:
                p[col] = {"display": "—", "sort": None, "series": cell.get("series"),
                          "series_display": cell.get("series_display"),
                          "reason": "flagged_inconsistent",
                          "note": f"{_long(period)}: {absence.PER_PERIOD['flagged_inconsistent']}."}
        for q in sorted(own):
            p.setdefault("markers", []).append(
                {"at": table_rows._label(q, pipeline), "kind": "flag",
                 "text": f"{_long(q)}: {absence.PER_PERIOD['flagged_inconsistent']}."})


# ── merger markers ────────────────────────────────────────────────────────────────────────────

def _breaks(pipeline: str) -> list[dict]:
    f = ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "series_breaks.json"
    return json.loads(f.read_text())["breaks"] if f.exists() else []


def _merger_markers(pipeline: str, dates: list[str]) -> dict[str, list[dict]]:
    """{line code: its merger markers}: each declared merger, at the first reading on or after it."""
    out: dict[str, list[dict]] = {}
    for b in _breaks(pipeline):
        at = next((d for d in dates if d >= b["effective"]), None)
        if not b.get("label") or at is None:
            continue
        text = (f"{_long(b['effective'])}: {b['label']}. Growth across it is left out (it would "
                f"count the merged book as growth); size keeps the jump.")
        for line in b["lines"]:
            if line.get("statement") == "bank":
                out.setdefault(line["code"], []).append(
                    {"at": table_rows._label(at, pipeline), "kind": "merger", "text": text})
    return out


def add_markers(conn, pipeline: str, t: dict) -> None:
    """Name each declared merger on the rows it touched (a bank, a group, the total)."""
    sid = (t.get("columns") or {}).get("size")
    if not sid or not _breaks(pipeline):
        return
    dates = sorted({p for (p,) in conn.execute(
        "SELECT DISTINCT period FROM signals WHERE pipeline=? AND metric_id=?", (pipeline, sid))})
    marks = _merger_markers(pipeline, dates)
    for row in [*t["parts"], t["total"]]:
        code = "total" if row is t["total"] else row["entity"]
        if code in marks:
            row.setdefault("markers", []).extend(marks[code])


# ── each bank's own book ──────────────────────────────────────────────────────────────────────

def _book_lines(pipeline: str):
    import importlib
    cm = manifest.load(pipeline).get("cuts_module")
    return getattr(importlib.import_module(cm), "BOOK", None) if cm else None


def books(conn, pipeline: str, period: str, reg: dict) -> dict[str, dict]:
    """{bank: its book as a table}: one row per declared line (BOOK, in the cuts module), its
    size, share of the bank's book, growth and pace, each with its stored history. The pinned
    row is the bank's whole book. Rows carry their own column→signal map, because each row is a
    different signal for the same bank (the gate reads it per row)."""
    lines = _book_lines(pipeline)
    if not lines:
        return {}
    by = {}                                        # (metric, method, value_type) -> signal id
    for sid, s in reg.items():
        c = s.get("compute", {})
        if s.get("pipeline") == pipeline and c.get("metric") and not c.get("table_column"):
            by[(c["metric"], c["method"], c.get("value_type", "value"))] = sid
    COL = {"size": ("csv_bank_scan", "value"), "of_book": ("csv_bank_ratio_scan", "value"),
           "growth": ("csv_bank_scan", "yoy"), "pace": ("csv_bank_acceleration", "value")}
    FMT = {"size": table_rows._rs, "of_book": table_rows._pct, "growth": table_rows._pct,
           "pace": table_rows._pp}

    hist, sigs = {}, {}
    for ln in [{"metric": lines["whole"], "label": None}] + lines["lines"]:
        for col, (meth, vt) in COL.items():
            sid = by.get((ln["metric"], meth, vt))
            if sid:
                sigs[(ln["metric"], col)] = sid
                hist[sid] = table_rows._history(conn, pipeline, sid, "bank")
    periods = {col: sorted({d for (m, c), sid in sigs.items() if c == col
                            for rows in hist[sid].values() for d in rows})
               for col in COL}
    labels = {col: [table_rows._label(d, pipeline) for d in ds] for col, ds in periods.items()}

    def row(metric: str, bank: str) -> tuple[dict, dict]:
        out, cols = {}, {}
        for col in COL:
            sid = sigs.get((metric, col))
            if not sid:
                out[col] = None
                continue
            rows = hist[sid].get(bank, {})
            series = [None if rows.get(d) is None else round(rows[d], 4) for d in periods[col]]
            cell = table_rows.Cell.of(rows.get(period), FMT[col],
                                      series if any(v is not None for v in series) else None)
            out[col] = None if cell is None else cell.__dict__
            if cell is not None:
                cols[col] = sid
        return out, cols

    whole_size = sigs[(lines["whole"], "size")]
    marks = _merger_markers(pipeline, periods["size"])   # a bank's merger touches every line
    out = {}
    for bank, rows in hist[whole_size].items():
        if period not in rows:
            continue
        total, tcols = row(lines["whole"], bank)
        total["entity"] = None
        whole = (total.get("size") or {}).get("display")
        parts = []
        for ln in lines["lines"]:
            r, cols = row(ln["metric"], bank)
            if not cols:
                continue
            parts.append({"entity": ln["label"], "sub_cut": None, "indent": ln.get("indent", 0),
                          **r, "columns": cols,
                          **({"markers": marks[bank]} if bank in marks else {})})
        if bank in marks:
            total["markers"] = marks[bank]
        out[bank] = {
            "cut": f"book/{bank}", "flow_label": "New", "coverage": None, "level": "book",
            "bank": bank, "parts": parts, "total": total,
            # Which columns the table draws, each named by one signal that fills it (the whole
            # book's where it has one); each row's own signals are in its `columns`.
            "columns": {c: tcols.get(c) or next(p["columns"][c] for p in parts if c in p["columns"])
                        for c in COL if total.get(c) or any(p.get(c) for p in parts)},
            "parent_columns": tcols, "parent_entities": {c: bank for c in tcols},
            "periods": labels, "parent_periods": labels,
            # The share column says what it divides by, and the line under the table says it in
            # words (DASHBOARD_SPEC §17.6); the bank's name is filled in by the stamp's labeller.
            "col_labels": {"of_book": "Of its book"},
            "key": [f"Of its book: each line as a share of {{bank}}'s own credit ({whole}). "
                    f"Click a line for its history."] if whole else [],
            "source_signals": sorted(set(sigs.values())),
        }
    return out
