# Pipeline Architecture — India Credit Lens

> Single source of truth for the data ingestion and content generation pipeline.
> Referenced by `CLAUDE.md`. Read this before adding any new report or period.

---

## Overview: Two Objects, One Pipeline

Every SIBC report file produces two objects. Both go through the same stages
in sequence. The pipeline never merges first — per-period analysis always
comes before the merged view.

```
SIBC .xlsx
    │
    ▼
[Stage 1] extract_sibc.py
    │  → rbi_sibc/{period}/sections.json
    │
    ▼
[Stage 1b] update_web_data.py
    │  Consolidates ALL xlsx files → single deduplicated long CSV
    │  → rbi-analytics/consolidated/consolidated_long.csv
    │  → web/public/data/rbi_sibc_consolidated.csv   ← dashboard charts live here
    │  Dedup rule: latest report_date wins for any (statement, code, date) overlap
    │
    ▼
[Stage 2] Claude: Per-period analysis
    │  → rbi_sibc/{period}/system_model.json
    │  → rbi_sibc/{period}/subsystems.json      (co-generated, always a unit)
    │  → rbi_sibc/{period}/annotations_draft.ts
    │  → rbi_sibc/{period}/insights.md
    │  → rbi_sibc/{period}/gaps.md
    │  → rbi_sibc/{period}/opportunities.md
    │
    ▼
[Stage 3] run_evals.py (gate — exit 1 blocks next stage)
    │  Checks: sections.json, annotations_draft.ts, system_model.json, subsystems.json
    │
    ▼
[Stage 4] generate_mermaid.py
    │  → output/mermaid/rbi_sibc/{period}/*.mmd
    │  → output/mermaid/rbi_sibc/{period}/subsystems.json  (copy; canonical is period dir)
    │
    ▼
[Stage 5] generate_merge.py
    │  → rbi_sibc/merged/sections_merged.json
    │    (merges all periods; later period values override earlier for same month)
    │
    ▼
[Stage 6] Claude: Merged analysis
    │  → rbi_sibc/merged/system_model.json
    │  → rbi_sibc/merged/subsystems.json
    │  → rbi_sibc/merged/annotations_merged.ts
    │  → rbi_sibc/merged/insights.md
    │  → rbi_sibc/merged/gaps.md
    │  → rbi_sibc/merged/opportunities.md
    │
    ▼
[Stage 7] run_evals.py --merged (gate)
    │
    ▼
[Stage 8] Web + content update
    │  → web/lib/reports/rbi_sibc.ts  (from merged annotations)
    │  → newsletter_config.json        (from merged system_model + subsystems)
    │  → generate_newsletter.py        (script-only, no Claude)
```

---

## Directory Structure

```
analysis/
├── rbi_sibc/
│   ├── timeline.json               ← Registry of all ingested periods
│   ├── merged/
│   │   ├── sections_merged.json    ← Combined time-series across all periods
│   │   ├── system_model.json       ← Causal model of merged data
│   │   ├── subsystems.json         ← Subsystem map for merged model
│   │   ├── annotations_merged.ts   ← Draft annotations (→ web/lib/reports/)
│   │   ├── insights.md
│   │   ├── gaps.md
│   │   └── opportunities.md
│   └── {YYYY-MM-DD}/               ← One folder per SIBC publication date
│       ├── sections.json           ← Raw extracted data (from extract_sibc.py)
│       ├── system_model.json       ← Per-period causal model
│       ├── subsystems.json         ← Per-period subsystem map (canonical)
│       ├── annotations_draft.ts    ← Per-period draft annotations
│       ├── insights.md
│       ├── gaps.md
│       └── opportunities.md
│
├── output/
│   └── mermaid/
│       └── rbi_sibc/
│           └── {YYYY-MM-DD}/       ← Generated diagram files
│               ├── flowchart.mmd
│               ├── overview.mmd
│               ├── quadrant.mmd
│               ├── sankey.mmd
│               ├── subsystems.json ← Copy of period dir canonical
│               └── sub_*.mmd
│
├── extract_sibc.py                 ← Stage 1: xlsx → sections.json
├── generate_merge.py               ← Stage 5: sections[] → sections_merged.json
├── generate_mermaid.py             ← Stage 4: system_model → .mmd files
├── generate_delta.py               ← Ad-hoc: period-over-period delta (not in pipeline)
├── validate_sections.py            ← Validator: sections.json
├── validate_annotations.py         ← Validator: annotations .ts files
├── validate.py                     ← Validator: system_model.json + subsystems
├── run_evals.py                    ← Master eval orchestrator (Stages 3, 7)
├── report_analysis_prompt.md       ← Master prompt for all Claude analyses
│
└── newsletter/
    ├── generate_newsletter.py      ← Script-only content generator
    ├── newsletter_config.json      ← Input config (from merged system_model)
    └── output/                     ← Generated newsletters (dated)

rbi-analytics/                      ← Ingestion layer (do not restructure)
├── parser.py                       ← Called by extract_sibc.py
├── consolidate.py                  ← Multi-file consolidation (exploration)
├── dashboard.py                    ← Streamlit exploration tool (local only)
├── SIBC*.xlsx                      ← Source files (raw, never modified)
└── consolidated/                   ← CSV outputs from parser.py

web/
└── lib/reports/
    └── rbi_sibc.ts                 ← Live annotations (from merged annotations_merged.ts)
```

