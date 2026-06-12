# System Model Composition Specification — India Credit Lens
> Version 1.0 | June 2026 | Extends `SYSTEM_MODEL_SPEC.md` v3.0

This document defines how **multiple pipeline system models compose** into one ecosystem view,
and refines the v3.0 behavioral layer by splitting it into a **data-less causal structure** and a
**dated instance layer**. It is the contract for building SIBC, then payments, then any future
ingestion (TReDS, secured-loan originations, …) such that **each new pipeline plugs into a shared
hub without touching the others**.

Read `SYSTEM_MODEL_SPEC.md` v3.0 first — the per-pipeline structural skeleton (its §5–§7) is
unchanged and is the substrate this document builds on.

---

## 1. The five strata

v3.0 had three strata (skeleton / behavioral / dynamic). v1.0 composition refines the middle and
adds the cross-system + inference strata. The five strata, and who owns each:

| # | Stratum | Produced | Scope | Changes when |
|---|---------|----------|-------|--------------|
| **S1** | Structural skeleton | deterministic (CSV + profile) | per pipeline | source adds/removes a code |
| **S2a** | Causal structure (data-less) | authored | **shared hub** | a new *mechanism* is learned |
| **S2b** | Force instances (dated) | authored | per pipeline | a real-world event occurs |
| **S3** | Dynamic causal view | computed each period | per pipeline + composed | every ingestion |
| **S4** | Inference + sourcing | LLM-proposed, source-validated | feedback into S2 | data reveals a new pattern |

**The cycle:** `S1 → S2a/S2b → S3 → S4 → (promote) → S2a`. S1 is the fixed substrate; S4 is the
only non-deterministic stratum and it may only write into S2 **after source validation** (§8).

**Composition principle (locked):** *federate the source of truth, compose by reference, project
the combined view.* No pipeline's model is ever merged into another. The ecosystem graph is
**computed on demand** by following references through the shared hub; it is never an authored file.

---

## 2. The S2a / S2b split (refines v3.0 §8, §10.1, §13)

v3.0 collapsed three things into one `force` node: the durable mechanism, the dated event, and the
current evidence. v1.0 separates them.

### 2a — Causal structure (the data-less backbone)
A **causal channel** is a durable cause→effect mechanism, defined over **concepts** (§4), never over
pipeline-specific entity codes, and carrying **no dates, URLs, or signal evidence**. It is true
whether or not anything is currently happening.

```
channel := {
  id, label,
  driver_type        : policy_action | macro_factor | structural_shift | institutional_behavior,
  source_concept     : a concept ref describing the exogenous driver (e.g. macro:collateral_price),
  target_concepts    : [concept refs it acts on],          # what it drives/suppresses
  mechanism          : structural prose — HOW, no current observations,
  polarity           : + | - | ~ ,
  lifecycle          : permanent | conditional             # permanent = always a valid channel
}
```
Channels live in the **shared hub** (`analysis/ontology/channels.json`), not in any pipeline. This
is the single most important move: a channel like *collateral price → secured-lending capacity*
applies identically to SIBC gold-loan **stock**, a future originations **flow**, and a future TReDS
**flow** — define it once, every pipeline that tags the concept inherits it. **S2a is therefore also
the cross-system connective tissue** (§6).

### 2b — Force instances (the dated, sourced events)
A **force instance** is a real-world event that *activates* a channel at a point in time. All the
"news noise" (dates, sources, excerpts, signal evidence) lives here.

```
force_instance := {
  id, label,
  instance_of        : channel id,                          # which channel it activates
  scope_entities     : [entity URNs] this event actually touched (§3),
  signal_evidence    : [L1 signal ids],                     # v3.0 §13 protocol still applies
  source, source_url, source_verified_date, source_excerpt, source_rationale,
  claim_type         : inference | hypothesis,
  status             : emerging | active | watch | retired,
  retire_period?
}
```
Instances live with their pipeline (`analysis/{pipeline}/merged/force_instances.json`) or inline in
the model under a `force_instances` array. Retiring an instance (gold stops rising) does **not**
remove the channel — the mechanism remains valid, simply dormant.

