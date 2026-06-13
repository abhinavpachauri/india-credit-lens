# Handoff — Full Pipeline & Architecture Review
> For a new session whose job is to **review the entire pipeline and every design decision afresh**,
> to confirm (or correct) that the system is **scalable** (pipeline-by-pipeline) and **deterministic**
> (reproducible, with non-determinism quarantined). Authored 2026-06-13. Everything below is on `main`.

This is a **review brief, not a build brief.** Each section names what exists, *why* it was built that
way, and *what to scrutinise*. Challenge the decisions — they were made under time pressure in one long
session and have not had an independent review.

---

## 0. How to orient fast (read these first, in order)
1. `analysis/SYSTEM_MODEL_SPEC.md` (v3.0) — per-pipeline model: 3 strata, structure-first, D1/D2/D3.
2. `analysis/COMPOSITION_SPEC.md` (v1.0) — the **5-strata** model, federation/hub/projection, §12 UI contract.
3. `PIPELINE_ARCHITECTURE.md` — stage sequence + the 5-strata table.
4. `CLAUDE.md` "Current Platform State" + "CLI Tools" — what's live + how to run.
5. This file — decisions + determinism/scalability map + risks.

Run the gates to see it work: `python3 analysis/run_evals.py --period merged --merged` (SIBC, incl. build)
and `python3 analysis/run_atm_pos_evals.py --period 2026-04-30 --skip-build` (payments). `source .env.local`
first for any LLM step (narrative / S4).

---

## 1. The architecture in one screen

```
Layer 1   per-entity signals      registry.json + signals.db + compute/      DETERMINISTIC (no LLM)
          per-period evaluate     evaluate.py (claude)                       LLM (narrative only)
─────────────────────────────────────────────────────────────────────────────────────────────
Layer 2a  S1 structural skeleton  generate_skeleton.py → system_model.json   DETERMINISTIC (CSV+profile)
          S2a causal structure    ontology/channels.json  (SHARED HUB)       AUTHORED, data-less, stable
          S2b force instances     force_instances[] in system_model.json     AUTHORED, dated + sourced
─────────────────────────────────────────────────────────────────────────────────────────────
Layer 2b  composition (federated) ontology/concepts.json + derive_cross_links COMPUTED candidates
          confirmed cross-edges   cross_source/composition.json               AUTHORED (confirm)
─────────────────────────────────────────────────────────────────────────────────────────────
S3        dynamic state           generate_system_state.py (from signals.db) COMPUTED each period
          live opportunities      derive_opportunities.py                     COMPUTED
          ecosystem projection    compose_ecosystem.py                        COMPUTED (never stored as truth)
─────────────────────────────────────────────────────────────────────────────────────────────
Present.  UI feed                 generate_opportunities_feed.py              DETERMINISTIC assemble
          plain-English narrative generate_opportunity_narrative.py (claude/API) LLM (read-only, cached)
          /opportunities (gated)  web/app/opportunities/page.tsx
─────────────────────────────────────────────────────────────────────────────────────────────
S4        inference loop          run_inference.py (Anthropic API + web_search) LLM, SOURCING-GATED
                                  → analysis/s4_proposals/{period}.json         never auto-promoted
─────────────────────────────────────────────────────────────────────────────────────────────
Layer 3   ecosystem strategy      NOT BUILT — next session
```

Both pipelines (`sibc`, `atm_pos`) run S1→S2→S3→opportunities→ecosystem→feed inside their gate.
S4 and narrative are **manual/post-gate** steps (LLM, not in the deterministic gate).

---

## 2. Component map (what each file is, and its nature)

