# Fable brief — Insight Archetypes: deterministic cross-segment insights with a real-world map

> **For a Fable session.** Design-first, then implement, per the authoring rules in the root
> `CLAUDE.md`. Produce a spec (`analysis/INSIGHT_ARCHETYPES_SPEC.md`) and get it approved before
> code. Design against **both pipelines at once** (SIBC + ATM/POS) — one generic mechanism, not
> per-pipeline one-offs. **Dashboard/insight IA redesign is explicitly OUT of scope** (separate
> task). This brief sets the problem, the spine, and the boundaries; you produce the detailed
> spec + implementation.

---

## The goal in one line

Turn the hand-crafted "insight archetypes" (rotation, divergence, cluster) into **deterministic,
spec-encoded outputs** that carry a **defensible real-world map** — computed every period, for
every segment, across both pipelines — so the platform emits map-to-the-real-world insights
automatically instead of a human hunting for them each cycle.

Motivation: *a data insight with no real-world map is just a number.* Today the per-segment scan
insights are descriptive ("X leads, Y lags"). The value is in the cross-segment *reading* — where
capital is rotating, which segments contradict their family, which clusters are firing — **and what
that reflects in the real world.** That reading is currently manual; it should be mechanism.

---

## The non-negotiable spine: the three-layer decomposition

Every archetype separates into three layers. **This separation is the whole design — do not blur it.**

| Layer | Who produces it | Rule |
|---|---|---|
| **Detection** | deterministic compute | The pattern is computed from signals.db. No LLM, no judgment. |
| **Meaning** (the real-world map) | authored **once**, **sourced** where it claims transmission | A fixed taxonomy of what segments *represent*. Applied deterministically per period. Never re-inferred per run. |
| **Editorial** ("vs the prevailing narrative", voice) | **human, downstream** | NOT generated. The engine emits the defensible pattern+meaning; the human adds the narrative hook on LinkedIn. |

The LLM may **narrate** the detected pattern + authored meaning in plain English (like the existing
scan/opportunity narration), but it **must never invent the economics**. Same discipline as the
sourced-force / channel model: real-world knowledge enters as authored, sourced structure — never as
per-period LLM freelancing. (This is the failure mode behind the self-contradicting-card and
"fully-engaged-loop" bugs — keep it out.)

---

## The archetypes are a generalization of `scan`

You already have **scan** signals (`csv_sector_scan_yoy`, `csv_sector_scan_share` for SIBC;
`csv_bank_scan`, `csv_category_scan_share` for ATM/POS) — cross-entity distribution at a point in
time. The archetypes are the natural family scan belongs to. Design them as a **relational-insight
signal class**:

| Archetype | Detects | Deterministic rule (design the exact form) | Status |
|---|---|---|---|
| **scan** | distribution now → leaders/laggards | existing | ✅ have |
| **rotation** | distribution of *change* → who is gaining/losing ground | rank entities by Δshare (or Δgrowth) over a window; top gainers vs top losers | **new** |
| **divergence** | entities contradicting their **parent/family** | flag child whose direction ≠ parent's (e.g. consumer-durables ↓ while personal-loans ↑); or two family members with opposite sign | **new** |
| **cluster** | a defined group moving together | co-movement above threshold across an **authored** group | ✅ exists as system-model channels/loops (PLI loop) — reuse, don't rebuild |
| **cross-system** | flow/stock, construct, loop across pipelines | ecosystem cross-edges | ✅ done (COMPOSITION_SPEC) |

So the new work is **rotation** + **divergence** as compute methods, plus wiring cluster/cross-system
readings into the same typed-insight output. Generic by construction: the same operators must run on
SIBC industries, SIBC sub-sectors, ATM/POS banks, and ATM/POS spend-categories.

---

## What to design & specify (produce these in the spec)

1. **Relational-insight signal class.** New `compute.method`s (`*_rotation`, `*_divergence` — name per
   convention) in `registry.json`, implemented in `analysis/signals/compute/` (SIBC + ATM/POS share
   the engine). Define: the window, the ranking/flagging rule, the output shape in signals.db,
   status rules. Rotation and divergence are **relational** (operate over an entity set / a
   parent-child relation), like scan — extend the scan machinery rather than inventing a parallel one.

2. **The `economic_role` taxonomy (the meaning layer).** Add a dimension to `concept_tags` (today:
   product/measure/segment/lender/geography → add `economic_role`), declared per entity in the
   skeleton profile so it regenerates deterministically. Values are an authored, small controlled
   vocabulary (e.g. `energy_logistics_capex`, `capital_goods`, `industrial_inputs`,
   `consumer_traditional`, `consumer_mobility`, …). **Sourcing rule:** where a role mapping underlies
   a *transmission claim* ("credit to energy_logistics_capex leads generation capex"), it must be
   **sourced** exactly like a channel/force (SYSTEM_MODEL_SPEC §13). A pure grouping label needs no
   source; a causal reading does.