---

## Key Rules

### One pipeline, two objects
- Per-period object: analysis of a single SIBC file. Never published directly.
- Merged object: analysis of combined data across all periods. This is what the
  web dashboard and newsletter use.
- Merge happens at the **data level** (`sections.json`), not annotation level.
  Merged annotations are always a fresh Claude analysis pass on merged data.

### Subsystems are co-generated with system_model
- `generate_mermaid.py` runs immediately after `system_model.json` is produced.
- They are always a unit. Never generate one without the other.
- Canonical subsystems location: `rbi_sibc/{period}/subsystems.json`
- The copy in `output/mermaid/` is for diagram generation only.

### Validators are pipeline gates
- `run_evals.py` exits 1 on any error. The next stage does not run until it exits 0.
- Warnings are non-blocking; errors block.
- Run evals after Stage 2 (per-period) and after Stage 6 (merged).

### annotation_ids are sacred
- Every `annotation_id` in `system_model.json` must exactly match an `id` in the
  annotations file. Copy-paste — never retype.
- The validator enforces this at every run.

### Newsletter from merged only
- `newsletter_config.json` is generated from the merged system_model + subsystems.
- Per-period system models do not feed the newsletter directly.

### No carousel in active pipeline
- `generate_carousel.py` is ad-hoc only. Run manually when needed.
- `generate_delta.py` exists but is not a pipeline stage — parked for future use.

### Git / deployment
- Never auto-push to GitHub.
- Always run `npm run build` + `tsc --noEmit` before pushing (or run `run_evals.py`
  without `--skip-build`).
- Commit per-period and merged outputs separately for clean git history.

---

## timeline.json Schema

```json
{
  "report_id": "rbi_sibc",
  "report_name": "RBI Sector/Industry-wise Bank Credit",
  "periods": [
    {
      "period":          "Jan 2026",
      "dataDate":        "2026-02-27",
      "total_credit_lcr": 204.8,
      "yoy_growth_pct":  14.6,
      "subsystem_count": 7,
      "paths": {
        "sections":          "rbi_sibc/2026-02-27/sections.json",
        "system_model":      "rbi_sibc/2026-02-27/system_model.json",
        "subsystems":        "rbi_sibc/2026-02-27/subsystems.json",
        "annotations_draft": "rbi_sibc/2026-02-27/annotations_draft.ts",
        "annotations_live":  "web/lib/reports/rbi_sibc.ts",
        "mermaid_output":    "output/mermaid/rbi_sibc/2026-02-27"
      }
    }
  ],
  "merged": {
    "sections": "rbi_sibc/merged/sections_merged.json"
  }
}
```

Add a new entry to `periods[]` for every new SIBC file ingested.
Update `merged.sections` path if the merged file moves.

---

## Adding a New Period (Phase 3 checklist)

```
□  Place SIBC .xlsx in rbi-analytics/
□  python3 analysis/extract_sibc.py rbi-analytics/SIBC{date}.xlsx
□  python3 analysis/update_web_data.py
□  Validate: python3 analysis/run_evals.py --period {date} --skip-build
□  Claude: per-period analysis → system_model.json + subsystems.json + annotations_draft.ts + docs
□  Validate: python3 analysis/run_evals.py --period {date} --skip-build
□  python3 analysis/generate_mermaid.py rbi_sibc/{date}/system_model.json
□  python3 analysis/generate_merge.py   (auto-discovers all periods from timeline.json)
□  Update timeline.json — add new period entry
□  Claude: merged analysis → merged/system_model.json + subsystems.json + annotations_merged.ts + docs
□  Validate: python3 analysis/run_evals.py --period merged --skip-build  (once merged eval added)
□  Update web/lib/reports/rbi_sibc.ts from merged annotations
□  npm run build + tsc --noEmit
□  Commit + push
```
