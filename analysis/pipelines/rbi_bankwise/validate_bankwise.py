#!/usr/bin/env python3
"""
validate_bankwise.py — the saved quarters checked against RBI's own totals (BANKWISE_SPEC.md §5)
──────────────────────────────────────────────────────────────────────────────────────────────────
Reads the committed releases (never the local table) and checks, per quarter:

  5.1 sums     every group row = the sum of the banks in its block, per amount column; All SCBs =
               the sum of its member groups (declared: Public + Private + Foreign + Small Finance;
               the Local Area Bank group sits outside it, measured 2026-11-14)
  5.2 ratios   RBI's printed ratios recompute from their parts; a null ratio only where the
               denominator is exactly 0, a printed ratio only where it is not
  5.3 global   domestic + overseas = global, for every amount measure printed three ways
  5.4 parts    the identities inside a row (sectors → non-food, retail parts → retail, NPA classes
               → GNPAs, capital tiers, deposits, assets = liabilities, the infrastructure tree, the
               profit ladder); parts ≥ 0
  5.5 sheets   every bank on all eight sheets in a quarter
  5.6 zeros    a bank whose credit sheets are all zero while another sheet shows a book is
               `not_reported` (listed, not failed)
  5.7 scale    All SCBs gross advances within a wide band of the previous saved quarter and of
               SIBC's non-food credit (a units mistake, not a definition check)

The structure (which columns are ratios, which identities hold) is RBI's published layout, stated
here from the labels; the bounds were measured once on the probe (`--measure`) and are never
rewritten by a run. Each check states the population it iterates in its output.

    python3 analysis/pipelines/rbi_bankwise/validate_bankwise.py            # the gate stage
    python3 analysis/pipelines/rbi_bankwise/validate_bankwise.py --measure  # observed gaps
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / ".git").is_dir()) / "analysis"))
from core import manifest  # noqa: E402

PIPELINE = "rbi_bankwise"
OPS = {"Domestic Operation": "dom", "Overseas Operation": "ovs", "Global Operation": "glb"}

# Bounds, measured on the probe export (3 quarters, 2026-11-14, `--measure`) and approved with the
# spec; a run never rewrites them. Amounts are crores printed to 4 decimals; ratios to 6.
BOUNDS = {
    "sum_abs": 0.05,        # group row vs its banks (crores), observed max: see --measure
    "sum_rel": 1e-6,        #   … or relative to the group value, whichever is larger
    "ratio_abs": 0.001,     # printed ratio vs recomputed (percentage points)
    "global_abs": 0.05,     # domestic + overseas vs global (crores)
    "part_abs": 0.05,       # an identity's parts vs its total (crores)
    "part_rel": 1e-6,
    "negative_abs": 0.01,   # a part may be negative by rounding only (AmEx −0.00005 Cr)
    "scale_band": 0.5,      # All SCBs gross advances within ±50% of last quarter and of SIBC
}
SCB_MEMBERS = ["group:psb", "group:pvt", "group:foreign", "group:sfb"]   # measured: LAB outside

# Measured on the probe (2026-11-14), each with its reason; a run never widens them.
# Domestic + overseas = global holds for credit only: balance-sheet and profit items net out
# inter-office balances in the global figure (Bank of Baroda current deposits, Jun 2026:
# 79,571 + 69,067 vs 1,48,664 Cr).
GLOBAL_ADDS = ("asset_quality",)
# Parts must be ≥ 0 on the credit sheets; on the balance sheet reserves go negative with accumulated
# losses (American Express −386 Cr, Sep 2024) and other assets/liabilities net.
NON_NEGATIVE = ("asset_quality", "major_sectoral", "priority_non_priority_break_up", "infrastructure_financing_items")
# RBI's Capital Adequacy sheet carries no Small Finance or Local Area Bank (all three quarters).
NOT_COVERED = {"capital_adequacy": ("group:sfb", "group:lab")}

# Named exceptions: RBI's own figures that break its own stated identity, each measured and
# reasoned. (check, quarter or "*", entity, column prefix). Anything not named here fails.
EXCEPTIONS = [
    # RBI's printed Net Operating Income is not its own "[5 - 6]" for these banks in every probed
    # quarter (gap up to 12.5%; HDFC Jun 2026 27,741 vs 26,789 Cr); NOI is used as printed, never
    # recomputed, and the groups they sit in inherit the gap.
    *[("5.4", "*", e, "7_net_operating_income") for e in
      ("hdfc-bank", "icici-bank", "idbi-bank", "yes-bank", "group:pvt", "group:scb")],
    # One cell each: a blank ratio over GNPAs of 4.23 Cr; global loans sold to ARCs printed as
    # half the domestic figure (1.0662 vs 0.5331 Cr), carried into the group totals.
    ("5.2", "2024-09-30", "sonali-bank-plc", "other_retail_loans_gnpa_ratio"),
    *[("5.3", "2024-09-30", e, "21. Loans sold to ARCs") for e in ("karur-vysya-bank", "group:pvt", "group:scb")],
]


# Where RBI's own figures disagree in one bank or group, the cell is flagged and recorded, not
# failed (user, 2026-11-14): over 11 quarters at most 2 banks broke a check in any one column of a
# quarter. A reading error maps a column the same way for every bank, so it breaks a column across
# most of the ~90 banks; that pattern fails. The line sits at 5× the observed maximum.
COLUMN_WIDE_BANKS = 10
FLAGS = "inconsistencies.json"


def where(check: str, line: str) -> tuple[str, str]:
    """(entity, column key) of a failure line, as check_quarter writes it."""
    t = line.split(" ")
    ent = t[0].rstrip(":")
    if check == "5.5":
        return ent, "sheets"
    if check == "5.3":
        return ent, " ".join(t[1:]).split(":")[0]
    return ent, f"{t[1]} {t[2].rstrip(':')}"


def excepted(check: str, quarter: str, line: str) -> bool:
    parts = line.split(" ", 2)
    return any(c == check and q in ("*", quarter) and parts[0] == e and parts[2].startswith(col)
               for c, q, e, col in EXCEPTIONS)


def slug(text: str) -> str:
    return re.sub(r"_+", "_", re.sub(r"[^a-z0-9]+", "_", text.lower())).strip("_")


def is_ratio(sheet_id: str, measure: str) -> bool:
    """A whole word: "ratio" inside "Electricity Generation" or "Operational Risk" once dropped
    those amounts from every sum (found by the injection run, 2026-11-14)."""
    return (sheet_id == "performance_indicators" or "%" in measure
            or re.search(r"\bratio\b", measure, re.I) is not None)


# ── the structure, from RBI's labels ──────────────────────────────────────────

def structure(declared: dict) -> dict:
    """For each sheet: amount and ratio column ids, ratio formulas, and identities
    [(total_id, [(sign, part_id)…])], all derived from the declared labels."""
    out = {}
    for title, spec in declared["sheets"].items():
        sid = spec["id"]
        cols = [(m, o) for m, o in spec["columns"]]
        by_label: dict[str, dict[str, str]] = {}
        for n, (m, o) in enumerate(cols):
            cid = (slug(m) if m else f"unlabelled_{n}") + (f"@{OPS[o]}" if o else "")
            by_label.setdefault(m, {})[OPS.get(o, "")] = cid
        amounts = [c for m, d in by_label.items() if m and not is_ratio(sid, m) for c in d.values()]
        ratios = [c for m, d in by_label.items() if m and is_ratio(sid, m) for c in d.values()]
        out[sid] = {"title": title, "labels": by_label, "amounts": amounts, "ratios": ratios,
                    "formulas": [], "identities": []}
    S = out

    def col(sid, label, op):
        return S[sid]["labels"][label][op]

    def ops(sid, label):
        return list(S[sid]["labels"][label])

    def formula(sid, ratio, num, den):
        for op in ops(sid, ratio):
            S[sid]["formulas"].append((col(sid, ratio, op), col(sid, num, op), col(sid, den, op)))

    def identity(sid, total, parts):
        for op in ops(sid, total):
            S[sid]["identities"].append((col(sid, total, op), [(sg, col(sid, p, op)) for sg, p in parts]))

    # Major Sectoral and Priority: "X - GNPA Ratio" = "X - GNPAs" / "X - Gross Advances".
    for sid in ("major_sectoral", "priority_non_priority_break_up"):
        labels = S[sid]["labels"]
        formula(sid, "Gross NPAs to Gross Advances (%)", "Gross NPAs", "Gross Advances")
        for lab in labels:
            if lab.endswith(" - GNPA Ratio"):
                p = lab[: -len(" - GNPA Ratio")]
                num = next(x for x in (f"{p} - GNPAs", f"{p} - Gross NPAs", f"{p}  - Gross NPAs") if x in labels)
                formula(sid, lab, num, f"{p} - Gross Advances")
    sec = lambda p, k="Gross Advances": f"{p} - {k}"  # noqa: E731
    for k, npa in (("Gross Advances", None), ("GNPAs", "Gross NPAs")):
        labels = S["major_sectoral"]["labels"]
        name = lambda p: next(x for x in (sec(p, k), sec(p, npa or k)) if x in labels)  # noqa: E731
        top = "Gross Advances" if k == "Gross Advances" else "Gross NPAs"
        identity("major_sectoral", top, [(1, name("Food Credit")), (1, name("Non-Food Credit"))])
        identity("major_sectoral", name("Non-Food Credit"),
                 [(1, name(p)) for p in ("Agriculture and Allied Activities", "Industry", "Services",
                                         "Retail Loans", "Other Non-food Credit")])
        identity("major_sectoral", name("Retail Loans"),
                 [(1, name(p)) for p in ("Retail Loans - Housing Loans", "Retail Loans - Vehicle/Auto Loans",
                                         "Retail Loans - Credit Card Receivables", "Retail Loans - Education",
                                         "Other Retail Loans")])
    pr = S["priority_non_priority_break_up"]["labels"]
    for k in ("Gross Advances", "GNPAs"):
        n = lambda p: next(x for x in (f"{p} - {k}", f"{p} - Gross NPAs") if x in pr)  # noqa: E731
        top = "Gross Advances" if k == "Gross Advances" else "Gross NPAs"
        identity("priority_non_priority_break_up", top, [(1, n("Priority Sector")), (1, n("Other than Priority"))])
        identity("priority_non_priority_break_up", n("Priority Sector"),
                 [(1, n("Priority - Agriculture and Allied Activities")), (1, n("Priority - MSE")),
                  (1, n("Other Priority Sector"))])

    aq = "asset_quality"
    formula(aq, "9. Gross NPAs to Gross Advances (%)", "8. Gross NPAs NPAs at the end of the Period (a+b+c)", "1. Gross Advances")
    formula(aq, "16. Net NPAs to Net Advances (%)", "15. Net NPAs", "14. Net Advances")
    formula(aq, "18. Restructured Std Adv to Gross Advances (%)", "17. Restructured Standard Advances", "1. Gross Advances")
    formula(aq, "20. Stressed Advances (GNPAs+RestStdAdv) to Gross Advances (%)", "19. Stressed Advances (GNPAs+RestStdAdv)", "1. Gross Advances")
    identity(aq, "8. Gross NPAs NPAs at the end of the Period (a+b+c)",
             [(1, "a. Sub-standard advances"), (1, "b. Doubtful advances"), (1, "c. Loss advances")])
    identity(aq, "19. Stressed Advances (GNPAs+RestStdAdv)",
             [(1, "8. Gross NPAs NPAs at the end of the Period (a+b+c)"), (1, "17. Restructured Standard Advances")])

    ca = "capital_adequacy"
    for r, n in (("Capital Ratio (CRAR)-Standalone", "Total Capital-Standalone"),
                 ("Tier I Capital Ratio-Standalone", "Tier I Capital-Standalone"),
                 ("CET I Capital Ratio-Standalone", "Common Equity Tier I Capital -Standalone"),
                 ("Tier 2 Capital Ratio-Standalone", "Tier II Capital-Standalone")):
        formula(ca, r, n, "Total RWAs-Standalone (a+b+c)")
    identity(ca, "Total Capital-Standalone", [(1, "Tier I Capital-Standalone"), (1, "Tier II Capital-Standalone")])
    identity(ca, "Total RWAs-Standalone (a+b+c)", [(1, "a. Total RWAs (Credit Risk)-Standalone"),
                                                   (1, "b. Total RWAs (Market Risk)-Standalone"),
                                                   (1, "c. Total RWAs (Operational Risk)-Standalone")])

    bs = "major_balance_sheet_items"
    identity(bs, "Total Deposits (a+b)", [(1, "a. Customer Deposits (i+ii+iii+iv+v)"), (1, "b. Deposits of Banks (i+ii)")])
    identity(bs, "a. Customer Deposits (i+ii+iii+iv+v)", [(1, x) for x in ("i. Current Deposits", "ii. Savings Deposits",
             "iii. Time Deposits", "iV. NRI Deposits", "V. Certificates of Deposits")])
    identity(bs, "b. Deposits of Banks (i+ii)", [(1, "i. Banks in India"), (1, "ii. Overseas Banks")])
    identity(bs, "Total Assets", [(1, x) for x in ("Cash Funds", "Due from Banks/FIs/CCPs", "SLR/Approved Securities",
             "Non-SLR Investments", "Net Loans and Advances", "Fixed Assets (net)", "Other Assets")])
    identity(bs, "Total Capital & Liabilities", [(1, x) for x in ("Paid-up Share Capital", "Reserves & Surplus",
             "Total Deposits (a+b)", "Total Borrowings", "Other liabilities")])
    identity(bs, "Total Assets", [(1, "Total Capital & Liabilities")])

    pf = "profitability"
    L = {k.split(".")[0]: k for k in S[pf]["labels"] if k[:2].strip(".").isdigit()}
    identity(pf, L["3"], [(1, L["1"]), (-1, L["2"])])
    identity(pf, L["5"], [(1, L["3"]), (1, L["4"])])
    identity(pf, L["7"], [(1, L["5"]), (-1, L["6"])])
    identity(pf, L["10"], [(1, L["7"]), (1, L["8"]), (1, L["9"])])

    inf = "infrastructure_financing_items"
    labels = list(S[inf]["labels"])
    num = {lab: lab.split(" ", 1)[0].rstrip(".") for lab in labels if re.match(r"^\d+(\.\d+)*\.? ", lab)}
    tops = [lab for lab, n in num.items() if "." not in n]
    identity(inf, "Total", [(1, t) for t in tops])
    for lab, n in num.items():
        kids = [k for k, m in num.items() if m.startswith(n + ".") and m.count(".") == n.count(".") + 1]
        if kids:
            identity(inf, lab, [(1, k) for k in kids])
    return out


# ── the checks ────────────────────────────────────────────────────────────────

def close(a: float, b: float, abs_tol: float, rel_tol: float = 0.0) -> bool:
    return abs(a - b) <= max(abs_tol, rel_tol * max(abs(a), abs(b)))


def check_quarter(q: dict, st: dict, B: dict = BOUNDS) -> dict[str, list[str]]:
    """{check: [failures]} for one saved quarter (its `banks` and `groups`)."""
    f = {k: [] for k in ("5.1", "5.2", "5.3", "5.4", "5.5")}
    banks, groups = q["banks"], q["groups"]
    v = lambda e, s, c: (e["sheets"].get(s) or {}).get(c)  # noqa: E731
    # 5.1 sums
    for gid, g in groups.items():
        if not g["members"] and gid != "group:scb":
            f["5.1"].append(f"{gid}: closes no block and is not a declared total")
            continue
        if gid == "group:scb" and [x for x in SCB_MEMBERS if x not in groups]:
            f["5.1"].append(f"group:scb: member group(s) {[x for x in SCB_MEMBERS if x not in groups]} absent")
        for sid, s in st.items():
            if sid not in g["sheets"]:
                continue
            members = ([groups[x] for x in SCB_MEMBERS if x in groups] if gid == "group:scb"
                       else [banks[b] for b in g.get("members_by_sheet", {}).get(sid, g["members"])])
            for c in s["amounts"]:
                gv = v(g, sid, c)
                parts = [v(m, sid, c) for m in members]
                if gv is None and all(p is None for p in parts):
                    continue
                tot = sum(p or 0.0 for p in parts)
                if gv is None and close(tot, 0.0, B["sum_abs"]):
                    continue                     # RBI prints nothing over parts that are all zero
                if gv is None or not close(gv, tot, B["sum_abs"], B["sum_rel"]):
                    f["5.1"].append(f"{gid} {sid} {c}: printed {gv} vs banks {tot:.4f}")
    ents = [(b, e) for b, e in banks.items()] + [(g, e) for g, e in groups.items()]
    for name, e in ents:
        for sid, s in st.items():
            # 5.2 ratios
            for r, n, d in s["formulas"]:
                rv, nv, dv = v(e, sid, r), v(e, sid, n), v(e, sid, d)
                if dv in (None, 0) or nv is None:
                    if rv not in (None, 0):
                        f["5.2"].append(f"{name} {sid} {r}: printed {rv} with denominator {dv}")
                    continue
                if rv is None:
                    if nv != 0:                  # RBI prints a 0% ratio as blank (GNPAs 0)
                        f["5.2"].append(f"{name} {sid} {r}: null with denominator {dv}, numerator {nv}")
                elif not close(rv, 100 * nv / dv, B["ratio_abs"]):
                    f["5.2"].append(f"{name} {sid} {r}: printed {rv} vs {100 * nv / dv:.6f}")
            # 5.3 global
            for lab, d in s["labels"].items():
                if lab and set(d) == {"dom", "ovs", "glb"} and d["dom"] in s["amounts"] and sid in GLOBAL_ADDS:
                    a, o, g = (v(e, sid, d[k]) for k in ("dom", "ovs", "glb"))
                    if g is not None and not close((a or 0) + (o or 0), g, B["global_abs"]):
                        f["5.3"].append(f"{name} {sid} {lab}: {a} + {o} vs {g}")
            # 5.4 parts
            for tot, parts in s["identities"]:
                tv = v(e, sid, tot)
                pv = [(sg, v(e, sid, p), p) for sg, p in parts]
                if tv is None and all(x is None for _, x, _ in pv):
                    continue
                got = sum(sg * (x or 0.0) for sg, x, _ in pv)
                if tv is None and close(got, 0.0, B["part_abs"]):
                    continue
                if tv is None or not close(tv, got, B["part_abs"], B["part_rel"]):
                    f["5.4"].append(f"{name} {sid} {tot}: {tv} vs parts {got:.4f}")
                for sg, x, p in pv:
                    if sg > 0 and x is not None and x < -B["negative_abs"] and sid in NON_NEGATIVE:
                        f["5.4"].append(f"{name} {sid} {p}: negative part {x}")
    # 5.5 every bank on every sheet
    for b, e in banks.items():
        missing = [sid for sid in st if sid not in e["sheets"] and e.get("group") not in NOT_COVERED.get(sid, ())]
        if missing:
            f["5.5"].append(f"{b}: absent from {missing}")
    return f


CREDIT = ("major_sectoral", "priority_non_priority_break_up")


def not_reported(q: dict) -> list[str]:
    """5.6: banks whose credit sheets are all zero while Asset Quality or the balance sheet show a book."""
    out = []
    for b, e in q["banks"].items():
        credit = [x for s in CREDIT for x in (e["sheets"].get(s) or {}).values() if x]
        book = [x for s in ("asset_quality", "major_balance_sheet_items")
                for c, x in (e["sheets"].get(s) or {}).items() if x and ("advances" in c or "loans" in c)]
        if not credit and book:
            out.append(b)
    return out


def sibc_nonfood(period: str) -> float | None:
    try:
        path = manifest.consolidated_csv("sibc")
    except Exception:
        return None
    best = None
    with path.open() as fh:
        for r in csv.DictReader(fh):
            if r["sector"] == "Non-food Credit" and r["date"][:7] == period[:7]:
                if best is None or r["report_date"] > best[0]:
                    best = (r["report_date"], float(r["outstanding_cr"]))
    return best[1] if best else None


def scale(quarters: dict[str, dict], st: dict, B: dict = BOUNDS) -> list[str]:
    """5.7: All SCBs gross advances against the previous saved quarter and SIBC non-food."""
    out, prev = [], None
    for p in sorted(quarters):
        g = quarters[p]["groups"].get("group:scb", {})
        ga = (g.get("sheets", {}).get("major_sectoral") or {}).get("gross_advances@dom")
        if ga is None:
            out.append(f"{p}: no All SCBs gross advances")
            continue
        if prev and not (1 - B["scale_band"]) <= ga / prev <= (1 + B["scale_band"]) * 2:
            out.append(f"{p}: All SCBs gross advances {ga:,.0f} vs previous saved {prev:,.0f}")
        s = sibc_nonfood(p)
        if s and not (1 - B["scale_band"]) <= ga / s <= 1 + B["scale_band"]:
            out.append(f"{p}: All SCBs gross advances {ga:,.0f} vs SIBC non-food {s:,.0f}")
        prev = ga
    return out


def load_quarters() -> dict[str, dict]:
    import gzip
    rel = manifest.path(PIPELINE, "releases")
    out = {}
    for d in sorted(rel.iterdir()):
        files = sorted(d.glob("*.json.gz"))
        if files:
            out[d.name] = json.loads(gzip.decompress(files[-1].read_bytes()))
    return out


def classify(quarters: dict, st: dict) -> tuple[list[dict], list[dict], dict, dict]:
    """(patterns, flags, named, populations). A pattern is a (quarter, check, column) failing for
    COLUMN_WIDE_BANKS or more banks; everything else unexcepted is a flag on one bank or group."""
    rows, named = [], {k: 0 for k in ("5.1", "5.2", "5.3", "5.4", "5.5")}
    for p, q in sorted(quarters.items()):
        for k, fl in check_quarter(q, st).items():
            for x in fl:
                if excepted(k, p, x):
                    named[k] += 1
                    continue
                ent, col = where(k, x)
                rows.append({"quarter": p, "check": k, "entity": ent, "column": col, "detail": x})
    banks_by = {}
    for r in rows:
        if not r["entity"].startswith("group:"):
            banks_by.setdefault((r["quarter"], r["check"], r["column"]), set()).add(r["entity"])
    wide = {key for key, b in banks_by.items() if len(b) >= COLUMN_WIDE_BANKS}
    patterns = [r for r in rows if (r["quarter"], r["check"], r["column"]) in wide]
    flags = [r for r in rows if (r["quarter"], r["check"], r["column"]) not in wide]
    n_ent = sum(len(q["banks"]) + len(q["groups"]) for q in quarters.values())
    pops = {"5.1": f"{sum(len(q['groups']) for q in quarters.values())} group rows × {sum(len(s['amounts']) for s in st.values())} amount columns",
            "5.2": f"{n_ent} rows × {sum(len(s['formulas']) for s in st.values())} printed ratios",
            "5.3": f"{n_ent} rows × credit measures printed three ways",
            "5.4": f"{n_ent} rows × {sum(len(s['identities']) for s in st.values())} identities",
            "5.5": f"{sum(len(q['banks']) for q in quarters.values())} bank-quarters × {len(st)} sheets"}
    return patterns, flags, named, pops


def run(quarters: dict, st: dict) -> tuple[bool, list[str], list[dict]]:
    patterns, flags, named, pops = classify(quarters, st)
    lines, ok = [], not patterns
    for k in pops:
        pk = [r for r in patterns if r["check"] == k]
        fk = [r for r in flags if r["check"] == k]
        lines.append(f"{'✓' if not pk else '✗'} {k} {pops[k]}: {len(pk)} column-wide failure(s), "
                     f"{len(fk)} flagged in {len({(r['quarter'], r['entity']) for r in fk})} bank/group-quarter(s)"
                     + (f", {named[k]} named exception(s)" if named[k] else "")
                     + "".join(f"\n      {r['detail']}" for r in pk[:6]))
    zeros = {p: not_reported(q) for p, q in quarters.items()}
    lines.append("· 5.6 not_reported (credit sheets all zero, a book elsewhere): " +
                 ("; ".join(f"{p}: {', '.join(z)}" for p, z in sorted(zeros.items()) if z) or "none"))
    sc = scale(quarters, st)
    ok &= not sc
    lines.append(f"{'✓' if not sc else '✗'} 5.7 scale, {len(quarters)} quarters: {len(sc)} failure(s)"
                 + "".join(f"\n      {x}" for x in sc[:6]))
    return ok, lines, flags


def write_flags(flags: list[dict]) -> Path:
    """The record of where RBI's own figures disagree, one row per failure, for signals to honour."""
    out = manifest.path(PIPELINE, "data_dir") / FLAGS
    doc = {"_meta": {"what": "cells where RBI's own bank-wise figures fail a check in one bank or group "
                             "(BANKWISE_SPEC §5); a signal never publishes a flagged cell as if it held",
                     "rule": f"isolated = fewer than {COLUMN_WIDE_BANKS} banks failing the same column in a quarter",
                     "count": len(flags)},
           "flags": sorted(flags, key=lambda r: (r["quarter"], r["check"], r["entity"], r["column"]))}
    out.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
    return out