3. **Typed insight output.** Every emitted insight gets an `archetype` field
   (`scan|rotation|divergence|cluster|cross_system`) + carries its `economic_role` reading in
   `basis`. This is what a later IA task will organize by — but **just emit the type; do not redesign
   the dashboard here.**

4. **Traceability extension.** Every number in a rotation/divergence insight must trace to signals.db,
   same as Check 2g (SIBC) / Stage 4c (ATM/POS). Extend the existing checks; do not add a parallel
   path. Rotation/divergence numbers are deterministic → grounded by construction, but the checks must
   still cover them.

5. **Consolidation opportunity (do this right).** SIBC insight generation lives in
   `pipelines/sibc/generate_analysis_report.py`; ATM/POS in `pipelines/atm_pos/generate_atm_pos_insights.py`.
   The archetype engine is the chance to put the **generic relational-insight + narration logic in
   `core/`** (both pipelines call it), advancing the §4 unification instead of duplicating. Design it
   in `core/`, parameterized per pipeline.

---

## Hard boundaries (the epistemics — from the design conversation)

- **Directional / leading reads only.** "Accelerating credit to X signals a capex upcycle forming in
  X" is defensible (credit leads real activity). **Point predictions** ("output will grow 8%") and
  **specific attributions** ("because of scheme Y") are OUT — they need external data (IIP/GDP) or a
  sourced force. The taxonomy must not let the engine claim outcomes it can't ground.
- **Deterministic detection, authored+sourced meaning, human editorial.** No LLM invents economics.
- **Both pipelines, one mechanism** (the scalability test). If it can't run on payments banks as
  cleanly as SIBC industries, the design is wrong.
- **Dashboard/insight IA redesign is OUT of scope.** Emit the `archetype` type; stop there.
- **"vs prevailing narrative" is NOT generated** — the engine emits the pattern; the human adds it.

---

## Concrete test cases (May 2026 data — the design must produce these)

- **Rotation (SIBC industry-by-type):** Ports +82.8%, Petroleum +40.9%, Engineering +35.1%, Power
  +23.8% gaining; Textiles +10.3%, Infrastructure +11.6% lagging vs aggregate +17.5% → read:
  *"capital rotating toward energy_logistics_capex + capital_goods, away from consumer_traditional."*
- **Divergence (SIBC personal loans):** Consumer durables −3.4% while Vehicle loans +18% and personal
  loans overall +15% → read: *"consumption credit bifurcating — mobility up, durable-financing
  contracting."* (child contradicts parent/family.)
- **Cluster (SIBC industry):** Engineering +35%, Electronics +24%, Iron&Steel +23%, Basic Metal +21%,
  Vehicles +26% moving together above aggregate → the metals→engineering→electronics chain (the
  existing PLI loop) firing. Reuse the system-model group.
- **ATM/POS analog:** rotation across bank categories / spend-categories; divergence of a bank vs its
  category. Prove the mechanism is generic.

---

## Deliverables

1. `analysis/INSIGHT_ARCHETYPES_SPEC.md` — the three-layer contract, the relational-signal class,
   the `economic_role` taxonomy + sourcing boundary, the typed-insight output, the epistemics
   boundary. **Approved before code.**
2. Implementation: registry methods + `core/` engine + `economic_role` in concepts/profiles +
   traceability extension. Both pipelines.
3. Tests (unit tests for rotation/divergence detection like `test_scan_insight.py`) + both gates
   green incl. build.
4. Update `RESEARCH_BACKLOG.md` / `CLAUDE.md` component table when live.

## References to ground on

| File | Why |
|---|---|
| `analysis/signals/registry.json` + `signals/compute/{sibc,atm_pos}.py` | where scan lives; extend for rotation/divergence |
| `analysis/pipelines/sibc/generate_analysis_report.py` (`deterministic_scan_insight`) | current SIBC insight gen (recently fixed for scan share/yoy/N=2) — model for the archetype narration |
| `analysis/pipelines/atm_pos/generate_atm_pos_insights.py` | ATM/POS insight gen — unify into core/ |
| `analysis/ontology/concepts.json` + `{pipeline}/skeleton_profile.*` | concept_tags — add `economic_role` |
| `analysis/SYSTEM_MODEL_SPEC.md` §13 | sourcing protocol the taxonomy's transmission claims must follow |
| `analysis/rbi_sibc/merged/system_model.json` (PLI loop) | existing cluster structure to reuse |
| `validate_sibc_traceability.py` (2g) / `validate_atm_pos_insights.py` (4c) | traceability to extend |

---

*Scope reminder: build the insight-archetype **engine**. The dashboard reorganization that consumes
`archetype` types is a deliberately separate task — do not start it here.*
