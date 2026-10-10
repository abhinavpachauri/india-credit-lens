# System Model Specification — India Credit Lens
> Version 3.1 | October 2026 | Domain-agnostic
> v3.1 (2026-10-08): force state judged against a baseline, with timing fields (§10.1, §16 Step 3); explanation coverage computed in S3 and read by S4, with structural explanations (§16 Step 6a); relationships admitted by a test (§16 Step 6b). Built.

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
`signal_evidence`: L1 signal IDs a reader should look at for this force. Pointers for review and
narration; since v3.1 they **do not decide** the force's state (§16 Step 3).
**Timing (v3.1, 2026-10-08):** a force is either *dated* or *standing*, never neither.
- Dated: `starts` (ISO date the instrument or event took effect: the effective date, not the
  announcement), `delay_months` (how long before the effect can show in the data),
  `fades_after_months` (how long after `starts + delay` the effect should stay visible; after it
  the line has settled at a new normal and the force no longer explains a gap).
- Standing: `standing: true` and no dates. For slow conditions with no single start
  (formalisation, a price trend). Always in its window.

The dates are the editor's, filled from the force's own source text at sourcing time, and live
in fields because a date inside `label` ("eff. 1 Apr 2025") is readable by a person and by no check.

**`timing_rule`** names how the force works, and the rule, not a per-force judgment, sets
`delay_months` and `fades_after_months` (user, 2026-10-08):

| `timing_rule` | delay | visible for | why |
|---|---|---|---|
| `relabelling` | 0 | 12 | a limit change moves loans already on the book into a category on day one; YoY carries the jump exactly 12 months, then the base absorbs it |
| `capital_cost` | 3 | 24 | banks reprice and slow new lending over quarters |
| `eligibility` | 3 | 24 | newly eligible borrowers build up gradually |
| `guarantee_window` | 1 | scheme period + 12 | lending happens while it is open; YoY carries it a year more |
| `exit` | 0 | 12 | a one-off step, then in the base |
| `long_lag` | from the force's own text | 24 | approvals turn into drawdowns years later |
| `standing_regime` | — | standing | a rule in force since before our data starts (2020–22 instruments) |
| `trend` | — | standing | a slow condition with no single start |

A force whose delay or window differs from its rule says why in `source_rationale`.
**A standing force explains a steady gap, never a sudden move** (§16 Step 6a): "zero MDR since
2020" cannot be the reason something changed in August 2026.

Written 2026-10-08 for all 20 forces (13 SIBC, 7 payments). At SIBC 2026-09-30 (Aug 2026 data),
4 dated forces had faded (the Nov 2023 unsecured risk weights and the three PSL 2025 ceilings),
and every live payments force is standing, so payments has no dated cause in window.
**Required:** `id, tier, label, description, claim_type, domain, force_type, non_observable_reason, signal_evidence, source, source_url, source_verified_date, source_excerpt, source_rationale, status`, and either `starts + delay_months + fades_after_months` or `standing: true`

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

**Step 2a — Coherence of every propagated direction (added 2026-08-19).** A parent's direction is a *summary of children who may disagree*, and today nothing records whether they did. Alongside each aggregate `direction`, emit `coherence = |Σ child_delta| / Σ|child_delta|` ∈ [0,1] over the children that produced it — the same quantity Layer 1 already computes for the same hierarchy (`signals/README.md`, movement methods), so this is a read, not a second calculation.

`direction: +1, coherence: 1.00` (all children rising) and `direction: +1, coherence: 0.12` (children in near-cancellation, one issuer reclassifying) are currently **indistinguishable in the state file**, and every downstream consumer — edge firing, loop state, opportunity status, narrative — inherits that blindness. Measured 2026-08-19 on ATM/POS `pos_terminals` bank categories: coherence **0.120** on a window where private banks shed 257,290 terminals while public banks added 204,595. The parent direction was a true statement about a fact that mattered far less than the transfer underneath it.

