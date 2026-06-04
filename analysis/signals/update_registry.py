"""
One-time registry update:
  1. Add sub_layer ("1a") to all existing SIBC + ATM/POS Layer 1 signals
  2. Add compute specs to all 21 ATM/POS Layer 1 signals
  3. Re-classify 2 ATM/POS signals to sub_layer "1b" and 5 to "1c"
  4. Add 13 new SIBC Layer 1b signals
  5. Add 4 new SIBC Layer 1c scan signals
  6. Add 3 new ATM/POS Layer 1b signals
"""

import json
from pathlib import Path

REG = Path(__file__).parent / "registry.json"

with open(REG) as f:
    reg = json.load(f)

sigs = reg["signals"]

# ── 1. Mark existing SIBC Layer 1 as sub_layer 1a ─────────────────────────────
for sid, s in sigs.items():
    if s["pipeline"] == "sibc" and s.get("layer") == 1:
        s["sub_layer"] = "1a"

# ── 2. ATM/POS sub_layer classification ───────────────────────────────────────
ATM_1A = {
    "cc-ecom-vs-pos-share", "cc-cards-streak", "cc-txn-surge",
    "dc-atm-share-structural", "dc-pos-cash-decline", "dc-ecom-share",
    "dc-cards-streak", "gap-dc-cash-dominance", "gap-dc-ecom-low",
    "infra-qr-per-pos", "infra-pos-streak", "infra-upi-vs-bharat-qr",
    "gap-bharat-qr-contraction", "gap-atm-offsite-decline",
}
ATM_1B = {"dc-psb-dominance", "gap-foreign-cc-decline"}
ATM_1C = {
    "cc-category-share-shift", "cc-top5-concentration",
    "dc-top-bank-leader", "infra-top-bank-pos", "gap-pos-concentration",
}

for sid, s in sigs.items():
    if s["pipeline"] == "atm_pos" and s.get("layer") == 1:
        if sid in ATM_1A:
            s["sub_layer"] = "1a"
        elif sid in ATM_1B:
            s["sub_layer"] = "1b"
        elif sid in ATM_1C:
            s["sub_layer"] = "1c"

