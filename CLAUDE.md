# India Credit Lens — Root Context

> Single source of truth for session startup. Keep short — detail lives in linked files.
> Strategy & revenue: `STRATEGY_PLANNER.md` | Pipeline detail: `PIPELINE_ARCHITECTURE.md`

---

## What This Is

India Credit Lens (`indiacreditlens.com`) turns Indian regulatory credit reports into
structured, executive-level insights for NBFCs, banks, fintechs, PE/VC funds.

**Differentiator:** Causal model layer — explains *why* credit moved, not just that it moved.
**Model:** Content ladder from free (LinkedIn/Substack) → paid (SaaS + consulting).

---

## Decision Filter

Before any feature, report, content, or technical decision:

1. Does it build expert positioning in the Indian lending ecosystem?
2. Does it attract CPOs, CROs, credit analysts, PE/VC at NBFCs/banks/fintechs?
3. Does it move toward a monetisable asset (consulting, CPO role, or SaaS subscriber)?

No to all three → deprioritise.

---

## Engineering Principle (non-negotiable) — Design for the long term

This platform is **multi-pipeline by design** (SIBC, ATM/POS, future sources) and that count only
grows. Every technical decision must scale to **multiple ingestion types and multiple pipelines** —
never optimise for the single case in front of you.

- **One generic mechanism per pipeline, not per-pipeline one-offs.** Both pipelines run the *same*
  scripts/validators/gates; alignment is by construction, not parallel hand-maintenance.
- **Compute once, ship compact.** Precompute artifacts at ingestion/build time; never make the
  browser parse raw consolidated data or re-derive series client-side.
- **Single source of truth.** No parallel copies that "agree today but could drift" — guard with a
  deterministic freshness/traceability check.
- Given "quick win vs proper fix", **default to the proper fix**; state it as the recommendation.
- Test every design against: *does this still hold at N pipelines / N ingestion types?*

---

## Current Platform State (June 2026)

Live components only. Planned work lives in `STRATEGY_PLANNER.md`.