| File | Role | Nature |
|------|------|--------|
| `analysis/signals/registry.json` | L1 signal catalog (206 signals) | authored catalog |
| `analysis/signals/signals.db` | sole signal store (SQLite) | computed; **binary, tracked (churns — review)** |
| `analysis/signals/compute/` + `generate_signal_history.py` | L1 compute + `append`/`evaluate`/`seed`/`status` | deterministic compute; status roll-up sync |
| `analysis/{pipeline}/skeleton_profile.json` | column→role / composition map, reclass map, **concept_tags**, exhaustive flags | the only authored structural input |
| `analysis/generate_skeleton.py` | emit skeleton + URN + concept_tags + signal_ids + registry_domain; **merge preserves behavioral + force_instances** | deterministic |
| `analysis/{pipeline}/merged/system_model.json` | S1 entities + structural edges + behavioral edges + `force_instances[]` + loops (schema 4.0) | mixed |
| `analysis/validate_system_model.py` | structural + D1/D2/D3 + behavioral + force sourcing + URN/concept checks | gate |
| `analysis/ontology/concepts.json` | 5-dim vocab (product/measure/segment/lender/geography) + driver_concepts | shared hub |
| `analysis/ontology/channels.json` | **S2a** data-less channels over concepts (17) | shared hub, authored |
| `analysis/derive_cross_links.py` | R1 stock↔flow · R2 shared-channel · R3 corresponds → `candidates.json` | deterministic |
| `analysis/cross_source/composition.json` | confirmed cross-edges (2) | authored |
| `analysis/validate_composition.py` | cross-edge integrity + **no-monolith** rule | gate-adjacent |
| `analysis/generate_system_state.py` | leaf dirs from DB → share-weighted propagation → force/edge/loop states + **mismatch detector** | computed |
| `analysis/derive_opportunities.py` | opportunity/risk status from driver firing over 2 periods | computed |
| `analysis/compose_ecosystem.py` | cross-system projection → `ecosystem_state_{period}.json` | computed |
| `analysis/generate_opportunities_feed.py` | UI bundle; **preserves narrative across regen** | deterministic assemble |
| `analysis/generate_opportunity_narrative.py` | plain-English copy (no jargon), cached | LLM, read-only |
| `analysis/run_inference.py` | **S4** detect→propose→web-verify→sourcing-gated proposals | LLM (API) |
| `analysis/run_evals.py` / `run_atm_pos_evals.py` | the gates | orchestration |
| `analysis/build_behavioral_layer.py`, `migrate_forces_to_instances.py` | **one-time** build helpers (drafts deleted) | historical |

---

## 3. Key decisions to challenge (the heart of the review)

