# Pipeline Architecture — India Credit Lens

> Single source of truth for the data ingestion and content generation pipeline.
> Referenced by `CLAUDE.md`. Read this before adding any new report or period.

---

## Architecture Overview

The pipeline has two distinct layers:

**Data layer** — runs every period, fully deterministic:
```
xlsx → sections.json → sections_merged.json → rbi_sibc_consolidated.csv
```

**Analysis layer** — runs every period, but scope depends on cadence:
- Per-period: `delta_brief.md` only (lightweight, ~5 min Claude pass)
- Merged: **FOUNDATION mode** (FY-end, ~once/year) or **UPDATE mode** (interim, ~10 months/year)

**Only the merged layer publishes to the web dashboard and newsletter.**
Per-period analysis artifacts (system_model, subsystems, annotations) are not created.
The system_model.json and subsystems.json are living documents that evolve deliberately —
they are not regenerated from scratch on every period.

---

## Pipeline Stages

```
SIBC .xlsx
    │
    ▼
[Stage 1] extract_sibc.py
    │  → rbi_sibc/{period}/sections.json
    │  → rbi_sibc/{period}/format_report.json
    │
    ▼
[Stage 1b] update_web_data.py
    │  Consolidates ALL xlsx files → single deduplicated long CSV
    │  → rbi-analytics/consolidated/consolidated_long.csv
    │  → web/public/data/rbi_sibc_consolidated.csv   ← dashboard charts live here
    │  Dedup rule: latest report_date wins for any (statement, code, date) overlap
    │
    ▼
[Stage 2] Claude: delta_brief.md  (per-period, always)
    │  → rbi_sibc/{period}/delta_brief.md
    │  Scope: what moved vs prior period, any data quality flags, one newsletter hook
    │  NOT a full analysis — no system_model, no subsystems, no annotations_draft
    │
    ▼
[Stage 3] run_evals.py --period {date} (reduced gate)
    │  Check 0:   validate_timeline.py      timeline.json schema + path existence
    │  Check 0.5: format_report.json        format detection confirmed + supported
    │  Check 1:   validate_sections.py      sections.json schema + data integrity
    │  Check 1b:  web CSV dedup check       auto-fixes via update_web_data.py
    │  — Checks 2, 2b, 2c, 4, 5 are skipped (no per-period analysis artifacts) —
    │
    ▼
[Stage 4] generate_merge.py
    │  → rbi_sibc/merged/sections_merged.json
    │    (merges all periods; later period non-null values override earlier for same month)
    │  Auto-runs validate_sections.py --merged post-write; exits 1 on failure
    │
    ▼
[Stage 5] Claude: Merged analysis — FOUNDATION or UPDATE mode
    │
    │  Determine mode BEFORE starting (see System Model Cadence rules below):
    │
    │  FOUNDATION (FY-end, ~once/year — full rebuild):
    │  → rbi_sibc/merged/system_model.json       full rebuild, _meta.mode = "foundation"
    │  → rbi_sibc/merged/subsystems.json         full rebuild
    │  → rbi_sibc/merged/annotations_merged.ts   full rewrite (IDs may change — see guard)
    │  → rbi_sibc/merged/insights.md
    │  → rbi_sibc/merged/gaps.md
    │  → rbi_sibc/merged/opportunities.md
    │
    │  UPDATE (interim months — additive only):
    │  → rbi_sibc/merged/system_model.json       update stats + add new nodes only
    │                                             _meta.mode = "update", bump last_updated
    │  → rbi_sibc/merged/subsystems.json         append new subsystems only
    │  → rbi_sibc/merged/annotations_merged.ts   update bodies + add new IDs only
    │  → rbi_sibc/merged/insights.md
    │  → rbi_sibc/merged/gaps.md
    │  → rbi_sibc/merged/opportunities.md
    │
    ▼
[Stage 6] run_evals.py --period merged --merged (gate)
    │  Full check suite; null values in Jan series are warnings not errors
    │
    ▼
[Stage 7] Web + content update
    │  promote_annotations.py              (automated copy + ID verification)
    │  → web/lib/reports/rbi_sibc.ts
    │  generate_mermaid.py                 (only if system_model nodes/edges changed)
    │  → newsletter_config.json            (from merged system_model + subsystems)
    │  → generate_newsletter.py            (script-only, no Claude)
```

