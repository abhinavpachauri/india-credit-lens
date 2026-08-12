"""
Rebuild SIBC Layer 1 signal definitions in registry.json.

Removes all existing SIBC L1 signals and replaces with the v1.0 spec:
  5 × 1a  — system-level aggregates
  27 × 1b — named sector/sub-sector scalars
  7 × 1c  — full entity scans
  = 39 total

Run once. Safe to re-run (idempotent).
"""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO
REG_PATH = REPO / "analysis" / "signals" / "registry.json"

# ── Signal definitions ────────────────────────────────────────────────────────

SIBC_L1_SIGNALS: dict[str, dict] = {

    # ── 1a: system-level aggregates ──────────────────────────────────────────

    "sibc-bank-credit-yoy": {
        "title":        "Bank credit YoY growth (%)",
        "type":         "data",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_headline",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "bankCredit",
            "series":  "Bank Credit",
        },
    },

    "sibc-bank-credit-abs": {
        "title":        "Bank credit absolute volume (₹Cr)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_headline",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_abs",
            "section": "bankCredit",
            "series":  "Bank Credit",
            "unit":    "lcr_cr",
        },
    },

    "sibc-nonfood-credit-yoy": {
        "title":        "Non-food credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_headline",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "bankCredit",
            "series":  "Non-food Credit",
        },
    },

    "sibc-nonfood-credit-abs": {
        "title":        "Non-food credit absolute volume (₹Cr)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_headline",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_abs",
            "section": "bankCredit",
            "series":  "Non-food Credit",
            "unit":    "lcr_cr",
        },
    },

    "sibc-sectors-positive-yoy-count": {
        "title":        "Number of main sectors with positive YoY (breadth)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_headline",
        "spec_version": "1.0",
        "compute": {
            "method":  "count_positive_yoy",
            "section": "mainSectors",
        },
    },

    # ── 1b: main sectors ─────────────────────────────────────────────────────

    "sibc-agriculture-yoy": {
        "title":        "Agriculture credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "mainSectors",
            "series":  "Agriculture",
        },
    },

    "sibc-agriculture-share": {
        "title":        "Agriculture share of total credit (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "mainSectors",
            "series":  "Agriculture",
        },
    },

    "sibc-industry-yoy": {
        "title":        "Industry credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "mainSectors",
            "series":  "Industry",
        },
    },

    "sibc-industry-share": {
        "title":        "Industry share of total credit (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "mainSectors",
            "series":  "Industry",
        },
    },

    "sibc-services-yoy": {
        "title":        "Services credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "mainSectors",
            "series":  "Services",
        },
    },

    "sibc-services-share": {
        "title":        "Services share of total credit (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "mainSectors",
            "series":  "Services",
        },
    },

    "sibc-personal-loans-yoy": {
        "title":        "Personal loans credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "mainSectors",
            "series":  "Personal Loans",
        },
    },

    "sibc-personal-loans-share": {
        "title":        "Personal loans share of total credit (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "mainSectors",
            "series":  "Personal Loans",
        },
    },

    # ── 1b: industry by size ─────────────────────────────────────────────────

    "sibc-msme-micro-small-yoy": {
        "title":        "Micro & Small enterprises credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "industryBySize",
            "series":  "Micro and Small",
        },
    },

    "sibc-msme-micro-small-share": {
        "title":        "Micro & Small share of industry credit (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "industryBySize",
            "series":  "Micro and Small",
        },
    },

    "sibc-msme-medium-yoy": {
        "title":        "Medium enterprises credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "industryBySize",
            "series":  "Medium",
        },
    },

    "sibc-msme-medium-share": {
        "title":        "Medium enterprises share of industry credit (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "industryBySize",
            "series":  "Medium",
        },
    },

    "sibc-large-corporate-yoy": {
        "title":        "Large corporate credit YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "industryBySize",
            "series":  "Large",
        },
    },

    "sibc-large-corporate-share": {
        "title":        "Large corporate share of industry credit (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "industryBySize",
            "series":  "Large",
        },
    },

    "sibc-msme-size-yoy-spread": {
        "title":        "MSME vs Large corporate YoY spread (pp)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":   "yoy_spread_named",
            "section":  "industryBySize",
            "series_a": "Micro and Small",
            "series_b": "Large",
        },
    },

    # ── 1b: personal loans ───────────────────────────────────────────────────

    "sibc-pl-housing-yoy": {
        "title":        "Housing loans YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "personalLoans",
            "series":  "Housing",
        },
    },

    "sibc-pl-housing-share": {
        "title":        "Housing share of personal loans (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "personalLoans",
            "series":  "Housing",
        },
    },

    "sibc-pl-gold-yoy": {
        "title":        "Gold loans YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "personalLoans",
            "series":  "Gold Loans",
        },
    },

    "sibc-pl-gold-share": {
        "title":        "Gold loans share of personal loans (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "personalLoans",
            "series":  "Gold Loans",
        },
    },

    "sibc-pl-cc-yoy": {
        "title":        "Credit card outstanding YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "personalLoans",
            "series":  "Credit Card Outstanding",
        },
    },

    "sibc-pl-cc-share": {
        "title":        "Credit cards share of personal loans (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_share",
            "section": "personalLoans",
            "series":  "Credit Card Outstanding",
        },
    },

    "sibc-pl-vehicle-yoy": {
        "title":        "Vehicle loans YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "personalLoans",
            "series":  "Vehicle Loans",
        },
    },

    "sibc-pl-education-yoy": {
        "title":        "Education loans YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "personalLoans",
            "series":  "Education",
        },
    },

    # ── 1b: priority sector ──────────────────────────────────────────────────

    "sibc-psl-agri-yoy": {
        "title":        "PSL Agriculture YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "psl",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "prioritySector",
            "series":  "Agriculture",
        },
    },

    "sibc-psl-msme-yoy": {
        "title":        "PSL Micro & Small enterprises YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "psl",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "prioritySector",
            "series":  "Micro and Small Enterprises",
        },
    },

    "sibc-psl-housing-yoy": {
        "title":        "PSL Housing YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "psl",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "prioritySector",
            "series":  "Housing",
        },
    },

    "sibc-psl-renewable-yoy": {
        "title":        "PSL Renewable Energy YoY growth (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "psl",
        "spec_version": "1.0",
        "compute": {
            "method":  "series_yoy",
            "section": "prioritySector",
            "series":  "Renewable Energy",
        },
    },

    # ── 1c: full entity scans ────────────────────────────────────────────────

    "sibc-industry-type-yoy-scan": {
        "title":        "YoY growth scan — all industry types (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":      "section_scan_yoy",
            "section":     "industryByType",
            "entity_type": "industry_type",
        },
    },

    "sibc-industry-type-share-scan": {
        "title":        "Share scan — all industry types (% of industry credit)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "industry",
        "spec_version": "1.0",
        "compute": {
            "method":      "section_scan_share",
            "section":     "industryByType",
            "entity_type": "industry_type",
        },
    },

    "sibc-services-yoy-scan": {
        "title":        "YoY growth scan — all services sub-sectors (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":      "section_scan_yoy",
            "section":     "services",
            "entity_type": "service_sector",
        },
    },

    "sibc-services-share-scan": {
        "title":        "Share scan — all services sub-sectors (% of services credit)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "sector_mix",
        "spec_version": "1.0",
        "compute": {
            "method":      "section_scan_share",
            "section":     "services",
            "entity_type": "service_sector",
        },
    },

    "sibc-pl-yoy-scan": {
        "title":        "YoY growth scan — all personal loan sub-categories (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":      "section_scan_yoy",
            "section":     "personalLoans",
            "entity_type": "pl_category",
        },
    },

    "sibc-pl-share-scan": {
        "title":        "Share scan — all personal loan sub-categories (% of PL)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "retail",
        "spec_version": "1.0",
        "compute": {
            "method":      "section_scan_share",
            "section":     "personalLoans",
            "entity_type": "pl_category",
        },
    },

    "sibc-psl-yoy-scan": {
        "title":        "YoY growth scan — all PSL sub-categories (%)",
        "pipeline":     "sibc",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "psl",
        "spec_version": "1.0",
        "compute": {
            "method":      "section_scan_yoy",
            "section":     "prioritySector",
            "entity_type": "psl_category",
        },
    },
}