**Implemented 2026-08-19** in `generate_system_state.compute`: each aggregate entity's `entity_states[urn]` gains `coherence` + `children`, measured on the **primary** decomposition only — the alternates are other views of the same total, so pooling them would double-count. All five SIBC aggregates currently read 1.000, which is the honest answer while every sector is growing.

**Coherence qualifies a direction; it never suppresses one.** Low coherence is a finding (the parts are trading places), not a defect. Consumers that state a direction in prose must state its coherence regime with it.

**Step 2b — Mix state (added 2026-08-19). Layer 2 reads the movement family, not just a sign.**

Steps 1–2 reduce every signal to `direction ∈ {+1, 0, −1}`. That discards magnitude, speed, tilt
and agreement — so the causal layer cannot express the one thing a credit mix is actually doing,
which is being *managed*. The Layer-1 movement methods (`signals/README.md`) compute the raw
quantities; this step is where Layer 2 consumes them. **No new registry signals** — the registry
stays L1-computed-only (the June 2026 decision that retired 34 L2 stubs); mix state is a computed
field on the hierarchy node, exactly as `coherence` is in Step 2a.

For each entity that has children carrying movement signals, read from `signals.db`:

```
tilt_i     = alloc_i − weight_i          share of the new units minus the child's existing weight
coherence  = |Σ delta| / Σ|delta|        Step 2a, already computed
toward     = argmax  tilt_i              the child the new money is FAVOURING
away_from  = argmin  tilt_i              the child it is being taken from

mix_state =
  steered       coherence ≥ 0.90, `toward` unchanged for ≥2 windows, and tilt_toward material
  drifting      coherence ≥ 0.90, but no child holds a material tilt across two windows
  contested     0.50 ≤ coherence < 0.90 — direction rests on a majority, not a consensus
  reallocating  coherence < 0.50 — members are trading places; the net is the least of it
```

**"Material" is self-calibrating, never a constant.** Max |tilt| scales with the number of
children — measured 2026-08-19, median max-tilt is **5.6 pp** on the four main sectors and
**23.7 pp** on the nineteen industry types. An absolute threshold would call the same behaviour
material in one cut and noise in another. A tilt is material when it exceeds **that cut's own
median max-tilt over its history**, the idiom `proximity.typical_move` already uses for the same
reason.

**Two windows, not one** — the same noise filter `derive_opportunities` applies before an
opportunity may reach `active`. One month of tilt is a month, not management.

**`toward`, not `argmax |tilt|`.** The largest tilt in either direction would name the biggest
mover and call it the destination — measured 2026-08-19, the main-sector cut's largest |tilt| is
Personal Loans at **−4.9 pp**, i.e. the child money is moving AWAY from. Reporting that as the lead
would invert the finding. Both ends are emitted; only the positive one decides `steered`.

**Keyed by CUT, not by entity.** Industry carries two decompositions — by size (Statement 1) and by
type (Statement 2) — hanging off the same node. They are different mixes with different states, so
keying by entity would silently drop one. Each entry carries its `entity_urn` and `decomposition`.

**The PSL lens node (closed 2026-08-19).** Priority-sector entities are emitted as
`reclassification` leaves with `parent_code: null` — ten orphans with nothing to belong to, and a
list of their ids that the generator collected and never used. So PSL could carry movement cards
but no mix state. The skeleton now emits a **`Priority Sector Lending (memo)`** node (`code: PSL`,
`structural_role: root`, `decomposition: psl_lens`) and composes the ten into it.

`additive: false`, because PSL is a **lens over the primary tree, not a partition of it** — its
Agriculture is the same rupees as the main cut's Agriculture, so summing would double-count. `root`
rather than `aggregate` because it is the top of its own decomposition and has no parent, which is
precisely the shape the tree check reserves a null `parent_code` for.

**Measured on SIBC at 2026-07-31:** main sectors **steered** toward Services (+4.9 pp) away from
Personal Loans; services **steered** toward NBFCs (+15.9 pp); industry by size, industry by type and
personal loans **drifting**; priority sector **drifting** toward Micro & Small Enterprises
(+5.5 pp); infrastructure sub-types **contested** (coherence 0.778). All seven SIBC cuts covered.