> Migration: each v3.0 `force` node splits into exactly one channel (S2a, dedup across pipelines)
> + one force instance (S2b). The edge `force → entity (mechanism, polarity)` becomes the channel's
> `source_concept → target_concepts`; the instance keeps the sourcing + evidence.

---

## 3. Global entity addressing (URN)

Cross-system reference requires a global namespace. Every entity gets a stable **URN**:

```
icl:{pipeline}/{partition}/{code}
  e.g. icl:sibc/Statement1/4.8         (Gold Loans, stock)
       icl:atm_pos/cards/credit_cards  (Credit cards outstanding, count)
```
- The pipeline-local `id` (`e_S1_4_8`) is retained for intra-pipeline edges; the URN is the
  cross-pipeline handle. The generator emits both (`id` + `urn`).
- URNs are **permanent** (same rule as annotation IDs). A code that disappears retires its URN; it
  is never reissued.

---

## 4. The shared semantic hub

`analysis/ontology/concepts.json` — a small, slowly-changing controlled vocabulary across five
dimensions. Every pipeline entity maps to a point in this space via `concept_tags`; cross-system
links are derived from shared coordinates (§6).

| Dimension | Controlled vocabulary (seed — extend as pipelines arrive) | Notes |
|-----------|-----------------------------------------------------------|-------|
| **product** | `bank_credit, food_credit, agriculture, industry, msme_credit, large_corporate, services, nbfc_credit, trade_credit, infrastructure_credit, personal_loan, housing, gold_loan, vehicle_loan, credit_card, debit_card, consumer_durable, education_loan, export_credit, pos_acceptance, qr_acceptance, atm_cash, micro_atm, card_spend` | the *what*. The primary join key across systems. |
| **measure** | `stock, flow, count` × `value, volume, balance` | **the cross-system law lives here** — `flow` leads/accumulates into `stock` (§6). SIBC=stock; payments=flow/count; TReDS/originations=flow. |
| **segment** | `retail, msme, corporate, agri, government, financial_institution` | borrower class. |
| **lender** | `psb, private, foreign, sfb, payment_bank, nbfc, all` | `all` = system-total (SIBC today); payments resolves lender. |
| **geography** | `national, metro, non_metro, state:{code}` | mostly `national` today; deferred resolution until an ingestion provides it. |

```
concept_tags on an entity := {
  product   : <vocab>        # required
  measure   : <vocab>        # required
  segment   : <vocab|null>
  lender    : <vocab|null>   # 'all' for system-total pipelines
  geography : <vocab|null>   # 'national' default
}
```
Tags are declared in the **pipeline profile** (`skeleton_profile.json`, a new `concept_tags` block
keyed by `(partition, code)`), so they regenerate with the skeleton and stay deterministic. An
untagged entity is a **tagging gap** (audit output), not an error.

---

## 5. Determinism contract

| Stratum | Deterministic? | Where judgment / non-determinism is quarantined |
|---------|----------------|--------------------------------------------------|
| S1 skeleton | yes | — |
| S2a channels | authored, stable | small reviewed registry; versioned |
| S2b instances | authored | sourcing-gated (v3.0 §13) |
| concept_tags | authored once, then deterministic | profile-declared |
| **cross-system candidates** | **derived deterministically** (§6) | — |
| cross-system confirmation | authored / LLM | reviewed; never auto-promoted |
| S3 dynamic | computed | — |
| S4 inference | LLM | **source validation gate before any S2 write** |

The backbone (S1, tags, candidate derivation, S3) is fully reproducible. Judgment exists only in
S2 authoring and S4 confirmation, both gated.

---

## 6. Cross-system composition (M+N, never M×N)

