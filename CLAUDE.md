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
| signal compute layer | **Live** — `analysis/signals/` — registry.json (174 signals total: SIBC 84 L1 + ATM/POS 82 L1 + L2/L3), signals.db (SQLite — sole store); compute engine in signals/compute/; Check 2e validates DB + registry |
| signal evaluate layer | **Live** — `analysis/signals/evaluate.py` — Stage 5 LLM evaluation via `claude -p` CLI (Pro subscription, no API cost); prompt v1.4 (executive tone, full period series in payload); prior-period signal narratives auto-injected for diff from 2nd period onward; evaluations written to `signals/evaluations/{pipeline}/{period}.json` |
| L1 annotation classification | **Done** — all 49 SIBC annotations classified: 26 L1 / 18 L2 / 5 L3; all 21 ATM/POS insights classified: 16 L1 / 3 L2 / 2 gaps |
| Subsystem generation | **Live** — `generate_mermaid.py` → `.mmd` + `validate.py --check-subsystems` |
| detect_format.py (Stage 0) | **Live** — flags format changes in new XLSX before extraction |
| ATM/POS pipeline | **Live** — `rbi_atm_pos/` — Stages 0–3 complete; Stage 4 (L1 compute) — 82 signals in registry, 56 with DB values (26 YoY signals pending prior-year data); Stage 5 evaluation complete for 2026-03-31 |
| AppShell + DLS | **Live** — shared Header (one instance), `dls/InsightCard`, `dls/InsightCTAStrip` used by both SIBC and Payments |

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
| `python3 analysis/source_claims.py` | Post-model-update: source all system model claims (run after any Layer 2a model change) |
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
| `analysis/signals/evaluations/sibc/2026-04-30.json` | Latest SIBC evaluation — 84 signals, 5 domains, prompt v1.4 |
| `analysis/signals/evaluations/atm_pos/2026-03-31.json` | Latest ATM/POS evaluation — 50 signals, 4 domains, prompt v1.4 |
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

See `STRATEGY_PLANNER.md` for the prioritised roadmap. Immediately next:

1. **Ingest next SIBC + ATM/POS period** — files expected soon; run full pipeline gate after ingestion
2. **UI wiring for L1 signals** — wire UI to consume from evaluation JSONs instead of hand-authored annotations for L1 signals; requires:
   - Add `chart_series` + `chart_dim` fields to registry.json per L1 signal (maps signal → chart highlight)
   - `preferredMode` derivable from compute method type (yoy→"yoy", abs→"absolute", fy_acceleration→"fy")
   - Build `generate_analysis_report.py` output formatter
3. **Two ATM/POS signal gaps to fix**:
   - `dc-psb-share` computed but not appearing in evaluation (check domain routing in evaluate.py)
   - `dc-bank-scan` missing from registry — debit card bank-level scan needed
4. **Tag live annotations with layer: 1/2/3** — metadata-only change, safe to do now
5. **ATM/POS Layer 2a** — first FOUNDATION pass on system_model.json (6 months of data now available)
6. Newsletter standardisation: blocked on Layer 2 signal evaluation
