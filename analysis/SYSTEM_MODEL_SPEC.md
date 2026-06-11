# System Model Specification — India Credit Lens
> Version 3.0 | June 2026 | Domain-agnostic

This document is the canonical definition for all system models in the India Credit Lens pipeline.
Read it before any FOUNDATION or UPDATE pass on any pipeline's `system_model.json`.
It supersedes any conventions embedded in existing model files.

## What changed from v2.0
- **Structural skeleton is now the foundational stratum.** A system model is built in three strata: (1) structural skeleton — deterministic, from the source's code hierarchy; (2) behavioral-causal — authored forces, constraints, loops; (3) dynamic state — computed each period. Strata 1 and 2 live in the same `system_model.json`.
- **Structure precedes causality.** The skeleton is built and validated *first*. The behavioral layer is built on top and must respect skeleton constraints.
- **Three structural relationship types:** `composes_into`, `alternate_decomposition` (via decomposition tags), `reclassifies` (cross-cutting lens).
- **Deterministic emission procedure** (Section 6) — the skeleton is generated from the source's native code/statement structure with no judgment. This makes future ingestion reproducible.
- **Behavioral-discipline rules** (Section 9) — three hard constraints the behavioral layer must satisfy against the skeleton.
- **Complete structural map** — every code in the source hierarchy becomes an entity node, even those with no L1 signal and no causal role. The structural map is faithful to the data; gaps in L1 signal coverage are surfaced by comparing skeleton entities against `registry.json`.
- All v2.0 content (forces, loops, dynamic state, lifecycle, claim types, sourcing) retained.

---

## 1. Purpose and Scope

A **system model** explains how a data source's measured world is structured and why it moves. It is built in three strata:

| Stratum | What it is | How produced | Where it lives |
|---------|-----------|--------------|----------------|
| **Structural skeleton** | The composition/decomposition/reclassification structure of the entities | **Deterministic** — emitted from the source's code hierarchy. No judgment. | `system_model.json` (`nodes` + structural `edges`) |
| **Behavioral-causal** | Exogenous forces, constraints, behavioral relationships, feedback loops | **Authored** at FOUNDATION/UPDATE, with sourcing | `system_model.json` (`nodes` + behavioral `edges` + `loops`) |
| **Dynamic state** | The above two with current Layer 1 signals applied | **Computed** each period | `system_state_{period}.json` |

The skeleton answers: *how is this credit/payment world structured?*
The behavioral layer answers: *what forces drive it and what consequences follow?*
The dynamic state answers: *what is the system doing right now?*

**A system model is NOT** a narrative (Layer 1 annotation), a forecast, or a cross-source synthesis (Layer 2b).

**Minimum data:** ≥6 periods for the behavioral layer. The skeleton requires only one period (it is structural, not temporal).

**File convention:** `analysis/{pipeline_name}/merged/system_model.json`

---

## 2. Placement in the Layer Architecture

```
Layer 1     Per-entity signals. Deterministic, from CSV. (no LLM)
            ─────────────────────────────────────────────
Layer 2a    PER-SOURCE SYSTEM MODEL — this document.
            ├── Structural skeleton  (deterministic — like L1, but relational)
            └── Behavioral-causal    (authored — forces, loops, constraints)
            ─────────────────────────────────────────────
Layer 2b    Cross-source causal model (e.g. SIBC ↔ ATM/POS). Separate file.
            Blocked until both sources have a complete Layer 2a model.
            ─────────────────────────────────────────────
Layer 3     Lending ecosystem — strategic / workflow implications.
            Consumes L2a + L2b causal graphs. Authored ~6-monthly.
            Layer 3 APPLIES mechanism to strategy; it does not DEFINE mechanism.
```

The behavioral-causal mechanism (e.g. "gold price → gold loans") is **Layer 2a**. The strategic implication ("therefore lender X should do Y") is **Layer 3**. Opportunity nodes in the L2a model are proto-L3: retained here, anchored to forces/entities, until the L3 ecosystem model consumes them.

---

## 3. The Three Strata in Detail