# ── 3. ATM/POS compute specs ──────────────────────────────────────────────────
ATM_COMPUTE = {
    # Layer 1a
    "cc-ecom-vs-pos-share": {
        "method": "csv_ratio_sum", "metric": "cc_ecom_txn_vol",
        "denominator_metrics": ["cc_ecom_txn_vol", "cc_pos_txn_vol"],
        "status_rules": [
            {"if": "value > 50", "then": "strengthening"},
            {"if": "value > 40", "then": "active"},
            {"if": "value > 30", "then": "weakening"},
            {"if": "true",       "then": "reversed"},
        ],
    },
    "cc-cards-streak": {
        "method": "csv_total_yoy", "metric": "credit_cards",
        "status_rules": [
            {"if": "value > prev_value and value > 10", "then": "strengthening"},
            {"if": "value > 10",  "then": "active"},
            {"if": "value > 0",   "then": "weakening"},
            {"if": "true",        "then": "reversed"},
        ],
    },
    "cc-txn-surge": {
        "method": "csv_sum_yoy", "metrics": ["cc_pos_txn_vol", "cc_ecom_txn_vol"],
        "status_rules": [
            {"if": "value > 25", "then": "strengthening"},
            {"if": "value > 15", "then": "active"},
            {"if": "value > 0",  "then": "weakening"},
            {"if": "true",       "then": "reversed"},
        ],
    },
    "dc-atm-share-structural": {
        "method": "csv_ratio_sum", "metric": "dc_atm_withdrawal_vol",
        "denominator_metrics": ["dc_pos_txn_vol", "dc_ecom_txn_vol", "dc_atm_withdrawal_vol"],
        "status_rules": [
            {"if": "value > 60", "then": "strengthening"},
            {"if": "value > 45", "then": "active"},
            {"if": "value > 30", "then": "weakening"},
            {"if": "true",       "then": "reversed"},
        ],
    },
    "dc-pos-cash-decline": {
        "method": "csv_total_yoy", "metric": "dc_pos_withdrawal_vol",
        "status_rules": [
            {"if": "value < 0",  "then": "strengthening"},
            {"if": "value < 5",  "then": "weakening"},
            {"if": "true",       "then": "absent"},
        ],
    },
    "dc-ecom-share": {
        "method": "csv_ratio_sum", "metric": "dc_ecom_txn_vol",
        "denominator_metrics": ["dc_pos_txn_vol", "dc_ecom_txn_vol", "dc_atm_withdrawal_vol"],
        "status_rules": [
            {"if": "value > 25", "then": "strengthening"},
            {"if": "value > 15", "then": "active"},
            {"if": "value > 5",  "then": "weakening"},
            {"if": "true",       "then": "absent"},
        ],
    },
    "dc-cards-streak": {
        "method": "csv_total_yoy", "metric": "debit_cards",
        "status_rules": [
            {"if": "value > 5",  "then": "active"},
            {"if": "value > 0",  "then": "weakening"},
            {"if": "true",       "then": "reversed"},
        ],
    },
    "gap-dc-cash-dominance": {
        "method": "csv_ratio_sum", "metric": "dc_atm_withdrawal_val",
        "denominator_metrics": ["dc_atm_withdrawal_val", "dc_pos_txn_val", "dc_ecom_txn_val"],
        "status_rules": [
            {"if": "value > 50", "then": "strengthening"},
            {"if": "value > 35", "then": "active"},
            {"if": "true",       "then": "weakening"},
        ],
    },
    "gap-dc-ecom-low": {
        "method": "csv_ratio_sum", "metric": "dc_ecom_txn_vol",
        "denominator_metrics": ["dc_pos_txn_vol", "dc_ecom_txn_vol", "dc_atm_withdrawal_vol"],
        "status_rules": [
            {"if": "value < 10", "then": "strengthening"},
            {"if": "value < 20", "then": "active"},
            {"if": "true",       "then": "absent"},
        ],
    },
    "infra-qr-per-pos": {
        "method": "csv_total_ratio", "metric": "upi_qr", "denominator_metric": "pos_terminals",
        "status_rules": [
            {"if": "value > 5",  "then": "strengthening"},
            {"if": "value > 2",  "then": "active"},
            {"if": "value > 1",  "then": "weakening"},
            {"if": "true",       "then": "absent"},
        ],
    },
    "infra-pos-streak": {
        "method": "csv_total_yoy", "metric": "pos_terminals",
        "status_rules": [
            {"if": "value > prev_value and value > 10", "then": "strengthening"},
            {"if": "value > 10", "then": "active"},
            {"if": "value > 0",  "then": "weakening"},
            {"if": "true",       "then": "reversed"},
        ],
    },
    "infra-upi-vs-bharat-qr": {
        "method": "csv_total_ratio", "metric": "upi_qr", "denominator_metric": "bharat_qr",
        "unit": "ratio",
        "status_rules": [
            {"if": "value > 10", "then": "strengthening"},
            {"if": "value > 5",  "then": "active"},
            {"if": "value > 2",  "then": "weakening"},
            {"if": "true",       "then": "absent"},
        ],
    },
    "gap-bharat-qr-contraction": {
        "method": "csv_total_yoy", "metric": "bharat_qr",
        "status_rules": [
            {"if": "value < 0",  "then": "strengthening"},
            {"if": "value < 5",  "then": "active"},
            {"if": "true",       "then": "absent"},
        ],
    },
    "gap-atm-offsite-decline": {
        "method": "csv_total_yoy", "metric": "atm_offsite",
        "status_rules": [
            {"if": "value < 0",  "then": "strengthening"},
            {"if": "value < 3",  "then": "weakening"},
            {"if": "true",       "then": "absent"},
        ],
    },
    # Layer 1b
    "dc-psb-dominance": {
        "method": "csv_category_share", "metric": "debit_cards",
        "category": "Public Sector Banks",
        "status_rules": [
            {"if": "value > 65", "then": "strengthening"},
            {"if": "value > 55", "then": "active"},
            {"if": "true",       "then": "weakening"},
        ],
    },
    "gap-foreign-cc-decline": {
        "method": "csv_category_yoy", "metric": "credit_cards",
        "category": "Foreign Banks",
        "status_rules": [
            {"if": "value < 0",  "then": "strengthening"},
            {"if": "value < 5",  "then": "active"},
            {"if": "true",       "then": "absent"},
        ],
    },
    # Layer 1c
    "cc-category-share-shift": {
        "method": "csv_category_scan_share", "metric": "credit_cards",
        "status_rules": [
            {"if": "value > prev_value + 1", "then": "strengthening"},
            {"if": "value > 20",             "then": "active"},
            {"if": "value > 5",              "then": "weakening"},
            {"if": "true",                   "then": "absent"},
        ],
    },
    "cc-top5-concentration": {
        "method": "csv_bank_scan_concentration", "metric": "credit_cards", "top_n": 5,
        "status_rules": [
            {"if": "value > 75", "then": "strengthening"},
            {"if": "value > 65", "then": "active"},
            {"if": "true",       "then": "weakening"},
        ],
    },
    "dc-top-bank-leader": {
        "method": "csv_bank_scan_rank", "metric": "debit_cards",
        "rank_by": "value", "top_n": 5,
    },
    "infra-top-bank-pos": {
        "method": "csv_bank_scan_rank", "metric": "pos_terminals",
        "rank_by": "value", "top_n": 5,
    },
    "gap-pos-concentration": {
        "method": "csv_bank_scan_concentration", "metric": "pos_terminals", "top_n": 5,
        "status_rules": [
            {"if": "value > 60", "then": "strengthening"},
            {"if": "value > 50", "then": "active"},
            {"if": "true",       "then": "weakening"},
        ],
    },
}

