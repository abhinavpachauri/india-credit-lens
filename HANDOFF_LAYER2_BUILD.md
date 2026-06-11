# Handoff — Build Layer 2 System Models (SIBC + Payments)
> For a new session. Authored 2026-06-10.
> Read `analysis/SYSTEM_MODEL_SPEC.md` (v3.0) FIRST — it is the contract this build must satisfy.

---

## Where we are

The system model has been **formally specified** (v3.0). Two **draft** models exist but they predate the spec's structural-skeleton requirement and the v3.0 three-strata architecture — they are **NOT yet spec-compliant** and must be rebuilt, not patched.

| Artifact | State |
|---|---|
| `analysis/SYSTEM_MODEL_SPEC.md` | **v3.0, final.** The contract. Domain-agnostic. |
| `analysis/rbi_sibc/skeleton_profile.md` | **Done.** SIBC structural profile — 86 nodes, column mapping, PSL reclass target map. |
| `analysis/rbi_atm_pos/` skeleton profile | **MISSING.** Must be authored before the ATM/POS skeleton. |
| `analysis/rbi_sibc/merged/system_model_v3_draft.json` | **Stale draft.** Has behavioral content + loops but NO structural skeleton, only ~21 entities (not 86), no `code`/`structural_role`/`composes_into`. Mine it for behavioral content; rebuild structure from scratch. |
| `analysis/rbi_atm_pos/merged/system_model_draft.json` | **Stale draft.** Same problem. ~13 entities, no skeleton. Mine for behavioral content. |
| Live `analysis/rbi_sibc/merged/system_model.json` | Untouched v2 (schema 2.0). The currently-deployed model. |

---

## The build sequence (per pipeline — do SIBC first, it's fully specified)

The spec mandates **structure first, behavior second, dynamic state third**. Do not skip or reorder.

### Phase 1 — Structural skeleton (deterministic)
1. Read the pipeline's `skeleton_profile.md` (SIBC: exists; ATM/POS: author it first — see below).
2. Emit entities from the consolidated CSV per SPEC §6: identity key `(partition, code)`, carry `code`/`statement`/`structural_role`/`level`/`parent_code`/`decomposition`/`additive`.
   - SIBC CSV: `web/public/data/rbi_sibc_consolidated.csv` (86 nodes).
   - ATM/POS CSV: `web/public/data/atm_pos_consolidated.csv`.
3. Emit `composes_into` edges (child→parent within decomposition) and `reclassifies` edges (lens→target, additive:false) per the profile's target map.
4. **Validate additivity against the CSV values** — each decomposition's children must sum to the parent (tolerance-checked). This is the proof the skeleton is faithful. SIBC: verify by-size (2.1+2.2+2.3 = Industry) and that by-type also sums to Industry independently; verify III = 1+2+3+4; I = II+III.
5. Attach `signal_ids` (from `registry.json`) and `data_section`/`data_series` to each entity. Many of the 86 will have `signal_ids: []` — that's expected and is the L1-gap audit output.
6. **Consider scripting this** — it is deterministic and will run every ingestion. A `generate_skeleton.py` reading CSV + profile → skeleton JSON would make future periods reproducible. Discuss with user whether to script now or hand-build this first pass.

### Phase 2 — Behavioral-causal layer (authored, Layer 2a)
7. Layer forces, behavioral edges, risks, opportunities, gaps, loops ON TOP of the skeleton.
8. Mine the stale drafts for already-authored behavioral content (forces with sourcing, loops, opportunities) — most of the intellectual work is reusable; it just needs re-anchoring to the 86-node skeleton.
9. **Enforce the discipline rules (SPEC §9):**
   - D1: never author a behavioral edge that duplicates a `composes_into` ancestor link.
   - D2: never author `leads` across a part-whole chain.
   - D3: any behavioral edge between two `by_size`↔`by_type` Industry nodes must carry `double_count_risk: true`.
10. Every force needs the full Force Identification Protocol (SPEC §13): external source + signal_evidence + documented mechanism. Carry forward the sourcing already done in the drafts.
11. Run the inter-group relationship analysis the user raised: Agriculture↔Food Credit, Industry-by-size↔Industry-by-type, Services sub-sectors, PSL reclassification interactions. These are the behavioral edges the structural skeleton now lets us state cleanly.

### Phase 3 — Dynamic state (defer or prototype)
12. SPEC §16 defines `generate_system_state.py`. This is computed, not authored. Likely a separate work item after both static models are accepted. Confirm scope with user.

---

## ATM/POS-specific prerequisites
- **Author `analysis/rbi_atm_pos/skeleton_profile.md` first.** ATM/POS structure differs from SIBC: no `statement` column; the partition/decomposition logic is different (channel × card-type × measure; bank-type as a cross-cutting lens). Inspect `atm_pos_consolidated.csv` columns to determine the column→role mapping.
- ATM/POS likely has its own alternate decompositions (transactions by channel vs by bank-type) and its own reclassification lens (PSB/private/payment-bank shares). Work these out from the CSV, not from SIBC.
- Carry forward the two unresolved ATM/POS hypotheses from the draft: `force_rbi_card_lifecycle_norms` (now sourced to RBI MD 12156 §8), `force_ncmc_transit_rollout` (two competing hypotheses: NCMC/transit vs RuPay-credit-on-UPI — unresolved, `gap_cc_other_composition` documents why).

---

## Key decisions already locked (do not relitigate)
- Industry primary tree = **by_size**; by_type = alternate decomposition (tag-only).
- Structural map is **complete** (every CSV code → entity, even with no L1 signal).
- Alternate decomposition is a **tag**, not an edge type. Two structural edge types only: `composes_into`, `reclassifies`.
- Entity identity key = `(partition, code)`.
- PSL is a **reclassification lens** (`additive:false`), not a 5th sector. No parent `entity_psl` aggregate node.
- Behavioral mechanism = Layer 2a (same file). Layer 3 (ecosystem strategy) is separate and later.
- Spec is generic; pipeline-specifics live in `skeleton_profile.md` per pipeline.

## Open questions for the user at session start
1. Script the skeleton emission (`generate_skeleton.py`) now, or hand-build the first SIBC skeleton to validate the spec by doing, then script?
2. Phase 3 (dynamic state computation) — in scope for this build, or a separate follow-up after both static models are accepted?
3. Acceptance gate: when does a rebuilt model replace the live `system_model.json`? (Prior pattern: user reviews draft, then explicit copy.)

## Context pointers
- Layer architecture + pending items: `CLAUDE.local.md`
- Spec: `analysis/SYSTEM_MODEL_SPEC.md`
- SIBC profile: `analysis/rbi_sibc/skeleton_profile.md`
- L1 signal registry: `analysis/signals/registry.json`
- Prior review feedback (already applied to drafts): `HANDOFF_SYSTEM_MODEL_REVIEW.md`
