# System Model Composition Specification — India Credit Lens
> Version 1.1 | July 2026 | Extends `SYSTEM_MODEL_SPEC.md` v3.0
> Part I (§1–§12, v1.0): federation, hub, cross-edges, projection — unchanged.
> Part II (§13–§22, v1.1): the ecosystem meta-model — constructs, eco-edges, cross-pipeline loops, reconciliation constraints, domains, Layer 3 narrative.

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
| **economic_role** | `energy_logistics_capex, capital_goods, industrial_inputs, construction_real_estate, agri_inputs, trade_channel, consumer_traditional, consumer_mobility, consumer_durables, consumer_finance, financial_intermediation, digital_payment_rails, cash_infrastructure` | the *real-world reading* — what activity this credit/infrastructure finances. Powers the relational insights (rotation/divergence, `signals/README.md`). **Optional** (null allowed); untagged = tagging gap. |

```
concept_tags on an entity := {
  product       : <vocab>        # required
  measure       : <vocab>        # required
  segment       : <vocab|null>
  lender        : <vocab|null>   # 'all' for system-total pipelines
  geography     : <vocab|null>   # 'national' default
  economic_role : <vocab|null>   # real-world reading; null = untagged (gap, not error)
}
```
Tags are declared in the **pipeline profile** (`skeleton_profile.json`, a new `concept_tags` block
keyed by `(partition, code)`), so they regenerate with the skeleton and stay deterministic. An
untagged entity is a **tagging gap** (audit output), not an error.

**How `economic_role` is determined (labels vs transmission — keep these distinct):**
- A role tag is a **grouping label** — standard industry classification (Power/Ports →
  `energy_logistics_capex`; Textiles → `consumer_traditional`). Textbook, low-stakes; a wrong tag is
  a categorization error, not a false claim. **No source required.** Drafted by the LLM from
  established taxonomy, sanity-checked by the operator, then fixed in the profile.