---

## System Model Cadence (governing rule)

`system_model.json` and `subsystems.json` are **living documents**, not generated artifacts.
They evolve in two modes. **Choosing the wrong mode is the most consequential error in this pipeline.**

### FOUNDATION mode — full rebuild

**When:** The new period is the March year-end file (dataDate falls in April–May, covers
the complete fiscal year). Approximately once per year.

**What happens:**
- Full rebuild of `system_model.json` from `sections_merged.json` — all nodes and edges
- Full rebuild of `subsystems.json`
- Full rewrite of `annotations_merged.ts` — IDs may change (see annotation ID guard below)
- Full rewrite of `insights.md`, `gaps.md`, `opportunities.md`

**Why FY-end:** The March file gives Claude the complete annual picture — all four quarters,
confirmed YoY growth, full sector composition. Interim files have partial data; a FOUNDATION
pass on interim data produces a shallower model than the same data would produce at year-end.

**Guard — set in `_meta`:**
```json
"_meta": {
  "mode": "foundation",
  "last_foundation_date": "2026-04-30"
}
```

### UPDATE mode — additive only

**When:** All non-FY-end periods. Default for ~10 months of the year.

**What happens:**
- Read the existing `system_model.json` first — the current model is the starting point
- Update stats/values in existing node descriptions (e.g., ₹X.XL Cr → ₹Y.YL Cr)
- Add new nodes only for genuinely new signals (new driver, new sector behaviour, new gap)
- **Never delete or rename existing nodes** — node IDs are permanent once created
- Append new annotations; update bodies of existing ones; never delete existing IDs
- `subsystems.json`: add new subsystem clusters only; never restructure existing ones

**Guard — set in `_meta`:**
```json
"_meta": {
  "mode": "update",
  "last_updated": "2026-03-30",
  "last_foundation_date": "2026-04-30"
}
```

### Mode decision table

| Condition | Mode |
|---|---|
| March year-end file (dataDate April–May, covers full FY) | **FOUNDATION** |
| Any other month | **UPDATE** |
| Structural event changes multiple causal relationships simultaneously | **FOUNDATION** (explicit decision required — note why in `_meta.note`) |
| First-ever period for a new report type | **FOUNDATION** (always) |

### Mermaid generation cadence

`generate_mermaid.py` is **on-demand**, not automatic on every period:
- **Always** after a FOUNDATION pass
- After an UPDATE pass **only if** new nodes or edges were added
- **Not** after an UPDATE pass that only updated node description stats
- Check: compare node/edge count before and after the UPDATE pass as your guide

---

## Per-period folder (minimal)

Each period folder contains exactly three files:

```
rbi_sibc/{YYYY-MM-DD}/
    ├── sections.json        ← Raw extracted data — input to generate_merge.py
    ├── format_report.json   ← Format detection result — Check 0.5 gate
    └── delta_brief.md       ← Lightweight Claude delta analysis
```

`delta_brief.md` structure (keep tight — 150–200 words max):
```markdown
## Period
{month} {year} | dataDate: {YYYY-MM-DD} | vs prior: {prev_period}

## What moved
- 2–4 bullet observations on what changed vs prior period

## Data quality flags
- Any format anomalies, null series, reclassification effects in this file

## Newsletter hook
- One headline stat or story for the upcoming newsletter issue
```

**No system_model.json, subsystems.json, annotations_draft.ts, insights.md, gaps.md,
opportunities.md, or mermaid output in per-period folders.**
Existing period folders (2026-02-27, 2026-03-30, 2026-04-30) retain their historical
artifacts — do not delete them. New periods follow the minimal structure.

---

## Directory Structure