Cross-system relationships are **derived, then confirmed** — never hand-authored pairwise.

**Derivation (deterministic).** Given the tagged entities of any two pipelines, emit *candidate*
cross-links:
1. **Stock↔flow** — same `product`, different `measure` class (`flow` vs `stock`) ⇒ candidate
   `leads` (`flow → stock`). *e.g.* `icl:originations/.../gold_disbursement (flow)` →
   `icl:sibc/Statement1/4.8 (stock)`. This is the highest-value, near-deterministic law.
2. **Shared channel** — two entities tag a `product`/`segment` that a channel (§2a) targets ⇒
   candidate `co_driven` (both move with the channel). *e.g.* zero-MDR channel co-drives
   `icl:atm_pos/.../qr_acceptance` (+) and `icl:atm_pos/.../pos_acceptance` (−).
3. **Same product, different lens** — same `product` + `segment`, complementary measures ⇒ candidate
   `corresponds_to`. *e.g.* card-spend `flow` ↔ credit-card `stock`.

**Confirmation.** Each candidate is reviewed (authored) or proposed by S4 + source-validated, then
promoted into `analysis/cross_source/composition.json` as a confirmed cross-edge (by URN). Only
confirmed edges enter the projected ecosystem graph.

**Adding a pipeline is M+N:** map its entities to concepts (N tags) + attach to channels; the
derivation produces its candidate links against every existing pipeline automatically. No existing
model is edited. This is the scalability guarantee.

---

## 7. The projected ecosystem view (S3, composed)

The "combined model" is a **read projection**, computed by `compose_ecosystem.py`:
```
inputs : every pipeline's system_model.json (S1+S2b) + ontology/{concepts,channels}.json (S2a)
       + cross_source/composition.json (confirmed cross-edges) + current signal DB (S3 states)
output : ecosystem_state_{period}.json  — a graph keyed by URN, with channel activation,
         intra- and cross-system edge states, loops, and observations. NEVER hand-edited.
```
Because it is computed, it can be regenerated identically and cheaply each period, and it never
couples pipeline release cadences.

---

## 8. The S4 inference loop (LLM → sourcing → promote)

Data (S3) surfaces a pattern not yet in S2 → an LLM proposes a **new channel** (S2a) or a **new
force instance** (S2b) or a **cross-edge** (§6). The proposal is a *candidate only* until it passes
the v3.0 §13 Force Identification Protocol (external source + ≥1 L1 signal change + documented
mechanism). **Unvalidated proposals never enter the source of truth.** This is the single, gated
path by which non-deterministic inference improves the deterministic backbone.

---

## 9. File conventions (additions to v3.0 §19)

| Item | Path |
|------|------|
| Concept vocabulary | `analysis/ontology/concepts.json` |
| Causal channel registry (S2a, shared) | `analysis/ontology/channels.json` |
| Per-pipeline concept tags | inside `analysis/{pipeline}/skeleton_profile.json` (`concept_tags` block) |
| Per-pipeline force instances (S2b) | `analysis/{pipeline}/merged/system_model.json` (`force_instances[]`) |
| Confirmed cross-system edges (L2b) | `analysis/cross_source/composition.json` |
| Candidate cross-links (derived) | `analysis/cross_source/candidates_{period}.json` (regenerable) |
| Ecosystem projection (S3 composed) | `analysis/cross_source/ecosystem_state_{period}.json` |
| Composer | `analysis/compose_ecosystem.py` |
| Candidate deriver | `analysis/derive_cross_links.py` |

---

## 10. Validation additions

| Check | Rule |
|-------|------|
| URN integrity | every entity has a unique, well-formed URN; no reissued URNs across periods |
| concept_tags | `product` + `measure` present; all tag values in `concepts.json` vocabulary |
| channel refs | every channel `source_concept`/`target_concepts` resolve to concept vocab |
| instance refs | every `force_instance.instance_of` resolves to a channel; `scope_entities` are valid URNs; sourcing per §13 |
| cross-edge refs | every confirmed cross-edge endpoint is a valid URN in a different pipeline |
| no monolith | no `system_model.json` references another pipeline's entities directly (must go via `composition.json`) |