**What consumes it.** `mix_state` is evidence available to force firing and to
`derive_opportunities`; a force claiming to steer the mix can be checked against whether the mix
is in fact `steered`, and toward which child. It qualifies, it does not fire on its own —
consistent with Step 2a, coherence never suppresses a direction.

**Step 3 — Force states: a check that can fail (v3.1, specced 2026-10-08, not yet built).**

*What it replaces, and why.* v3.0 read `signal_evidence` and called a force `active` if **any**
evidence signal had a direction. About 80% of SIBC signal rows read up in a given month
(Aug 2026: 864 of 1,064), so every force was active every month: 13/13 SIBC, 7/7 payments, every
period. Step 4 then judged each force→entity edge against **zero**, so a force that "drives" a
line passed whenever the line grew at all, and a force that "suppresses" one failed whenever it
grew at all. Wrong in both directions. Aug 2026, v3.0 against the built v3.1 check:

| force (polarity) | line | reading | v3.0 says | v3.1 says |
|---|---|---|---|---|
| RBI unsecured risk weights, Nov 2023 (−) | Credit card outstanding | +3.6% vs Personal Loans +16.9% | `reversed` | `faded` (read `working` at every assessable reading inside its window) |
| KCC collateral-free limit, Jan 2025 (+) | Agriculture | +17.2% vs Non-food credit +18.8% | `active` | `contradicted`, **in doubt** |
| PSL Directions 2025 (+) | Export credit | −9.7% | `active` | `faded` (window Apr 2025 – Mar 2026) |
| Gold price surge (+) | Loans against gold | +83.2% vs Personal Loans +16.9% | `active` | `working` |

*Correction, 2026-10-08:* an earlier draft of this table had NBFC risk weights → Services as
contradicted, on "Services +4.0%". That 4.0 was `sibc-sectors-positive-yoy-count` (the number of
growing sectors), read by a quick query that took the first signal on the node whose id contained
"yoy". Services grew 24.4% against 18.8%, and the force reads `working`. The built check reads
growth only through the declared resolver below, which is why that query was the wrong tool.

*The rule.* A force is judged through its force→entity edges, and each edge asks one question:
**did the line beat its baseline in the direction the force predicts?**

1. **Growth reading.** The entity's YoY at the period, from `signals.db`, through **one resolver**
   (`force_check.growth_series`) joined through the registry's own declarations: a
   `csv_sector_yoy` / `csv_total_yoy` row for the node's code, else the node's row in its
   parent's `*_scan_yoy`. The cut tables read the same stored rows. Never picked per force. No
   reading → the edge is `unassessable` with its reason; it never silently drops (absences stay
   visible).
2. **Baseline**, chosen by the entity's place in the skeleton, never per force:

   | entity's place | baseline | why |
   |---|---|---|
   | child in an additive decomposition | its parent's YoY, same period | "faster than its group" is what a force acting on one part predicts |
   | member of a non-additive lens (`additive: false`, e.g. PSL), force dated | its own YoY at the last reading before `starts` | lens members overlap and sum to nothing; the only clean comparison is the line against itself |
   | non-additive member with a standing force, or no parent at all | the pipeline root's YoY (SIBC: bank credit; payments: its total) | the widest group available |

3. **Gap** = growth − baseline, in percentage points. Expected sign: `drives` and `amplifies` →
   positive; `suppresses` → negative. `~` polarity has no expected sign and is `unassessable`.
4. **Noise band**, from the line's own history, never a constant: the median absolute
   reading-to-reading change of this same gap over the line's history (the self-calibrating
   idiom of Step 2b and `proximity.typical_move`). Stored per edge as `noise_pp`. The exact
   statistic is confirmed in the measurement below and the choice recorded.
5. **Window.** Dated force: in window from `starts + delay_months` to that plus
   `fades_after_months`. Before → `not_yet_due`; after → `faded`. Standing force: always in window.

