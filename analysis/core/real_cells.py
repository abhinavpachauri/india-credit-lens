#!/usr/bin/env python3
"""
real_cells.py — the table's "vs the real economy" columns (DASHBOARD_SPEC §21)
──────────────────────────────────────────────────────────────────────────────
Two columns beside a cut's credit numbers, from the 1f signals (signals/README §1f): Real credit
(loans net of the part's own prices) and Output 12m (what the part's industry produced over the
last year). Every cell is read from signals.db and rendered here, as every table cell is.

What a 1f cell carries that an ordinary cell does not, and why:
  * `period` — the reading's OWN period. A quarterly column on a monthly table shows the latest
    quarter, labelled (`period_label`: "Q1"); the gate checks the cell at that period, never by
    widening the table's.
  * `reason` — an empty cell is "—" with a code from core/absence.py, never 0 and never blank.
  * `note` — the sentence a hover shows, rendered here. A real-credit value names its deflator
    and that deflator's own change, so "petroleum −17% real" arrives with "net of mineral-oil
    prices, +38.5% over the year" rather than reading as a collapse.

The gate (guards/validate_cut_table.py) re-renders every note, coverage line and approximation
share from stored rows with the functions below and requires the shipped string to match.
"""
from __future__ import annotations

import json
from datetime import date, timedelta
from functools import lru_cache

from core import absence, manifest
from core.table_columns import F1_COLUMN
from core.table_rows import _history, _periods_of, _aligned, _label, _pct

#: The month a fiscal quarter ends → its name. RBI and MoSPI both count Q1 from April.
FISCAL_QUARTER = {6: "Q1", 9: "Q2", 12: "Q3", 3: "Q4"}
QUARTER_SPAN = {"Q1": "Apr–Jun", "Q2": "Jul–Sep", "Q3": "Oct–Dec", "Q4": "Jan–Mar"}


# ── Inputs ────────────────────────────────────────────────────────────────────

@lru_cache(maxsize=None)
def _registry() -> dict:
    from core.paths import ANALYSIS
    return json.loads((ANALYSIS / "signals" / "registry.json").read_text())["signals"]


def f1_signals(pipeline: str, stem: str) -> dict[str, dict]:
    """{column: registry entry} for the cut's 1f signals; empty when the cut declares none."""
    out = {}
    for sig in _registry().values():
        c = sig.get("compute") or {}
        if sig.get("pipeline") == pipeline and c.get("cut") == stem and c.get("method") in F1_COLUMN:
            out[F1_COLUMN[c["method"]]] = sig
    return out


@lru_cache(maxsize=None)
def series_names(reference: str) -> dict[str, str]:
    """{dataset/code: the name MoSPI gives it}: the last named level of its own label."""
    labels = json.loads(manifest.path(reference, "labels").read_text())
    out: dict[str, str] = {}
    for ds, m in labels.items():
        if not isinstance(m, dict):
            continue
        for label, code in m.items():
            name = [s.strip() for s in label.split("›") if s.strip()]
            key = f"{ds}/{code}"
            if name and (key not in out or "Growth Rate" in out[key]):
                out[key] = name[-1]
    return out


def _credit(pipeline: str):
    from signals.compute import csv_sector, real_economy
    return real_economy.credit(csv_sector._load_df(pipeline)), csv_sector


# ── Which reading a cell shows ────────────────────────────────────────────────

def cell_period(conn, pipeline: str, sig: dict, period: str) -> str | None:
    """The period a cell reads: the table's own for a monthly signal; the latest stored quarter
    at or before it for a quarterly one. Never later than the table, and a monthly cell never
    falls back to an earlier month (no carry-forward, §21.4)."""
    if sig.get("cadence") != "quarterly":
        return period
    row = conn.execute("SELECT MAX(period) FROM signals WHERE pipeline=? AND metric_id=? AND period<=?",
                       (pipeline, sig["id"], period)).fetchone()
    return row[0] if row else None


