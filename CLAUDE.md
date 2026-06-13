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

## Current Platform State (June 2026)

Live components only. Planned work lives in `STRATEGY_PLANNER.md`.

| Component | Status |
|---|---|
| RBI SIBC dashboard | **Live** — 7 sections, 49 annotations (merged Jan 2024–Mar 2026) |
| SEO layer | **Live** — metadata, OG image, sitemap, JSON-LD |
| Email / Substack CTA | **Live** — `SubstackCTA.tsx` + `EmailGate.tsx` |
| Free newsletter generator | **Live** — `analysis/newsletter/generate_newsletter.py` (Issue #3 published) |
| LinkedIn post generator | **Live** — `analysis/newsletter/generate_linkedin.py` (7-post package per cycle) |
| validate_content.py (Check 2b) | **Live** — content accuracy eval on annotation bodies |
| validate_claims.py (Check 2c) | **Live** — claim sourcing + citation layer on system model |
| validate_annotation_basis.py (Check 2d) | **Live** — basis completeness check (inference/hypothesis → basis.inferences non-empty) |
| promote_annotations.py (Stage 7) | **Live** — automated verified copy to web |
| signal_registry.json | **Live** — 7 signals tracked across 3 issues (newsletter subsystem) |
| signal compute layer | **Live** — `analysis/signals/` — registry.json (**206 signals**: SIBC 84 L1 + 34 L2 + 4 L3; ATM/POS 84 L1), signals.db (SQLite — sole store); compute engine in signals/compute/; Check 2e validates DB + registry |
| signal evaluate layer | **Live** — `analysis/signals/evaluate.py` — Stage 5 LLM evaluation via `claude -p` CLI (Pro subscription, no API cost); prompt v1.4 (executive tone, full period series in payload); prior-period signal narratives auto-injected for diff from 2nd period onward; evaluations written to `signals/evaluations/{pipeline}/{period}.json` |
| L1 annotation classification | **Done** — all 49 SIBC annotations classified: 26 L1 / 18 L2 / 5 L3; all 21 ATM/POS insights classified: 16 L1 / 3 L2 / 2 gaps |
| Subsystem generation | **Live** — `generate_mermaid.py` → `.mmd` + `validate.py --check-subsystems` |
| detect_format.py (Stage 0) | **Live** — flags format changes in new XLSX before extraction |
| ATM/POS pipeline | **Live** — `rbi_atm_pos/` — Stages 0–3 + L1 compute (84 signals) + evaluate complete through **2026-04-30** (16 periods in DB). **Dashboard insights** come from a *separate deterministic path*: Stage 4a `compute_atm_pos_signals.py` → `rbi_atm_pos/signals.json` → Stage 4b `generate_atm_pos_insights.py` → `atm_pos_insights.json` (17 insights, Apr 2026). Both stages run inside `run_atm_pos_evals.py`. NB: `generate_atm_pos_analysis_report.py` (the db/eval-driven "Stage 5.5") is currently a **no-op** (it only updates `layer==1` items and 4b writes none) — 4b is authoritative until the dual paths are reconciled. |
| AppShell + DLS | **Live** — shared Header (one instance), `dls/InsightCard`, `dls/InsightCTAStrip` used by both SIBC and Payments |
| **Layer 2a system models (v4.0)** | **Live** — `system_model.json` for both pipelines (SIBC 85 entities, ATM/POS 35). Deterministic structural skeleton (`generate_skeleton.py`) + behavioral-causal split into shared **channels** (S2a) + dated **force_instances** (S2b). Specs: `analysis/SYSTEM_MODEL_SPEC.md` v3.0 + `analysis/COMPOSITION_SPEC.md` v1.0. Validated by `validate_system_model.py` in both gates. |
| **Composition hub (Layer 2b)** | **Live** — `analysis/ontology/{concepts,channels}.json` shared across pipelines; entities carry global URNs + `concept_tags`. `derive_cross_links.py` derives cross-system candidates (stock↔flow + shared-channel); `cross_source/composition.json` holds confirmed cross-edges; `validate_composition.py` enforces the no-monolith rule. |
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
| `python3 analysis/run_evals.py` | SIBC gate — Stages 0–6 (data integrity + signal + model validation) |
| `python3 analysis/run_atm_pos_evals.py --xlsx {file}` | ATM/POS gate — Stages 0–3 + L1 signal append + build |
| `python3 analysis/promote_annotations.py` | Stage 7: verified copy annotations_merged.ts → rbi_sibc.ts — never `cp` or manual paste |
| `python3 analysis/detect_format.py` | Stage 0: flag format changes before extraction (SIBC) |
| ~~`python3 analysis/source_claims.py`~~ | **Legacy** — v2 claim sourcing; superseded by `validate_system_model.py` (sourcing built in). Detached from gate. |
| `python3 analysis/generate_skeleton.py --pipeline {sibc\|atm_pos}` | Stage 4-struct: regenerate the deterministic skeleton (preserves behavioral layer + force_instances). Runs inside both gates. |
| `python3 analysis/validate_system_model.py --pipeline {name}` | v4.0 model gate — structural + D1/D2/D3 discipline + force sourcing + URN/concept_tags. Replaces legacy checks 4/5/2c. |
| `python3 analysis/generate_system_state.py --pipeline {name} --period {date}` | S3: compute dynamic state from `signals.db` → `system_state_{period}.json`. |
| `python3 analysis/derive_opportunities.py --pipeline {name} --period {date}` | Derive live opportunity/risk status from S3 driver firing. |
| `python3 analysis/derive_cross_links.py` · `compose_ecosystem.py` · `validate_composition.py` | Cross-system pass (Layer 2b): derive candidates → project ecosystem state → validate cross-edges. |
| `python3 analysis/generate_opportunities_feed.py` then `generate_opportunity_narrative.py` | Presentation: build `opportunities_feed.json`, then add plain-English narrative (post-gate, cached). |
| `python3 analysis/generate_signal_history.py append --pipeline {name} --period {date}` | Stage 4: Layer 1 signal compute → writes to signals.db + updates registry |
| `python3 analysis/generate_signal_history.py evaluate --pipeline {name} --period {date}` | Stage 5: LLM signal evaluate → evaluations JSON; auto-loads prior period for narrative diff |
| `python3 analysis/generate_signal_history.py status` | Print current signal states across all pipelines |
| `python3 analysis/validate_signal_history.py` | Check 2e: signal history integrity — DB rows, registry schema, status sync vs DB |
| `python3 analysis/newsletter/validate_newsletter_config.py` | Newsletter gate — exception path, not part of standard pipeline |

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
- Always run `python3 analysis/run_evals.py` (includes `npm run build`) before `git push`
- Show results and wait for explicit confirmation

---

## Key Files

| File | Purpose |
|---|---|
| `CLAUDE.md` | This file |
| `STRATEGY_PLANNER.md` | Content ladder, revenue model, product roadmap |
| `PIPELINE_ARCHITECTURE.md` | **Pipeline stages, system model cadence, adding-period checklist** |
| `analysis/report_analysis_prompt.md` | Master prompt + analytical framework for all report analyses |
| `analysis/run_evals.py` | Master eval gate — Stages 3 and 6 |
| `analysis/validate_timeline.py` | Check 0: timeline.json schema + path existence |
| `analysis/validate_sections.py` | Check 1: sections.json data integrity |
| `analysis/validate_annotations.py` | Check 3: live rbi_sibc.ts structure (Checks A–H) |
| `analysis/validate_content.py` | Check 2b: dates/values/growth in annotation bodies vs sections.json |
| `analysis/validate_claims.py` | Check 2c: claim sourcing — every system model claim has a source |
| `analysis/validate_annotation_basis.py` | Check 2d: basis completeness — inference/hypothesis annotations must have basis.inferences |
| `analysis/validate_signal_history.py` | Check 2e: signal history integrity — DB rows, registry schema, status sync vs DB |
| `analysis/validate.py` | Checks 4, 5: system_model.json + subsystems.json |
| `analysis/extract_sibc.py` | Stage 1: SIBC xlsx → sections.json + format_report.json |
| `analysis/detect_format.py` | Stage 0: detect structural changes in new XLSX vs prior period (SIBC) |
| `analysis/update_web_data.py` | Stage 3: all xlsx → rbi_sibc_consolidated.csv |
| `analysis/generate_merge.py` | Stage 3: sections.json[] → sections_merged.json (auto-validates) |
| `analysis/generate_mermaid.py` | On-demand: system_model → .mmd files (always after FOUNDATION; after UPDATE only if nodes/edges changed) |
| `analysis/source_claims.py` | Post-model-update: source all claims in system_model.json |
| `analysis/promote_annotations.py` | Stage 7: annotations_merged.ts → rbi_sibc.ts (verified copy + ID diff) |
| `analysis/generate_signal_history.py` | Stage 4 (`append`) + Stage 5 (`evaluate`) + `status` + `seed` commands |
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
| `analysis/newsletter/CLAUDE.md` | Newsletter + LinkedIn generation context — read before any content generation |
| `analysis/newsletter/newsletter_config.json` | Current issue config — signals, hero narrative, image assignments |
| `analysis/newsletter/signal_registry.json` | Cumulative signal tracker — update before each issue |
| `analysis/newsletter/newsletter_delta_brief.py` | Generates delta_brief from merged outputs for newsletter authoring |
| `analysis/newsletter/validate_newsletter_config.py` | Gate: validates config before generation |
| `analysis/newsletter/generate_images.py` | Renders Mermaid .mmd → PNG for newsletter + LinkedIn |
| `analysis/newsletter/generate_newsletter.py` | Renders newsletter HTML (standard + Substack) |
| `analysis/newsletter/generate_linkedin.py` | Renders 7-post LinkedIn package (1 anchor + 6 signal posts) |

---

## Skills (load on demand — not every session)

| Skill | When to invoke |
|---|---|
| `/per-period-analysis` | Writing `delta_brief.md` for a new period (lightweight — ~150 words) |
| `/merged-analysis` | Layer 2a model UPDATE or FOUNDATION pass — check `is_fy_end` in timeline first |
| `/add-new-report` | Full walkthrough: adding a new SIBC period end-to-end |

Newsletter and LinkedIn generation are an exception path — not yet standardised to the unified pipeline architecture. Run scripts directly per `analysis/newsletter/CLAUDE.md` only when explicitly resuming newsletter work.

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

**Immediately next:**
1. **Ingest next SIBC + ATM/POS period** — run full gate after ingestion (now also regenerates skeleton + S3 + opportunities).
2. **Layer 3 ecosystem strategic model** — authored ~6-monthly; consumes L2a/L2b causal graphs (next session).
3. **Review S4 proposals** — `analysis/s4_proposals/{period}.json`: source + promote the worthwhile candidate channels.
4. Newsletter standardisation: now unblocked by the Layer 2 model.