for sid, spec in ATM_COMPUTE.items():
    if sid in sigs:
        sigs[sid]["compute"] = spec

# ── 4. New SIBC Layer 1b signals ──────────────────────────────────────────────
SIBC_1B = [
    # mainSectors — sector composition of non-food credit
    {
        "id": "sibc-sector-industry-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "Industry share of total credit",
        "formula": "Industry / sum(mainSectors)",
        "compute": {
            "method": "series_share",
            "section": "mainSectors", "series": "Industry",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 28",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    {
        "id": "sibc-sector-services-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "Services share of total credit",
        "formula": "Services / sum(mainSectors)",
        "compute": {
            "method": "series_share",
            "section": "mainSectors", "series": "Services",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 25",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    {
        "id": "sibc-sector-pl-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "Personal loans share of total credit",
        "formula": "Personal Loans / sum(mainSectors)",
        "compute": {
            "method": "series_share",
            "section": "mainSectors", "series": "Personal Loans",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 28",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    # industryBySize — MSME size divergence
    {
        "id": "sibc-industry-msme-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "MSME share of industry by size",
        "formula": "Micro and Small / sum(industryBySize)",
        "compute": {
            "method": "series_share",
            "section": "industryBySize", "series": "Micro and Small",
            "status_rules": [
                {"if": "value > prev_value + 2", "then": "strengthening"},
                {"if": "value > 25",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    {
        "id": "sibc-industry-size-yoy-spread",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "MSME vs Large corporate YoY spread",
        "formula": "Micro and Small YoY − Large YoY",
        "compute": {
            "method": "yoy_spread_named",
            "section": "industryBySize",
            "series_a": "Micro and Small", "series_b": "Large",
            "status_rules": [
                {"if": "value > 20", "then": "strengthening"},
                {"if": "value > 10", "then": "active"},
                {"if": "value > 0",  "then": "weakening"},
                {"if": "true",       "then": "reversed"},
            ],
        },
    },
    # personalLoans — retail composition shift
    {
        "id": "sibc-pl-gold-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "Gold loans share of personal loans",
        "formula": "Gold Loans / sum(personalLoans)",
        "compute": {
            "method": "series_share",
            "section": "personalLoans", "series": "Gold Loans",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 4",              "then": "active"},
                {"if": "value > 1",              "then": "weakening"},
                {"if": "true",                   "then": "absent"},
            ],
        },
    },
    {
        "id": "sibc-pl-cc-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_stress", "type": "data",
        "label": "Credit card share of personal loans",
        "formula": "Credit Card Outstanding / sum(personalLoans)",
        "compute": {
            "method": "series_share",
            "section": "personalLoans", "series": "Credit Card Outstanding",
            "status_rules": [
                {"if": "value < prev_value - 0.5", "then": "strengthening"},
                {"if": "value > 6",                "then": "active"},
                {"if": "value > 3",                "then": "weakening"},
                {"if": "true",                     "then": "absent"},
            ],
        },
    },
    {
        "id": "sibc-pl-secured-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "Secured retail share of personal loans (gold + vehicle)",
        "formula": "(Gold Loans + Vehicle/Auto Loans) / sum(personalLoans)",
        "compute": {
            "method": "multi_series_share",
            "section": "personalLoans",
            "series": ["Gold Loans", "Vehicle/Auto Loans"],
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 20",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    # industryByType — capex signals
    {
        "id": "sibc-industry-engineering-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "All Engineering share of industry by type",
        "formula": "All Engineering / sum(industryByType)",
        "compute": {
            "method": "series_share",
            "section": "industryByType", "series": "All Engineering",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 12",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    {
        "id": "sibc-industry-infra-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_stress", "type": "data",
        "label": "Infrastructure share of industry by type",
        "formula": "Infrastructure / sum(industryByType)",
        "compute": {
            "method": "series_share",
            "section": "industryByType", "series": "Infrastructure",
            "status_rules": [
                {"if": "value < prev_value - 1", "then": "strengthening"},
                {"if": "value > 30",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    # prioritySector — PSL composition
    {
        "id": "sibc-psl-housing-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "policy", "type": "data",
        "label": "Housing share of PSL total",
        "formula": "Housing / sum(prioritySector)",
        "compute": {
            "method": "series_share",
            "section": "prioritySector", "series": "Housing",
            "status_rules": [
                {"if": "value > prev_value + 2", "then": "strengthening"},
                {"if": "value > 20",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    {
        "id": "sibc-psl-msme-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "MSME share of PSL total",
        "formula": "Micro and Small Enterprises / sum(prioritySector)",
        "compute": {
            "method": "series_share",
            "section": "prioritySector", "series": "Micro and Small Enterprises",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 15",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    # services — channel composition
    {
        "id": "sibc-services-software-share",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1b",
        "domain": "credit_growth", "type": "data",
        "label": "Computer Software share of Services credit",
        "formula": "Computer Software / sum(services)",
        "compute": {
            "method": "series_share",
            "section": "services", "series": "Computer Software",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 10",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
]

for sig in SIBC_1B:
    sid = sig["id"]
    if sid not in sigs:
        sigs[sid] = {k: v for k, v in sig.items() if k != "id"}
        sigs[sid]["current_status"] = "unknown"
        sigs[sid]["first_seen"] = None

# ── 5. New SIBC Layer 1c scan signals ─────────────────────────────────────────
SIBC_1C = [
    {
        "id": "sibc-industry-type-scan",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1c",
        "domain": "credit_growth", "type": "data",
        "label": "YoY growth scan — all industry types",
        "formula": "YoY for each industryByType series",
        "compute": {
            "method": "section_scan_yoy",
            "section": "industryByType",
            "entity_type": "industry_type",
            "status_rules": [
                {"if": "value > 20", "then": "strengthening"},
                {"if": "value > 10", "then": "active"},
                {"if": "value > 0",  "then": "weakening"},
                {"if": "true",       "then": "reversed"},
            ],
        },
    },
    {
        "id": "sibc-services-scan",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1c",
        "domain": "credit_growth", "type": "data",
        "label": "YoY growth scan — all services sub-sectors",
        "formula": "YoY for each services series",
        "compute": {
            "method": "section_scan_yoy",
            "section": "services",
            "entity_type": "service_type",
            "status_rules": [
                {"if": "value > 20", "then": "strengthening"},
                {"if": "value > 10", "then": "active"},
                {"if": "value > 0",  "then": "weakening"},
                {"if": "true",       "then": "reversed"},
            ],
        },
    },
    {
        "id": "sibc-pl-scan",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1c",
        "domain": "credit_growth", "type": "data",
        "label": "YoY growth scan — all personal loan sub-series",
        "formula": "YoY for each personalLoans series",
        "compute": {
            "method": "section_scan_yoy",
            "section": "personalLoans",
            "entity_type": "loan_type",
            "status_rules": [
                {"if": "value > 20", "then": "strengthening"},
                {"if": "value > 10", "then": "active"},
                {"if": "value > 0",  "then": "weakening"},
                {"if": "true",       "then": "reversed"},
            ],
        },
    },
    {
        "id": "sibc-psl-scan",
        "pipeline": "sibc", "layer": 1, "sub_layer": "1c",
        "domain": "policy", "type": "data",
        "label": "YoY growth scan — all PSL sub-categories",
        "formula": "YoY for each prioritySector series",
        "compute": {
            "method": "section_scan_yoy",
            "section": "prioritySector",
            "entity_type": "psl_category",
            "status_rules": [
                {"if": "value > 20", "then": "strengthening"},
                {"if": "value > 10", "then": "active"},
                {"if": "value > 0",  "then": "weakening"},
                {"if": "true",       "then": "reversed"},
            ],
        },
    },
]

for sig in SIBC_1C:
    sid = sig["id"]
    if sid not in sigs:
        sigs[sid] = {k: v for k, v in sig.items() if k != "id"}
        sigs[sid]["current_status"] = "unknown"
        sigs[sid]["first_seen"] = None

# ── 6. New ATM/POS Layer 1b signals ──────────────────────────────────────────
ATM_1B_NEW = [
    {
        "id": "atm-cc-cash-stress",
        "pipeline": "atm_pos", "layer": 1, "sub_layer": "1b",
        "domain": "credit_stress", "type": "data",
        "label": "CC ATM withdrawal share of total CC transactions (cash-as-credit proxy)",
        "formula": "cc_atm_withdrawal_vol / (cc_pos_txn_vol + cc_ecom_txn_vol + cc_atm_withdrawal_vol)",
        "compute": {
            "method": "csv_ratio_sum", "metric": "cc_atm_withdrawal_vol",
            "denominator_metrics": ["cc_pos_txn_vol", "cc_ecom_txn_vol", "cc_atm_withdrawal_vol"],
            "status_rules": [
                {"if": "value > 10", "then": "strengthening"},
                {"if": "value > 5",  "then": "active"},
                {"if": "value > 2",  "then": "weakening"},
                {"if": "true",       "then": "absent"},
            ],
        },
    },
    {
        "id": "atm-private-cc-share",
        "pipeline": "atm_pos", "layer": 1, "sub_layer": "1b",
        "domain": "market_structure", "type": "data",
        "label": "Private sector banks share of total credit cards",
        "formula": "Private Sector Banks credit_cards / Total credit_cards",
        "compute": {
            "method": "csv_category_share", "metric": "credit_cards",
            "category": "Private Sector Banks",
            "status_rules": [
                {"if": "value > prev_value + 1", "then": "strengthening"},
                {"if": "value > 60",             "then": "active"},
                {"if": "true",                   "then": "weakening"},
            ],
        },
    },
    {
        "id": "atm-pos-per-cc",
        "pipeline": "atm_pos", "layer": 1, "sub_layer": "1b",
        "domain": "market_structure", "type": "data",
        "label": "POS terminals per credit card (acceptance density)",
        "formula": "pos_terminals / credit_cards",
        "compute": {
            "method": "csv_total_ratio", "metric": "pos_terminals",
            "denominator_metric": "credit_cards", "unit": "ratio",
            "status_rules": [
                {"if": "value > prev_value + 0.1", "then": "strengthening"},
                {"if": "value > 1",                "then": "active"},
                {"if": "value > 0.5",              "then": "weakening"},
                {"if": "true",                     "then": "absent"},
            ],
        },
    },
]

for sig in ATM_1B_NEW:
    sid = sig["id"]
    if sid not in sigs:
        sigs[sid] = {k: v for k, v in sig.items() if k != "id"}
        sigs[sid]["current_status"] = "unknown"
        sigs[sid]["first_seen"] = None

# ── save ───────────────────────────────────────────────────────────────────────
reg["_meta"]["last_updated"] = "2026-06-04"
with open(REG, "w") as f:
    json.dump(reg, f, indent=2, ensure_ascii=False)

total = len(reg["signals"])
layer1 = sum(1 for s in reg["signals"].values() if s.get("layer") == 1)
print(f"Registry updated: {total} signals total, {layer1} Layer 1")
by_sublayer = {}
for s in reg["signals"].values():
    sl = s.get("sub_layer", "—")
    by_sublayer[sl] = by_sublayer.get(sl, 0) + 1
for sl, n in sorted(by_sublayer.items()):
    print(f"  sub_layer {sl}: {n}")