```
analysis/
├── rbi_sibc/
│   ├── timeline.json               ← Registry of all ingested periods
│   ├── merged/
│   │   ├── sections_merged.json    ← Combined time-series across all periods
│   │   ├── system_model.json       ← Causal model (living doc — FOUNDATION or UPDATE)
│   │   ├── subsystems.json         ← Subsystem map (living doc — append only in UPDATE)
│   │   ├── annotations_merged.ts   ← Draft annotations (→ web/lib/reports/)
│   │   ├── insights.md
│   │   ├── gaps.md
│   │   └── opportunities.md
│   └── {YYYY-MM-DD}/               ← One folder per SIBC publication date
│       ├── sections.json           ← Raw extracted data (always present)
│       ├── format_report.json      ← Format detection (always present)
│       └── delta_brief.md          ← Delta analysis (always present, new periods only)
│
├── output/
│   └── mermaid/
│       └── rbi_sibc/
│           └── {YYYY-MM-DD}/       ← Generated diagram files (merged only, on-demand)
│               ├── flowchart.mmd
│               ├── overview.mmd
│               ├── quadrant.mmd
│               ├── sankey.mmd
│               ├── subsystems.json ← Copy of merged subsystems at generation time
│               └── sub_*.mmd
│
├── extract_sibc.py                 ← Stage 1: xlsx → sections.json + format_report.json
├── generate_merge.py               ← Stage 4: sections.json[] → sections_merged.json (auto-validates)
├── generate_mermaid.py             ← Stage 7 (on-demand): system_model → .mmd files
├── promote_annotations.py          ← Stage 7: annotations_merged.ts → rbi_sibc.ts (verified copy)
├── generate_delta.py               ← Ad-hoc: period-over-period delta (not in pipeline)
├── validate_timeline.py            ← Validator: timeline.json (Check 0)
├── validate_sections.py            ← Validator: sections.json (Check 1)
├── validate_annotations.py         ← Validator: annotations .ts files (Check 3)
├── validate_content.py             ← Validator: numbers/dates in annotation bodies (Check 2b)
├── validate.py                     ← Validator: system_model.json + subsystems (Checks 4, 5)
├── run_evals.py                    ← Master eval orchestrator (Stages 3, 6)
├── report_analysis_prompt.md       ← Master prompt for all Claude analyses
│
└── newsletter/
    ├── generate_newsletter.py      ← Script-only content generator
    ├── newsletter_config.json      ← Current-issue config (new signals only)
    ├── signal_registry.json        ← Cumulative signal tracker — ALL prior issues
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

### Analysis layer is merged-only
- Per-period folder contains data only (`sections.json`, `format_report.json`, `delta_brief.md`).
- All analytical output — system_model, subsystems, annotations — lives in `merged/` only.
- Web dashboard and newsletter always source from merged outputs. Never from per-period.

### System model is a living document
- `system_model.json` and `subsystems.json` evolve deliberately. See System Model Cadence above.
- In UPDATE mode: read first, add/update only, never delete nodes or edges.
- In FOUNDATION mode: full rebuild is legitimate — but only at FY-end or an explicit structural event.
- The `_meta.mode` field in `system_model.json` records which mode produced the current version.

### Annotation IDs are permanent
- An `id` field in `annotations_merged.ts`, once created, is never renamed or deleted.
- UPDATE mode may add new IDs. FOUNDATION mode may restructure — but before promoting,
  run `promote_annotations.py --dry-run` and explicitly account for every removed ID.
- `annotation_ids` in `system_model.json` must exactly match `id` fields in the annotations
  file. Copy-paste — never retype. The validator enforces this at every run.

### Stage 3 evals scope depends on mode
- Per-period run: Checks 0, 0.5, 1, 1b only. No Claude artifacts to validate.
- Merged run: full check suite (Checks 0, 1, 1b, 2b, 2c, 3, 4, 5, 6).

### Stage 4 self-validates
- `generate_merge.py` auto-runs `validate_sections.py --merged` after writing.
- If post-merge validation fails, `generate_merge.py` exits 1 — Stage 5 must not run.

### Stage 7 promotion is automated, not manual
- Use `promote_annotations.py` to copy `annotations_merged.ts` → `rbi_sibc.ts`.
- The script verifies annotation IDs match before and after the write.
- Never copy manually — the verification step is the guardrail.

### Newsletter from merged only
- `newsletter_config.json` is generated from the merged system_model + subsystems.
- `signal_registry.json` must be updated before authoring `newsletter_config.json` each issue.

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
      "period":           "Mar 2026",
      "dataDate":         "2026-04-30",
      "is_fy_end":        true,
      "total_credit_lcr": 213.6,
      "yoy_growth_pct":   16.1,
      "fy_growth_pct":    16.1,
      "paths": {
        "sections":      "rbi_sibc/2026-04-30/sections.json",
        "format_report": "rbi_sibc/2026-04-30/format_report.json",
        "delta_brief":   "rbi_sibc/2026-04-30/delta_brief.md"
      }
    }
  ],
  "merged": {
    "sections":     "rbi_sibc/merged/sections_merged.json",
    "system_model": "rbi_sibc/merged/system_model.json",
    "subsystems":   "rbi_sibc/merged/subsystems.json",
    "annotations":  "rbi_sibc/merged/annotations_merged.ts"
  }
}
```