*Edge verdicts:* `working` (in window, gap the expected sign, |gap| > `noise_pp`) ·
`contradicted` (in window, gap the opposite sign, |gap| > `noise_pp`) · `unclear` (|gap| ≤
`noise_pp`) · `not_yet_due` · `faded` · `unassessable` (with reason).

*Force verdict*, over its in-window, assessed edges: `working` if working edges outnumber
contradicted ones; `contradicted` if the reverse; otherwise `unclear`. If no edge is in window, the
window verdict carries through (`not_yet_due` / `faded`).

*Persistence.* A force authored `active` whose verdict is `contradicted` for `MIX_PERSISTENCE`
(2) consecutive readings becomes **`in_doubt`**. Same constant as Step 2b, imported, not
copied. Readings, not months: SIBC history has gaps, and a gap does not count as agreement.
`in_doubt` replaces v3.0's `mismatch` and is what S4 receives as "authored vs observed"
(COMPOSITION_SPEC §8): S4 then works on forces the data disputes, not on lines that merely grow.

*Output per force:* `verdict`, `in_doubt`, `window`, and per edge `growth`, `baseline`,
`baseline_kind`, `gap_pp`, `noise_pp`, `verdict`. Every number here is a stored reading or a
difference of two, so prose can quote the operands.

*Scope.* Force→entity edges only. Entity→entity edges keep the Step 4 rule until the
relationships inside a pipeline are redesigned (the next step of the same plan).
Force nodes feed edges downstream (`creates_opportunity`, `creates_risk`) with direction +1 only
when their verdict is `working`, so opportunities stop firing off a force the data does not support.

*Measured before it is trusted* (DECISIONS: no gate change without catch and false-rejection rates):
old vs new over **every period × every force**, both pipelines, shown side by side; known-good
control = the Nov 2023 risk-weight force reads `working` on credit cards **in the periods inside
its window** (Feb 2024 – Feb 2026) and `faded` after it; known-bad control = an
injected force pointing at a falling line reads `contradicted`; the count of forces whose answer
changes is reported, not sampled. Logged in `ai_pm_register.json`.

*Built 2026-10-08* (`core/force_check.py`, tests `tests/test_force_check.py`). Emitted as
`force_check` in every `system_state_{period}.json`. **Which rule a pipeline's forces are judged
by is declared in its manifest** (`"force_check": "v3.1"`, read by `manifest.force_check`;
undeclared = `v3.0`). Under v3.1 the verdict drives `force_states` (`working` → `active`, every
other verdict by name), the force's driver edges (`working` → active, `contradicted` →
reversed, anything else → dormant), `dominant_forces`, `authored_vs_observed_mismatches`
(= `in_doubt`, S4's input) and opportunity firing in `derive_opportunities` (a force driver fires
only when `working`). **Switched on for SIBC 2026-10-08** (user, after reviewing `--history`):
dominant forces 13 → 7, KCC in doubt, the PSLC-reclassification opportunity closed (its PSL
ceilings have faded), and the PLI supply-chain loop no longer active (basic metals reads unclear).
**Payments switched on 2026-10-10** (user, option A): dominant forces 7 → 1 (zero MDR), card
lifecycle norms in doubt (the misfit below), the transit tap-to-pay opportunity closed (its force
reads unclear). *Group totals added 2026-10-10:*
8 `csv_sum_yoy` signals (cards in force, ATMs, credit / debit / all card spend by value and
volume), read by `growth_series` from the node whose leaf set they add up; 34 of 35 payments
lines now have a growth reading (acceptance infrastructure has none on purpose: QR codes, POS
and ATMs do not add). A missing part makes a total unknown, never smaller. Payments verdicts
over 32 readings: 13 working, 23 contradicted, 15 unclear, 18 faded (was 224/224 unassessable).
*Known misfit before switching payments on:* card lifecycle norms read contradicted at every
reading because "cards in force" is ~90% debit, so the test is credit vs debit cards; the force
claims episodic purges (a step change), not a steady gap. Measured over every reading:

