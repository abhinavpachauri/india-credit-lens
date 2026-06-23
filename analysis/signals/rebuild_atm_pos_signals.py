"""
Rebuild ATM/POS Layer 1 signal definitions in registry.json.

Removes all existing ATM/POS L1 signals and replaces with the v1.0 spec:
  22 × 1a — system-level aggregates
  6  × 1b — named bank category scalars (PSB vs Private)
  5  × 1c — full entity scans
  = 33 total

Run once. Safe to re-run (idempotent).
"""

import json
from pathlib import Path

import sys
sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT as REPO
REG_PATH = REPO / "analysis" / "signals" / "registry.json"

_CC_ALL_VAL  = ["cc_pos_txn_val", "cc_ecom_txn_val", "cc_atm_withdrawal_val", "cc_other_txn_val"]
_DC_ALL_VAL  = ["dc_atm_withdrawal_val", "dc_pos_txn_val", "dc_ecom_txn_val",
                "dc_pos_withdrawal_val", "dc_other_txn_val"]

ATM_POS_L1_SIGNALS: dict[str, dict] = {

    # ── 1a: infrastructure ───────────────────────────────────────────────────

    "atm-onsite-abs": {
        "title":        "Onsite ATMs — absolute count",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_abs", "metric": "atm_onsite"},
    },

    "atm-onsite-yoy": {
        "title":        "Onsite ATMs YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "atm_onsite"},
    },

    "atm-offsite-abs": {
        "title":        "Offsite ATMs — absolute count",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_abs", "metric": "atm_offsite"},
    },

    "atm-offsite-yoy": {
        "title":        "Offsite ATMs YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "atm_offsite"},
    },

    "pos-terminals-abs": {
        "title":        "POS terminals — absolute count",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_abs", "metric": "pos_terminals"},
    },

    "pos-terminals-yoy": {
        "title":        "POS terminals YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "pos_terminals"},
    },

    "upi-qr-yoy": {
        "title":        "UPI QR codes YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "upi_qr"},
    },

    "bharat-qr-yoy": {
        "title":        "Bharat QR codes YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "bharat_qr"},
    },

    "micro-atm-yoy": {
        "title":        "Micro-ATMs YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "micro_atms"},
    },

    "upi-qr-per-pos": {
        "title":        "UPI QR codes per POS terminal (ratio)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {
            "method":             "csv_total_ratio",
            "metric":             "upi_qr",
            "denominator_metric": "pos_terminals",
            "unit":               "ratio",
        },
    },

    # ── 1a: cards outstanding ────────────────────────────────────────────────

    "cc-outstanding-yoy": {
        "title":        "Credit cards outstanding YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "credit_cards"},
    },

    "dc-outstanding-yoy": {
        "title":        "Debit cards outstanding YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "debit_cards"},
    },

    # ── 1a: credit card channel mix ──────────────────────────────────────────

    "cc-pos-val-yoy": {
        "title":        "CC POS transaction value YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_card_txn",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "cc_pos_txn_val"},
    },

    "cc-ecom-val-yoy": {
        "title":        "CC ecommerce transaction value YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_card_txn",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "cc_ecom_txn_val"},
    },

    "cc-atm-val-yoy": {
        "title":        "CC ATM withdrawal value YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_card_txn",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "cc_atm_withdrawal_val"},
    },

    "cc-ecom-val-share": {
        "title":        "CC ecommerce share of total CC transaction value (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_card_txn",
        "spec_version": "1.0",
        "compute": {
            "method":            "csv_ratio_sum",
            "metric":            "cc_ecom_txn_val",
            "denominator_metrics": _CC_ALL_VAL,
        },
    },

    "cc-atm-val-share": {
        "title":        "CC ATM cash share of total CC transaction value (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "credit_card_txn",
        "spec_version": "1.0",
        "compute": {
            "method":            "csv_ratio_sum",
            "metric":            "cc_atm_withdrawal_val",
            "denominator_metrics": _CC_ALL_VAL,
        },
    },

    # ── 1a: debit card channel mix ───────────────────────────────────────────

    "dc-atm-val-yoy": {
        "title":        "DC ATM withdrawal value YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "debit_card_txn",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "dc_atm_withdrawal_val"},
    },

    "dc-pos-val-yoy": {
        "title":        "DC POS transaction value YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "debit_card_txn",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "dc_pos_txn_val"},
    },

    "dc-ecom-val-yoy": {
        "title":        "DC ecommerce transaction value YoY growth (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "debit_card_txn",
        "spec_version": "1.0",
        "compute": {"method": "csv_total_yoy", "metric": "dc_ecom_txn_val"},
    },

    "dc-atm-val-share": {
        "title":        "DC ATM cash share of total DC transaction value (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "debit_card_txn",
        "spec_version": "1.0",
        "compute": {
            "method":            "csv_ratio_sum",
            "metric":            "dc_atm_withdrawal_val",
            "denominator_metrics": _DC_ALL_VAL,
        },
    },

    "dc-ecom-val-share": {
        "title":        "DC ecommerce share of total DC transaction value (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1a",
        "domain":       "debit_card_txn",
        "spec_version": "1.0",
        "compute": {
            "method":            "csv_ratio_sum",
            "metric":            "dc_ecom_txn_val",
            "denominator_metrics": _DC_ALL_VAL,
        },
    },

    # ── 1b: PSB vs Private named category scalars ────────────────────────────

    "cc-psb-share": {
        "title":        "PSB share of credit cards outstanding (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {
            "method":   "csv_category_share",
            "metric":   "credit_cards",
            "category": "Public Sector Banks",
        },
    },

    "cc-private-share": {
        "title":        "Private bank share of credit cards outstanding (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {
            "method":   "csv_category_share",
            "metric":   "credit_cards",
            "category": "Private Sector Banks",
        },
    },

    "dc-psb-share": {
        "title":        "PSB share of debit cards outstanding (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {
            "method":   "csv_category_share",
            "metric":   "debit_cards",
            "category": "Public Sector Banks",
        },
    },

    "dc-private-share": {
        "title":        "Private bank share of debit cards outstanding (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {
            "method":   "csv_category_share",
            "metric":   "debit_cards",
            "category": "Private Sector Banks",
        },
    },

    "pos-psb-share": {
        "title":        "PSB share of POS terminals (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {
            "method":   "csv_category_share",
            "metric":   "pos_terminals",
            "category": "Public Sector Banks",
        },
    },

    "pos-private-share": {
        "title":        "Private bank share of POS terminals (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1b",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {
            "method":   "csv_category_share",
            "metric":   "pos_terminals",
            "category": "Private Sector Banks",
        },
    },

    # ── 1c: full entity scans ────────────────────────────────────────────────

    "cc-category-share-scan": {
        "title":        "CC outstanding share — every bank category (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {"method": "csv_category_scan_share", "metric": "credit_cards"},
    },

    "dc-category-share-scan": {
        "title":        "DC outstanding share — every bank category (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {"method": "csv_category_scan_share", "metric": "debit_cards"},
    },

    "pos-category-share-scan": {
        "title":        "POS terminal share — every bank category (%)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {"method": "csv_category_scan_share", "metric": "pos_terminals"},
    },

    "cc-bank-scan": {
        "title":        "CC outstanding — every bank (absolute count)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "cards_stock",
        "spec_version": "1.0",
        "compute": {
            "method":     "csv_bank_scan",
            "metric":     "credit_cards",
            "value_type": "value",
        },
    },

    "pos-bank-scan": {
        "title":        "POS terminals — every bank (absolute count)",
        "type":         "data",
        "pipeline":     "atm_pos",
        "layer":        1,
        "sub_layer":    "1c",
        "domain":       "infrastructure",
        "spec_version": "1.0",
        "compute": {
            "method":     "csv_bank_scan",
            "metric":     "pos_terminals",
            "value_type": "value",
        },
    },
}


