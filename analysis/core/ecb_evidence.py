#!/usr/bin/env python3
"""
ecb_evidence.py — RBI's monthly ECB borrower lists, read as evidence for S4
─────────────────────────────────────────────────────────────────────────────
analysis/sources/README.md, "ECB borrower lists" (probed 2026-11-13). RBI publishes every external
commercial borrowing registered each month, one row per borrower: economic sector (NIC 2008 wording),
amount in US$, purpose, maturity, lender. As a monthly timing driver it did no better than chance
(3 of 16 unexplained falls matched against 25% of ordinary months), so it is NOT a driver series
(user, 2026-11-13). It is evidence: when a line falls unexpectedly, a deal in its sector that month,
above all one that refinances rupee loans, is an official, verbatim reason a bank loan went away.

  discover   read RBI's ECB page (scriptable) → month, XLSX and PDF links → raw/index.json
  save       read downloaded XLSX files (the file host drops scripted connections, so the editor's
             Chrome downloads them) → raw/{YYYY-MM}.xlsx, keyed by the month the file names
  evidence   for one SIBC period: each unexplained falling move on a line whose firms borrow
             abroad, beside that sector's deals in the data month and the one before

Every economic-sector label must resolve to a NIC division (`sources/ecb/nic2008_divisions.json`),
or the read stops: a new label is a decision, not a silent drop. Deterministic; no LLM.

    python3 analysis/core/ecb_evidence.py discover
    python3 analysis/core/ecb_evidence.py save --xlsx ~/Downloads/ECB*.XLSX
    python3 analysis/core/ecb_evidence.py evidence --pipeline sibc [--period 2026-10-30]
"""
from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT  # noqa: E402

HERE = ROOT / "analysis/sources/ecb"
RAW = HERE / "raw"
DIVISIONS = HERE / "nic2008_divisions.json"
LISTING = "https://www.rbi.org.in/Scripts/ECBView.aspx"
SHEET = "ECB-FCCB"
MIN_PREFIX = 20                       # RBI truncates long sector names; a shorter prefix is ambiguous
MONTHS = {m.lower(): i for i, m in enumerate(calendar.month_name) if m}


class UnknownSector(ValueError):
    """A sector label no NIC division explains: stop, so a new label is decided, never dropped."""


def _letters(s: str) -> str:
    return re.sub(r"[^a-z]", "", s.lower())


def division_of(label: str, table: dict | None = None) -> str:
    """NIC 2008 division code for an RBI sector label (punctuation and truncation tolerated)."""
    table = table or json.loads(DIVISIONS.read_text())
    key = _letters(label)
    for alias, code in table["aliases"].items():
        if _letters(alias) == key:
            return code
    for code, name in table["divisions"].items():
        full = _letters(name)
        if key == full or (len(key) >= MIN_PREFIX and full.startswith(key)):
            return code
    raise UnknownSector(f"economic sector {label!r} matches no NIC division; add it to "
                        f"{DIVISIONS.relative_to(ROOT)} (an alias) after checking what it is")


def month_of(title: str) -> str | None:
    m = re.search(r"month of\s+(\w+)\s+(\d{4})", title or "", re.I)
    return f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}" if m and m.group(1).lower() in MONTHS else None