**New field: `is_fy_end`** — set `true` when the period is a March year-end file
(dataDate in April–May). This is the trigger for FOUNDATION mode in Stage 5.
All prior period entries should be backfilled with `is_fy_end: false`.

---

## Adding a New Period (checklist)

Determine mode before starting. Check `is_fy_end` for the incoming file.

### Interim period — UPDATE mode (~10 months/year)

```
□  Place SIBC .xlsx in rbi-analytics/
□  python3 analysis/extract_sibc.py rbi-analytics/SIBC{date}.xlsx
□  python3 analysis/update_web_data.py
□  Claude: delta_brief.md → rbi_sibc/{date}/delta_brief.md   (150–200 words, see structure above)
□  Update timeline.json — add new period entry with is_fy_end: false
□  python3 analysis/run_evals.py --period {date} --skip-build
   (Checks 0, 0.5, 1, 1b only — should pass cleanly if extraction was clean)
□  python3 analysis/generate_merge.py
□  READ rbi_sibc/merged/system_model.json before starting Stage 5
   — confirm _meta.mode of current model, note node/edge count
□  Claude: merged UPDATE pass
   — update stats in existing nodes, add new nodes only for genuinely new signals
   — update annotation bodies, add new IDs only, never delete existing IDs
   — set _meta.mode = "update", bump _meta.last_updated
□  python3 analysis/run_evals.py --period merged --merged --skip-build
□  IF new nodes/edges were added: python3 analysis/generate_mermaid.py rbi_sibc/merged/system_model.json
□  python3 analysis/promote_annotations.py --dry-run   (verify no IDs removed)
□  python3 analysis/promote_annotations.py
□  python3 analysis/run_evals.py --period merged --merged   (full run with build)
□  Commit per-period outputs, then merged outputs, then web/ separately
□  git push
```

### FY-end period — FOUNDATION mode (~once/year, March file published April–May)

```
□  All steps above through generate_merge.py
□  READ rbi_sibc/merged/system_model.json — note last_foundation_date, record prior node count
□  Confirm: is this truly a March year-end file? (dataDate April–May, full fiscal year visible)
   If not certain, use UPDATE mode instead.
□  Claude: merged FOUNDATION pass
   — full rebuild of system_model.json from sections_merged.json
   — set _meta.mode = "foundation", _meta.last_foundation_date = dataDate
   — full rebuild of subsystems.json
   — full rewrite of annotations_merged.ts
□  python3 analysis/run_evals.py --period merged --merged --skip-build
□  python3 analysis/generate_mermaid.py rbi_sibc/merged/system_model.json   (always after FOUNDATION)
□  python3 analysis/promote_annotations.py --dry-run
   — REVIEW the ID diff carefully: any removed IDs must be explicitly justified
□  python3 analysis/promote_annotations.py
□  python3 analysis/run_evals.py --period merged --merged   (full run with build)
□  Update signal_registry.json — add history entries for any signals with new data
□  Commit per-period outputs, then merged outputs, then web/ separately
□  git push
```
