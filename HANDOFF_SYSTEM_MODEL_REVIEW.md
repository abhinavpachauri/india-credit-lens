# System Model Review Handoff
> Authored: 2026-06-10 | For review in a fresh Claude session

---

## Context

This handoff is for a **peer review session** of three new documents produced in the India Credit Lens pipeline. The reviewer's job is to read all three documents, identify gaps, inconsistencies, or design flaws, and return structured feedback. Changes will be made in a follow-up session.

**Do not make any changes in the review session.** Read and critique only.

---

## What was built in this session

### 1. System Model Specification (`analysis/SYSTEM_MODEL_SPEC.md`)
The first formal, domain-agnostic definition of what a "system model" is in this pipeline. Previously the system model was built by feel — this spec formalises the rules so future models can be generated and updated deterministically.

Key decisions made:
- System models are **anchored to Layer 1 data boundary groups** (registry.json `domain` field). No new observable entities are invented during system model construction.
- Five node tiers: `force`, `entity`, `risk`, `opportunity`, `gap`
- Edge scope is mechanically determined by `registry_domain` of connected entity nodes: `intra_group` (same domain) → `inter_group` (different domain, same pipeline) → `cross_source` (different pipelines, Layer 2b)
- Force identification is **deterministic**: requires (1) external verifiable source with URL+date+excerpt, (2) ≥1 L1 signal showing measurable status change in same/adjacent period, (3) documented mechanism in description. No LLM-generated forces without external sourcing.
- Two update modes: FOUNDATION (full structural review, can add/retire nodes) and UPDATE (additive only, no new entity nodes)
- Node lifecycle for force/risk/opportunity: emerging → active → watch → retired. Nodes are never deleted.

### 2. SIBC System Model v3 Draft (`analysis/rbi_sibc/merged/system_model_v3_draft.json`)
The existing SIBC system model (v2, schema_version 2.0) reevaluated and translated against the new spec. The original file (`system_model.json`) is **unchanged** — this is a new draft file pending review.

Changes from v2:
- Tier renames: `driver`→`force`, `sector`→`entity`, `pressure`→`risk`
- New fields: `force_type`, `non_observable_reason`, `status` (force/risk/opp), `registry_domain` (entity), `scope` (edges), `gap_type`
- Edge renames: `causes`→`drives`, `reinforces`→`amplifies`, `reroutes_demand_to`→`reroutes_to`, `contrast`→`contrasts_with`, `signals`→`leads`
- `entity` nodes now have `claim_type: fact` (was inconsistent in v2)

Stats: 42 nodes, 43 edges → 42 nodes (same), 43 edges (same), all translated.

### 3. ATM/POS System Model Draft (`analysis/rbi_atm_pos/merged/system_model_draft.json`)
First-ever FOUNDATION pass for the ATM/POS pipeline. Built from scratch using:
- 16 months of signal data (Jan 2025 – Apr 2026)
- 16 LLM evaluation files in `analysis/signals/evaluations/atm_pos/`
- 4 L1 registry domains: `infrastructure`, `cards_stock`, `credit_card_txn`, `debit_card_txn`

Stats: 28 nodes (4 force, 12 entity, 3 risk, 3 opportunity, 3 gap), 29 edges.

---

## Files to read (in order)

1. `analysis/SYSTEM_MODEL_SPEC.md` — Read fully. This is the ground truth for the review.
2. `analysis/rbi_sibc/merged/system_model_v3_draft.json` — Review against the spec.
3. `analysis/rbi_atm_pos/merged/system_model_draft.json` — Review against the spec.
4. `analysis/signals/registry.json` — Reference for valid `registry_domain` values and L1 domain groups.

---

## Specific review questions

### On the Spec (`SYSTEM_MODEL_SPEC.md`)

**Q1 — Scope rule completeness**: The spec says edges from/to force, risk, opportunity, or gap nodes default to `inter_group`. Is this correct, or should force→entity edges have their own scope tag (e.g., `exogenous`) to distinguish them from entity→entity inter-group edges?

**Q2 — Entity hierarchy**: The spec allows both parent-level entities (e.g., the `retail` domain as a whole) and sub-level entities (e.g., `gold_loans` within `retail`) as valid entity nodes. Both share the same `registry_domain` value. Is this sufficient to determine intra-group vs inter-group scope, or do we need a `level: parent/sub` field to distinguish them for edge validation?

**Q3 — `leads` edge minimum**: The spec says `leads` requires ≥3 periods OR structural self-evidence. Is "structural self-evidence" too vague? Should there be a specific criterion for what qualifies?

**Q4 — UPDATE mode force addition**: The spec allows adding a force node in UPDATE mode if it passes the Force Identification Protocol. Does this create a risk that UPDATE mode accumulates unreviewed force nodes between FOUNDATION cycles? Should there be a cap (e.g., max 2 new force nodes per UPDATE cycle)?

**Q5 — Hypothesis node retirement rule**: The spec says hypotheses must be promoted or retired after two FOUNDATION cycles. Is "two FOUNDATION cycles" the right threshold? For SIBC this could be 2 years; for ATM/POS it depends on when FOUNDATION cycles are declared.

---

### On the SIBC v3 Draft

**Q6 — `entity_bank_credit → entity_X (leads)` edges**: The v2 model had four `signals` edges from `entity_bank_credit` to its component sectors. These were converted to `leads` in v3. However, these may not be true leading-indicator relationships — they might be decomposition relationships (the aggregate is composed of its parts). Should these edges be: (a) kept as `leads` with better labels, (b) changed to a new `decomposes_into` edge type, or (c) removed entirely (entity nodes are self-describing)?