def read(path: Path) -> tuple[str, list[dict]]:
    """(month, rows) from one RBI ECB workbook. A row is a numbered registration with an amount."""
    import openpyxl
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    if SHEET not in wb.sheetnames:
        raise ValueError(f"{path.name}: no {SHEET!r} sheet ({wb.sheetnames}); RBI changed the layout?")
    table = json.loads(DIVISIONS.read_text())
    month, rows, route = None, [], None
    for row in wb[SHEET].iter_rows(values_only=True):
        cells = [c for c in row if c is not None]
        first = cells[0] if cells else None
        if month is None and isinstance(first, str):
            month = month_of(first)
        if isinstance(first, str) and re.search(r"automatic|general permission|approval", first, re.I):
            route = re.sub(r"[^A-Za-z ]", "", first).strip()
        if len(row) >= 8 and isinstance(row[0], (int, float)) and isinstance(row[4], (int, float)):
            sector = re.sub(r"\s+", " ", str(row[3])).strip()
            rows.append({"no": int(row[0]), "route": route, "kind": str(row[1]).strip(),
                         "borrower": re.sub(r"\s+", " ", str(row[2])).strip(), "sector": sector,
                         "nic": division_of(sector, table), "usd": float(row[4]),
                         "purpose": re.sub(r"\s+", " ", str(row[5])).strip(),
                         "maturity": re.sub(r"\s+", " ", str(row[6] or "")).strip(),
                         "lender": re.sub(r"\s+", " ", str(row[7] or "")).strip()})
    if not month:
        raise ValueError(f"{path.name}: no 'month of …' title; cannot tell which month it holds")
    if not rows:
        raise ValueError(f"{path.name}: {month} read with no registrations; refusing an empty month")
    return month, rows


def save(paths: list[Path]) -> list[str]:
    """Copy each workbook to raw/{month}.xlsx. Same bytes again → nothing; other bytes → refuse."""
    RAW.mkdir(parents=True, exist_ok=True)
    out = []
    for p in paths:
        month, rows = read(p)
        target = RAW / f"{month}.xlsx"
        if target.exists():
            if hashlib.sha256(target.read_bytes()).digest() == hashlib.sha256(p.read_bytes()).digest():
                out.append(f"{month}: already saved")
                continue
            raise SystemExit(f"✗ {month}: a different file is already saved ({target.name}); RBI re-issued "
                             f"it? Decide before overwriting.")
        shutil.copyfile(p, target)
        out.append(f"{month}: {len(rows)} registrations, US$ {sum(r['usd'] for r in rows) / 1e9:.2f} bn ← {p.name}")
    return out


def discover() -> dict:
    """Month → XLSX/PDF links from RBI's ECB page (www.rbi.org.in answers a script; rbidocs does not)."""
    import urllib.request
    req = urllib.request.Request(LISTING, headers={"User-Agent": "curl/8"})
    html = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "ignore")
    found = {}
    # Each month: a heading "September - 2026", then its XLSX and PDF links.
    for m in re.finditer(r"(January|February|March|April|May|June|July|August|September|October|November|December)"
                         r"\s*-\s*(\d{4})(.*?)(?=(?:January|February|March|April|May|June|July|August|September|"
                         r"October|November|December)\s*-\s*\d{4}|$)", html, re.S):
        links = re.findall(r'href="(https://rbidocs\.rbi\.org\.in/rdocs/ECB/[^"]+)"', m.group(3))
        key = f"{m.group(2)}-{MONTHS[m.group(1).lower()]:02d}"
        x = [u for u in links if u.upper().endswith(".XLSX")]
        p = [u for u in links if u.upper().endswith(".PDF")]
        if x and key not in found:
            found[key] = {"xlsx": x[0], "pdf": p[0] if p else None}
    if not found:
        raise SystemExit("✗ RBI's ECB page listed no months; the layout changed, or the read failed")
    RAW.mkdir(parents=True, exist_ok=True)
    idx = RAW / "index.json"
    prior = json.loads(idx.read_text()) if idx.exists() else {}
    prior.update(found)
    idx.write_text(json.dumps(dict(sorted(prior.items())), indent=1) + "\n")
    return found


def saved_rows() -> dict[str, list[dict]]:
    return {p.stem: read(p)[1] for p in sorted(RAW.glob("????-??.xlsx"))}


def _prev(month: str) -> str:
    y, m = map(int, month.split("-"))
    return f"{y - (m == 1)}-{12 if m == 1 else m - 1:02d}"


def is_rupee_refinancing(purpose: str) -> bool:
    p = purpose.lower()
    return "refinanc" in p and "rupee" in p