def period_label(pipeline: str, sig: dict, period: str) -> str | None:
    if sig.get("cadence") != "quarterly":
        return None
    _, csv_sector = _credit(pipeline)
    return FISCAL_QUARTER[date.fromisoformat(csv_sector.resolve_csv_date(pipeline, period)).month]


def stored(conn, pipeline: str, sid: str, period: str, etype: str, eid: str):
    return conn.execute("SELECT value, reason, operands FROM signals WHERE pipeline=? AND period=? "
                        "AND metric_id=? AND entity_type=? AND entity_id=?",
                        (pipeline, period, sid, etype, eid)).fetchone()


# ── The sentences ─────────────────────────────────────────────────────────────

def value_note(col: str, operands: dict, reference: str) -> str:
    """What a value cell is net of, or measured by. Every number in it is a stored operand."""
    names = series_names(reference)
    if col == "real_credit":
        d = operands["deflator"]
        pi = f"{operands['deflator_yoy']:+.1f}% over the year"
        if d["kind"] == "implicit":
            return f"Net of the national-accounts deflator, {pi}."
        ds = d["series"][0].split("/", 1)[0].upper()
        what = (names.get(d["series"][0], d["series"][0]) if len(d["series"]) == 1
                else f"{len(d['series'])} {ds} groups, weighted")
        return f"Net of {what} prices ({ds}), {pi}."
    ds = operands["series"][0].split("/", 1)[0]
    what = ", ".join(names.get(s, s) for s in operands["series"])
    if ds == "nas":
        return f"Real GVA ({what}): the last 4 quarters against the 4 before."
    return f"IIP {what}: the last 12 months against the 12 before."


def reason_note(reason: str, csv_date: str, part: dict, col: str, reference: str) -> str:
    """Why a cell is empty, in a sentence; `not_released` says when MoSPI's figure is due."""
    text = absence.STATIC.get(reason) or absence.PER_PERIOD[reason]
    note = text[0].upper() + text[1:]
    if reason == "not_released":
        spec = part["deflator" if col == "real_credit" else "output"]
        series = spec.get("series") or spec.get("implicit")
        ds = series[0].split("/", 1)[0]
        ref = manifest.load(reference)
        due = date.fromisoformat(csv_date) + timedelta(
            days=ref["datasets"][ds]["expected_lag_days"] + int(ref.get("grace_days", 0)))
        note += f" (due by {due:%-d %b %Y})"
    return note + "."


def approx_note(conn, pipeline: str, period: str, code: str, spec: dict) -> str:
    """The ⓘ sentence on an approximate aggregate, with its share computed this period from the
    stored size rows of the parts it names (COMPOSITION_SPEC §24.1). Never typed."""
    text = absence.APPROXIMATIONS[code]
    text = text[0].upper() + text[1:]
    if not spec.get("numerator"):
        return text + "."
    num = sum(_size(conn, pipeline, period, u) for u in spec["numerator"])
    den = _size(conn, pipeline, period, spec["denominator"])
    return f"{text}: {100 * num / den:.1f}% of it this month."


def _size(conn, pipeline: str, period: str, urn: str) -> float:
    """A credit row's stored size, found through the cut whose scan holds it."""
    cred, csv_sector = _credit(pipeline)
    csv = csv_sector.resolve_csv_date(pipeline, period)
    name = cred.name[(urn, csv)]
    for (st, parent, d), kids in cred.children.items():
        if d == csv and urn in kids:
            for sig in _registry().values():
                c = sig.get("compute") or {}
                if (sig.get("pipeline") == pipeline and c.get("method") == "csv_sector_scan_abs"
                        and c.get("statement") == st and c.get("parent_code") == parent):
                    row = conn.execute("SELECT value FROM signals WHERE pipeline=? AND period=? AND "
                                       "metric_id=? AND entity_id=?", (pipeline, period, sig["id"], name)).fetchone()
                    if row:
                        return row[0]
    raise LookupError(f"{urn}: no stored size row at {period}")