### 3.1 Structural skeleton (deterministic)
The skeleton is the set of entity nodes plus the structural edges between them. It is derivable from the source's native code/statement hierarchy by the procedure in Section 6 — **no forces, no behavior, no judgment, no sourcing.** Because it is deterministic, it can be script-generated and regenerated identically each ingestion.

### 3.2 Behavioral-causal (authored)
Forces, behavioral edges, constraints, and feedback loops, layered on top of the skeleton. These require sourcing (Section 11) and must respect skeleton constraints (Section 9). This is the intellectual content of the Layer 2a model.

### 3.3 Dynamic state (computed)
Each period, the skeleton + behavioral graph + current L1 signal states are combined into a computed `system_state_{period}.json` (Section 16). Two kinds of propagation occur:
- **Mechanical** — a leaf entity's signal change propagates up its `composes_into` chain by accounting. Deterministic.
- **Behavioral** — a force/entity's signal state activates or deactivates behavioral edges. Per Section 16 rules.

---

## 4. Foundational Principles

### P0 — Structure-First Principle (NEW)
The structural skeleton is built and validated before any behavioral node or edge. The behavioral layer is constrained by the skeleton (Section 9). A model whose behavioral layer contradicts its skeleton is invalid.

### P1 — Anchor Principle
Every entity node corresponds to a node in the source's code hierarchy. Skeleton entities are emitted from that hierarchy (Section 6). No observable entity is invented during behavioral authoring.

### P2 — Sourcing Principle
Every behavioral claim is deterministically sourceable. Force nodes require an external verifiable source (URL + date + excerpt). Structural edges require no sourcing — they are derived from the data's own structure.

### P3 — Scope Principle
Every edge carries a `scope`: `intra_group`, `inter_group`, or `cross_source`, determined by the `registry_domain` of the connected entities. On edges touching a force/risk/opportunity/gap node, `inter_group` is a notational convention only.

### P4 — Lifecycle Principle
Force, risk, and opportunity nodes have lifecycle: `emerging → active → watch → retired`. Never deleted; retired nodes keep a `retire_period`.

### P5 — Periodicity Principle
- `leads`: ≥3 periods, OR the source is the structural capacity constraint on the target.
- `risk`/`opportunity` → `active`: ≥2 periods of corroborating signal.
- Force: external event precedes/coincides with ≥1 L1 signal status change.
- `contrasts_with`: ≥2 periods of observed opposite movement.

### P6 — Update Determinism Principle
FOUNDATION = full review. UPDATE = additive only. The **skeleton is regenerated** each ingestion (deterministic) and diffed; new codes appear as new entities automatically. The behavioral layer follows FOUNDATION/UPDATE rules (Section 15).

### P7 — Discovery Governance Principle
Groups not in the code hierarchy are classified before any node is added: Layer 1 gap, data acquisition target, or force (Section 14).

### P8 — Hierarchy Principle
Entity nodes carry `registry_domain` (L1 mapping) and structural metadata (`code`, `structural_role`, `decomposition`, `level`). These determine edge scope and skeleton validity — not judgment.

---

## 5. Structural Skeleton — Node Model

Skeleton nodes are `entity` tier with structural metadata.

**Structural fields on every entity:**
| Field | Meaning |
|-------|---------|
| `statement` | The source partition this node belongs to (e.g. SIBC `Statement 1` = by-size primary tree; `Statement 2` = by-type alternate). Part of the identity key. |
| `code` | The source's native code for this node (e.g. SIBC `I`, `III`, `2`, `2.1`, `4.8`, `ii`). |
| `structural_role` | `root` (the top aggregate, e.g. Bank Credit) \| `aggregate` (has children) \| `leaf` (no children) |
| `level` | Integer depth from root. root = 0. (Matches the `level` column in the ingested CSV.) |
| `decomposition` | Which decomposition this node belongs to under its parent, when the parent has more than one. E.g. `by_size` or `by_type` for SIBC Industry children. `primary` when the parent has a single decomposition. |
| `parent_code` | The `code` of this node's parent. `null` for root and for reclassification entities. |
| `additive` | `true` if this node's value contributes to its parent's sum within its decomposition; `false` for reclassification entities (Section 7). |

