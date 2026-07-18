# Fable brief — Cross-segment insights with a real-world reading

> **For a Fable session.** Spec-first, then implement, per the root `CLAUDE.md` authoring rules.
> Design against **both pipelines at once** (SIBC + ATM/POS) — one generic mechanism.
>
> ## ⚠️ Scope discipline: this is NOT a new layer
> An earlier draft of this brief invented the word *"insight archetypes"* and proposed a new
> `INSIGHT_ARCHETYPES_SPEC.md`. **That was wrong — do not do it.** The work decomposes cleanly into
> **three extensions of existing specs**. Creating a new stratum/vocabulary would paper over the fact
> that these pieces deliberately live at *different* strata (L1 signals vs S2a model structure vs L2b
> composition). **No new spec document. No new layer. No new umbrella term.**
>
> Dashboard/insight IA redesign is also **out of scope** (separate task).

---

## The goal

Emit **cross-segment** insights that carry a **defensible real-world reading** — computed every
period, for every segment, on both pipelines — instead of a human hand-crafting them each cycle.

Motivation: *a data insight with no real-world map is just a number.* Today's per-segment scan
insights are descriptive ("X leads, Y lags"). The value is in the cross-segment reading — where
capital is **rotating**, which segments **contradict their family** — and what that reflects in the
real world.

---

## The three extensions (this is the whole scope)

### 1. Signal layer — two new compute methods
**Home:** `analysis/signals/README.md` (conventions) + `registry.json` (specs) + `signals/compute/`.
These are ordinary new **L1 signal types**, exactly like `csv_streak` or `csv_sector_scan_yoy` —
nothing architecturally novel.

| Method | Detects | Rule (design the exact form) |
|---|---|---|
| **rotation** | who is *gaining/losing ground* | rank entities by Δshare (or Δgrowth) over a window → top gainers vs top losers |
| **divergence** | a child contradicting its **parent/family** | flag entity whose direction ≠ parent's (consumer-durables ↓ while personal-loans ↑), or family members with opposite sign |

Both are **relational** (operate over an entity set / a parent-child relation) — like `scan`. **Extend
the existing scan machinery; do not build a parallel one.** Must run generically on SIBC industries,
SIBC sub-sectors, ATM/POS banks, ATM/POS spend-categories.

### 2. Semantic hub — one new `concept_tags` dimension
**Home:** `analysis/COMPOSITION_SPEC.md` §4 + `ontology/concepts.json` + per-pipeline
`skeleton_profile`. Today's dimensions: `product, measure, segment, lender, geography` → **add
`economic_role`** (§4 already says "extend the vocab as new pipelines arrive" — this is its
documented extension point).

Small controlled vocabulary, e.g. `energy_logistics_capex`, `capital_goods`, `industrial_inputs`,
`consumer_traditional`, `consumer_mobility`. Declared per entity in the skeleton profile so it
regenerates deterministically.

### 3. Transmission claims — **nothing new; they are channels**
A causal reading ("credit to `energy_logistics_capex` *leads* generation capex") is **exactly the
definition of a channel** (S2a): a durable, data-less cause→effect defined over *concepts*, carrying
a source. Author it in `ontology/channels.json` — or let **S4** propose it. **Do not invent a new
construct for this.**

Plus a minor field on the emitted insight recording which method/structure produced it (extend the
existing insight schema; do not restructure it).

---

## The discipline (non-negotiable): detection / meaning / editorial

Distinct from *strata* — this is about **who produces what**:

| Role | Producer | Rule |
|---|---|---|
| **Detection** | deterministic compute | pattern computed from signals.db. No LLM, no judgment. |
| **Meaning** (real-world reading) | authored **once**, **sourced** where it claims transmission | applied deterministically per period; never re-inferred per run. |
| **Editorial** ("vs the prevailing narrative", voice) | **human, downstream** | NOT generated. Engine emits pattern+meaning; the human adds the hook. |

The LLM may **narrate** detected pattern + authored meaning in plain English (as scan/opportunity
narration already does) but **must never invent the economics**. This is the failure mode behind the
self-contradicting-card and "fully-engaged-loop" bugs — keep it out.

---

## How the meaning is *determined* (the operator cannot author economics from scratch)

Split it — the two halves are determined very differently:

**(a) `economic_role` labels — textbook, low-stakes, LLM-drafted + human sanity-checked.**
Standard industry classifications (Power/Petroleum/Ports → `energy_logistics_capex`; Textiles →
`consumer_traditional`; Engineering → `capital_goods`). A wrong label is a *categorization* error,
not a false claim. **No source required for a pure grouping label.** This half alone powers
**rotation + divergence** — roughly 80% of the value.

