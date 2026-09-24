# Payments (ATM/POS) pipeline — what is specific to it

RBI's monthly *ATM, Acceptance Infrastructure and Card Statistics*: 26 measures (card counts,
terminals, QR codes, transaction volumes and values) for every reporting bank. **To ingest a
period use `/ingest-period atm_pos {xlsx}`.** The stage sequence shared by every pipeline is in
`PIPELINE_ARCHITECTURE.md`; this file holds only what differs for payments. Revised 2026-09-24.

## The source

- Monthly XLSX, released ~M+2 and irregularly (Mar → early Jun, May → late Jul); manual download
  into `analysis/rbi_atm_pos/incoming/`. `extract` archives it into `{period}/raw/`.
- `report_date` is always a canonical month-end. **If a file ever carries an early-month date,
  stop:** a date in days 1–7 of a month means prior-month data. Ask the user to classify it and
  record the decision in `{period}/date_overrides.json` before consolidating. Payments has no
  gated remap record like SIBC's, because it has never needed one.
- The format detector handles older layouts (abbreviated month names, date-less sheets, sheets
  found by content). Keep it loud rather than tolerant.

## The bank roster (`canonical_banks.json`)

The roster is **time-aware**: a bank carries `status`, `closed_from`, `renamed_from` or a former
name, and `validate_atm_pos.load_canonical_names(report_date)` returns the roster as it stood on
that date. Paytm Payments Bank closed from 2026-04-30 (64 → 63 banks); Fincare merged April 2024;
Dhanalaxmi renamed November 2024; Slice SFB renamed May 2025.

When a name changes: Check A fails with "unexpected bank name" → verify against RBI's list → add the
new name and mark the old one with its date in `canonical_banks.json` → re-run. **A changed bank
count is a finding, not noise.**

## Data checks (stage 2, `validate_atm_pos.py`)

| Check | What |
|---|---|
| A | every bank name is on the roster for that date |
| B | no negative outstanding values |
| C | a volume above 0 implies a value above 0 |
| D | the total row equals the sum of banks, ±0.1% |
| E | `report_date` is a valid month-end |

Consolidation keeps the latest extraction for a (bank, metric, month); the CSV integrity stage
rejects duplicate rows and non-month-end dates.

## Data shapes

- `web/public/data/atm_pos_consolidated.csv` (long): `report_date, bank_name, bank_category,
  record_type (bank | total), metric, value, unit, data_status`. Values in `rs_thousands` convert to
  crore by **÷ 1e4** (a `/100` bug once drew ₹219 lakh crore; a magnitude test pins it).
- Compute shape `atm_pos`: many measures over the same bank and bank-category entities. Every
  measure breaks out over the reporting banks; each breakout ships as its own file under
  `web/public/data/atm_pos_banks/`, fetched when opened.

## The card path (why payments has two extra stages)

```
4a  compute_atm_pos_signals.py   → rbi_atm_pos/signals.json      MUST run before 4b
4b  generate_atm_pos_insights.py → web/public/data/atm_pos_insights.json
4c  validate_atm_pos_insights.py   numbers vs signals.json / signals.db + YoY drift guard
4d  validate_atm_pos_claims.py     declared signal keys exist; reasoning chains well-formed
```

- `signals.json` carries `meta.latest_month`; skipping 4a serves the prior month silently.
- Every card is a declaration in one ordered `CARDS` list. Anchored scalar cards take their prose
  from the eval (`EVAL_ANCHOR` → a registered signal id); scans, shares and gaps stay deterministic.
- **The dominance guard** (`signals/dominance.py`) runs unconditionally: a move owned by one bank
  (POS terminals −15.8% YoY was ~98% ICICI's reclassification) is attributed by name, not
  published as the market.
- Refresh the characterisation golden deliberately (`analysis/tests/golden/refresh_atm_pos_cards.py`),
  after checking that every dropped card is an honest null.