# ── Update registry ───────────────────────────────────────────────────────────

def main():
    with open(REG_PATH) as f:
        reg = json.load(f)

    # Add new domains
    new_domains = {
        "cards_stock":      "Cards outstanding — credit and debit card counts by issuer category",
        "credit_card_txn":  "Credit card transaction flows — POS, ecommerce, ATM withdrawal: value and channel mix",
        "debit_card_txn":   "Debit card transaction flows — ATM cash, POS, ecommerce: value and channel mix",
    }
    added_domains = 0
    for k, v in new_domains.items():
        if k not in reg["domains"]:
            reg["domains"][k] = v
            added_domains += 1
    print(f"Added {added_domains} new domains")

    # Remove all existing ATM/POS Layer 1 signals
    old_ids = [sid for sid, s in reg["signals"].items()
               if s.get("pipeline") == "atm_pos" and s.get("layer") == 1]
    for sid in old_ids:
        del reg["signals"][sid]
    print(f"Removed {len(old_ids)} old ATM/POS L1 signals")

    # Add new signals
    for sid, sig in ATM_POS_L1_SIGNALS.items():
        sig["id"]             = sid
        sig["current_status"] = None
        sig["first_seen"]     = None
        reg["signals"][sid]   = sig
    print(f"Added {len(ATM_POS_L1_SIGNALS)} new ATM/POS L1 signals")

    with open(REG_PATH, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
        f.write("\n")

    # Verify
    atm_l1 = [s for s in reg["signals"].values()
               if s.get("pipeline") == "atm_pos" and s.get("layer") == 1]
    by_sl = {}
    for s in atm_l1:
        sl = s.get("sub_layer", "?")
        by_sl[sl] = by_sl.get(sl, 0) + 1
    print(f"Total ATM/POS L1: {len(atm_l1)}")
    for sl, n in sorted(by_sl.items()):
        print(f"  {sl}: {n}")
    print(f"Total domains: {len(reg['domains'])}")


if __name__ == "__main__":
    main()
