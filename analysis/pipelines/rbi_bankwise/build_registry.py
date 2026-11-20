#!/usr/bin/env python3
"""
build_registry.py — the bank-wise signals, written into registry.json from one declared list
──────────────────────────────────────────────────────────────────────────────────────────────
BANKWISE_SPEC §8a. The measures are the skeleton's entities (`rbi_bankwise/skeleton_profile.json`,
one list, never retyped here) plus the gross NPA ratio. Each measure gets the same family, computed
by the payments module (`signals/compute/atm_pos.py`): every bank's size, share of all banks,
growth a year, crore added over the year and share of the year's new money; the total's growth; the bank groups' size, share and
growth; and (new) the measure's share of each bank's own book. Rewrites only `rbi_bankwise`
entries, so re-running it is a no-op when nothing changed.

    python3 analysis/pipelines/rbi_bankwise/build_registry.py [--check]
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
REG = ROOT / "analysis/signals/registry.json"
PROFILE = ROOT / "analysis/rbi_bankwise/skeleton_profile.json"
PIPELINE = "rbi_bankwise"
FIRST = "2015-03-31"
GROSS = "major_sectoral.gross_advances@dom"
GNPA = "major_sectoral.gross_npas_to_gross_advances@dom"
DOMAIN = {"gross": "credit_headline", "food": "credit_headline", "non_food": "credit_headline",
          "other_non_food": "credit_headline", "agri": "sector_mix", "industry": "industry",
          "services": "sector_mix", "retail": "retail", "housing": "retail", "vehicle": "retail",
          "cards": "retail", "education": "retail", "other_retail": "retail"}
RISING = [{"if": "value > prev_value", "then": "strengthening"},
          {"if": "value < prev_value", "then": "weakening"}, {"if": "true", "then": "active"}]


def entries() -> dict[str, dict]:
    nodes = json.loads(PROFILE.read_text())["nodes"]
    out = {}

    def add(sid, title, desc, compute, domain, unit_note=""):
        out[sid] = {"id": sid, "title": title, "description": desc, "pipeline": PIPELINE, "layer": 1,
                    "sub_layer": "1c", "type": "data", "cadence": "quarterly", "domain": domain,
                    "spec_version": "1.0", "first_seen": FIRST, "current_status": "active",
                    "compute": compute}

    for n in nodes:
        m, code, lab, dom = n["metric"], n["code"], n["label"].lower(), DOMAIN[n["code"]]
        p = f"bw-{code.replace('_', '-')}"
        add(f"{p}-bank-scan", f"{n['label']} — per bank",
            f"Domestic gross advances in {lab} for every scheduled commercial bank, each quarter.",
            {"method": "csv_bank_scan", "metric": m, "unit": "crore", "status_rules": RISING}, dom)
        add(f"{p}-bank-share-scan", f"{n['label']} — each bank's share of all banks",
            f"Each bank's share of all banks' {lab}; denominator RBI's All SCBs row.",
            {"method": "csv_bank_scan_share", "metric": m, "status_rules": RISING}, dom)
        add(f"{p}-bank-yoy-scan", f"{n['label']} — per-bank growth a year",
            f"Year-on-year change in each bank's {lab}; absent with merger_break across a declared merger.",
            {"method": "csv_bank_scan", "metric": m, "value_type": "yoy", "status_rules": RISING}, dom)
        add(f"{p}-bank-momentum", f"{n['label']} — crore each bank added over the year",
            f"Each bank's change in {lab} over the year, with the net, gross and coherence that bound "
            f"its share of the year's new money; absent across a declared merger.",
            {"method": "csv_bank_momentum", "metric": m, "unit": "crore", "window": 12}, dom)
        add(f"{p}-bank-allocation", f"{n['label']} — each bank's share of the year's new money",
            f"Of the year's change in {lab}, how much each bank added or lost (contribution, always; "
            f"alloc when banks moved together); absent across a declared merger.",
            {"method": "csv_bank_allocation", "metric": m, "unit": "crore", "window": 12}, dom)
        add(f"{p}-bank-acceleration", f"{n['label']} — each bank's pace",
            f"The change in each bank's growth a year in {lab} since the previous quarter, in points; "
            f"absent across a declared merger.",
            {"method": "csv_bank_acceleration", "metric": m}, dom)
        add(f"{p}-yoy", f"{n['label']} — all banks, growth a year",
            f"Year-on-year change in all banks' {lab} (RBI's All SCBs row).",
            {"method": "csv_total_yoy", "metric": m}, dom)
        add(f"{p}-category-size-scan", f"{n['label']} — per bank group",
            f"{n['label']} for each bank group, the sum of its banks as RBI printed them that quarter.",
            {"method": "csv_category_scan_abs", "metric": m, "unit": "crore", "window": 12,
             "status_rules": [{"if": "value > prev_value", "then": "active"}, {"if": "true", "then": "declining"}]}, dom)
        add(f"{p}-category-momentum", f"{n['label']} — crore each bank group added over the year",
            f"Each bank group's change in {lab} over the year, with the net, gross and coherence; "
            f"absent across a declared merger.",
            {"method": "csv_category_momentum", "metric": m, "unit": "crore", "window": 12}, dom)
        add(f"{p}-category-allocation", f"{n['label']} — each bank group's share of the year's new money",
            f"Of the year's change in {lab}, how much each bank group added or lost.",
            {"method": "csv_category_allocation", "metric": m, "window": 12, "coherence_min": 0.9}, dom)
        add(f"{p}-category-acceleration", f"{n['label']} — each bank group's pace",
            f"The change in each bank group's growth a year since the previous quarter, in points.",
            {"method": "csv_category_acceleration", "metric": m}, dom)
        add(f"{p}-category-share-scan", f"{n['label']} — each bank group's share",
            f"Each bank group's share of all banks' {lab}.",
            {"method": "csv_category_scan_share", "metric": m, "status_rules": RISING}, dom)
        add(f"{p}-category-yoy-scan", f"{n['label']} — per bank group growth a year",
            f"Year-on-year change in each bank group's {lab}.",
            {"method": "csv_category_scan_yoy", "metric": m, "status_rules": RISING}, dom)
        if m != GROSS:
            add(f"{p}-of-book-scan", f"{n['label']} — share of each bank's own book",
                f"Each bank's {lab} as a share of its own domestic gross advances (absent with no_book "
                f"for a bank with none).",
                {"method": "csv_bank_ratio_scan", "metric": m, "denominator_metric": GROSS}, dom)
    add("bw-gnpa-ratio-bank-scan", "Gross NPA ratio — per bank",
        "Each bank's gross NPAs as a share of its domestic gross advances, as RBI prints it (Major Sectoral).",
        {"method": "csv_bank_scan", "metric": GNPA, "unit": "pct", "status_rules": RISING,
         "table_column": {"metric": GROSS, "column": "gnpa"}}, "credit_stress")
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    a = ap.parse_args()
    reg = json.loads(REG.read_text())
    want = entries()
    have = {k: v for k, v in reg["signals"].items() if v.get("pipeline") == PIPELINE}
    # current_status is the engine's to update; compare the declaration, not the live status.
    strip = lambda d: {k: v for k, v in d.items() if k != "current_status"}  # noqa: E731
    same = set(want) == set(have) and all(strip(want[k]) == strip(have[k]) for k in want)
    if a.check:
        print(f"  {'✓' if same else '✗'} {len(want)} rbi_bankwise registry entries {'match' if same else 'differ from'} the profile")
        return 0 if same else 1
    for k in have:
        if k not in want:
            del reg["signals"][k]
    for k, v in want.items():
        v["current_status"] = have.get(k, {}).get("current_status", v["current_status"])
        reg["signals"][k] = v
    reg["pipelines"][PIPELINE] = {"id": PIPELINE, "name": "RBI bank-wise quarterly variables (DBIE)",
                                  "cadence": "quarterly", "domain_primary": "credit", "snapshot_path": None,
                                  "insight_source": None,
                                  "description": "Every scheduled commercial bank's credit by sector, quarterly from Mar 2015"}
    REG.write_text(json.dumps(reg, indent=2, ensure_ascii=False) + "\n")
    print(f"  ✓ wrote {len(want)} rbi_bankwise registry entries")
    return 0


if __name__ == "__main__":
    sys.exit(main())