def measure(quarters: dict, st: dict) -> None:
    """The observed gaps, for setting BOUNDS once."""
    loose = {k: 1e18 for k in BOUNDS}
    worst = {}
    for p, q in quarters.items():
        for k, fl in check_quarter(q, st, {**loose, "negative_abs": 0.0}).items():
            pass
    import math
    gaps = {"5.1": 0.0, "5.2": 0.0, "5.3": 0.0, "5.4": 0.0}
    v = lambda e, s, c: (e["sheets"].get(s) or {}).get(c)  # noqa: E731
    for q in quarters.values():
        for gid, g in q["groups"].items():
            members = [q["banks"][b] for b in g["members"]] or [q["groups"][x] for x in SCB_MEMBERS if x in q["groups"]]
            for sid, s in st.items():
                for c in s["amounts"]:
                    gv = v(g, sid, c)
                    if gv is not None:
                        gaps["5.1"] = max(gaps["5.1"], abs(gv - sum(v(m, sid, c) or 0 for m in members)))
        for e in list(q["banks"].values()) + list(q["groups"].values()):
            for sid, s in st.items():
                for r, n, d in s["formulas"]:
                    rv, nv, dv = v(e, sid, r), v(e, sid, n), v(e, sid, d)
                    if rv is not None and nv is not None and dv:
                        gaps["5.2"] = max(gaps["5.2"], abs(rv - 100 * nv / dv))
                for tot, parts in s["identities"]:
                    tv = v(e, sid, tot)
                    if tv is not None:
                        gaps["5.4"] = max(gaps["5.4"], abs(tv - sum(sg * (v(e, sid, p) or 0) for sg, p in parts)))
    for k, g in gaps.items():
        print(f"  {k}: max observed gap {g:.6g}")


def main() -> int:
    ap = argparse.ArgumentParser(description="bank-wise checks against RBI's own totals")
    ap.add_argument("--measure", action="store_true")
    ap.add_argument("--write-flags", action="store_true", help="write the flagged cells for signals to honour")
    a = ap.parse_args()
    declared = json.loads(manifest.path(PIPELINE, "sheets").read_text())
    st = structure(declared)
    quarters = load_quarters()
    if not quarters:
        print("  ✗ no saved quarters")
        return 1
    if a.measure:
        measure(quarters, st)
        return 0
    ok, lines, flags = run(quarters, st)
    for line in lines:
        print("  " + line)
    if a.write_flags:
        print(f"  → {write_flags(flags).relative_to(manifest.path(PIPELINE, 'data_dir').parents[1])}: {len(flags)} flag(s)")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