- **SIBC, 13 forces × 25 readings (325).** v3.0: 237 active, 88 latent. v3.1: 106 working,
  20 contradicted, 11 unclear, 27 not yet due, 22 faded, 139 unassessable; 14 in doubt.
  Unassessable is mostly honest: SIBC has YoY only from Jan 2025 data (2024 has no year-ago
  figure) and the wobble needs 3 changes, so the check judges from about Apr 2025.
- **Payments, 7 forces × 32 readings (224): all unassessable.** Two reasons, both real gaps:
  the parent totals (cards in force, credit/debit card spend) carry **no YoY signal** in
  `signals.db`, so no payments line has a group to be compared with; and 3 payments forces plus
  SIBC's ECLGS 5.0 have **no driver edge**, so the model never said which way they push.
- **Controls.** Known-good: the Nov 2023 risk weights read `working` at every assessable
  reading in their window, `faded` after. Known-bad (unit test): a force driving a falling line
  reads `contradicted` and `in_doubt`. Mutation check: forcing every verdict to `working` fails
  2 tests; reverting to the zero baseline fails 4.
- **What it found.** KCC → agriculture is contradicted at 12 of its 13 assessable readings
  (agriculture grows slower than non-food credit) and in doubt now. Vehicle scrappage was
  contradicted for its first 5 assessable readings, working since. PSL renewable was
  contradicted twice inside its window.

*Migration.* Done 2026-10-08: all 20 forces carry `timing_rule` and either dates or
`standing: true` (§10.1). The validator check (§18) can now be switched on.

**Step 4 — Behavioral edge states.** Force→entity edges: Step 3. Other behavioral edges (polarity
`+`/`-`/`~`): `active` | `dominant` | `dormant` | `reversed` per from-node direction and polarity
(v3.0 rule, zero baseline; known weak, redesign pending).

**Step 5 — Loop states.** `active_reinforcing` | `active_balancing` | `partial` | `dormant` from participating edge states.

**Step 6 — System observations.** `dominant_forces`, `binding_constraints` (active `-` edges), `active_reinforcing_loops`, `active_balancing_loops`.

**Step 6a — Explanation coverage: how much of this period's movement the model accounts for
(v3.1, specced 2026-10-08, not yet built).**

*What it replaces.* The only existing measure of "unexplained" is S4's `detect_unexplained`
(`run_inference.py`), and it answers the wrong question three ways: it counts a leaf that is
**moving at all** (so Housing, growing at its usual pace, acceleration −0.14, is "unexplained");
it counts a leaf as explained when **any** driver edge or force scope touches it, working or not;
and it **stops at 15** and lives only inside an S4 run, so nothing can track it across periods.
This step computes the count properly, once, in S3; S4 reads it (COMPOSITION_SPEC §8) and keeps
no detection of its own. The other "coverage" numbers in the code (1f match share on tables,
parts-of-total on table rows, construct measurements observed) measure data, not explanation, and
are untouched.

*Population.* Every entity except a root (leaves, groups and lens members), derived from the
skeleton. A line without a usable reading is listed in `no_reading` with its reason, never
dropped. *Changed while building (2026-10-08):* the first draft counted leaves only, on the
argument that aggregates move mechanically from their children. But moves are measured against
the line's group, so a force acting on a group (Services, All Engineering) cancels out of every
member's move and can only explain the **group** beating its own parent. Leaves-only made every
force on a group uncountable; groups are counted for that reason.

*What counts as a move.* The line's gap to its baseline changed since **the month before** by
more than `MOVE_FACTOR` (3) × its typical month-to-month change. Baseline: its parent when it is
an additive child, else the root of its own tree, else (no reading for either, e.g. payments'
group totals today) its own earlier growth, recorded as `baseline_kind: none`. The typical change
is the median |month-to-month change| over the line's own history (the Step 3 wobble, from the
same shared function, `force_check.monthly_changes`). A line growing steadily with its group is
**not** a move and needs no explanation.

- **Why 3×, not 1×** (measured 2026-10-08 over every reading): at 1× half of any line's
  readings beat its own median by construction — 47% of SIBC line-readings, 43% of payments.
  2× flags 20% / 18%; 3× flags 11% / 10%, so a move is roughly a one-in-ten event per line,
  close to the usual ~2σ bar for "unusual". One named constant (`coverage.MOVE_FACTOR`).
