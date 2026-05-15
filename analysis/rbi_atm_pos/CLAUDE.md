# ATM/POS Pipeline — India Credit Lens

RBI ATM, Acceptance Infrastructure and Card Statistics.
Completely isolated from SIBC — separate scripts, separate eval gate, separate CSV output.

---

## Stages (run in order via master gate)

```
python3 analysis/run_atm_pos_evals.py --xlsx path/to/file.xlsx [file2.xlsx ...]
```

Or step by step:
```
Stage 0: python3 analysis/detect_atm_pos_format.py {xlsx}   → {period}/format_report.json
Stage 1: python3 analysis/extract_atm_pos.py {xlsx}         → {period}/sections.json + raw/
Stage 2: python3 analysis/validate_atm_pos.py {YYYY-MM-DD}  → checks A–E
Stage 3: python3 analysis/consolidate_atm_pos.py {YYYY-MM-DD} → atm_pos_consolidated.csv + timeline.json
```

Re-validate an already-extracted period:
```
python3 analysis/run_atm_pos_evals.py --period 2026-03-31
```

---

## Folder structure

```
analysis/rbi_atm_pos/
  canonical_banks.json     64-bank registry — update here for renames/mergers
  timeline.json            ingested months registry
  incoming/                drop new XLSX files here before running pipeline
  {YYYY-MM-DD}/
    format_report.json     Stage 0 output (must be confirmed before Stage 1)
    sections.json          Stage 1 output (wide format, one record per bank)
    raw/                   archived source XLSX

web/public/data/
  atm_pos_consolidated.csv Stage 3 output (long format, all periods)
```

---

## Data model

### sections.json (wide, per period)
```json
{
  "report_date": "2026-03-31",
  "report_month": "March 2026",
  "data_status": "provisional",
  "bank_count": 64,
  "records": [
    {
      "bank_name": "HDFC BANK LTD",
      "bank_category": "Private Sector Banks",
      "record_type": "bank",
      "credit_cards": 21500000,
      "cc_pos_txn_vol": 95000000,
      ...
    }
  ]
}
```

### atm_pos_consolidated.csv (long, all periods)
Columns: `report_date, bank_name, bank_category, record_type, metric, value, unit, data_status`

`record_type`: `bank` | `total`

---

## Metrics tracked

| Metric | Unit | Credit signal |
|---|---|---|
| `credit_cards` | count | Direct — credit supply |
| `debit_cards` | count | Context — cc/dc ratio |
| `pos_terminals` | count | Acceptance infrastructure |
| `upi_qr` | count | Credit-on-UPI infrastructure |
| `atm_onsite` / `atm_offsite` | count | Cash infrastructure |
| `cc_pos_txn_vol/val` | txns / Rs'000 | Active CC utilisation |
| `cc_ecom_txn_vol/val` | txns / Rs'000 | Digital CC spend |
| `cc_atm_withdrawal_vol/val` | txns / Rs'000 | CC cash stress proxy |
| `dc_atm_withdrawal_vol/val` | txns / Rs'000 | Cash dependency signal |

---

## Guard rails

| Guard rail | Where enforced |
|---|---|
| Column count must = 29 | Stage 0: detect_atm_pos_format.py |
| Sheet name must match "For Website {Month} {Year}" | Stage 0 |
| All 64 bank names must match canonical_banks.json | Stage 2 Check A |
| No negative outstanding values | Stage 2 Check B |
| Volume > 0 implies value > 0 | Stage 2 Check C |
| Total = sum of bank rows ±0.1% | Stage 2 Check D |
| report_date must be valid month-end | Stage 2 Check E |
| Dedup: latest extraction wins for same (bank, metric, month) | Stage 3 consolidation |

---

## When a bank name changes (merger / rename)

1. Stage 2 Check A will fail with "Unexpected bank name" warning
2. Verify against RBI's official list
3. Update `canonical_banks.json` — add new name, mark old name with `"status": "merged_into"` note
4. Re-run from Stage 2

---

## Isolation from SIBC pipeline

- No shared scripts — all ATM/POS scripts are prefixed `atm_pos_` or named `*_atm_pos.py`
- No shared data files — output goes to `atm_pos_consolidated.csv`, not `rbi_sibc_consolidated.csv`
- No shared timeline — `rbi_atm_pos/timeline.json` is independent
- `run_evals.py` (SIBC gate) is never called — use `run_atm_pos_evals.py` only