**Q7 — `risk_unsecured_migration` with no source**: This node has `claim_type: hypothesis` and no source URL. The review note flags that RBI Digital Lending Guidelines actually require BNPL/digital credit to report to CICs, which contradicts the "untracked channels" claim. Should this node be: (a) sourced and retained if evidence exists that CIC reporting compliance is incomplete, (b) reformulated as a narrower claim, or (c) retired?

**Q8 — `force_msme_formalisation` sourcing**: The current source is the SIBC data itself (the growth effect), not the external force mechanism (UDYAM/GST formalisation). A better source would be a SIDBI MSME Pulse or RBI MSME credit survey. Has the reviewer seen such a document? If not, should this remain as hypothesis?

**Q9 — `opp_vehicle_ev` with no source**: This has no source and no source_rationale. Should it be: (a) sourced with VAHAN data or SMEV report on EV share of vehicle registrations, or (b) retired from v3?

**Q10 — `force_nbfc_regulatory_recovery` as `status: watch`**: This was demoted from `active` to `watch` in the translation because the claim hasn't been upgraded to inference. Is `watch` appropriate, or should it be `active` (the regulatory cycle has fully played out) or `retired` (the risk-weight effect is over)?

**Q11 — Missing L1 domain in SIBC v3**: The SIBC registry has a `psl` domain with 13 signals. The v3 model has `entity_psl_housing` and `entity_export_credit` as psl entities but does not have a parent-level `entity_psl` (the PSL aggregate). Is this a gap, or is the PSL aggregate not analytically useful at the system model level?

---

### On the ATM/POS Draft

**Q12 — `force_rbi_card_lifecycle_norms` (hypothesis)**: The Oct 2025 credit card purge is clearly visible in the data. The specific RBI circular governing mandatory inactive card closure has not been cited. The reviewer should check **RBI Master Direction on Credit Card and Debit Card issuance (RBI/2022-23/86)** for Section 8 (card lifecycle provisions). If found, promote to inference.

**Q13 — `force_ncmc_transit_rollout` (hypothesis)**: The 300-500% YoY growth in `cc_other_txn` is the observable. The NCMC/NFC hypothesis needs a source. Reviewer should check: **NPCI NCMC page** or **Ministry of Housing and Urban Affairs (MoHUA) metro fare integration documentation**. If not found, is there an alternative hypothesis for the `other` category explosion?

**Q14 — ATM/POS entity granularity**: The draft uses `entity_atm_network` as a single entity covering both onsite and offsite ATMs. However, these two sub-types are in opposite trajectories: onsite (branch ATMs) are stable, offsite (cash-access ATMs) are declining. Should `entity_atm_network` be split into `entity_atm_onsite` and `entity_atm_offsite` to enable an `intra_group` `contrasts_with` edge? Or is this too granular for the system model level?

**Q15 — Missing `debit_card_txn` intra-group edge**: The draft has `entity_dc_atm_txn ↔ entity_dc_ecom_txn (contrasts_with)` but does not have an explicit relationship between `entity_dc_pos_txn` and the other two. Is this correct (dc_pos_txn is not in a substitution or contrast relationship with dc_atm or dc_ecom), or is there a missing edge?

**Q16 — ATM/POS force completeness check**: Are there exogenous forces active in the Jan 2025 – Apr 2026 window that are NOT covered by the four force nodes in the draft? Reviewer should consider:
- RBI guidelines on bank BC/ATM availability requirements
- DPDP Act (Digital Personal Data Protection) implications for card data
- Any other RBI circular in 2025-26 that affected ATM/POS market structure

**Q17 — `gap_upi_transaction_data` as data_acquisition**: UPI transaction data is published monthly by NPCI. Should this gap trigger an immediate Layer 1 signal spec task (add UPI transaction metrics to registry.json and ingest from NPCI), or is this a longer-term data acquisition project? If the former, it should be filed as a known Layer 1 gap and tracked in registry.json.

---

## Design decisions that need explicit sign-off

These are not review questions — they are architectural decisions the original author (Abhinav) needs to confirm:

**D1**: Should the cross-source model (Layer 2b, SIBC ↔ ATM/POS) live in `analysis/cross_source/system_model.json` as a separate file, or in a single merged model that contains scope 1+2+3 edges? The spec currently proposes a separate file.

**D2**: When should the first ATM/POS FOUNDATION be declared "reviewed and accepted"? Once accepted, the draft file replaces `system_model.json` and future ingestions run in UPDATE mode. What is the acceptance gate?

**D3**: The spec says hypotheses must be promoted or retired after two FOUNDATION cycles. For ATM/POS, this is the first FOUNDATION — the two-cycle clock starts now. For SIBC v3, two hypothesis nodes (`force_msme_formalisation`, `force_nbfc_regulatory_recovery`) and two opportunity nodes (`opp_vehicle_ev`) predate this FOUNDATION. Do they get a fresh two-cycle grace period, or does this FOUNDATION count as cycle 1?

---

## What to return

The reviewer should produce a response structured as:

```
## Spec feedback
[Q1–Q5 answers with reasoning]

## SIBC v3 feedback  
[Q6–Q11 answers; note any spec violations found in the JSON]

## ATM/POS draft feedback
[Q12–Q17 answers; note any spec violations found in the JSON]

## Design decisions
[D1–D3 recommendations]

## Additional findings
[Any other gaps, inconsistencies, or spec violations not covered by the questions above]
```

Feedback returns to the original session for implementation. Do not edit any files in the review session.

---

*End of handoff — India Credit Lens System Model Review, 2026-06-10*
