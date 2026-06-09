# ATM/POS Pipeline — India Credit Lens

RBI ATM, Acceptance Infrastructure and Card Statistics.
Separate gate from SIBC — same stage sequence, different scripts.
Full architecture: see `PIPELINE_ARCHITECTURE.md`.

---

## Current stage mapping vs unified architecture

| Unified Stage | Purpose | ATM/POS script | Status |
|---|---|---|---|
| 0 | Format detection | `detect_atm_pos_format.py` | ✓ Live |
| 1 | Extraction | `extract_atm_pos.py` | ✓ Live |
| 2 | Per-period validation | `validate_atm_pos.py` (Checks A–E) | ✓ Live |
| 3 | Consolidation | `consolidate_atm_pos.py` → CSV + timeline | ✓ Live · sections_merged.json pending |
| 4 | Layer 1 signal evaluate | `generate_signal_history.py append` | ⚠ Presence/absence only · numeric compute specs pending |
| 5 | Layer 2a signal evaluate | `generate_atm_pos_insights.py` (runs in gate for now) | ⚠ Insight script is Layer 2a — needs decoupling from gate |
| 6 | Evals gate | `run_atm_pos_evals.py` | ✓ Live |
| 7 | Presentation promote | Direct write (no promotion step yet) | ⚠ Pending |

## Running the gate

```
python3 analysis/run_atm_pos_evals.py --xlsx path/to/file.xlsx [file2.xlsx ...]
```

Flags:
- `--skip-insights`  skip insight generation (Stages 4b/4c/4d) — data-only run
- `--skip-build`     skip tsc + npm run build

Step by step:
```
Stage 0:  python3 analysis/detect_atm_pos_format.py {xlsx}     → {period}/format_report.json
Stage 1:  python3 analysis/extract_atm_pos.py {xlsx}           → {period}/sections.json + raw/
Stage 2:  python3 analysis/validate_atm_pos.py {YYYY-MM-DD}    → checks A–E
Stage 3:  python3 analysis/consolidate_atm_pos.py {YYYY-MM-DD} → atm_pos_consolidated.csv + timeline.json
[Stage 4] python3 analysis/generate_signal_history.py append --pipeline atm_pos --period {YYYY-MM-DD}
[Stage 5] python3 analysis/generate_atm_pos_insights.py        → web/public/data/atm_pos_insights.json
          python3 analysis/validate_atm_pos_insights.py        → validates numbers vs signals.json (±0.5%)
          python3 analysis/validate_atm_pos_claims.py          → validates reasoning.chain (≥2 steps)
Stage 6:  (automatic in gate) web CSV integrity check + tsc + npm run build
```

Re-validate an already-extracted period:
```
python3 analysis/run_atm_pos_evals.py --period 2026-03-31
```

---

## Date normalisation rules (same principle as SIBC)

ATM/POS `report_date` values are canonical month-ends by design (e.g. `2026-03-31`) —
`consolidate_atm_pos.py` currently does no date remapping.

However, **the same rule applies if RBI ever publishes a file with an early-month date:**
a publication date in the first week of a month represents data from the **prior** month-end.

| Published on | Maps to | Example |
|---|---|---|
| Day 1–7 of any month | Last day of prior month | May 3 → Apr 30 |
| Day 8 onward | Last day of same month | Apr 19 → Apr 30 |

If a new ATM/POS file arrives with a raw date that doesn't match a canonical month-end,
**stop and classify it before consolidating** — ask the user whether it is current-month
or prior-month data, document the decision in a `{period}/date_overrides.json`, and wire
the override into `consolidate_atm_pos.py` (mirroring how SIBC handles it in
`update_web_data.py`). Full rule table: `PIPELINE_ARCHITECTURE.md` → SIBC date
normalisation section.

**Always show the full date remapping and get explicit confirmation before the CSV is written.**

---

## Folder structure

```
analysis/rbi_atm_pos/
  canonical_banks.json         64-bank registry — update here for renames/mergers
  timeline.json                ingested months registry
  incoming/                    drop new XLSX files here before running pipeline
  {YYYY-MM-DD}/
    format_report.json         Stage 0 output (must be confirmed before Stage 1)
    sections.json              Stage 1 output (wide format, one record per bank)
    raw/                       archived source XLSX

web/public/data/
  atm_pos_consolidated.csv     Stage 3 output (long format, all periods)
  atm_pos_insights.json        Stage 4b output (insight + gap objects with reasoning)
  atm_pos_signals.json         Signals reference file (values validated against in 4c/4d)
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

### atm_pos_insights.json (insight objects)
```json
[
  {
    "id": "cc-pos-share-rising",
    "group": "cc",
    "mode": "top_n",
    "type": "insight",
    "title": "...",
    "body": "...",
    "implication": "...",
    "reasoning": {
      "signals": [{"key": "cc_pos_share", "value": 62.3}],
      "chain": [
        "Step 1 ...",
        "Step 2 ..."
      ]
    }
  }
]
```

`reasoning.chain` maps to `InsightCard`'s `chain` prop (inference expand).
`reasoning.signals` are validated against `atm_pos_signals.json` in Stage 4c/4d.

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
| Signal values in insights match atm_pos_signals.json ±0.5% | Stage 4c: validate_atm_pos_insights.py |
| Each signal key declared in insight exists in signals.json | Stage 4d: validate_atm_pos_claims.py |
| reasoning.chain must have ≥ 2 steps per insight | Stage 4d: validate_atm_pos_claims.py |
| atm_pos_consolidated.csv has no duplicate (date, bank, metric) rows | Stage 5: run_atm_pos_evals.py |
| All report_date values in CSV are canonical month-end | Stage 5: run_atm_pos_evals.py |
| tsc --noEmit passes cleanly | Stage 6: run_atm_pos_evals.py |
| npm run build completes without error | Stage 6: run_atm_pos_evals.py |

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
