#!/usr/bin/env python3
"""
reader.py — one DBIE bank-wise export (all eight sheets) → rows, or a loud refusal
────────────────────────────────────────────────────────────────────────────────────
BANKWISE_SPEC.md §3, §5.0. The export is the editor's Chrome download of DBIE's "Variables to be
published Bank and Bank Group wise (For Public Access)", Export → Excel → All reports.

Every shape a wrong export can take must raise, never read as a smaller valid one (§5.0):
  * a sheet missing or extra (the declared eight, `sheets.json`);
  * a header that differs from the declared ordered list, in either direction (a mislabelled
    column would pass every sum: "Roads" and "Ports" swapped add up the same);
  * a unit other than crores (lakhs would pass every ratio and sum);
  * a bold row whose name is not a declared group (a new group must be decided, not guessed);
  * a bank name the roster does not claim (core/banks.py).
Group rows are found by layout (RBI prints them bold; "AUSTRALIA AND NEW ZEALAND BANKING GROUP
LIMITED" is not), never by name pattern; a bank belongs to the group row that closes its block.
A group row directly after another group row is a total of groups (All SCBs), with no members.

    python3 analysis/pipelines/rbi_bankwise/reader.py --xlsx FILE            # print a summary
    python3 analysis/pipelines/rbi_bankwise/reader.py --xlsx FILE --declare  # (re)write sheets.json
"""
from __future__ import annotations

import argparse
import datetime
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / ".git").is_dir()) / "analysis"))
from core.banks import Resolver  # noqa: E402

SOURCE = "rbi_bankwise"
DECLARED = HERE / "sheets.json"
OPERATIONS = {"Domestic Operation": "dom", "Overseas Operation": "ovs", "Global Operation": "glb"}


class ExportShapeError(ValueError):
    """The workbook is not the export the spec declares."""


def norm(text) -> str:
    return " ".join(str(text).split()) if text is not None else ""


