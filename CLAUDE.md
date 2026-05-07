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

## Current Platform State (May 2026)

| Component | Status |
|---|---|
| RBI SIBC dashboard | **Live** — 7 sections, 49 annotations (merged Jan 2024–Mar 2026) |
| SEO layer | **Live** — metadata, OG image, sitemap, JSON-LD |
| LinkedIn carousel generator | **Live** — `analysis/carousel/generate_carousel.py` |
| Free newsletter generator | **Live** — `analysis/newsletter/generate_newsletter.py` (Issue #3 published) |
| validate_content.py (Check 2b) | **Live** — content accuracy eval on annotation bodies |
| promote_annotations.py (Stage 7) | **Live** — automated verified copy to web |
| signal_registry.json | **Live** — 7 signals tracked across 3 issues |
| System View dashboard tab | Planned |
| Monthly Digest generator | Planned |
| Gold Loan Monitor page | Planned |
| Email/Substack CTA on dashboard | Planned |

---

## CLI Tools

Use CLI tools for all external service interactions — they are the most context-efficient approach (one line of output vs loading API JSON).

| Tool | Use for |
|---|---|
| `gh` | PRs, CI status, issues, release notes — never use GitHub web for anything scriptable |
| `vercel` | Domain management, deployment status, env vars — Next Build #1 uses `vercel domains add` |
| `python3 analysis/run_evals.py` | Always run through the eval script, not individual validators ad-hoc |
| `python3 analysis/promote_annotations.py` | Always use for Stage 8 — never `cp` or manual paste |

---

## Authoring Rules (non-negotiable)

### Visual outputs
1. **ASCII layout first** — proportions, zones, text hierarchy
2. **Explicit approval** — no code until layout confirmed
3. **Then implement** — translate approved ASCII directly

### Analysis outputs
- `annotation_ids` in `system_model.json` must **exactly match** `id` fields in the annotations file. Copy-paste — never retype.
- **Annotation IDs are permanent.** Once an `id` exists in `annotations_merged.ts`, it is never renamed or deleted — even across FOUNDATION rebuilds. UPDATE mode only adds. FOUNDATION mode may restructure, but any removed ID requires explicit justification after `promote_annotations.py --dry-run`.
- **Merged system_model.json has two modes — read `PIPELINE_ARCHITECTURE.md` before every Stage 5.** FY-end (March file) = FOUNDATION. All other months = UPDATE. Wrong mode = wrong depth of analysis.
- Stage 7 always uses `promote_annotations.py` — never manual copy.

### Git / deployment
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
| `analysis/validate_annotations.py` | Check 3: live rbi_sibc.ts structure |
| `analysis/validate_content.py` | Check 2b: dates/values/growth in annotation bodies vs sections.json |
| `analysis/validate.py` | Checks 4, 5: system_model.json + subsystems.json |
| `analysis/extract_sibc.py` | Stage 1: SIBC xlsx → sections.json + format_report.json |
| `analysis/update_web_data.py` | Stage 1b: all xlsx → rbi_sibc_consolidated.csv |
| `analysis/generate_merge.py` | Stage 4: sections.json[] → sections_merged.json (auto-validates) |
| `analysis/generate_mermaid.py` | Stage 7 (on-demand): system_model → .mmd files |
| `analysis/promote_annotations.py` | Stage 7: annotations_merged.ts → rbi_sibc.ts (verified copy + ID diff) |
| `analysis/rbi_sibc/timeline.json` | Registry of all ingested periods (includes `is_fy_end` flag) |
| `analysis/rbi_sibc/merged/` | Merged outputs (Jan 2024–Mar 2026) — source for live dashboard |
| `analysis/newsletter/signal_registry.json` | Cumulative signal tracker — update before each newsletter issue |
| `web/lib/reports/rbi_sibc.ts` | Live dashboard annotations (promoted from merged) |
| `web/CLAUDE.md` | Web-specific context (Next.js, Vercel, component patterns) |

---

## Skills (load on demand — not every session)

| Skill | When to invoke |
|---|---|
| `/per-period-analysis` | Stage 2: writing `delta_brief.md` for a new period (lightweight — ~150 words) |
| `/merged-analysis` | Stage 5: merged UPDATE or FOUNDATION pass — check `is_fy_end` in timeline first |
| `/add-new-report` | Full walkthrough: adding a new SIBC period end-to-end |

Use `Use a subagent to investigate X` when exploring data files — keeps main context clean.

## Compaction Instructions

When compacting, always preserve:
- Current pipeline stage (e.g. "Stage 3, per-period 2026-03-30, evals failing on Check 4")
- Period directory being worked on
- Any unresolved eval errors and which check they came from
- File paths of outputs written this session

## Session Notes (CLAUDE.local.md)

For session-specific state (current period, what's been validated, what's pending), write to `CLAUDE.local.md` at repo root — it is git-ignored and does not affect the shared context.

---

## Next Builds (in order)

1. Connect `indiacreditlens.com` domain on Vercel
2. Add Substack/email CTA to dashboard footer
3. Publish Feb 2026 carousel + newsletter
4. System View tab (interactive diagram from `system_model.json`)
5. `generate_digest.py` — premium monthly PDF
6. Gold Loan Monitor page (free version — data in SIBC)
7. BSR-1 Quarterly — next report
8. CIBIL Quarterly — unlocks cross-report Gold Loan Monitor