- **Only changes one data month apart count**, for the wobble and for the move. SIBC never
  published Sep–Dec 2025 and NBFC reads irregularly; a change across a hole spans several months
  and is not comparable to a monthly wobble. Counted, it made Jan 2026 show 32 SIBC moves and
  NBFC Mar 2026 show 11. After a hole the line reads `no_reading: no reading for the month before`.
  Step 3 uses the same rule for its wobble (one more contradicted SIBC reading as a result).

*What counts as explained*, tried in this order; a move is filed under the **first** that holds,
and every one that holds is listed:

| order | kind | holds when | source |
|---|---|---|---|
| 1 | `artifact` | the move is dominated by one reporting entity, merger or reclassification | `signals/dominance.py` |
| 1a | `structural` | not a separate event (added 2026-10-08): an **echo** (the group moved the other way by at least half the line's change), a **twin** (a lens member whose `reclassifies` partner moved the same way; the main-table line keeps the event), or **carried** by a member (that member moved the same way and its weighted change is at least half the group's own; the member keeps the event) | the skeleton + latest CSV weights |
| 2 | `prices_activity` | the line's 1f deflator YoY (or its output growth) changed in the same direction and covers at least half the change in its nominal YoY | 1f operands (`deflator_yoy`, `credit_yoy`) and `*-output-growth` |
| 3 | `cause` | a **dated** force whose edge to this line is `working` (Step 3), in window, with expected sign matching the move. A standing force never files a move here: it explains a steady gap, not a change (§10.1) | Step 3 |
| 4 | `relationship` | an entity→entity edge into this line whose state matches the move | Step 4 (zero until the in-pipeline relationships are built; honest, not hidden) |
| — | `unexplained` | none of the above | → S4 |

The "at least half" threshold for `prices_activity` is a starting value, confirmed in the
measurement below and the choice recorded. A line with no 1f match cannot be tested for row 2
and says so (`prices_activity: not_decomposable`), so "no price effect" and "price effect not
measurable" never read the same.

*Not an explanation:* the mix state (Step 2b). "Money was steered toward Services" restates the
move; it does not explain it (DECISIONS: an excerpt that restates our own series is the effect,
not a cause). It stays alongside each move as context.

*Output.* `explanation_coverage` in each `system_state_{period}.json`: one record per move
(`entity`, `direction`, `gap_change_pp`, `noise_pp`, `filed_under`, `also_holds`) plus a summary:

```
moves  N   artifact a   prices_activity b   cause c   relationship d   unexplained u   no_reading r
```

No cap anywhere. If S4's prompt must be shortened, the shortening happens in S4 and prints how
many it left out.

*Why it matters.* This is the number that says whether the model is getting tighter. Adding a
force or a relationship is an improvement only if `unexplained` falls on the periods it claims to
cover. Step 3 alone may **raise** `unexplained` (forces that read contradicted stop counting), and
that is the honest starting point.

*Measured before it is trusted:* computed over every period for both pipelines, and the
per-period summary is shown. Controls: a line with an injected step change must count as a move;
a line moving in step with its parent must not; a move with a matched working force must file
under `cause`; the same move with the force's sign flipped must file under `unexplained`.
Logged in `ai_pm_register.json`.

*Built 2026-10-08* (`core/coverage.py`, tests `tests/test_coverage.py`; `--history` prints the
summary for every reading). Emitted as `explanation_coverage` in every
`system_state_{period}.json`; S4's `detect_unexplained` now reads it and raises on a state
without it (a missing count must not read as "nothing unexplained"). The prompt still sees at
most 15 moves, ranked by size against their own bar, and prints how many it left out.

- **The starting point.** SIBC, every month from Apr 2025: 4–15 moves of 84 lines; prices and
  activity explain 2 in total, working causes 5, relationships 1; the rest are unexplained.
  Aug 2026: 6 moves (Food Credit, Housing slowing against personal loans, loans against
  deposits, Textiles, Other Industries, Fertiliser), all unexplained. Payments: 1–7 moves a month,
  all unexplained except two one-bank artifacts (Nov 2025, Jun 2026). NBFC: 2 a month, unexplained.