**(b) Transmission claims — via the S4 sourcing gate, never hand-authored.**
Reuse `analysis/core/run_inference.py` + SYSTEM_MODEL_SPEC §13: the **LLM proposes the channel *with a
citation*** (economic literature / RBI — "credit leads capex" is documented, not opinion) → the
**sourcing gate validates** → the operator **reviews and promotes**. Never auto-promoted.

**Invariant: propose ≠ promote.** LLM proposing the *one-time* structure through a sourcing gate is
allowed (that's S4). LLM inventing the reading *per period, unvalidated, into output* is forbidden.

**Sequencing:** ship **(a) first** — labels make rotation + divergence work immediately with no
sourcing bottleneck. Then **(b)** as an S4-fed layer. Do not block the feature on sourcing.

---

## Hard boundaries (epistemics)

- **Directional / leading reads only.** "Accelerating credit to X signals a capex upcycle forming in
  X" is defensible (credit leads real activity). **Point predictions** ("output will grow 8%") and
  **specific attributions** ("because of scheme Y") are OUT — they need external data (IIP/GDP) or a
  sourced force.
- **Both pipelines, one mechanism.** If it can't run on payments banks as cleanly as SIBC industries,
  the design is wrong.
- **Traceability:** every number must trace to signals.db — extend Check 2g (SIBC) / Stage 4c
  (ATM/POS); do not add a parallel path.
- **Consolidation opportunity:** SIBC insight gen lives in `pipelines/sibc/generate_analysis_report.py`,
  ATM/POS in `pipelines/atm_pos/generate_atm_pos_insights.py`. Put the generic relational-insight logic
  in **`core/`** (both pipelines call it) — advancing the §4 unification rather than duplicating.

---

## Concrete test cases (May 2026 data — the design must produce these)

- **Rotation (SIBC industry-by-type):** Ports +82.8%, Petroleum +40.9%, Engineering +35.1%, Power
  +23.8% gaining; Textiles +10.3%, Infrastructure +11.6% lagging vs aggregate +17.5% → *"capital
  rotating toward energy_logistics_capex + capital_goods, away from consumer_traditional."*
- **Divergence (SIBC personal loans):** Consumer durables −3.4% while Vehicle loans +18% and personal
  loans overall +15% → *"consumption credit bifurcating — mobility up, durable-financing contracting."*
- **Cluster (existing, reuse):** Engineering +35%, Electronics +24%, Iron&Steel +23%, Basic Metal +21%,
  Vehicles +26% together above aggregate → the metals→engineering→electronics chain (existing PLI loop).
- **ATM/POS analog:** rotation across bank categories / spend-categories; divergence of a bank vs its
  category. Proves the mechanism is generic.

---

## Deliverables

1. **Spec edits to EXISTING documents** (approved before code):
   - `analysis/signals/README.md` — the two new compute methods + their conventions.
   - `analysis/COMPOSITION_SPEC.md` §4 — `economic_role` dimension + the label-vs-transmission rule.
   - `analysis/SYSTEM_MODEL_SPEC.md` — only if the channel usage needs a clarifying note; likely none.
2. Implementation: registry entries + `core/` relational-insight engine + `economic_role` in
   concepts/profiles + traceability extension. Both pipelines.
3. Unit tests (mirror `analysis/tests/test_scan_insight.py`) + both gates green incl. build.
4. Update `CLAUDE.md` component table + `RESEARCH_BACKLOG.md` when live.

## References

| File | Why |
|---|---|
| `analysis/signals/README.md`, `registry.json`, `signals/compute/{sibc,atm_pos}.py` | where scan lives; extend for rotation/divergence |
| `analysis/COMPOSITION_SPEC.md` §4 | concept_tags hub — the `economic_role` extension point |
| `analysis/ontology/{concepts,channels}.json` | vocabulary + channels (transmission claims) |
| `analysis/SYSTEM_MODEL_SPEC.md` §13 | sourcing protocol for transmission channels |
| `analysis/core/run_inference.py` | S4 — how sourced proposals enter |
| `analysis/pipelines/sibc/generate_analysis_report.py` (`deterministic_scan_insight`) | model for deterministic insight narration (recently fixed for share/yoy/N=2) |
| `validate_sibc_traceability.py` (2g) / `validate_atm_pos_insights.py` (4c) | traceability to extend |
| `analysis/rbi_sibc/merged/system_model.json` (PLI loop) | existing cluster structure to reuse |

---

*Scope reminder: two signal methods + one concept dimension + reuse channels. **No new layer, no new
spec document, no new umbrella vocabulary.** Dashboard IA is a separate task.*