def slug(text: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


def _header(ws) -> tuple[int, int, int, list[tuple[str, str]], str]:
    """(header row, period column, name column, [(measure, operation)], unit text) of the FIRST
    header; later headers in the same sheet are read by `columns_at` (a layout change mid-sheet)."""
    rows = [[c.value for c in r] for r in ws.iter_rows(min_row=1, max_row=12)]
    hr = next((i for i, r in enumerate(rows) if "Period" in [norm(v) for v in r] and "Banks" in [norm(v) for v in r]), None)
    if hr is None:
        raise ExportShapeError(f"{ws.title}: no 'Period | Banks' header row in the first 12 rows")
    row = [norm(v) for v in rows[hr]]
    pc, nc = row.index("Period"), row.index("Banks")
    unit = " ".join(norm(v) for r in rows[:hr] for v in r if v and ("Crore" in str(v) or "Lakh" in str(v)
                                                                       or "Million" in str(v) or "Amount" in str(v)))
    return hr + 1, pc, nc, columns_at(ws, hr + 1, nc), unit


def columns_at(ws, at: int, nc: int) -> list[tuple[str, str]]:
    """[(measure, operation)] of the header row `at` (1-based). A measure heads exactly the columns
    its merged cell spans: never forward-filled, because RBI's export has merged header cells left
    EMPTY over columns that hold numbers (Asset Quality AZ:BB and Major Sectoral AQ, Jun 2025 only;
    found 2026-11-14). Forward-filling named them after the measure to their left."""
    row = [norm(c.value) for c in ws[at]]
    after = row[nc + 1:]
    if any(v in OPERATIONS for v in after):
        mr = at - 1
        span = {}
        for rg in ws.merged_cells.ranges:
            if rg.min_row <= mr <= rg.max_row:
                for c in range(rg.min_col, rg.max_col + 1):
                    span[c] = norm(ws.cell(rg.min_row, rg.min_col).value)
        above = [norm(c.value) for c in ws[mr]]
        return [(span.get(j + 1, above[j] if j < len(above) else ""), op)
                for j, op in enumerate(after, start=nc + 1) if op]
    return [(v, "") for v in after if v]


def layouts_of(spec: dict) -> dict[str, list[tuple[str, str]]]:
    """A sheet's declared layouts: id → ordered columns. RBI changes a classification now and then
    (Infrastructure, Mar → Jun 2022) and one export then prints both, each under its own header."""
    if "layouts" in spec:
        return {k: [tuple(c) for c in v["columns"]] for k, v in spec["layouts"].items()}
    return {"current": [tuple(c) for c in spec["columns"]]}


def _fits(cols: list[tuple[str, str]], want: list[tuple[str, str]], blank_ok: set) -> list[tuple[str, str]] | None:
    """The declared columns `cols` stands for, if `cols` is an ORDERED SUBSET of `want`: DBIE prints
    only the measures that hold data in the quarters selected (Profitability: 42 columns for
    2024-26, 51 for 2021-23; found 2026-11-14), so an export may skip declared columns but never
    reorder or rename one. A label in `blank_ok` may print blank (DBIE prints '22. Loss or gain on
    loan sales' only for some selections)."""
    out, j = [], 0
    for g in cols:
        while j < len(want) and not (g == want[j] or (g == ("", want[j][1]) and want[j][0] in blank_ok)):
            j += 1
        if j == len(want):
            return None
        out.append(want[j])
        j += 1
    return out


def match_layout(title: str, cols: list[tuple[str, str]], spec: dict) -> tuple[str, list[tuple[str, str]]]:
    """(layout id, the DECLARED columns the printed header stands for). Ids always come from the
    declaration, so one column has one id whatever an export prints."""
    lays = layouts_of(spec)
    for lid, want in lays.items():
        blank = set((spec.get("layouts", {}).get(lid) or {}).get("blank_ok_labels", []))
        got = _fits(cols, want, blank)
        if got is not None:
            return lid, got
    want = lays.get("current") or next(iter(lays.values()))
    unknown = [c for c in cols if c not in want and c[0]]
    raise ExportShapeError(f"{title}: header is not an ordered subset of any declared layout ({list(lays)}); "
                           f"{len(unknown)} column(s) not in '{next(iter(lays))}', first {unknown[:2]} "
                           f"(new measures? merge them with --declare-merge after checking the export)")


def merge_columns(want: list[tuple[str, str]], got: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Both are ordered subsets of RBI's full list: interleave them, keeping each one's order."""
    out, i = [], 0
    for g in got:
        if g in want[i:]:
            k = want.index(g, i)
            out += want[i:k + 1]
            i = k + 1
        elif g not in out and g not in want:
            out.append(g)
    return out + want[i:]


def column_ids(cols: list[tuple[str, str]]) -> list[str]:
    """A measure's slug and operation; a column RBI left without a measure is `unlabelled_{n}`,
    numbered by position, kept as data and never published until someone identifies it."""
    ids = [(slug(m) if m else f"unlabelled_{n}") + (f"@{OPERATIONS[o]}" if o else "")
           for n, (m, o) in enumerate(cols)]
    if len(set(ids)) != len(ids):
        raise ExportShapeError(f"two columns share an id: {sorted(i for i in ids if ids.count(i) > 1)}")
    return ids


def declare(path: Path) -> dict:
    """The declared shape, read once from an export the editor has checked. Never at read time."""
    import openpyxl
    wb = openpyxl.load_workbook(path)
    out = {"_meta": {"from": path.name, "declared": datetime.date.today().isoformat(),
                     "rule": "the reader refuses any export whose sheets or headers differ from these, in order"},
           "groups": {}, "sheets": {}}
    for ws in wb.worksheets:
        _, _, _, cols, _ = _header(ws)
        out["sheets"][ws.title] = {"id": slug(ws.title), "columns": [[m, o] for m, o in cols]}
    return out


def read(path: Path, declared: dict | None = None, resolver: Resolver | None = None) -> dict:
    """{"quarters": {period: {"banks": {id: {...}}, "groups": {gid: {...}}}}, "names": {...}}.

    A bank's entry: {"group": gid, "sheets": {sheet_id: {column_id: value}}}. A group's entry:
    {"members": [bank ids] or [], "sheets": {...}}. `names` keeps the printed name per bank id."""
    import openpyxl
    declared = declared or json.loads(DECLARED.read_text())
    resolver = resolver or Resolver(SOURCE)
    wb = openpyxl.load_workbook(path)
    got, want = [ws.title for ws in wb.worksheets], list(declared["sheets"])
    if got != want:
        raise ExportShapeError(f"sheets {got} ≠ declared {want} (was 'All reports' ticked on export?)")
    quarters, names = {}, {}
    for ws in wb.worksheets:
        spec = declared["sheets"][ws.title]
        first, pc, nc, cols, unit = _header(ws)
        layout, cols = match_layout(ws.title, cols, spec)
        # The Unit prompt applies to the whole export; a sheet that prints no unit (Infrastructure)
        # is covered by the sheets that do, and is declared as printing none.
        if spec.get("unit", "crores") == "crores" and "crore" not in unit.lower():
            raise ExportShapeError(f"{ws.title}: unit {unit!r} is not crores (the Unit prompt)")
        if spec.get("unit") == "not_printed" and unit:
            raise ExportShapeError(f"{ws.title}: declared to print no unit, but prints {unit!r}")
        ids = column_ids(cols)
        sid = spec["id"]
        period, block, prev_group = None, [], False
        for r in ws.iter_rows(min_row=first + 1):
            pv, nm = r[pc].value, r[nc].value
            if norm(nm) == "Banks":                      # a second header: the layout changes here
                if block:
                    raise ExportShapeError(f"{ws.title}: banks before a header row without a closing group")
                layout, cols = match_layout(ws.title, columns_at(ws, r[nc].row, nc), spec)
                ids, period = column_ids(cols), None
                continue
            if isinstance(pv, datetime.datetime):
                period = pv.date().isoformat()
            if not isinstance(nm, str) or not nm.strip():
                continue
            if nm.strip().startswith("Source"):
                break
            if period is None:
                raise ExportShapeError(f"{ws.title}: row {nm!r} before any period")
            vals = {i: r[nc + 1 + j].value for j, i in enumerate(ids)}
            for i, v in vals.items():
                if v is not None and not isinstance(v, (int, float)):
                    raise ExportShapeError(f"{ws.title} {period} {nm!r} {i}: non-numeric cell {v!r}")
            q = quarters.setdefault(period, {"banks": {}, "groups": {}, "layouts": {}})
            if q["layouts"].setdefault(sid, layout) != layout:
                raise ExportShapeError(f"{ws.title} {period}: printed under two layouts")
            if r[nc].font.bold:
                gid = declared["groups"].get(norm(nm).lower())
                if gid is None:
                    raise ExportShapeError(f"{ws.title} {period}: bold row {nm!r} is not a declared group "
                                           f"(add it to sheets.json 'groups' after checking it)")
                g = q["groups"].setdefault(gid, {"members": [], "members_by_sheet": {}, "sheets": {}})
                g["sheets"][sid] = vals
                if not prev_group:
                    # Membership is per sheet: a bank can be on every sheet but one (a foreign bank
                    # missing from Capital Adequacy, Mar 2024). The presence check (§5.5) names it;
                    # the sums (§5.1) use each sheet's own block.
                    g["members_by_sheet"][sid] = list(block)
                    g["members"] = sorted(set(g["members"]) | set(block))
                block, prev_group = [], True
                continue
            bid = resolver(nm, period)
            names.setdefault(bid, norm(nm))
            b = q["banks"].setdefault(bid, {"group": None, "sheets": {}})
            if sid in b["sheets"]:
                raise ExportShapeError(f"{ws.title} {period}: {bid} appears twice")
            b["sheets"][sid] = vals
            block.append(bid)
            prev_group = False
        if block:
            raise ExportShapeError(f"{ws.title} {period}: banks after the last group row ({block[:3]}…)")
    for period, q in quarters.items():
        for gid, g in q["groups"].items():
            for bid in g["members"]:
                q["banks"][bid]["group"] = gid
    return {"quarters": quarters, "names": names}


def unknown_names(path: Path, declared: dict | None = None, resolver: Resolver | None = None) -> dict[str, list[str]]:
    """Every non-group name in an export that the roster does not resolve, with its quarters, so a
    backfill batch is reviewed once rather than one refusal at a time. Reads nothing else."""
    import openpyxl
    from core.banks import UnknownBank
    declared = declared or json.loads(DECLARED.read_text())
    resolver = resolver or Resolver(SOURCE)
    out: dict[str, set] = {}
    for ws in openpyxl.load_workbook(path).worksheets:
        first, pc, nc, _, _ = _header(ws)
        period = None
        for r in ws.iter_rows(min_row=first + 1):
            pv, nm = r[pc].value, r[nc].value
            if isinstance(pv, datetime.datetime):
                period = pv.date().isoformat()
            if not isinstance(nm, str) or not nm.strip() or nm.strip().startswith("Source") or norm(nm) == "Banks":
                continue
            if r[nc].font.bold:
                if norm(nm).lower() not in declared["groups"]:
                    out.setdefault(f"[group] {norm(nm)}", set()).add(period)
                continue
            try:
                resolver(nm, period)
            except UnknownBank:
                out.setdefault(norm(nm), set()).add(period)
    return {k: sorted(v) for k, v in sorted(out.items())}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--xlsx", type=Path, required=True)
    ap.add_argument("--declare", action="store_true", help="write sheets.json from this export (keeps 'groups')")
    ap.add_argument("--unknown", action="store_true", help="list names the roster does not resolve, with quarters")
    ap.add_argument("--declare-merge", action="store_true",
                    help="merge columns this export shows that the declaration lacks, at their printed position")
    a = ap.parse_args()
    if a.declare_merge:
        import openpyxl
        doc = json.loads(DECLARED.read_text())
        for ws in openpyxl.load_workbook(a.xlsx).worksheets:
            spec = doc["sheets"][ws.title]
            first, _, nc, _, _ = _header(ws)
            heads = [first] + [r[nc].row for r in ws.iter_rows(min_row=first + 1) if norm(r[nc].value) == "Banks"]
            for h in heads:
                cols = columns_at(ws, h, nc)
                lays = spec.get("layouts") or {"current": {"columns": spec["columns"]}}
                lid = max(lays, key=lambda k: len(set(map(tuple, lays[k]["columns"])) & set(cols)))
                before = [tuple(c) for c in lays[lid]["columns"]]
                after = merge_columns(before, [c for c in cols if c[0]])
                if after != before:
                    print(f"  {ws.title} [{lid}]: +{len(after) - len(before)} column(s): "
                          f"{[c for c in after if c not in before][:4]}")
                    lays[lid]["columns"] = [list(c) for c in after]
                    if "layouts" not in spec:
                        spec.pop("columns", None)
                        spec["layouts"] = lays
        DECLARED.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        return 0
    if a.unknown:
        un = unknown_names(a.xlsx)
        print(f"  {len(un)} unknown name(s)")
        for n, qs in un.items():
            print(f"   {n:60} {qs[0]} … {qs[-1]} ({len(qs)})")
        return 1 if un else 0
    if a.declare:
        doc = declare(a.xlsx)
        if DECLARED.exists():
            doc["groups"] = json.loads(DECLARED.read_text()).get("groups", {})
        DECLARED.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        print(f"  ✓ declared {len(doc['sheets'])} sheets, "
              f"{sum(len(s['columns']) for s in doc['sheets'].values())} columns → {DECLARED.name}")
        return 0
    got = read(a.xlsx)
    for p, q in sorted(got["quarters"].items()):
        print(f"  {p}: {len(q['banks'])} banks, groups " +
              ", ".join(f"{g} ({len(v['members'])})" for g, v in q["groups"].items()))
    return 0


if __name__ == "__main__":
    sys.exit(main())