1. **Structure-first.** Skeleton is emitted deterministically from the consolidated CSV + profile; behavior is layered on top and constrained by it. *Scrutinise:* is the CSV the right source of truth vs the raw RBI files?
2. **Identity = `(partition, code)` + global URN `icl:{pipeline}/{partition}/{code}`.** Case-preserving (SIBC reuses `I/i`). *Scrutinise:* URN stability across RBI format changes.
3. **Only two structural edge types** (`composes_into`, `reclassifies`); alternate decomposition is a **tag**, not an edge. *Scrutinise:* does this hold for future sources (TReDS/originations)?
4. **Additivity is tolerance-checked, never hard-fails.** Known residuals (SIBC Non-food +4.9%, NBFC +65%) are profile-flagged `exhaustive:false` → reported as notes. *Scrutinise:* is "note not error" the right call?
5. **S2a / S2b split (the big one).** Durable mechanism = **channel** over *concepts*, in the shared hub; the dated, sourced event = **force_instance** in the pipeline. *Scrutinise:* is the channel/instance boundary clean? Are channels truly pipeline-agnostic?
6. **Federate, don't merge.** Per-pipeline models are source-of-truth; the combined view is a **computed projection**, never authored. Cross-system links are **M+N** (each pipeline maps to the hub once), not M×N pairwise. *Scrutinise:* this is the core scalability claim — verify it holds when a 3rd/4th pipeline is added.
7. **Concept hub = 5 dimensions.** `measure` (stock/flow/count) carries the cross-system law **"flow leads stock."** *Scrutinise:* dimension completeness; vocab governance (append-only).
8. **D1/D2/D3 discipline** — structure constrains causality (no behavioral edge duplicating a part-whole link; no `leads` across a chain; cross-decomposition edges flagged). Validator-enforced.
9. **S3 propagation** = leaf direction from signal *status* (sign), rolled up **share-weighted by CSV value**. *Scrutinise (real risk):* sign-of-status loses magnitude; unit-weight fallback where value missing; tie-breaks.
10. **Opportunity status is derived, not authored** — driver firing over 2 periods → active/watch/closed; `retired` is respected (never data-resurrected). *Scrutinise:* the 2-period rule + most-common roll-up.
11. **Narrative is expository, read-only** — verbalises S2+S3, never changes the model; plain English (jargon banned); cached; **preserved across feed regen**; **not in the gate.** *Scrutinise:* drift if not re-run; preservation-by-id can carry stale copy.
12. **S4 proposes, sourcing gates, never auto-promotes.** Web-verification built in (Anthropic API + `web_search`, *not* the rate-gated `claude -p`). Proposals are hypotheses in `s4_proposals/`. *Scrutinise:* hallucinated-source risk (mitigated by web-verify); promotion is manual.
13. **Legacy retired** from the gate: `validate.py` checks 4/5, `validate_claims.py` (2c), `generate_mermaid.py`, subsystems, `source_claims.py`. Scripts remain on disk, detached. *Scrutinise:* anything still depending on them?
14. **Annotation IDs are permanent**; SIBC promotes via `promote_annotations.py`. `credit-cycle-expansion` was reclassified L3→L1 (it's a computable bank-credit fact).

---

## 4. Determinism & scalability — claims vs seams

**Deterministic (reproducible byte-for-byte given inputs):** S1 skeleton, concept_tags, L1 compute,
cross-link *candidate* derivation, S3 state, opportunity status, ecosystem projection, feed assembly.
The gate regenerates these and they match committed output (verified — clean tree after a gate run).

**Authored but stable (change only when new data/mechanism appears):** channels (S2a), concept vocab,
reclass target map, SIBC `parent_overrides` (II/III→I), force_instances (S2b, sourced).

**Non-deterministic, deliberately quarantined:** L1 evaluate narrative, opportunity narrative, **S4
proposals**. None of these can write the source-of-truth without a gate: S4 requires a verified external
source before promotion; narrative is read-only.

**Scalability path (adding a pipeline):** author `skeleton_profile.json` (+ concept_tags) → run
`generate_skeleton.py` → layer behavioral (reuse hub channels, add instances) → `derive_cross_links.py`
auto-produces its cross-candidates against existing pipelines → **no existing pipeline is edited.**
*This is the property to stress-test in review* (e.g. dry-run a TReDS or originations profile).

---

## 5. Known gaps / risks to scrutinise (be skeptical here)
- **S3 direction = sign of signal status** (strengthening/active→+1, weakening/declining→−1). Loses magnitude; `active`↔`strengthening` both +1. Propagation is share-weighted by CSV value but falls back to unit weights where no value. **Review whether this is faithful enough.**
- **Multi-entity status roll-up = most-common (mode).** A simplification for scan/bank-scan/category-share `current_status`.
- **No automated test suite** beyond the gate validators. No unit tests on the Python.
- **Ongoing behavioral UPDATE is hand-editing `system_model.json`** (preserved across regen). The only tooling is the one-time `build_behavioral_layer.py` (drafts deleted). No additive-UPDATE helper.
- **Narrative not in the gate** → after a gate run the feed has narrated copy only because of preserve-by-id; if an opportunity's wording changes, narrative must be re-run. LLM cost/reliability now on the API.
- **Cross-system confirmation is manual** — 43 candidates derived, only 2 confirmed in `composition.json`. R2 "shared-channel" candidates are noisy.
- **`signals.db` is binary + tracked** — every compute churns it in git. Consider rebuild-from-source vs commit.
- **Payments charts use MoM** (no YoY/FY) via a `variant:"atm_pos"` slice — a shim, not a first-class fix.
- **D3 double-count flag is checked, not auto-applied.**
- **`/opportunities` is Clerk-gated** — can't be screenshotted without a login (verification used build + data checks).
- **S4 SIBC batch occasionally returns malformed JSON** (one-retry guard added; not bulletproof).

---

## 6. Current data state (latest)
- SIBC: 7 periods, latest `2026-05-29`; 84 L1 signals; 85-entity model; 8 force_instances; 7 active opportunities + 2 risks.
- ATM/POS: 16 periods, latest `2026-04-30`; 84 L1 signals; 35-entity model; **7 force_instances** (4 original + 3 promoted from S4); 3 opportunities + 3 risks.
- Cross-system: 2 confirmed edges; 1 live ecosystem signal ("card spend flow softening ahead of stock").
- S4: `s4_proposals/2026-05-29.json` — 27 proposals, 3 promoted to model (RuPay/cash-at-POS/contactless), rest hypotheses.
- 0 L1 `unknown` statuses; all gates green; `origin/main` current at `bf2bcf9`.

---

## 7. Layer 3 (the only unbuilt layer — for after review)
The ecosystem **strategic** model (lending-workflow implications), authored ~6-monthly. It *consumes*
the L2a/L2b causal graphs (channels, instances, cross-edges, loops) — all of which are now live. It does
not define mechanism; it applies it to strategy. Design it **after** this architectural review settles the
foundations below it.

---

## 8. Suggested review agenda
1. Re-derive the skeletons from scratch and diff vs committed (determinism check).
2. Stress-test scalability: sketch a TReDS profile + concept_tags; confirm zero edits to SIBC/payments.
3. Interrogate the S2a/S2b split and the concept hub dimensions for the next 2–3 real pipelines.
4. Decide if S3's sign-based direction + value-weighted propagation is faithful, or needs magnitudes.
5. Decide the place of LLM steps (narrative, S4) — keep out of the gate? add determinism guards?
6. Decide `signals.db` git policy + add a real test suite.
7. Then green-light Layer 3.

*— End of handoff. State is on `main` @ `bf2bcf9`; specs are the contracts; challenge freely.*