def evidence_for(moves: list[dict], data_month: str, parts: dict, by_month: dict, top: int = 3) -> list[dict]:
    """Pure: each unexplained FALLING move on a mapped line, with its sectors' deals in the data month
    and the one before, rupee-loan refinancing first, then by size. Rises get none: substitution
    (a firm borrowing abroad instead of from its bank) predicts a fall."""
    out = []
    window = [m for m in (data_month, _prev(data_month)) if m in by_month]
    for mv in moves:
        if mv.get("filed_under") != "unexplained" or mv.get("direction") != "down":
            continue
        divs = parts.get(mv.get("urn"))
        if not divs:
            continue
        deals = [{**r, "month": m} for m in window for r in by_month[m] if r["nic"] in divs]
        deals.sort(key=lambda r: (not is_rupee_refinancing(r["purpose"]), -r["usd"]))
        out.append({"entity": mv["entity"], "urn": mv["urn"], "gap_change_pp": mv["gap_change_pp"],
                    "divisions": divs, "months_read": window,
                    "months_missing": [m for m in (data_month, _prev(data_month)) if m not in by_month],
                    "refinancing": [d for d in deals if is_rupee_refinancing(d["purpose"])],
                    "deals": deals[:top], "n_deals": len(deals)})
    return out


def evidence(pipeline: str, period: str | None) -> tuple[str, list[dict]]:
    from core import coverage as cv
    from core import force_check as fc
    from core import generate_skeleton as gs
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    series, periods = fc.growth_series(pipeline, model), fc.periods_of(pipeline)
    period = period or periods[-1]
    data_month = fc.resolve_csv_date(pipeline, period)[:7]
    parts = json.loads((ROOT / f"analysis/ontology/evidence/{pipeline}__rbi_ecb.json").read_text())["parts"]
    moves = cv.for_period(pipeline, model, period, series, periods)["moves"]
    return data_month, evidence_for(moves, data_month, parts, saved_rows())


def main() -> int:
    ap = argparse.ArgumentParser(description="RBI ECB borrower lists as S4 evidence")
    ap.add_argument("command", choices=("discover", "save", "evidence"))
    ap.add_argument("--xlsx", nargs="+", type=Path)
    ap.add_argument("--pipeline", default="sibc")
    ap.add_argument("--period")
    a = ap.parse_args()
    if a.command == "discover":
        found = discover()
        have = {p.stem for p in RAW.glob("????-??.xlsx")}
        missing = sorted(set(found) - have)
        print(f"  RBI lists {len(found)} months ({min(found)} → {max(found)}); saved {len(have & set(found))}; "
              f"to download in the editor's Chrome: {len(missing)}")
        for m in missing:
            print(f"   {m}  {found[m]['xlsx']}")
        return 0
    if a.command == "save":
        if not a.xlsx:
            ap.error("save needs --xlsx FILE [FILE …]")
        for line in save(a.xlsx):
            print("  ✓", line)
        return 0
    month, ev = evidence(a.pipeline, a.period)
    idx = json.loads((RAW / "index.json").read_text()) if (RAW / "index.json").exists() else {}
    print(f"  {a.pipeline} data month {month}: {len(ev)} unexplained fall(s) on lines whose firms borrow abroad")
    for e in ev:
        miss = f"  (no ECB file for {', '.join(e['months_missing'])})" if e["months_missing"] else ""
        print(f"\n   {e['entity']}  gap {e['gap_change_pp']:+.2f} pp  · NIC {','.join(e['divisions'])} · "
              f"{e['n_deals']} deal(s) in {', '.join(e['months_read']) or '—'}{miss}")
        for d in e["deals"]:
            mark = "REFINANCES RUPEE LOANS" if is_rupee_refinancing(d["purpose"]) else d["purpose"][:34]
            print(f"     {d['month']}  US$ {d['usd'] / 1e6:8.1f} mn  {d['borrower'][:44]:44}  {mark}")
            src = idx.get(d["month"], {}).get("pdf")
            if src and is_rupee_refinancing(d["purpose"]):
                print(f"              source: {src} (row {d['no']}, {d['route'] or 'route not stated'})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
