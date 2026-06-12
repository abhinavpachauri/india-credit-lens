# ATM/POS Skeleton Profile
> Pipeline-specific structural profile for the ATM/POS system model.
> Consumed (machine form) by `analysis/generate_skeleton.py` via `skeleton_profile.json`.
> This file is the ONLY place ATM/POS-specific structure lives. The spec (`analysis/SYSTEM_MODEL_SPEC.md` §6) stays generic.

**Pipeline:** `atm_pos`
**Source CSV:** `web/public/data/atm_pos_consolidated.csv`
**Structural nodes:** 35 (26 metric leaves + 9 computed aggregates)

---

## 1. Why this profile authors the hierarchy (`hierarchy_source: profile`)

Unlike SIBC, the ATM/POS CSV is **long-format** — `(report_date, bank_name, bank_category,
record_type, metric, value, unit)`. There is **no `parent_code` column**: the source publishes a
flat list of ~26 metrics per bank, and the composition structure is implicit in the metric names
(`cc_pos_txn_val` = credit-card · POS channel · value measure). The hierarchy is therefore
**authored here** rather than derived from CSV columns. System totals are the rows with
`record_type = 'total'`.

New metrics appearing in a future CSV that are not covered by a node below are surfaced by
`generate_skeleton.py` as a **new-entity diff** — that is the scalability hook: the structure is
stable, additions are flagged for a profile update.

---

## 2. The three structural axes

| Axis | Values | Treatment |
|------|--------|-----------|
| **Card type** | credit / debit | decomposition under the spend roots |
| **Channel** | POS · e-commerce · ATM withdrawal · other · (DC only) POS cash withdrawal | leaves under each card type |
| **Measure** | count · value (`rs_thousands`) · volume (`transactions`) | **separate partitions / roots** — never summed across |

Measures are kept as **separate partitions** (`cards`, `spend_value`, `spend_volume`,
`infrastructure`) precisely because value and volume are different units and must never be added
together. This is the ATM/POS analogue of SIBC's alternate decompositions, but on the *measure*
axis, so it is expressed as distinct roots rather than `decomposition` tags on one parent.

---

## 3. Emitted tree (35 nodes, 4 roots)

```
cards (count)
└── cards_in_force [sum]
    ├── credit_cards
    └── debit_cards

spend_value (rs_thousands)
└── card_spend_value [sum]
    ├── cc_spend_value [sum] ── cc_pos_txn_val · cc_ecom_txn_val · cc_atm_withdrawal_val · cc_other_txn_val
    └── dc_spend_value [sum] ── dc_pos_txn_val · dc_ecom_txn_val · dc_atm_withdrawal_val · dc_other_txn_val · dc_pos_withdrawal_val

spend_volume (transactions)
└── card_spend_volume [sum]
    ├── cc_spend_volume [sum] ── cc_pos_txn_vol · cc_ecom_txn_vol · cc_atm_withdrawal_vol · cc_other_txn_vol
    └── dc_spend_volume [sum] ── dc_pos_txn_vol · dc_ecom_txn_vol · dc_atm_withdrawal_vol · dc_other_txn_vol · dc_pos_withdrawal_vol

infrastructure (count)
└── acceptance_infrastructure [grouping — NOT summed]
    ├── atms [sum] ── atm_onsite · atm_offsite
    ├── micro_atms
    ├── pos_terminals
    ├── bharat_qr
    └── upi_qr
```

**`aggregation` modes** (per node, validator-relevant):
- `sum` — children are disjoint and add to the parent; additivity is tolerance-checked
  (`cards_in_force`, `card_spend_value`, `cc_spend_value`, `dc_spend_value`, the volume mirror,
  `atms`).
- `grouping` — `acceptance_infrastructure` is a **container** over heterogeneous instruments
  (ATMs, micro-ATMs, POS terminals, Bharat-QR, UPI-QR). These are not summable into one quantity,
  so additivity is **not** checked for this node.
- `leaf` — terminal metric, value read from the CSV total.

---

## 4. Cross-cutting lens — `bank_category` (declared, not emitted)

Every metric is also reported per `bank_category` ∈ {Public Sector, Private Sector, Foreign,
Small Finance, Payment Banks}, and these **sum to the total** (a genuine additive decomposition).
The full bank-level matrix (63–64 banks × 26 metrics) is also in the CSV.

Neither is exploded into the skeleton — that would add hundreds of low-value nodes. Instead
`bank_category` is declared as a lens in `skeleton_profile.json` (`lens.bank_category`,
`emit_nodes: false`). The bank/category **share signals** (`cc-psb-share`, `dc-psb-share`,
`pos-private-share`, `*-bank-scan`, `*-category-share-scan`) attach to their underlying metric
leaf via `signal_attach` (`compute.metric`). If a future need arises for explicit per-category
aggregate nodes, add them here as `reclassifies` lens entities (`additive: false`).

---

## 5. Signal attachment (deterministic)

Every ATM/POS L1 signal in `registry.json` carries `compute.metric`. A metric leaf's `signal_ids`
= all L1 signals whose `compute.metric` equals the node's `metric`. Computed aggregates
(`metric: null`) carry `signal_ids: []` — they are populated by mechanical propagation in the
dynamic-state layer, not by direct signals. This skeleton-vs-registry comparison is the L1
signal-coverage audit for ATM/POS.

---

## 6. Carry-forward behavioral hypotheses (for the Layer 2a behavioral pass)

Two unresolved ATM/POS forces from the prior draft, to re-anchor onto this skeleton:
- `force_rbi_card_lifecycle_norms` — RBI credit-card lifecycle / mandatory inactive-card closure
  (sourced to RBI MD 12156 §8). Explains the debit-card base erosion and CC count dynamics.
- `force_ncmc_transit_rollout` — embedded card payment infrastructure: **two competing
  hypotheses** (NCMC/transit NFC vs RuPay-credit-on-UPI). Unresolved; `gap_cc_other_composition`
  documents why the `cc_other_txn` category cannot disambiguate them.