**Identity key:** an entity is identified by **`(partition, code)`**, not `code` alone. A source may reuse the same code string under two partitions for two unrelated nodes (two alternate decompositions of the same parent). Treating `code` alone as the key would collide these distinct nodes. The `partition`→column mapping is declared in the pipeline profile (Section 6.1).

**Completeness rule:** every code in the source hierarchy becomes an entity node — including nodes with no L1 signal (`signal_ids: []`) and no causal role. The skeleton mirrors the data faithfully. Comparing skeleton entities against `registry.json` surfaces L1 signal-coverage gaps (a later audit).

Entity nodes also retain their behavioral-layer fields (`signal_ids`, `annotation_ids`, `registry_domain`, `data_section`, `data_series`, `description`, `claim_type: fact`) per Section 10.2.

---

## 6. Structural Skeleton — Deterministic Emission Procedure

> This section is **domain-agnostic**. It contains no pipeline-specific structure. All pipeline-specific
> detail lives in that pipeline's **skeleton profile** (Section 6.1). A generator must read the profile —
> it must never infer structure from any other pipeline's profile or from examples elsewhere.

**Source of truth:** the skeleton is emitted from the pipeline's **ingested consolidated CSV**, never from the raw source file. The extraction stage resolves the hierarchy into columns; the skeleton is a faithful re-expression of those columns. Each pipeline's profile declares which CSV columns carry the structural roles below; the procedure itself is identical across pipelines.

**Structural roles** (each mapped to a CSV column by the profile):
| Role | Meaning |
|------|---------|
| `partition` | The table/section a row belongs to. Enables alternate decompositions. Constant if the source has a single partition. |
| `code` | The row's native code within its partition. |
| `level` | Integer depth from root. |
| `parent_ref` | The `(partition, code)` of the row's parent. Empty for roots and reclassification entities. |
| `reclass_flag` | Marks a row as a cross-cutting reclassification lens rather than a primary-tree node. |

**Procedure (identical for all pipelines):**
```
Entity identity key = (partition, code). Take distinct structural rows for the latest period.

1. ROOT(s): rows with empty parent_ref AND reclass_flag = false.  → role: root, level: 0
2. Every other non-reclass row → entity; composes_into its parent via (partition, parent_ref).
   Carry level from the CSV.
3. ALTERNATE DECOMPOSITIONS: if a parent has children under more than one partition value,
   tag each child decomposition = its partition value. All composes_into the same parent;
   non-additive across partitions.
4. RECLASSIFICATION: rows with reclass_flag = true → entity, additive: false,
   reclassifies → primary-tree target from the profile's authored target map (may be null).
   Each reclassifies edge carries a basis note.
5. Skip header/artifact rows per the profile (e.g. rows with empty code).
6. Emit no forces, behavioral edges, or loops in this step.
```

The **only** authored, non-mechanical input is the reclassification target map (step 4). Everything else is pure column logic. Profiles also optionally alias raw partition values to readable decomposition labels (cosmetic only).

### 6.1 Pipeline Skeleton Profile (required, per pipeline)
Each pipeline declares a profile at `analysis/{pipeline}/skeleton_profile.md` (or `.json`) containing exactly four things:
1. **Column → structural-role mapping** — which CSV columns are `partition`, `code`, `level`, `parent_ref`, `reclass_flag`.
2. **Decomposition labels** *(optional, cosmetic)* — aliases for partition values.
3. **Reclassification target map** *(authored)* — for each reclass entity, its primary-tree target `(partition, code)` or `null`, plus the `basis`.
4. **Artifact skip rules** — which rows to ignore.

The profile is the single location for pipeline-specific structure. The spec stays generic; SIBC, ATM/POS, and any future source each carry their own profile and never leak into this document.

### 6.2 Illustrative shape (non-normative, abstract)
A root `R` has children `A`, `B`. `A` is reported under two partitions `P1` and `P2`: under `P1` → {`A1`,`A2`}, under `P2` → {`Ax`,`Ay`}. These are **alternate decompositions** of `A` — each sums to `A` independently, never across. A separate lens `L` carries reclassification entities {`L1`,`L2`} where `L1 reclassifies A1` and `L2 reclassifies B`, with `additive:false`. This shape recurs across pipelines; concrete codes live only in each pipeline's profile.