- **Structural (1a), added 2026-10-08.** SIBC history: 18 of 102 unexplained moves were not
  separate events (13 echoes, 2 twins, 3 carried), so unexplained falls to 86. Aug 2026: Housing
  "slowing" is an echo of Personal Loans speeding up (gold loans +83%), Textiles an echo of
  Industry. Each points at the line that holds the event, which keeps its own filing, so an event
  is never filed away entirely.
- **Controls.** The four above are unit tests, plus standing force, unworking force, prices
  too small or the wrong way, no 1f match, artifact filed first with others still listed,
  relationship, group counted, hole. Mutations (factor 0, standing allowed, sign ignored) each
  fail a test.

**Step 6b — Relationships between parts: proposed with a reason, admitted by a test
(v3.1, 2026-10-08).** A relationship is an entity→entity driver edge (one line pushes another).
It explains a move in Step 6a (row 4). It enters the model only after it is **proposed** with a
real-world reason, a predicted sign (+ complement, − substitute) and a lag, and then **passes**
`core/relationship_test.py`. Every result, nulls included, is kept in
`analysis/{pipeline}/relationship_tests.json`; only `supported` may become an edge, and only with
the editor's yes.

*Why the data cannot find them.* Over ~15 monthly changes, coincidence looks like relationship:
across all 2,912 cross-group SIBC pairs, 86 co-move at |r| > 0.6 and a shuffled control produces
48. Discovery by correlation would admit mostly noise, so the reason comes first and the data can
only refute.

*The protocol, fixed before any result:* the measure is the monthly change in each line's gap to
its own group (the quantity Step 6a uses); both are first regressed on the root's monthly growth
change (**the tide**); 10,000 seeded shuffles give p; `supported` when the predicted sign holds
at p < 0.05 at the declared lag, `opposite` when reversed, else `not_supported`. Other lags are
reported, never used to rescue a verdict.

*First test (2026-10-08): bank lending to HFCs → banks' own housing loans, predicted
substitute: `not_supported`* (r = +0.35, p = 0.20). Raw, the two looked related, monthly new
lending r = +0.46, p = 0.03, but both follow total bank credit (housing r = 0.78 with it); with
the tide removed, r = +0.17, p = 0.43. That near-miss is why the tide step is in the protocol and
why its unit test (two lines sharing only a tide must fail) exists.

*Several declared together raise the bar* (`--family N`, Bonferroni, p < 0.05 / N): four tested
at once would otherwise pass one by luck about one time in five.

*Second test (2026-10-08), a family of four, all predicted +, lag 0, bar p < 0.0125:*
Construction → Cement (main), Construction → Iron and Steel, Commercial Real Estate → Cement,
Commercial Real Estate → Iron and Steel. **All `not_supported`**, none near (p 0.47–0.56; r
between −0.18 and +0.21). No other lag came close either.

*What a null means here: too weak to see, not absent.* The smallest |r| that can pass at p < 0.05
with n monthly changes: n = 15 → 0.51 (0.63 as one of four); 22 → 0.42; 36 → 0.33; 60 → 0.25;
120 → 0.18. SIBC has 15 usable monthly changes (YoY exists from Jan 2025 data, and Sep–Dec 2025
is missing), so only very strong links are visible. **History length is the binding constraint
on this layer:** a 5-year SIBC backfill (RBI publishes it) would bring the visible bar to ~0.25.

*Re-measured 2026-10-10 after backfill phase 1* (Sep–Nov releases; 36 continuous months, 23
monthly changes per line): all five tests stay `not_supported` (HFC → housing r = +0.21,
p = 0.35; the construction family |r| ≤ 0.31, p ≥ 0.16 against a bar of 0.0125). Coverage over
the longer history: 176 moves, 34 structural, 12 working causes, 2 prices/activity, 0
relationships, 128 unexplained. The 3× move threshold still flags 10% of readings (2× 20%,
1× 49%), so it stands.