- A **transmission claim** built on a role ("credit to `energy_logistics_capex` *leads* generation
  capex") is a **channel** (§2a) — it carries a source and enters via authoring or the S4 gate
  (SYSTEM_MODEL_SPEC §13). The tag alone never licenses a causal statement; deterministic insight
  templates may use tags for *composition* readings ("capital rotating toward energy & logistics
  capex") but must not assert lead/lag transmission without a channel behind it.

**Lender asymmetry (hard limit — do not design joins that cannot exist):** SIBC has **no lender
decomposition** (`lender: all`, system-total only — RBI publishes sectoral deployment system-wide).
Payments resolves lender per bank/category. Therefore bank-level cross-pipeline joins are
**impossible on the credit side**; the only well-formed comparison is payments-by-bank-type vs
SIBC-system-total, and any output pairing them must label the asymmetry.

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

### 8.1 Retrieval and verification — the measured bottleneck (added 2026-08-19)

> **CORRECTION, 2026-09-09 — an earlier note in this section claimed `pib.gov.in` had begun
> blocking the automated fetch. That was FALSE and is retracted.**
> `core.source_fetch.fetch_text` returns a **tuple** `(text, verdict)`. The probe called `len()`
> on the return value, so every host answered "2" — the length of a two-element tuple — and five
> PIB URLs answering "2" looked exactly like a host-wide block. A control was not run until later;
> Wikipedia and `example.com` answered "2" as well, which is what exposed it.
>
> Measured correctly, both primary official hosts are **fully open**: PIB returns 9,320 / 42,879 /
> 68,483 characters on three article URLs and `rbi.org.in` returns 11,185 on a notification URL,
> all with verdict `ok`. All three currently sourced SIBC forces — KCC, MSP and vehicle scrappage —
> re-verify their excerpts through the unattended path.
>
> **So rung 1 is machine-verifiable and the arc-3 regulatory watch may rely on it.** The 2026-08-19
> finding above stands unchanged and is the real constraint: what needs a browser is *finding which
> instrument*, not fetching it.
>
> The lesson is the one this section already teaches, turned on its author: an observation became a
> diagnosis without a control, and the untested diagnosis was about to redirect a build.



The gate is sound; **retrieval is where proposals die.** Measured 2026-08-19 across the two most
recent runs: `s4_proposals/2026-06-30.json` **42 proposals → 5 promoted**;
`s4_proposals/2026-07-31.json` **36 proposals → 1 promoted**. All 78 still carry
`status: "proposed"` and **zero** carry a verdict, an attempted URL, or a rejection reason.

Four distinct failures, previously merged into one informal "sourcing is hard":

- **R1 — Retrieval is blocked far more narrowly than recorded.** The prior note ("PIB/NPCI/
  Business Standard 403 the crawler; Chrome is the only path") was **generalised from a
  WebFetch-tool block to a site-wide one, and that is wrong.** Probed 2026-08-19 with plain `curl`
  and the **default user agent** (no spoofing):

  | host | result |
  |---|---|
  | `www.rbi.org.in` (HTML) | **200, real content**, no bot interstitial |
  | `www.pib.gov.in` (HTML, follow redirect) | **200, 73k chars** — and the KCC force's own excerpt, *"increased from Rs 1.6 lakh to Rs 2 lakh"*, verifies verbatim |
  | `rbidocs.rbi.org.in` (PDF host) | 200 but serves an **Imperva bot interstitial**, not the PDF |
  | `npci.org.in` | **403** |

  So the block is on the **document host and NPCI**, not on the official tier as such. RBI and PIB
  HTML — which carry most circulars, press releases and Master Direction landing pages — are
  directly reachable, and the KCC excerpt that was hand-verified through the editor's Chrome on
  2026-08-02 could have been machine-verified. **The editor's logged-in browser stays the documented
  path for bot-protected hosts only** (`rbidocs` PDFs, NPCI), supplying page text to
  `bank_sourcing.excerpt_on_page` (pure by design — it does not care how the text was obtained).
  **Never spoof a user agent to evade a bot block**; the successful probes above needed no UA at all.
  *Evidence strength: four URLs at one moment, not a survey — re-probe before relying on it at
  volume, and treat a future 403 as a site decision to respect, not a bug to route around.*
- **R2 — No PDF text path, and this blocker is smaller than recorded.** `excerpt_on_page` needs
  text; RBI's authoritative material (Master Directions, FSR, bulletins, circulars) is PDF.
  `PLAN_2026-08-11.md` records "no PDF extraction anywhere… its own project" — that **conflates two
  problems**. Table extraction into an *ingestion pipeline* is a project. Extracting text to verify
  an excerpt is one command: demonstrated 2026-08-19 with `pdftotext -layout` on the RBI PSL Master
  Direction (RBI/FIDD/2024-25/128), which yielded the targets table verbatim. `pdftotext` and
  `pypdf` are already available. **The sourcing half of that blocker should be closed, not planned.**
- **R3 — `required_source` is a single named target with no fallback ladder.** e.g. *"RBI Financial
  Stability Report section on corporate leverage ratios and credit growth by firm size."* If that
  exact section does not exist or is unreachable, the proposal dies rather than degrading. This is
  what happened to the large-corporate force: the FSR release addressed stability, not
  large-corporate credit, and the nearest figure was a different aggregate on a non-allowlisted
  host. **A proposal must carry a ranked ladder** — named document → same-issuer alternative
  (bulletin / circular / press release) → Tier-2 report → Tier-3 press corroboration — so a miss at
  the top rung degrades instead of terminating. The Protocol's evidence bar does not move; only the
  search does.
- **R4 — Negative results are discarded.** With no attempted-URL or rejection record, the same
  failing search re-runs every period at full cost and learns nothing. Proposals must accumulate
  `attempts: [{url, tier, verdict, date, note}]`. **A rejection is evidence about the world and is
  retained**; it is also the honest input to C9 corrections (DISTRIBUTION_SPEC §3).

**Built 2026-08-19 (R1/R2/R3/R4).** `core/source_fetch.fetch_text` is the single URL→text path
(HTML stripped to visible text; PDFs via `pdftotext -layout`; returns `(text, verdict)` and never
raises), shared with `distribution/bank_sourcing` so both stores verify identically.
`run_inference.check_source` gates every claimed source on **host-on-allowlist → page-retrievable →
excerpt literally on the page**, and `verify_proposal` walks the ladder (`required_source` +
`source_ladder`, capped at 3 rungs) stopping at the first rung that holds. Every rung appends to
`attempts[]` — including `no_source_named` when a proposal names nothing, because a silent drop is
the discard R4 exists to stop.

**Reachability census — all 47 allowlisted hosts probed 2026-08-19, not a sample.** An earlier
note in this section rested on four hand-picked hosts, which is the same narrow-negative-test
failure this project keeps re-learning. The whole list:

| verdict | hosts | meaning |
|---|---|---|
| `ok` | 19 | readable by `fetch_text` |
| `empty` | 6 | **inconclusive** — a JS-shell homepage. `pib.gov.in` reports `empty` at `/` and **68,504 chars** at an article URL, so a homepage probe under-reports a site's real availability |
| `blocked` | 11 | genuine 403 |
| `unreachable` | 11 | connection failure |

**Chrome is not a fallback for the long tail — it is the only path for a large part of the
allowlist.** `business-standard.com` is blocked, and it is the source of **all four** existing
`bank_claims`; so are `financialexpress.com`, `reuters.com`, `bloomberg.com`, `ndtvprofit.com`,
and, in the report tier, `cibil.com`, `transunioncibil.com`, `ficci.in`, `cii.in`, `worldline.com`.
Automated verification cannot reproduce the sourcing the store already holds. Rung 1 (official) is
where the automated path pays; rungs 2–3 will frequently land on `blocked`, and the correct outcome
there is a recorded attempt plus a human with `--page-file`, never a weaker claim.

**The verification it replaces was self-report.** The prompt said "do NOT invent a URL", which is an
instruction, not a check; nothing fetched the page, compared the excerpt, or consulted the
allowlist. Proven end-to-end on the KCC force: its own excerpt — hand-verified through the editor's
Chrome on 2026-08-02 — now verifies automatically from `pib.gov.in`, while a fabricated excerpt on
the same page is rejected. **Correction to the conversion figure quoted above: the 2026-07-31 run
used `--no-verify`, so verification never ran at all; 0 of 78 proposals carry a verification block
and the single promotion was manual. The 3% was the rate a human did the work, not a rejection rate.**

**Chrome is a first-class channel, not a fallback (2026-08-19).** The census above is the reason:
19 of 47 hosts readable, and every masthead this project has actually sourced from refuses an
automated read. So the flow is *crawler where it works, browser where it does not, same check
either way*:

```
run_inference.py                         # rung-1 official sources verify automatically
run_inference.py --worklist FILE         # what the crawler could not settle, with targets + urls
run_inference.py --resolve FILE --index N --url U --excerpt E --page-file P
```

`--resolve` runs `check_source` with the browser's text instead of the crawler's. It earns
nothing: host must still be allowlisted, excerpt must still be literally on the page, and the
attempt is recorded either way. Verified end-to-end — a real PIB excerpt passes, a fabricated
excerpt on that same page fails, and an off-allowlist host fails before anything is read.

**Two failure-handling fixes this exposed.** (1) The proposal call had a hardcoded
`max_tokens=2000`; adding `source_ladder` to the schema pushed the JSON past it, every domain came
back truncated, and the run wrote **0 proposals over 36 good ones** while printing three parse
warnings. A warning that does not stop the write is the same bug class as a rule that raises and is
ignored — the writer now refuses to replace a non-empty file with an empty result, negative-tested.
(2) `required_source` targets in the existing file are descriptions, not findable documents
("RBI Financial Stability Report section on corporate leverage ratios and credit growth by firm
size"), which is R3 in concrete form and why the ladder exists.

**Why this is scheduled with the movement signals, not after them.** Movement methods
(`signals/README.md`) produce the platform's strongest why-candidates — an acceleration that leads
its peers, or a low-coherence handover such as *"public sector banks took over POS deployment from
private banks"*. Every one of them arrives at this layer. Widening the signal surface while
retrieval converts at ~3% raises the count of unexplained findings, not the count of explained ones.

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

# Part II — The Ecosystem Meta-Model (v1.1)

## 13. Motivation and design position

v1.0 built **pairwise plumbing**: shared channels (S2a) give every pipeline the same mechanism
vocabulary, and confirmed cross-edges (§6) connect entities in different pipelines. That is
necessary but not sufficient for an ecosystem view. Three kinds of structure exist that **no
single pipeline can own**, and v1.0 had no home for them:

1. **Constructs** — real-world quantities like *unsecured retail appetite* that no pipeline
   measures directly; each pipeline's entities are partial *measurements* of them.
2. **Cross-pipeline loops** — feedback cycles whose segments live in different models
   (spend flow → balance stock → credit availability → spend).
3. **Cross-pipeline constraints** — numeric invariants that must hold *between* sources
   (a flow must reconcile with the stock it accumulates into).

**Design position (locked): there is ONE meta-model, thin and federated.** It owns *only* the
three kinds of structure above, composing everything else by URN reference. It never duplicates
or absorbs pipeline internals (the no-monolith rule now applies in both directions, §20).
"Lending" vs "consumption" meta-models are **not** separate models — they are *domains*, reading
lenses over the one meta-model that carry zero structure of their own (§18).

The same three-stratum discipline as everywhere else applies, one level up:

| Stratum | Meta-model element | Produced |
|---|---|---|
| authored structure (S2) | constructs, eco-edges, loops, constraints | authored / S4-proposed, sourcing-gated |
| derived candidates | candidate construct members, candidate cross-links | deterministic from concept_tags |
| dynamic state (S3) | construct/eco-edge/loop/constraint states | computed each compose run |

### File conventions (additions to §9)

| Item | Path |
|---|---|
| Ecosystem meta-model (authored: constructs, eco_edges, loops, constraints) | `analysis/cross_source/ecosystem_model.json` |
| Domain lenses (zero structure) | `analysis/ontology/domains.json` |
| Layer 3 strategic narrative + claims sidecar | `analysis/cross_source/strategic/{domain}/{period}.md` + `{period}_claims.json` |

`composition.json` is **unchanged**: it holds confirmed *derived* pairwise links (mechanical
provenance, §6). `ecosystem_model.json` holds *authored* meta-structure. The split is by
provenance: derived-then-confirmed vs authored. `compose_ecosystem.py` consumes both.

---

## 14. Ecosystem constructs

A **construct** is a named real-world quantity measured only indirectly, by entities across ≥2
pipelines. It is a first-class node with a URN and computed state — the promotion of a concept
from *tag* (vocabulary) to *node* (model).

```
construct := {
  id, urn            : icl:eco/{id}          # permanent, never reissued (same rule as §3)
  label,
  definition         : prose — what real-world quantity this stands for and why these
                       measurements bound it,
  concept_anchor     : { product: [vocab...], measure?: class, segment?: vocab }
                       # the concept coordinates this construct generalises — drives
                       # candidate-member derivation when new pipelines arrive,
  members            : [ { urn,                        # entity URN, any pipeline
                           role   : measures | proxies | contra_indicates,
                           weight : null | share,      # null = unit weight (sign vote)
                           note } ],
  lifecycle          : permanent | conditional,
  claim_type?, source?, source_url?, source_verified_date?
                       # required per v3.0 §13 iff the definition asserts a non-obvious
                       # mechanism; pure "these measure the same thing" needs no source
}
```

**Rules.**
- Members must span **≥2 pipelines**. A single-pipeline construct is just that pipeline's
  aggregate and belongs in its own model — validation error (§20).
- **Candidate members are derived, never hunted:** when a new pipeline lands, any entity whose
  `concept_tags` fall inside a construct's `concept_anchor` becomes a *candidate member*
  (emitted by `derive_cross_links.py` alongside cross-link candidates). Confirmation is a
  review step — candidates never auto-join. This preserves the M+N guarantee: constructs
  gain coverage from new pipelines with zero edits to existing members.
- Constructs may target/be targeted by **channels** (S2a) exactly as concepts are — a channel's
  `target_concepts` may include a construct URN.

**State (computed, sign-only — consistent with per-pipeline S3):**
```
role_sign  = -1 if role == contra_indicates else +1
direction  = sign( Σ  member_direction × role_sign × (weight or 1) )    over observed members
coherence  = | Σ contribution | / Σ | contribution |        over OBSERVED members
             where contribution = member_direction × role_sign × (weight or 1)
             — measured AFTER role_sign, so a contra-indicator falling AGREES with a
               construct rising; None when nothing moved (undefined, not perfect)
agree      = aligned (≥0.90) | contested (0.50–0.90) | split (<0.50) | still (None)
basis      = { observed, total, coherence, agree, members, pipelines: {name: period, ...} }
```
Missing pipelines don't block computation; `basis` records coverage so downstream consumers
(and the narrative layer) can see how much of the construct is actually observed.

**`coherence` added 2026-08-19 — `direction` alone cannot distinguish unanimity from a near-tie.**
A construct with 5 members up and 0 down and one with 3 up and 2 down both emit `direction: +1`.
`basis` records how many members were *observed*; nothing records whether they *agreed*. This is
the same blindness as SYSTEM_MODEL_SPEC §16 Step 2 and the same quantity Layer 1 computes for
hierarchies (`signals/README.md`, movement methods) — one definition, three strata.

It is load-bearing here because of §23.1: a construct fires an opportunity when `direction ≠ 0`
for ≥2 periods. **Without `coherence`, a 3–2 split can raise a live card on `/opportunities` and
nothing in the record says it was nearly a tie.** Every eco-driven opportunity therefore carries
its driver's coherence in `basis`, and the narrative layer must not assert a construct-wide
direction in prose when coherence < 0.50 — at that point the members are trading places, which is
a different and usually better claim (`signals/README.md`, router table).

**Implemented 2026-08-19.** `compose_ecosystem.construct_direction` emits `coherence` + `agree`;
`generate_opportunities_feed` states agreement in the coverage line, the chain and the body, and
`compose_ecosystem` names it in the published label when the members are not aligned. The live pair
is the argument for it: `unsecured_retail_appetite` (5 members, all rising, coherence 1.00) and
`card_consumption_activity` (3 rising, 1 falling, 1 flat, coherence 0.50) both read
`direction: +1` and both published as *"expanding (5/5 measurements observed)"* — identical wording
for a unanimous read and a majority one, with "5/5" (coverage) inviting the reading "they agree".

**No numeric coherence reaches published prose.** It is computed in the ecosystem state, not in
`signals.db`, so Check 4f cannot ground it — negative-tested 2026-08-19, invented values of 0.73 and
0.31 both passed. The regime WORD carries the meaning and the member rows show every direction
individually. A number no gate can check does not belong in a published sentence.

---

## 15. Eco-edges — causality at the construct level

Constructs participate in causality through **eco-edges** — behavioral edges whose endpoints may
be constructs. Without them, constructs would be inert aggregates.

```
eco_edge := {
  id,
  from, to           : construct URN | entity URN,
                       # at least one endpoint MUST be a construct — entity↔entity
                       # cross-pipeline links belong in composition.json (§6), and
                       # intra-pipeline links in that pipeline's model (§20)
  type               : drives | suppresses | feeds | constrains,
  polarity           : + | - | ~,
  channel?           : channel id (S2a) this edge instantiates,
  mechanism          : structural prose — HOW,
  claim_type         : structural | inference | hypothesis,
  source?, source_url?, source_verified_date?     # required iff claim_type != structural
}
```

**State:** identical semantics to per-pipeline S3 behavioral edges — the from-node's direction
vs polarity gives `active | reversed | dormant`. Sign-only; no magnitude (per the locked S3
decision).

**Structural constraints need no new node type.** A negative eco-edge (`polarity: "-"`,
`type: constrains`) that is firing IS a binding cross-system constraint, and appears in
`ecosystem_observations.binding_constraints` — exactly symmetric with how per-pipeline S3
treats negative behavioral edges. §17 covers the *numeric* constraints only.

---

## 16. Ecosystem loops

A **cross-pipeline loop** is a named feedback cycle whose member edges span models. The loop is
authored (or S4-proposed); its firing is computed.

```
eco_loop := {
  id, label,
  type               : reinforcing | balancing,
  closure            : internal | external,     closure_note?,
  member_edges       : [ qualified refs ],
  description        : the causal story, one paragraph
}

qualified ref := "{pipeline}:{edge_id}"     # intra-pipeline behavioral edge, e.g. "sibc:e_x__drives__e_y"
              |  "x:{cross_edge_id}"        # confirmed cross-edge from composition.json
              |  "eco:{eco_edge_id}"        # eco-edge from §15
```

**Rules.**
- A loop must contain **≥1 cross-pipeline element** (an `x:` or `eco:` ref, or intra refs from
  ≥2 pipelines). Otherwise it belongs in a pipeline model — validation error (§20).
- `corresponds_to` cross-edges are **barred** from loops: they are structural identities, not
  causal segments.
- Loops may be *detected* as cycles in the composed graph and proposed via S4, but only
  confirmed (authored) loops enter `ecosystem_model.json` — same promotion discipline as §8.

**Firing (computed in compose, same rule as per-pipeline S3 step 5):** resolve each member
edge's state — intra refs from that pipeline's latest `system_state` `edge_states`; `x:` refs
mapped `aligned→active, divergent→reversed, dormant→dormant`; `eco:` refs per §15 — then:
```
all members active            → active_reinforcing | active_balancing (by type)
any member active|reversed    → partial
else                          → dormant
```
**Mixed periods:** pipelines publish on different cadences, so a loop's members may be observed
at different periods. Compose records `input_periods` per pipeline on every loop state and sets
`mixed_period: true` when they differ; a spread greater than one publication cycle emits a
staleness warning. Never blocks — the ecosystem view is always the join of latest-known states.

---

## 17. Reconciliation constraints (the cross-pipeline trust layer)

Numeric invariants that must hold **between** pipelines. These extend the freshness/traceability
guard family (Check 2f, 2g, 4f) across source boundaries — they catch both data problems
(one source revised, the other not) and model problems (a claimed flow→stock relationship that
doesn't reconcile is a wrong edge).

```
constraint := {
  id, label,
  kind               : reconciliation,          # v1.1: numeric only — causal limits are §15
  operands           : [ { pipeline, signal_id } | { urn, metric } ],
  relation           : prose + explicit formula over the operands,
  tolerance          : { type: pct | abs | corridor, value },
  severity           : warn | fail,
  note
}
```

**Evaluation:** deterministic, every compose run, reading `signals.db` (period-aligned to each
operand's latest common period). Results land in `ecosystem_state.constraint_states` as
`holds | violated | unobservable` (+ the computed residual). `severity: fail` violations fail
the gate via `validate_composition.py`; `warn` surfaces in observations. `unobservable`
(an operand's pipeline not yet ingested for a comparable period) never blocks.

---

## 18. Domains — reading lenses, zero structure

`analysis/ontology/domains.json`:
```
domain := { id, label,
            concept_scope : [ product vocab values ],
            constructs    : [ construct URNs ],
            narrative_cadence : e.g. "6-monthly" }
```
A domain **carries no edges, loops, members, or state**. It exists so that Layer 3 narrative and
the UI can scope the one meta-model to an audience-sized view ("lending ecosystem",
"consumption & payments"). Validation checks only that refs resolve. Adding/removing a domain
changes nothing in the model — that is the test that domains stayed lenses. `lending` is the
first domain.

---

## 19. Layer 3 strategic narrative

The ~6-monthly authored artifact (FY-end + mid-year), **per domain**, written *on top of* the
computed projection — it is the interpretation of the meta-model's state, never the model itself.

- **Placement:** `analysis/cross_source/strategic/{domain}/{period}.md`, with a claims sidecar
  `{period}_claims.json` mapping every numbered claim in the narrative to its refs
  (`construct | eco_loop | constraint | cross_edge | signal_ids`) — the Check-2g discipline at
  Layer 3. A `validate_strategic_narrative.py` enforces it once the first narrative exists.
- **Authoring order (non-negotiable):** run compose first; write the narrative against
  `ecosystem_state_{period}.json`; every number traces to a signal, every causal statement to a
  named edge/loop/channel.
- **The narrative never introduces structure.** A pattern the narrative needs but the model
  lacks goes through S4 → sourcing → `ecosystem_model.json` *first*, then gets narrated.

---

## 20. Validation additions (`validate_composition.py` v1.1)

| Check | Rule |
|---|---|
| construct URNs | well-formed `icl:eco/{id}`, unique, permanent (never reissued) |
| construct members | every member URN resolves to a live entity; members span ≥2 pipelines |
| concept_anchor | all values in `concepts.json` vocabulary |
| eco-edge endpoints | resolve to construct/entity URNs; ≥1 endpoint is a construct |
| eco-edge sourcing | `claim_type != structural` ⇒ source fields present (v3.0 §13) |
| loop membership | all qualified refs resolve; ≥1 cross-pipeline element; no `corresponds_to` refs |
| constraint operands | every operand resolves to a registered signal in `registry.json` |
| **no-monolith, both directions** | no pipeline `system_model.json` references an `icl:eco/` URN or another pipeline's entities (v1.0 rule); AND `ecosystem_model.json` contains no edge whose endpoints are both entities of the *same* pipeline |
| domains | every `constructs` ref resolves; `concept_scope` values in vocabulary |

---

## 21. State computation additions (`compose_ecosystem.py` v1.1)

```
inputs  : (v1.0 inputs) + cross_source/ecosystem_model.json + ontology/domains.json
outputs : ecosystem_state_{period}.json gains —
  construct_states     : { urn: { direction, basis } }             (§14)
  eco_edge_states      : { id: { state, from, to, polarity } }     (§15)
  eco_loop_states      : { id: { state, live_edges, total_edges,
                                 input_periods, mixed_period } }   (§16)
  constraint_states    : { id: { state, residual, tolerance } }    (§17)
  ecosystem_observations : dominant_constructs, binding_constraints (negative eco/cross
                           edges firing), active_loops, reconciliation_violations
```

**Opportunity derivation extension (§12.3 unchanged in rule, wider in anchor):** a
`scope: cross_source` opportunity may now anchor to an **eco-loop or construct** as its driver
D, with the same firing→status rules and the same Check 4f `evidence_all` traceability (a
construct's evidence set = the union of its members' signal sets; a loop's = the union of its
member edges' endpoint signal sets).

---

## 22. Build order and seed content

Validators before content; compose behind validators; author last — every stage lands green.

1. **Schemas + validators** (§20) — empty `ecosystem_model.json` / `domains.json` validate PASS.
2. **Compose extension** (§21) — with empty inputs, output gains empty state blocks; gate green.
3. **Seed constructs (2–3, judgment work)** grounded in live data:
   `unsecured_retail_appetite` (SIBC personal-loan + credit-card stock × payments CC spend flow,
   card count), `consumption_payments_activity` (spend flows + acceptance infrastructure),
   `gold_collateral_lending` (SIBC gold stock; gains its flow member when an originations
   source lands — a deliberately partial construct proving `basis` coverage).
4. **First eco-loop:** cc spend → cc stock → unsecured_retail_appetite → spend — exercises the
   `x:` and `eco:` ref kinds (intra refs join with the first loop that routes through a
   pipeline-internal behavioral segment).
5. **First reconciliation constraint:** average-balance-per-card corridor over
   `x_cc_count_corresponds_cc_stock` operands — turns that structural edge into a live check.
6. **Insight path end-to-end (§23):** derivation → feed → narrative → `/opportunities` UI
   (ASCII-approved). The meta-model is not "done" until its insights are reviewable on the
   interface — this step is in scope of the initial build, not deferred.
7. **`domains.json`** with `lending`; Layer 3 narrative (§19) at the next FY-end/mid-year mark.
8. **The three-pipeline test:** when the next source (VAHAN) lands, its concept_tags must
   produce candidate construct members and cross-links with *zero edits* to Part II content —
   the M+N guarantee at N=3. If it doesn't, fix the derivation, never hand-patch.

**Retail product tie-in (`STRATEGY_PLANNER.md` §17; artifact spec in `PLAN_2026-08-11.md`'s parked
backlog, EN-1):** `ticker_map.json` targets may be
**construct URNs as well as entity URNs** — a construct is often the correct transmission anchor
(e.g. `icl:eco/unsecured_retail_appetite` → SBI Cards) and inherits its evidence set for the
call register's traceability.

---

## 23. The meta-model insight path (end-to-end, reviewable)

**Principle: eco insights ride the existing opportunity chain — never a parallel path.** The
chain `compose_ecosystem → opportunities feed → narrative → /opportunities UI` already exists
for cross-edge-driven items; the meta-model widens what can be a *driver*, changes nothing
about how insights flow. One generic mechanism, per the engineering principle.

### 23.1 Derivation (compose, deterministic)

The driver set for `scope: cross_source` opportunities/risks widens from `cross_edge` (v1.0) to:

| Driver kind | Fires when | Example insight |
|---|---|---|
| `cross_edge` | v1.0 §12.3 rules (unchanged) | flow softening ahead of stock |
| `construct` | direction ≠ 0 for ≥2 periods, or direction *flips* | "unsecured retail appetite turned negative" |
| `eco_loop` | state ∈ active_reinforcing \| active_balancing, or transitions | "the spend→stock loop is running" |
| `constraint` | state = violated | "card count and outstanding no longer reconcile" |

Status (`active | watch | closed`) follows §12.3 exactly. Every item carries
`refs {construct? | eco_loop? | constraint? | cross_edge?, entities: [urns]}`,
`evidence` (the firing subset) and `evidence_all` (per §21: union of member signal sets) —
so **Check 4f applies unchanged and strictly**.

### 23.2 Explainability contract (what makes an eco insight reviewable)

Every eco insight carries the **shared insight schema** `basis.{facts, inferences}`:

- `basis.facts` — the member signals' current values/directions, pulled from `signals.db`
  (traceable data points, as everywhere else).
- `basis.inferences` — the chain, **deterministic by construction**, one step per level of the
  computation: *member signals moved (named, with values) → member entity directions →
  construct/loop state → why that state constitutes an opening/risk (the authored mechanism
  prose from the eco-edge/channel)*. Each step cites its refs. Nothing in the chain is invented:
  steps 1–3 are the §14/§16 computation replayed as prose; step 4 is authored structure quoted.
- `representation: llm | deterministic` — same split as both pipelines: the deterministic chain
  is always generated first and is the fallback; `generate_opportunity_narrative` may rewrite
  the *prose* (plain-English body/implication/chain wording) with every number 4f-validated
  against `evidence_all`. The LLM narrates; it never reasons structure into existence.
  **Exceptions — never narrated:** constraint (data-check) cards and **eco-loop cards**. A
  loop's story *is* its segment-state mechanics, and a paraphrase can contradict the computed
  state (observed: "partial, one segment reversed" narrated as "fully engaged"). Deterministic
  prose is authoritative for both.

**Narrative preservation is state-scoped.** A narrative belongs to the computed state it was
written against, not to the card's `id`. On feed regeneration, prose is carried forward **only
if the deterministic `(title, status)` pair is unchanged** — that pair is the state's fingerprint:
cross-system titles encode direction (`softening ahead of stock` ↔ `leading stock — origination
headroom`), while pipeline titles are static model labels whose state signal is the status
(`active` ↔ `watch`). If either moved, the narrative is dropped: the card falls back to its
deterministic templated copy and is re-narrated on the next narrative run. A card may therefore
render plainer prose until then — **correct-but-plainer beats fluent-but-wrong**, and every item's
deterministic copy is written to be publishable, so a no-LLM budget degrades gracefully rather
than pinning last period's story under this period's title. (Observed 2026-07-08 on
`xopp_x_cc_spend_leads_cc_stock`: April's "spending slowing" body survived under June's
"origination headroom" title.) Enforced in `generate_opportunities_feed.preserve_narratives`,
pinned by `analysis/tests/test_feed_narrative_preservation.py`. Word-level direction checks on
the prose are deliberately **not** used — fuzzy substring heuristics are warning-grade only
(cf. the Check 2g status-substring warnings); the deterministic key comparison replaces them.

### 23.3 Feed projection (`generate_opportunities_feed`)

`refs → charts[]` using the existing `ChartRef` shape (`{pipeline, section, highlight, caption}`):
a construct-driven item emits one chart per member entity that has a registered `chart_series`,
**prioritised** `measures` before `proxies`, capped at 3 charts; a loop-driven item emits the
charts of its segment endpoints. Cross-pipeline items already render multi-chart — no new UI
data shape.

### 23.4 UI surfacing (`/opportunities`, cross-system section)

Eco-driven cards render in the existing cross-system section with:
- badge = the driver kind (`Ecosystem · construct` / `Ecosystem · loop` / `Data check`) instead
  of the pairwise `Credit ✕ Payments` badge;
- the multi-chart panel (23.3) with per-chart highlights, as today;
- a collapsible **"Why — computed basis"** block rendering `basis.inferences` steps with their
  cited signals/values (`basis.facts`) — this is the review surface: the operator can follow
  member signal → construct state → insight without leaving the card.
- UI implementation follows the ASCII-first authoring rule (layout approved before code).

### 23.5 Review loop (operator → model, gated)

Review happens on the interface; corrections happen in **authored structure**, never in computed
state: wrong membership/weight → edit `ecosystem_model.json` (constructs/eco_edges) and re-run
compose; missing mechanism → S4 proposal → sourcing → promote; wrong number → it's a data/gate
bug, fix the pipeline. `narrative: true` items keep their prose across regen (existing
preservation behavior).

---

*Composition Specification v1.1 — extends System Model Specification v3.0 — India Credit Lens*