# ── Update registry ───────────────────────────────────────────────────────────

def main():
    with open(REG_PATH) as f:
        reg = json.load(f)

    # Remove all existing SIBC Layer 1 signals
    old_ids = [sid for sid, s in reg["signals"].items()
               if s.get("pipeline") == "sibc" and s.get("layer") == 1]
    for sid in old_ids:
        del reg["signals"][sid]
    print(f"Removed {len(old_ids)} old SIBC L1 signals")

    # Add new signals (preserve current_status/first_seen stubs)
    for sid, sig in SIBC_L1_SIGNALS.items():
        sig["id"]             = sid
        sig.setdefault("type", "data")
        sig["current_status"] = None
        sig["first_seen"]     = None
        reg["signals"][sid]   = sig

    print(f"Added {len(SIBC_L1_SIGNALS)} new SIBC L1 signals")

    with open(REG_PATH, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Verify counts
    sibc_l1 = [s for s in reg["signals"].values()
               if s.get("pipeline") == "sibc" and s.get("layer") == 1]
    by_sublayer = {}
    for s in sibc_l1:
        sl = s.get("sub_layer", "?")
        by_sublayer[sl] = by_sublayer.get(sl, 0) + 1
    print(f"Total SIBC L1: {len(sibc_l1)}")
    for sl, n in sorted(by_sublayer.items()):
        print(f"  {sl}: {n}")


if __name__ == "__main__":
    main()
