"""
test_card_routing.py — which SIBC signals become cards, and under which section
───────────────────────────────────────────────────────────────────────────────
Both were hand-kept lists, and both failed the first month new signals reached an evaluation
(Aug 2026 ingest, 2026-10-02): 17 table-family cards and one infra card under sections whose charts
cannot draw them. The card↔chart check (5.7) caught every one. These pin the two derived rules.
"""
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))
sys.path.insert(0, str(ROOT / "analysis" / "pipelines" / "sibc"))

import generate_analysis_report as G                       # noqa: E402

REG = json.loads((ROOT / "analysis/signals/registry.json").read_text())
SIGS = REG["signals"] if isinstance(REG, dict) and "signals" in REG else REG
LIVE = [s for s in (SIGS.values() if isinstance(SIGS, dict) else SIGS)
        if s.get("pipeline") == "sibc" and s.get("layer") == 1 and not s.get("retire_period")]


def test_size_and_share_of_book_are_table_only():
    assert G.is_table_family({"method": "csv_sector_scan_abs", "parent_code": "2.18"})
    assert G.is_table_family({"method": "csv_sector_scan_share", "parent_code": "2.18",
                              "statement": "Statement 2", "denominator_code": "I",
                              "denominator_statement": "Statement 1"})


def test_a_share_of_its_own_parent_is_still_a_card():
    assert not G.is_table_family({"method": "csv_sector_scan_share", "parent_code": "2.18",
                                  "statement": "Statement 2", "denominator_code": "2.18",
                                  "denominator_statement": "Statement 2"})


def test_every_live_signal_with_a_cut_routes_to_a_section_that_draws_it():
    """Derived, over the whole registry: a signal whose cut resolves lands on the section whose
    chart draws that cut. The old list sent infra (Statement 2, 2.18) to main sectors."""
    secs = G.sibc_sections()
    infra = next(s for s in LIVE if s["id"] == "sibc-infra-yoy")
    assert G.section_from_cut(G.sibc_cut(infra["compute"]), secs) == "industryByType"
    for s in LIVE:
        sec = G.section_from_cut(G.sibc_cut(s.get("compute", {})), secs)
        if sec is None:
            continue
        cut = G.sibc_cut(s["compute"])
        drawn = secs[sec]
        assert drawn["statement"] == cut.statement, f"{s['id']} → {sec}: another statement"