def coverage_line(col: str, label: str, cells: list[tuple[dict | None, float | None]]) -> str:
    """'Real credit: 9 of 19 parts · 18.8% of this table's credit · 2 awaiting MoSPI.'

    Counts the cells that HAVE a value this period, never what the concordance maps; the share
    weighs them by the parts' own size cells."""
    have = [(c, s) for c, s in cells if c and c.get("sort") is not None]
    total = sum(s for _, s in cells if s is not None)
    share = 100 * sum(s for _, s in have if s is not None) / total if total else 0.0
    waiting = sum(1 for c, _ in cells if c and c.get("reason") == "not_released")
    line = f"{label}: {len(have)} of {len(cells)} parts · {share:.1f}% of this table's credit"
    return line + (f" · {waiting} awaiting MoSPI." if waiting else ".")


def footnote(kinds: dict[str, set], quarter: tuple[str, str] | None) -> list[str]:
    """What the two columns mean, built from the datasets this cut actually uses."""
    PRICE = {"wpi": "wholesale prices (WPI)", "cpi": "consumer prices (CPI)",
             "implicit": "the national-accounts deflator"}
    OUT = {"iip": "IIP production over the last 12 months", "nas": "real GVA over the last 4 quarters"}
    lines = []
    if kinds["real_credit"]:
        lines.append("Real credit = loans outstanding, year on year, net of each part's own prices: "
                     + "; ".join(PRICE[k] for k in sorted(kinds["real_credit"])) + ".")
    if kinds["output"]:
        lines.append("Output = " + "; ".join(OUT[k] for k in sorted(kinds["output"])) + ".")
    if quarter:
        q, year = quarter
        lines.append(f"·{q} = {QUARTER_SPAN[q]} {year}; credit read at the quarter's end.")
    lines.append("Hover a — for why it is empty.")
    return lines


def urn_for(pipeline: str, period: str, stem: str, entity: str | None) -> str:
    """The concordance URN of a table row: a part by its name, or (None) the cut's parent."""
    from signals.compute import real_economy
    cred, csv_sector = _credit(pipeline)
    csv = csv_sector.resolve_csv_date(pipeline, period)
    reference = next(iter(f1_signals(pipeline, stem).values()))["compute"]["reference"]
    cut = real_economy.concordance(pipeline, reference)["cuts"][stem]
    if entity is None:
        return cut.get("parent_urn") or real_economy.urn(pipeline, cut["statement"], cut["parent_code"])
    for u in cred.children.get((cut["statement"], cut["parent_code"], csv), []):
        if cred.name[(u, csv)] == entity:
            return u
    raise LookupError(f"{stem}: no part named {entity!r} at {csv}")


# ── One cut ───────────────────────────────────────────────────────────────────