### 6.3 Determinism guarantee
Given the same CSV and profile, steps 1–6 emit the identical skeleton every ingestion (only the profile's reclassification target map is authored, and it is fixed per pipeline). New codes appear as new entities on regeneration; the UPDATE diff surfaces them. The skeleton-vs-`registry.json` diff is the L1 signal-coverage gap report.

---

## 7. Structural Edge Types

Structural edges carry `polarity: structural` and require **no sourcing**. They are emitted by Section 6.

| Type | From → To | Meaning | Additivity |
|------|-----------|---------|------------|
| `composes_into` | child entity → parent entity | The child is a component of the parent within its decomposition. A child's movement propagates to the parent by accounting. | Additive within a decomposition |
| `reclassifies` | lens entity → primary-tree entity (or `null`) | The lens entity re-slices credit already counted in the primary tree, under a different threshold/definition. Carries a `basis` field. | Non-additive with primary tree |

**There are only two structural edge types.** Alternate decompositions are **not** an edge type — they are represented by the `decomposition` tag on entities (Section 5). A parent has alternate decompositions when its `composes_into` children carry more than one `decomposition` value. This is intentionally tag-only: the `statement` column already distinguishes the sets, the validator checks per-decomposition additivity, and an explicit marker edge would be redundant bookkeeping that can drift out of sync.

**`composes_into` mechanical semantics:** in the dynamic state layer, a leaf's signal direction propagates up the `composes_into` chain weighted by share, **within its own decomposition only**. The two decompositions of a parent are propagated independently and never summed.

**`reclassifies` basis field:** e.g. `"PSL MSME uses turnover-based threshold (June 2020 definition); Industry MSME uses investment-based — different populations."`

---

## 8. Behavioral Edge Types

Behavioral edges carry a causal `polarity` and require sourcing where they originate from a force. `mechanism` describes the structural process, never current observations.

| Type | Polarity | From → To | Meaning |
|------|----------|-----------|---------|
| `drives` | `+` | force → entity | Positive directional effect |
| `suppresses` | `-` | force, entity → entity | Negative directional effect |
| `amplifies` | `+` | force, entity → entity | Compounds a positive trend already present in the target |
| `reroutes_to` | `~` | entity → entity | Demand/flow redistributes from source to target |
| `substitutes` | `~` | entity → entity | Source replaces target at the usage point. `intra_group` only. |
| `leads` | `+` | entity → entity | Positive leading indicator. `inter_group`/`cross_source` only. ≥3 periods or capacity-constraint. |
| `contrasts_with` | `structural` | entity → entity | Annotation: opposite movement, not causal. Not used in loop computation. |
| `creates_opportunity` | `+` | force, entity → opportunity | |
| `creates_risk` | `-` | force, entity → risk | |
| `creates_gap` | `structural` | force → gap | |
| `is_data_gap` | `structural` | entity → gap | |
| `masks` | `structural` | gap → entity | |

**Disallowed:** `force→force`; `opportunity→entity/force`; `risk→entity/force`; `substitutes` non-`intra_group`; `leads` `intra_group`. Plus the structure-discipline constraints in Section 9.

---

## 9. Behavioral-Discipline Rules (Structure Constrains Causality)

The behavioral layer must respect the skeleton. Three hard constraints, validator-enforced:

**D1 — No behavioral duplication of composition.** A behavioral edge (`drives`/`amplifies`/`leads`/etc.) may never connect a child to its own `composes_into` ancestor. A child-to-parent relationship is mechanical aggregation, computed in the dynamic layer — never authored as a behavioral edge.

**D2 — No `leads` across a composition boundary.** A `leads` edge may not run between an entity and any ancestor or descendant in its `composes_into` chain. Leading-indicator claims are only valid between entities that are not in a part-whole relationship.

**D3 — Double-counting flag across alternate decompositions.** Any behavioral edge between two entities in *different decompositions of the same parent* (i.e. carrying different `decomposition` tags) must carry `"double_count_risk": true` and a note. The same underlying credit may sit in both decompositions; the edge must acknowledge it.

**What structure does and does not do:**
- Structure **generates** the mechanical (aggregation) relationships — deterministic, not authored.
- Structure **constrains** the behavioral relationships via D1–D3.
- Structure does **not generate** behavioral causation — forces and evidence do.

---

## 10. Node Taxonomy

Five tiers. `force`, `entity`, `risk`, `opportunity`, `gap`.

### 10.1 `force`
Exogenous cause, not measurable in the CSV.
`force_type`: `policy_action` | `macro_factor` | `structural_shift` | `institutional_behavior`.
`domain` = `registry_domain` of the primary affected entity.
`signal_evidence`: L1 signal IDs confirming the force operates.
**Required:** `id, tier, label, description, claim_type, domain, force_type, non_observable_reason, signal_evidence, source, source_url, source_verified_date, source_excerpt, source_rationale, status`

### 10.2 `entity`
A node in the source code hierarchy.
**Structural fields (Section 5):** `code, structural_role, level, decomposition, parent_code, additive`.
**Behavioral/bridge fields:** `signal_ids` (L1 signals; may be `[]`), `registry_domain`, `data_section`, `data_series`, `annotation_ids`.
`claim_type`: always `fact`. Description: structural/definitional, no current-period numbers.
**Required:** `id, tier, label, description, claim_type: fact, code, structural_role, level, registry_domain, data_section, data_series, signal_ids, annotation_ids`

### 10.3 `risk`
Negative systemic consequence; spans ≥2 periods or structural tension. Anchored to ≥1 entity.
**Required:** `id, tier, label, description, claim_type, domain, status, annotation_ids`

### 10.4 `opportunity`
Strategic opening for a named participant class (proto-Layer-3). Anchored to ≥1 entity.
**Required:** `id, tier, label, description, claim_type, domain, status, annotation_ids`

### 10.5 `gap`
Structural data limitation with causal implications. `gap_type`: `measurement` | `definitional` | `data_acquisition`. Source fields optional.
**Required:** `id, tier, label, description, claim_type, domain, gap_type, annotation_ids`

---

## 11. Claim Types and Sourcing
| Type | Use | Evidence |
|------|-----|----------|
| `fact` | Directly readable from data | `data_section`+`data_series` (entities); structural edges are inherently fact |
| `inference` | Data + external evidence; mechanism clear | `source_url`+`source_excerpt` |
| `hypothesis` | Plausible, not externally confirmed | `source_rationale`; `source_url` may be empty |

Promotion forward only. Hypothesis not promoted after 2 FOUNDATION cycles OR 24 calendar months → mandatory review.

---

## 12. Node Lifecycle (force/risk/opportunity)
`emerging` → `active` (≥2 periods) → `watch` → `retired` (`retire_period` set; preserved). Retired-node edges keep `"retired_with": "{node_id}"`.

---

## 13. Force Identification Protocol
All three required: (1) external source with URL+date+excerpt; (2) ≥1 L1 signal status change in the same/adjacent window; (3) documented specific mechanism. Fail (1) → hypothesis. Fail (2) → do not add. Fail (3) → not ready.

---

## 14. Entity Discovery Governance
A potential entity not in the code hierarchy:
```
Computable from existing CSV?     → Layer 1 gap. Add to registry, compute, then add entity.
Computable from un-ingested CSV?  → data_acquisition gap node. No entity yet.
Structurally non-observable?      → force candidate (Section 13).
None of the above?                → do not add; re-examine conflation.
```

---

## 15. FOUNDATION vs UPDATE

**Skeleton (both modes):** regenerated deterministically each ingestion and diffed. New codes → new entities automatically. This is mechanical, not a judgment call.

**FOUNDATION (behavioral):** add/modify/retire any force/risk/opportunity/gap; add/remove behavioral edges; restructure loops; promote claim types; change schema version.

**UPDATE (behavioral):** additive only — add a force (full Protocol), add behavioral edges, update descriptions, promote claim type, change lifecycle status. May not retire nodes, remove edges, or change `schema_version`. Hypothesis forces not promoted by next FOUNDATION are auto-retired.

---

## 16. Dynamic State Output

Computed by `analysis/generate_system_state.py --pipeline {p} --period {date}` after L1 compute. File: `system_model_state_{period}.json` (or `system_state_{period}.json`).

**Step 1 — Leaf entity states.** For each leaf entity, read `signal_ids` from the period's signal DB → `direction` ∈ {+1, 0, −1}.

**Step 2 — Mechanical propagation (skeleton).** Propagate leaf directions up each `composes_into` chain, share-weighted, to compute aggregate entity directions. Deterministic. Alternate decompositions computed independently; never summed. Reclassification entities computed from their own signals, not propagated into the primary tree.

**Step 3 — Force states.** For each force, read `signal_evidence` → `active` | `latent`.

**Step 4 — Behavioral edge states.** For each behavioral edge (polarity `+`/`-`/`~`): `active` | `dominant` | `dormant` | `reversed` per from-node direction and polarity.

**Step 5 — Loop states.** `active_reinforcing` | `active_balancing` | `partial` | `dormant` from participating edge states.

**Step 6 — System observations.** `dominant_forces`, `binding_constraints` (active `-` edges), `active_reinforcing_loops`, `active_balancing_loops`.

**Output:** structured JSON with `entity_states` (incl. propagated aggregates), `force_states`, `edge_states`, `loop_states`, `system_observations`, and a `narrative: null` slot the LLM fills at Stage 5.X.

---

## 17. Loop Definitions
First-class objects in `loops[]`. Explicitly authored (loops may close through forces/externally). Fields: `id, label, type (reinforcing|balancing), closure (internal|partial|external), closure_note, participating_nodes, participating_edges, description`. Only `+`/`-`/`~` edges participate; `structural` excluded. All referenced nodes/edges must exist (validator check).

---

## 18. Validation Requirements

**Structural skeleton:**
| Check | Rule |
|-------|------|
| Code present | Every entity has a `code` |
| Tree integrity | Every non-root entity has a valid `parent_code` resolving to an existing entity |
| Role consistency | `aggregate` entities have ≥1 `composes_into` child; `leaf` entities have none |
| Additivity | Within each `decomposition`, children sum to parent (tolerance-checked where values exist) |
| Alternate decomposition | A parent with >1 `decomposition` value has each set independently summing to it; never cross-summed |
| Reclassification | `reclassifies` edges have `additive: false` source and a `basis` note |
| Completeness | Every source code appears as an entity (diff skeleton vs source hierarchy) |

**Behavioral discipline:**
| Check | Rule |
|-------|------|
| D1 | No behavioral edge duplicates a `composes_into` ancestor link |
| D2 | No `leads` edge between entities in a part-whole chain |
| D3 | Cross-decomposition behavioral edges carry `double_count_risk: true` + note |

**Behavioral layer (retained from v2.0):** valid tiers; valid edge types; polarity present; scope present; entity `signal_ids` present (may be empty array, key required); entity `claim_type: fact`; force `signal_evidence` + source fields; risk/opp `status`; gap `gap_type`; hypothesis `source_rationale`; disallowed tier combos; `leads`/`substitutes` scope; loop references valid; ≥1 force, ≥1 entity, ≥1 edge; `schema_version: "3.0"`.

---

## 19. File Conventions
| Item | Path |
|------|------|
| Pipeline static model | `analysis/{pipeline}/merged/system_model.json` |
| Pipeline dynamic state | `analysis/{pipeline}/merged/system_state_{period}.json` |
| Cross-source model (L2b) | `analysis/cross_source/system_model.json` |
| Spec | `analysis/SYSTEM_MODEL_SPEC.md` |
| Schema version | `_meta.schema_version: "3.0"` |
| Spec ref | `_meta.spec_ref: "analysis/SYSTEM_MODEL_SPEC.md"` |
| Drafts | `system_model_v3_draft.json` / `system_model_draft.json` — replace originals after acceptance |

---

*System Model Specification v3.0 — India Credit Lens*