*The model's own arrows, tested 2026-10-10* (user-approved A–D). The 12 entity→entity arrows
already in the models (SIBC 3, payments 9; authored, never tested) were run as one family of 12
(bar p < 0.0042), sign from the arrow type (leads / amplifies +; substitutes / reroutes_to /
suppresses −), lag 1 month for `leads`, else 0: **all `not_supported`**. Closest: DC ATM
withdrawals → DC e-commerce (predicted −) r = −0.51, p = 0.024, promising but short of the bar.
Consequences, all under force_check v3.1:
- **S3 edge states** for an arrow between two lines follow its latest test (supported → active,
  opposite → reversed, else dormant, marked `untested` when never tested), never the source's sign
  against zero (`relationship_test.latest_verdicts`, the one reader). Loops follow: payments
  `cc_penetration_R` active → dormant, `upi_network_effect_R` and SIBC `unsecured_rerouting_B`
  partial → dormant.
- **Coverage** credits a relationship only when its test is `supported`, with the test's sign;
  a delayed one reads its source's move `lag` months earlier.
- **A line driving an opportunity or risk** fires only when it beats its group in the arrow's
  direction (`force_check.line_verdict`, the Step 3 test applied to a line). A driver with no
  group reading makes the item `unassessable`, never `closed`. Payments: Micro-ATM rural cash
  → unassessable; card-concentration risk → closed. *Known ambiguity:* every risk arrow carries
  − and every opportunity arrow + (the type's default, not a stated direction); read as
  direction it fits most risks but not card concentration. Decide per arrow in the next pass.
- **Cross-pipeline links (Layer 2b)** are tested the same way, paired by data month with each
  side's own tide removed (`relationship_test.run_cross`, `analysis/cross_source/relationship_tests.json`).
  **Credit-card spend (payments) leads credit-card outstanding (SIBC) by one month: `supported`**
  (r = +0.54, p = 0.020 vs a family-of-2 bar of 0.025, n = 18; lag 0 r = −0.13, lag 2 −0.19),
  the first relationship any test has admitted; borderline, re-test as history grows. Its state
  is now `aligned` because of the test, not because both lines rose, and the cross-source
  opportunity it powers fires only while it is supported. The count ↔ outstanding link is
  definitional (`linked`); its co-movement test (not supported, r = +0.20) is information only.
- *Not yet:* the ecosystem constructs, eco-edges and eco-loop (Layer 3) still read direction
  only ("5/5 measurements observed"); out of this pass's scope.

*Reference series as L2 connections (2026-10-10).* Structured context data (`kind: reference`
pipelines: MoSPI now; RBI rates, bond/CP flows, FCI, CGA next) explains credit at L2 through
tested links, before S4 (DECISIONS: every source its own pipeline; only lending data gets a page).
`relationship_test.run_reference` reads a series through `real_economy.reference` (the 1f
reader), measures its monthly change in YoY with its own headline removed as the tide (WPI all
for a WPI item), and tests it against a credit line's gap changes, the same protocol. First
family of 2 (declared +, lag 0, bar 0.025): **WPI fertilisers → fertiliser credit not supported**
(r = +0.21, p = 0.33; best other lag 1, r = +0.38, p = 0.08, which can only be re-declared and
tested on months not yet seen); **WPI jewellery → gold loans not supported** (r = +0.18, p = 0.44).
The gold levels co-trend, but the shape does not fit a price cause: gold-loan YoY went 51% → 138%
(Sep 2024 → Apr 2025) while jewellery prices rose 8–12%, and slowed to 83% while prices were
still +24%. A non-price driver, so an S4 question. Recorded in `analysis/cross_source/relationship_tests.json`.

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

**Force timing (v3.1, enforced after the migration in §16 Step 3):** every force carries either
`starts` + `delay_months` + `fades_after_months` or `standing: true`, never both, never neither;
`starts` parses as an ISO date; `timing_rule` is one of the §10.1 values.

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