def for_cut(conn, pipeline: str, period: str, stem: str, part_sizes: dict[str, float | None]) -> dict | None:
    """The 1f columns for one cut, or None when it declares none."""
    from signals.compute import real_economy
    sigs = dict(f1_signals(pipeline, stem))
    if not sigs:
        return None
    reference = next(iter(sigs.values()))["compute"]["reference"]
    doc = real_economy.concordance(pipeline, reference)
    cut = doc["cuts"][stem]
    cred, csv_sector = _credit(pipeline)
    csv = csv_sector.resolve_csv_date(pipeline, period)

    # The parts and their URNs at this period; the parent and the cut that computes it.
    kids = cred.children.get((cut["statement"], cut["parent_code"], csv), [])
    urn_of = {cred.name[(u, csv)]: u for u in kids}
    parent = cut.get("parent_urn") or real_economy.urn(pipeline, cut["statement"], cut["parent_code"])
    home = next((s for s, c in doc["cuts"].items() if s != stem
                 and parent in cred.children.get((c["statement"], c["parent_code"], csv), [])), None)
    parent_sigs = f1_signals(pipeline, home) if home else sigs
    p_etype = "aggregate" if not home else None
    p_eid = "total" if not home else cred.name[(parent, csv)]

    out = {"parts": {}, "total": {}, "columns": {}, "parent_columns": {}, "parent_entities": {},
           "periods": {}, "parent_periods": {}, "approx": {}, "kinds": {"real_credit": set(), "output": set()},
           "source_signals": set()}
    quarter = None

    def cell(col, sig, etype, eid, urn, hist, hist_periods):
        nonlocal quarter
        cp = cell_period(conn, pipeline, sig, period)
        if cp is None:
            return None
        cp_csv = csv_sector.resolve_csv_date(pipeline, cp)
        row = stored(conn, pipeline, sig["id"], cp, etype, eid)
        if row is None:
            raise LookupError(f"{sig['id']} {cp} {eid}: no stored 1f row (Check 2f should have failed)")
        value, reason, ops = row
        part = doc["parts"][urn]
        spec = part["deflator" if col == "real_credit" else "output"]
        if "implicit" in spec:
            out["kinds"][col].add("implicit")
        elif "series" in spec:
            out["kinds"][col].add(spec["series"][0].split("/", 1)[0])
        lab = period_label(pipeline, sig, cp)
        if lab:
            quarter = (lab, cp_csv[:4])
        base = {"period": cp, "period_label": lab}
        if value is None:
            return {"display": "—", "sort": None, **base, "reason": reason,
                    "note": reason_note(reason, cp_csv, part, col, reference)}
        series = _aligned(hist, eid, hist_periods)
        return {"display": _pct(value), "sort": value,
                "series": series, "series_display": None if series is None else
                [None if v is None else _pct(v) for v in series],
                **base, "note": value_note(col, json.loads(ops), reference)}

    for col, sig in sigs.items():
        etype = sig["compute"].get("entity_type", "sector")
        hist = _history(conn, pipeline, sig["id"], etype)
        hp = _periods_of(hist)
        out["columns"][col] = sig["id"]
        out["periods"][col] = [_label(p, pipeline) for p in hp]
        out["source_signals"].add(sig["id"])
        for name in part_sizes:
            if name not in urn_of:
                raise LookupError(f"{stem}: table part {name!r} is not a child in the credit CSV at {csv}")
            out["parts"].setdefault(name, {})[col] = cell(col, sig, etype, name, urn_of[name], hist, hp)
        psig = parent_sigs[col]
        petype = p_etype or psig["compute"].get("entity_type", "sector")
        phist = _history(conn, pipeline, psig["id"], petype)
        php = _periods_of(phist)
        out["total"][col] = cell(col, psig, petype, p_eid, parent, phist, php)
        out["parent_columns"][col] = psig["id"]
        out["parent_entities"][col] = p_eid
        out["parent_periods"][col] = [_label(p, pipeline) for p in php]
        out["source_signals"].add(psig["id"])

    # A column this cut can NEVER fill is not drawn: every cell absent for a static reason (Personal
    # Loans' output, say) would be a column of dashes claiming the cut has a measure it has not —
    # the rule that keeps Pace off a bank breakout. A column waiting on MoSPI stays.
    for col in list(sigs):
        cells = [out["total"][col]] + [out["parts"][n][col] for n in part_sizes]
        if all(c and c.get("reason") in absence.STATIC for c in cells):
            for k in ("columns", "parent_columns", "parent_entities", "periods", "parent_periods"):
                out[k].pop(col, None)
            out["total"].pop(col)
            for n in part_sizes:
                out["parts"][n].pop(col)
            out["kinds"][col] = set()
            del sigs[col]

    for name, urn in [(None, parent)] + [(n, urn_of[n]) for n in part_sizes]:
        code = doc["parts"][urn].get("approximate")
        if code:
            out["approx"][name] = approx_note(conn, pipeline, period, code, doc.get("approximations", {}).get(code, {}))

    out["coverage"] = [coverage_line(col, label, [(out["parts"][n].get(col), s) for n, s in part_sizes.items()])
                       for col, label in (("real_credit", "Real credit"), ("output", "Output"))
                       if col in sigs]
    out["footnote"] = footnote(out["kinds"], quarter)
    out["source_signals"] = sorted(set(out["columns"].values()) | set(out["parent_columns"].values()))
    del out["kinds"]
    return out