---

## 11. Build order (pipeline by pipeline)

1. **Lock the hub** — author `concepts.json` (vocab) + `channels.json` (data-less channels) + URN scheme + validators.
2. **SIBC** — split its v3.0 forces into channels (→ hub) + instances; add `concept_tags` to its profile; regenerate; validate.
3. **Payments** — same; reuse/extend hub channels (zero-MDR, card-lifecycle).
4. **Cross pass** — run `derive_cross_links.py` (SIBC↔payments), confirm the real links → `composition.json`, project `ecosystem_state`. Validates the whole mechanism on two pipelines.
5. **Each new pipeline (TReDS, originations, …)** — skeleton + concept_tags + attach to channels; derivation auto-produces its cross-links; existing models untouched.

S3 dynamic compute and S4 inference are built after steps 1–4 prove the static composition.

---

## 12. Projection / Surfacing contract (model → UI)

The UI surfaces are **projections** of the model — different strata feed different surfaces.
No surface reads the source-of-truth files directly; each consumes a projected feed. Every
surfaceable node (insight / risk / opportunity) carries a small reference set so the UI knows
*where* to place it and can drill from headline → evidence.

### 12.1 Stratum → surface map
| Model element | Surface | Renders | Driven by |
|---|---|---|---|
| entity (S1) + L1 signals | per-pipeline dashboard — chart | series, value, YoY | S1 + signals.db |
| force_instance firing (S2b × S3) | per-pipeline dashboard — "why it moved" | causal explanation + source | S2b + S3 |
| risk, active | per-pipeline page (callout) | tension + evidence | S2 + S3 |
| opportunity, active | **`/opportunities` layer** | opening, status, evidence | channel/instance + S3 |
| cross-edge, active | **`/opportunities` — premium** | cross-system opening | cross-ref + S3 |

### 12.2 Surfaceable-node reference fields
Added to every `risk` / `opportunity` node (and to confirmed cross-edges):
```
surface : "sibc" | "payments" | "opportunities"      # which UI surface
scope   : "pipeline" | "cross_source"                 # placement + provenance
refs    : { entities:[urn...], channel:id?, instance:id?, cross_edge:id? }
status  : active | watch | closed                     # COMPUTED by S3, never hand-set
```
`scope: pipeline` → renders on that pipeline's dashboard. `scope: cross_source` → renders on the
opportunities layer. `refs` make the card drill-downable (channel → instance → source → live signals).

### 12.3 Deterministic opportunity status (replaces ad-hoc authoring)
Opportunity/risk `status` is **derived every period**, not hand-set:
```
for each opportunity O anchored to driver D (channel-instance or cross-edge):
    if D is firing (S3) for ≥2 periods         → active
    elif D fired previously but not now        → watch
    elif D dormant ≥N periods                  → closed
    attach the S3 signal evidence that decided it
```
This is the systematic trigger rule the prior ad-hoc opportunities lacked: driver → signal state →
opportunity status, with evidence, evaluated each ingestion.

### 12.4 Monetisation note (why the opportunities layer is the product)
Per-pipeline insights are commoditisable (anyone with the source file can derive them) — they build
credibility on the pipeline dashboards. **Cross-system opportunities** (`scope: cross_source`) cannot
be produced without the composition layer, so they are the differentiated, defensible product and
should populate the opportunities layer preferentially. Example: `x_cc_spend_leads_cc_stock` +
payments POS contraction ⇒ *"unsecured origination headroom opening — route via UPI-credit, not POS."*

---

*Composition Specification v1.0 — extends System Model Specification v3.0 — India Credit Lens*