| Component | Status |
|---|---|
| RBI SIBC dashboard | **Live** — 7 sections, 49 annotations (merged Jan 2024–Mar 2026) |
| SEO layer | **Live** — metadata, OG image, sitemap, JSON-LD |
| Email / Substack CTA | **Live** — `SubstackCTA.tsx` + `EmailGate.tsx` |
| Reply desk (X distribution) | **Live (2026-07-05)** — `analysis/replydesk/` — assisted (never automated) daily reply ritual: Claude-in-Chrome reads the user's logged-in X tabs, `reply_desk.py brief` supplies grounded ammunition, `check` hard-gates drafts (traceability + SEBI lint), **human clicks Post**, `log` records for engagement learning. Ritual spec: `analysis/replydesk/CLAUDE.md` — read it before running "Reply desk". |
| Newsletter v2 (2-post cadence) | **Live (2026-07-04)** — deterministic rendering over gate-validated artifacts: `generate_release_read.py` (L1, within 24h of release) + `generate_deep_read.py` (L2/L3 + ecosystem, mid-cycle). Self-gating traceability (`validate_newsletter.check_doc`: verbatim cards + declared-scope numbers, negative-tested). Output = .md + Substack-paste .html. v1 (config/mermaid/LinkedIn) retired to `legacy/newsletter_v1/` — LinkedIn posts are now written by the user in their own voice. |
| validate_content.py (Check 2b) | **Live** — content accuracy eval on annotation bodies |
| validate_claims.py (Check 2c) | **Retired** — superseded by `core/validate_system_model.py` (sourcing built in); archived in `analysis/legacy/` |
| validate_annotation_basis.py (Check 2d) | **Live** — basis completeness check (inference/hypothesis → basis.inferences non-empty) |
| promote_annotations.py (Stage 7) | **Live** — automated verified copy to web |
| signal_registry.json | **Live** — 7 signals tracked across 3 issues (newsletter subsystem) |
| signal compute layer | **Live** — `analysis/signals/` — registry.json (**225 signals**), signals.db (SQLite — sole store); compute engine in signals/compute/; Check 2e validates DB + registry, Check 2f/5b2 verifies DB == fresh recompute from CSV |
| **Relational signals (rotation + divergence)** | **Live (2026-07-20)** — 12 L1 signals (spec: `analysis/signals/README.md`): `csv_sector_rotation`/`csv_category_rotation` (Δshare over a 12-calendar-month window, share-scan reuse, per-entity rows + aggregate rotation-mass row) and `csv_sector_divergence`/`csv_bank_divergence` (one hierarchy operator, both trees — child vs parent YoY / bank vs bank_category YoY; flagged rows only). Backfilled all periods; covered by Check 2e/2f. `core/relational_insights.py :: rotation_insight` renders deterministic publishable prose (theme = majority `economic_role` of material movers from the system model's concept_tags; honest fallbacks). **Dashboard/report wiring pending operator review** — Stage 5.5 excludes relational signals until then; `csv_pair_divergence` (metric axis) still spec-only. |
| signal evaluate layer | **Live** — `analysis/signals/evaluate.py` — Stage 5 LLM evaluation via `claude -p` CLI (Pro subscription, no API cost); **prompt v1.11** (executive tone, full period series + full scan distribution in payload, per-signal **chain** output, traceability + no-invented-seasonality rules); prior-period narratives auto-injected for diff; evaluations written to `signals/evaluations/{pipeline}/{period}.json` |
| **Insight schema + traceability** | **Live** — ONE shared insight schema across both pipelines: `basis.{facts, inferences}` (facts = traceable data points, inferences = the chain the card renders). SIBC **scalar** insights = LLM chain (prompt v1.11); SIBC **scan/distribution** insights = deterministic (`generate_analysis_report.deterministic_scan_insight`, grounded by construction). **ATM/POS now mirrors SIBC**: Stage 4b does deterministic selection + UI routing + `basis.facts`, then **overrides the prose of anchored scalar insights with the LLM eval narrative** (`EVAL_ANCHOR` map → registered signal_id; consumes `evaluations/atm_pos/{period}.json`, prompt v1.11; scan/share/concentration/composed/gap stay deterministic). Each insight carries `representation: llm|deterministic`. **Check 2g** (`validate_sibc_traceability.py`) + ATM/POS Stage 4c (`validate_atm_pos_insights.py`) hard-fail any number in body/chain/implication that doesn't trace to the computed signals — ATM/POS LLM insights validate vs the **period-wide signals.db** ground truth (like 2g), deterministic ones vs signals.json, plus a strict signals.json==signals.db **YoY drift guard**. SIBC `_signal_type=='scan'` branch overrides LLM text with deterministic. (3 fuzzy status-substring warnings remain non-blocking — see Open Notes.) |
| L1 annotation classification | **Done** — all 49 SIBC annotations classified: 26 L1 / 18 L2 / 5 L3; all 21 ATM/POS insights classified: 16 L1 / 3 L2 / 2 gaps |
| Subsystem generation | **Live** — `generate_mermaid.py` → `.mmd` + `validate.py --check-subsystems` |
| detect_format.py (Stage 0) | **Live** — flags format changes in new XLSX before extraction |
| ATM/POS pipeline | **Live** — `rbi_atm_pos/` — Stages 0–3 + L1 compute (84 signals) + evaluate. **28 periods Jan 2024 → Apr 2026** (2024 backfilled 2026-06-20 → YoY now computes for all 16 of 2025+2026, was 4). Detector handles older formats (abbreviated months, date-less sheets → filename, content-based sheet detection); canonical roster time-aware (Fincare merged Apr 2024, Dhanalaxmi rename Nov 2024). **Dashboard insights** come from a *separate deterministic path*: Stage 4a `compute_atm_pos_signals.py` → `rbi_atm_pos/signals.json` → Stage 4b `generate_atm_pos_insights.py` → `atm_pos_insights.json` (17 insights, Apr 2026). Both stages run inside `core/gate.py --pipeline atm_pos`. 4b is the single authoritative payments insight generator — the old "Stage 5.5" `generate_atm_pos_analysis_report.py` (a no-op) was retired to `analysis/legacy/` in the §4 cutover. |
| AppShell + DLS | **Live** — shared Header (one instance), `dls/InsightCard`, `dls/InsightCTAStrip` used by both SIBC and Payments |
| **Layer 2a system models (v4.0)** | **Live** — `system_model.json` for both pipelines (SIBC 85 entities, ATM/POS 35). Deterministic structural skeleton (`generate_skeleton.py`) + behavioral-causal split into shared **channels** (S2a) + dated **force_instances** (S2b). Specs: `analysis/SYSTEM_MODEL_SPEC.md` v3.0 + `analysis/COMPOSITION_SPEC.md` **v1.1** (Part II = ecosystem meta-model: constructs/eco-edges/cross-loops/reconciliation constraints/domains — spec'd 2026-07-03, not yet implemented). Validated by `validate_system_model.py` in both gates. |
| **Composition hub (Layer 2b)** | **Live** — `analysis/ontology/{concepts,channels}.json` shared across pipelines; entities carry global URNs + `concept_tags`. `derive_cross_links.py` derives cross-system candidates (stock↔flow + shared-channel); `cross_source/composition.json` holds confirmed cross-edges; `validate_composition.py` enforces the no-monolith rule. |
| **Ecosystem meta-model (Part II, v1.1)** | **Live (2026-07-03)** — `cross_source/ecosystem_model.json` (2 constructs, 2 eco-edges, 1 cross-pipeline loop, 1 reconciliation constraint) + `ontology/domains.json` (`lending` lens). Compose computes construct/eco-edge/loop/constraint states each run; eco-driven `scope:cross_source` opportunities carry a deterministic **`basis` block** (member signals → directions → state, values from signals.db) rendered as "Why — computed basis" on `/opportunities`; LLM narrates prose only (4f-checked vs `evidence_all`). Constraint `cx_cc_balance_per_card` reconciles SIBC CC outstanding vs payments card count (₹24.9k/card, corridor 8k–60k, severity **fail** — negative-tested). `validate_composition` §20 checks wired into **both** gates; 15 unit tests in `tests/test_ecosystem_compose.py`. |
| **S3 dynamic state + opportunities** | **Live** — `generate_system_state.py` (forces/edges/loops fire from `signals.db`), `derive_opportunities.py` (status active/watch/closed/retired from driver firing), `compose_ecosystem.py` (cross-system premium feed). Both gates run these each ingestion. |
| **Opportunities UI** | **Live** — gated `/opportunities` reads `web/public/data/opportunities_feed.json` (`generate_opportunities_feed.py`); `generate_opportunity_narrative.py` adds plain-English, numbers-grounded copy (post-gate step). |
| ~~validate.py checks 4/5 · validate_claims (2c) · generate_mermaid · source_claims · subsystems~~ | **Retired** — superseded by the v4.0 system model + `validate_system_model.py`. Scripts remain on disk, detached from the gate. |

---

## CLI Tools

Use CLI tools for all external service interactions — they are the most context-efficient approach (one line of output vs loading API JSON).

### External services

| Tool | Use for |
|---|---|
| `gh` | PRs, CI status, issues, release notes — never use GitHub web for anything scriptable |
| `vercel` | Domain management, deployment status, env vars |

### Pipeline gates (always use these — never run validators ad-hoc)

| Tool | Use for |
|---|---|
| `python3 analysis/core/gate.py --pipeline sibc` | SIBC gate — Stages 0–6 (data integrity + signal + model validation) |
| `python3 analysis/core/gate.py --pipeline atm_pos --xlsx {file}` | ATM/POS gate — Stages 0–3 + L1 signal append + build |
| `python3 analysis/pipelines/sibc/promote_annotations.py` | Stage 7: verified copy annotations_merged.ts → rbi_sibc.ts — never `cp` or manual paste |
| `python3 analysis/pipelines/sibc/detect_format.py` | Stage 0: flag format changes before extraction (SIBC) |
| ~~`python3 analysis/legacy/source_claims.py`~~ | **Legacy** — v2 claim sourcing; superseded by `validate_system_model.py` (sourcing built in). Detached from gate. |
| `python3 analysis/generate_skeleton.py --pipeline {sibc\|atm_pos}` | Stage 4-struct: regenerate the deterministic skeleton (preserves behavioral layer + force_instances). Runs inside both gates. |
| `python3 analysis/validate_system_model.py --pipeline {name}` | v4.0 model gate — structural + D1/D2/D3 discipline + force sourcing + URN/concept_tags. Replaces legacy checks 4/5/2c. |
| `python3 analysis/generate_system_state.py --pipeline {name} --period {date}` | S3: compute dynamic state from `signals.db` → `system_state_{period}.json`. |
| `python3 analysis/derive_opportunities.py --pipeline {name} --period {date}` | Derive live opportunity/risk status from S3 driver firing. |
| `python3 analysis/derive_cross_links.py` · `compose_ecosystem.py` · `validate_composition.py` | Cross-system pass (Layer 2b): derive candidates → project ecosystem state → validate cross-edges. |
| `python3 analysis/generate_opportunities_feed.py` then `generate_opportunity_narrative.py` | Presentation: build `opportunities_feed.json`, then add plain-English narrative (post-gate, cached). |
| `python3 analysis/core/generate_signal_history.py append --pipeline {name} --period {date}` | Stage 4: Layer 1 signal compute → writes to signals.db + updates registry |
| `python3 analysis/core/generate_signal_history.py evaluate --pipeline {name} --period {date}` | Stage 5: LLM signal evaluate → evaluations JSON; auto-loads prior period for narrative diff |
| `python3 analysis/core/generate_signal_history.py status` | Print current signal states across all pipelines |
| `python3 analysis/validate_signal_history.py` | Check 2e: signal history integrity — DB rows, registry schema, status sync vs DB |
| `python3 analysis/check_signal_freshness.py [--pipeline {name}]` | Check 2f/5b2: signals.db freshness — recompute every period from the CSV and fail on any drift (value/status/missing/orphan). Deterministic guard; runs in both gates + pre-commit. Fix = re-append **every** period, not just the latest. |
| `python3 analysis/newsletter/generate_release_read.py [--pipeline atm_pos]` | Newsletter Post 1 (L1 release read) — self-gating; run after the ingestion gate is green |
| `python3 analysis/newsletter/generate_deep_read.py` | Newsletter Post 2 (L2/L3 deep read) — self-gating; publish mid-cycle |
| `python3 analysis/replydesk/reply_desk.py {brief\|check\|log}` | Reply desk: ammunition → draft gate (traceability + SEBI) → posted-reply log. Ritual: `analysis/replydesk/CLAUDE.md` |

---

## Authoring Rules (non-negotiable)

### Visual outputs
1. **ASCII layout first** — proportions, zones, text hierarchy
2. **Explicit approval** — no code until layout confirmed
3. **Then implement** — translate approved ASCII directly

### SIBC date normalisation (non-negotiable — read before any consolidation)

RBI publishes Statement 1 (Bank Credit / Food Credit / Non-food Credit) as a fortnightly
release — always a Friday, which can fall in the first week of the **following** month.
That publication date must be remapped to the **prior** month-end. Two rules are hard-coded
in `update_web_data.py`; specific edge cases live in `{period}/date_overrides.json`.

| Published on | Maps to | Why |
|---|---|---|
| Apr 1–7 | Mar 31 | Post-FY-end Bank Credit release — Apr 4–5 = March data |
| May 1–7 | Apr 30 | Post-April Bank Credit release — May 2–3 = April data |
| Mar 1–7 | Feb 28/29 | Early-March Bank Credit = February data — captured in `date_overrides.json` for the period |
| Any other date | Last day of same month | Mid-month sector snapshot → month-end |

**Before `update_web_data.py` writes the CSV:** always show the full remapping table
(overrides applied + normalization applied) and wait for explicit user confirmation.
This is the same A/B gate as `detect_format.py` — never skip it.

When a new XLSX introduces dates not covered by the rules above, ask the user to classify
each raw date before proceeding. Document the decision in `{period}/date_overrides.json`
if it is a semantic correction (early-month = prior-month data); the normalization rule
handles formatting-only cases automatically.

### Analysis outputs
- `annotation_ids` in `system_model.json` must **exactly match** `id` fields in the annotations file. Copy-paste — never retype.
- **Annotation IDs are permanent.** Once an `id` exists in `annotations_merged.ts`, it is never renamed or deleted — even across FOUNDATION rebuilds. UPDATE mode only adds. FOUNDATION mode may restructure, but any removed ID requires explicit justification after `promote_annotations.py --dry-run`.
- **Layer 2a model has two modes — read `PIPELINE_ARCHITECTURE.md` before every model update pass.** FY-end (March file) = FOUNDATION. All other months = UPDATE. Wrong mode = wrong depth of analysis. Signal evaluation (Stage 5) runs every period regardless of mode.
- Stage 7 always uses `promote_annotations.py` — never manual copy.

### Git / deployment
- **Solo project — work directly on `main`. Never create feature branches or worktrees.**
- Never auto-push to GitHub
- Always run `python3 analysis/core/gate.py --pipeline sibc` (includes `npm run build`) before `git push`
- Show results and wait for explicit confirmation

---

## Key Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | This file |
| `STRATEGY_PLANNER.md` | Content ladder, revenue model, product roadmap |
| `PIPELINE_ARCHITECTURE.md` | **Pipeline stages, system model cadence, adding-period checklist** |
| `analysis/report_analysis_prompt.md` | Master prompt + analytical framework for all report analyses |
| `analysis/core/gate.py` | Master eval gate — Stages 3 and 6 |
| `analysis/core/validate_timeline.py` | Check 0: timeline.json schema + path existence |
| `analysis/pipelines/sibc/validate_sections.py` | Check 1: sections.json data integrity |
| `analysis/pipelines/sibc/validate_annotations.py` | Check 3: live rbi_sibc.ts structure (Checks A–H) |
| `analysis/pipelines/sibc/validate_content.py` | Check 2b: dates/values/growth in annotation bodies vs sections.json |
| `analysis/legacy/validate_claims.py` | Check 2c (**retired** — archived): claim sourcing — superseded by `core/validate_system_model.py` |
| `analysis/pipelines/sibc/validate_annotation_basis.py` | Check 2d: basis completeness — inference/hypothesis annotations must have basis.inferences |
| `analysis/validate_signal_history.py` | Check 2e: signal history integrity — DB rows, registry schema, status sync vs DB |
| `analysis/check_signal_freshness.py` | Check 2f/5b2: deterministic signals.db freshness — recompute all periods from CSV, fail on drift. Closes the staleness gap `check_derived_fresh.py` leaves (it excludes the binary DB). |
| `analysis/pipelines/sibc/validate_sibc_traceability.py` | Check 2g: every number in a SIBC insight's body/chain/implication must trace to a value in signals.db (scalar = hard fail; scan = deterministic so grounded by construction). Status-substring contradictions = non-blocking warnings. Ground truth = `query.signal_numbers`/`flat_numbers` (period-wide, unit-aware). |
| `analysis/pipelines/atm_pos/validate_atm_pos_insights.py` | Stage 4c: ATM/POS traceability — numbers in body/**chain**/implication must trace to `signals.json`. Mirror of Check 2g for the deterministic payments path. |
| `analysis/core/validate_opportunity_traceability.py` | Check 4f: opportunity (Layer 2) number traceability — every number in an opportunity body/chain/implication must trace to the driver's **full declared evidence set (`evidence_all`)** (period-wide is vacuous at cross-pipeline scale). **STRICT in both gates** (the L2 analog of Check 2g; `derive_opportunities` emits `evidence_all` = driver's full signal set so structural risks ground even when not firing). |
| `analysis/pipelines/sibc/generate_analysis_report.py` | Stage 5.5: eval JSON → `sibc_l1_annotations.json`. Scalar insights carry the LLM chain → `basis.inferences`; **scan insights generated deterministically** (`deterministic_scan_insight`). Attaches `basis.facts` from `signal_numbers`. |
| `analysis/legacy/validate.py` | Checks 4, 5: system_model.json + subsystems.json |
| `analysis/pipelines/sibc/extract_sibc.py` | Stage 1: SIBC xlsx → sections.json + format_report.json |
| `analysis/pipelines/sibc/detect_format.py` | Stage 0: detect structural changes in new XLSX vs prior period (SIBC) |
| `analysis/pipelines/sibc/update_web_data.py` | Stage 3: all xlsx → rbi_sibc_consolidated.csv |
| `analysis/pipelines/sibc/generate_merge.py` | Stage 3: sections.json[] → sections_merged.json (auto-validates) |
| `analysis/legacy/generate_mermaid.py` | On-demand: system_model → .mmd files (always after FOUNDATION; after UPDATE only if nodes/edges changed) |
| `analysis/legacy/source_claims.py` | Post-model-update: source all claims in system_model.json |
| `analysis/pipelines/sibc/promote_annotations.py` | Stage 7: annotations_merged.ts → rbi_sibc.ts (verified copy + ID diff) |
| `analysis/core/generate_signal_history.py` | Stage 4 (`append`) + Stage 5 (`evaluate`) + `status` + `seed` commands |
| `analysis/signals/registry.json` | Universal signal catalog — 90 signals, layer 1/2/3 tagged; all Layer 1 signals have compute specs (SIBC + ATM/POS) |
| `analysis/signals/signals.db` | **Primary signal store** — SQLite; (pipeline, period, metric_id, entity_type, entity_id) fact table + metric_ranges |
| `analysis/signals/compute/` | Compute engine: engine.py dispatches; sibc.py + atm_pos.py implement all 1a/1b/1c/1d methods. Both read from consolidated CSVs. SIBC maps `dataDate → csv_date` via `timeline.json` before querying. |
| `analysis/signals/evaluate.py` | Stage 5 LLM evaluation engine — reads signals.db, builds domain payloads (full period series included), calls `claude -p` CLI, writes to evaluations/. prompt_version=1.4. Cache in llm_cache table. |
| `analysis/signals/query.py` | Builds signal payloads for evaluate — scalar + scan + full chronological series per signal |
| `analysis/signals/prompts/domain_eval_system.txt` | System prompt v1.4 — executive tone, trajectory style, no jargon |
| `analysis/signals/evaluations/sibc/2026-05-29.json` | Latest SIBC evaluation — 5 domains, prompt v1.5 |
| `analysis/signals/evaluations/atm_pos/2026-04-30.json` | Latest ATM/POS evaluation — 4 domains, prompt v1.5 |
| `analysis/signals/db.py` | DB init, schema, refresh_ranges() |
| `analysis/cross_source/catalog.json` | Tuple registry — all declared cross-source pairs (Layer 2b) |
| `analysis/cross_source/ecosystem_model.json` | **Authored meta-model** (COMPOSITION_SPEC Part II): constructs, eco-edges, cross-pipeline loops, reconciliation constraints — owns only what no pipeline can own |
| `analysis/ontology/domains.json` | Domain lenses (§18) — zero structure; scopes the one meta-model for Layer 3 narrative + UI |
| `analysis/tests/test_ecosystem_compose.py` | Unit tests for the §14–§17 pure state functions (construct direction, eco-edge state, loop firing, constraint eval) |
| `analysis/rbi_atm_pos/merged/system_model.json` | ATM/POS per-source system model (Layer 2a — pending first FOUNDATION) |
| `analysis/rbi_sibc/timeline.json` | Registry of all ingested periods (includes `is_fy_end`, `dataDate` = report release date, `csv_date` = actual data date matching the consolidated CSV) |
| `analysis/rbi_sibc/merged/` | Merged outputs (Jan 2024–Mar 2026) — source for live dashboard |
| `web/lib/reports/rbi_sibc.ts` | Live dashboard annotations (promoted from merged) |
| `web/CLAUDE.md` | Web-specific context — Next.js, AppShell, DLS components, colour system, mobile rules |
| `web/components/AppShell.tsx` | Shared shell: Header rendered once + dark mode state across all pages |
| `web/components/dls/InsightCard.tsx` | DLS: shared insight card (SIBC + Payments) |
| `web/components/dls/InsightCTAStrip.tsx` | DLS: shared entry/exit strip with headline ticker |
| `analysis/rbi_atm_pos/CLAUDE.md` | ATM/POS pipeline context — read before any ATM/POS work |
| `analysis/rbi_atm_pos/timeline.json` | Registry of ingested ATM/POS months |

### Newsletter subsystem

| File | Purpose |
|---|---|
| `analysis/newsletter/CLAUDE.md` | Newsletter v2 context — read before any content generation |
| `analysis/newsletter/newsletter_sources.py` | Data layer — reads only gate-validated artifacts (signals.db + insight/opportunity feeds) |
| `analysis/newsletter/newsletter_render.py` | Render layer — typed blocks → .md + Substack-paste .html |
| `analysis/newsletter/validate_newsletter.py` | Self-gate: verbatim-card + declared-scope number traceability (`check_doc`) |
| `analysis/newsletter/generate_release_read.py` | Post 1 (L1 release read, per pipeline) — run within 24h of release |
| `analysis/newsletter/generate_deep_read.py` | Post 2 (L2/L3 + ecosystem deep read) — publish mid-cycle |
| `analysis/newsletter/signal_registry.json` | Editorial record of every signal ever published |
| `analysis/legacy/newsletter_v1/` | Retired v1: config-driven generator, LinkedIn + mermaid-image scripts |

---

## Skills (load on demand — not every session)

| Skill | When to invoke |
|---|---|
| `/per-period-analysis` | Writing `delta_brief.md` for a new period (lightweight — ~150 words) |
| `/merged-analysis` | Layer 2a model UPDATE or FOUNDATION pass — check `is_fy_end` in timeline first |
| `/add-new-report` | Full walkthrough: adding a new SIBC period end-to-end |

Newsletter v2 is a deterministic rendering layer over gate-validated artifacts (no longer an exception path) — see `analysis/newsletter/CLAUDE.md` for the 2-post cadence and paste-to-Substack workflow. LinkedIn posts are written by the user in their own voice; there is no LinkedIn generator.

Use `Use a subagent to investigate X` when exploring data files — keeps main context clean.

---

## Compaction Instructions

When compacting, always preserve:
- Current pipeline stage (e.g. "Stage 3, per-period 2026-03-30, evals failing on Check 4")
- Period directory being worked on
- Any unresolved eval errors and which check they came from
- File paths of outputs written this session

## Session Notes (CLAUDE.local.md)

For session-specific state (current period, what's been validated, what's pending), write to `CLAUDE.local.md` at repo root — it is git-ignored and does not affect the shared context.

---

## Next Builds

See `STRATEGY_PLANNER.md` for the prioritised roadmap.

**Done (June 2026):** Layer 2a system models (both pipelines, v4.0) · composition hub + cross-system
derivation (Layer 2b) · S3 dynamic state · live opportunity derivation + `/opportunities` UI (per-card
chart highlight, cross-system 2-chart card) + plain-English narrative (preserved across gate regen) ·
**S4 inference loop** (`run_inference.py` — sourcing-gated proposals, never auto-promoted) · all L1 signal
`current_status` synced (scan/bank-scan/share roll-up in `seed`+`append`; 0 unknowns). The whole
`S1 → S2a/S2b → S3 → opportunities → ecosystem → UI` chain runs in the gates; S4 is a manual review step.

**Done (2026-06-23 session — dashboard/data front closed out, all pushed `63e07f9 → 3b7edc0`):**
payments **YoY-trend insights** + a real YoY chart mode (parity with SIBC); YoY **sourced from the registered
`*-yoy` signals.db** (no parallel recompute; drift-guarded) · payments **LLM-representation aligned with SIBC**
(scalar = LLM eval prose via API, scan/share/composed = deterministic; **11 cards LLM-represented**; 6 new L1
streak/ratio signals added) · **Check 4f STRICT in both gates** (`evidence_all` scope; L2 = signals-on-model,
LLM narrates only) · **registry now L1-computed-only-active on both pipelines** (SIBC's 34 legacy L2 inference
stubs retired/migrated → 2 new gap nodes) · **payments perf**: precomputed compact `atm_pos_chart_series.json`
(330 KB) replaces the 4.6 MB client-side CSV parse (`generate_chart_series.py`, compute-once-ship-compact) ·
**SIBC aggregate "Total" per card** (official parent row, off by default) · S4 + L1/L2 ingestion stages
documented in PIPELINE_ARCHITECTURE.md (Stage 5.7, Stage 8). Both pipelines now aligned **by construction**.

**Latest session handoff:** `HANDOFF_2026-06-23.md` (full arc + open items + the LinkedIn pivot).

**Immediately next — LinkedIn content for site engagement (new session).** The engine is mature; the
bottleneck is distribution. Lead with the **payments pipeline** framed for fintech/product builders (the
reachable network), per the `project_distribution_reality` memory. Workflow: `analysis/newsletter/CLAUDE.md`
→ `generate_linkedin.py` (7-post packages). It's the one exception path not yet on the unified pipeline.

**Queued — engineering-health / technical-design track (non-functional).** See `HANDOFF_TECH_QUALITY.md` (the
single authoritative backlog; the `analysis/` restructure is §4 of it). We've optimised for *functional*
correctness, not *technical*. Gaps: authoritative `ARCHITECTURE.md` (data-flow + lineage + module-dep +
invariants — PIPELINE_ARCHITECTURE is stage-prose only); **unit tests for the deterministic core** (today:
1 file/9 tests, S3 only — compute/date-rules/traceability/precompute untested; highest correctness ROI; wire
pytest into the gate); the **`analysis/` restructure** (ingestion/gate layer is copy-per-pipeline → `core/`
generic engines + manifest-driven gate + `pipelines/{name}/`; design on the 2 pipelines, **validate with
source #3**; phased, git-revertible); perf pass; READMEs + naming; **recurring design-system-coherence audit**
(SIBC vs payments DLS drift). Order: ARCHITECTURE.md → core tests → restructure → perf/READMEs → design cadence.

**Open Notes:**
- **Layer 2 opportunity traceability — Check 4f now STRICT (done 2026-06-20):** `validate_opportunity_traceability.py`
  hard-fails in **both** gates. `derive_opportunities` emits `evidence_all` (the driver's full declared signal
  set); Check 4f validates numbers vs `evidence_all` so structural risks ground even when their driver isn't
  firing. The undriven `risk_cc_market_concentration` got a `creates_risk` edge; the FY-range regex bug
  (`FY22-24`→`-24`) is fixed; `generate_opportunity_narrative` now uses the API (`evaluate._call_llm`). L2
  findings = signals mapped onto the model, LLM narrates only — never independent inference. See S4 (Stage 8 in
  PIPELINE_ARCHITECTURE.md) for how real-world nuance enters as sourced forces.
- **3 SIBC status-substring warnings (non-blocking):** `validate_sibc_traceability.py` flags scalar
  implications whose wording may conflict with the computed status (`sibc-industry-yoy` "decelerat" vs
  strengthening; `sibc-msme-size-yoy-spread` "accelerat" vs weakening; `sibc-pl-share-advances-yoy`
  "strengthening" vs declining). The check is a fuzzy substring heuristic (trips on hedged/conditional
  language) — kept as a warning, not a gate failure. Review the wording; tighten the heuristic only if it
  proves noisy.

**§4 ARCHITECTURE CUTOVER — DONE (2026-06-25).** `analysis/core/gate.py` is now the single
manifest-driven gate for **both** pipelines and **all** modes (sibc `--merged` / sibc `--period` /
atm_pos `--period` / atm_pos `--xlsx`). `run_evals.py` / `run_atm_pos_evals.py` and the 6 superseded
scripts (`source_claims`, `generate_mermaid`, `validate`, `build_behavioral_layer`,
`migrate_forces_to_instances`, `generate_atm_pos_analysis_report`) are archived in `analysis/legacy/`.
Per-pipeline modules live in `analysis/pipelines/{sibc,atm_pos}/`; `generate_signal_history` is in
`analysis/core/`. SIBC per-period parity was proven on the Dec 2025 backfill. Use the `gate.py`
commands in the runbooks below.

**Immediately next:**
1. **Ingest next SIBC + ATM/POS period** — run the full gate after ingestion (regenerates skeleton + S3 + opportunities).
2. **Layer 3 ecosystem strategic model** — authored ~6-monthly; consumes L2a/L2b causal graphs (next session).
3. **Review S4 proposals** — `analysis/s4_proposals/{period}.json`: source + promote the worthwhile candidate channels.
4. Newsletter standardisation: now unblocked by the Layer 2 model.
