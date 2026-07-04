# Architecture (generated)

> ⚠ **GENERATED — do not edit by hand.** Source of truth is the code, via
> `analysis/architecture/discover.py`. Regenerate:
> ```
> python3 analysis/architecture/discover.py && python3 analysis/architecture/render.py
> ```
> Authored rationale (layer model, design principles, guard purposes) lives in the
> hand-written `ARCHITECTURE.md`. This file is the structural, drift-guarded half.

_Derived from 57 scripts._

## 1. Data-flow

Artifact dependency DAG — nodes are artifacts, each edge is the script that
transforms one into the next. Derived from read/write analysis of the code.

```mermaid
flowchart LR
  n_analysis_COMPOSITION_SPEC_md(["COMPOSITION_SPEC.md"])
  n_analysis_SYSTEM_MODEL_SPEC_md(["SYSTEM_MODEL_SPEC.md"])
  n_analysis_cross_source_candidates_json["candidates.json"]
  n_analysis_cross_source_ecosystem_model_json(["ecosystem_model.json"])
  n_analysis_ontology_channels_json(["channels.json"])
  n_analysis_rbi_atm_pos_insights_json["insights.json"]
  n_analysis_rbi_atm_pos_merged_system_model_json["system_model.json"]
  n_analysis_rbi_atm_pos_signals_json["signals.json"]
  n_analysis_rbi_atm_pos_skeleton_profile_json(["skeleton_profile.json"])
  n_analysis_rbi_sibc_merged_system_model_json["system_model.json"]
  n_analysis_rbi_sibc_skeleton_profile_json(["skeleton_profile.json"])
  n_analysis_signals_narrative_cache_json["narrative_cache.json"]
  n_analysis_signals_registry_json["registry.json"]
  n_analysis_signals_signals_db["signals.db"]
  n_web_public_data_atm_pos_chart_series_json["atm_pos_chart_series.json"]
  n_web_public_data_atm_pos_consolidated_csv["atm_pos_consolidated.csv"]
  n_web_public_data_atm_pos_insights_json(["atm_pos_insights.json"])
  n_web_public_data_atm_pos_signals_json(["atm_pos_signals.json"])
  n_web_public_data_opportunities_feed_json["opportunities_feed.json"]
  n_web_public_data_sibc_l1_annotations_json["sibc_l1_annotations.json"]
  n_analysis_COMPOSITION_SPEC_md -->|derive_cross_links| n_analysis_cross_source_candidates_json
  n_analysis_SYSTEM_MODEL_SPEC_md -->|generate_skeleton| n_analysis_rbi_atm_pos_merged_system_model_json
  n_analysis_SYSTEM_MODEL_SPEC_md -->|generate_skeleton| n_analysis_rbi_sibc_merged_system_model_json
  n_analysis_cross_source_ecosystem_model_json -->|generate_opportunities_feed| n_web_public_data_opportunities_feed_json
  n_analysis_ontology_channels_json -->|derive_cross_links| n_analysis_cross_source_candidates_json
  n_analysis_ontology_channels_json -->|generate_opportunities_feed| n_web_public_data_opportunities_feed_json
  n_analysis_rbi_atm_pos_signals_json -->|generate_atm_pos_insights| n_analysis_rbi_atm_pos_insights_json
  n_analysis_rbi_atm_pos_skeleton_profile_json -->|generate_skeleton| n_analysis_rbi_atm_pos_merged_system_model_json
  n_analysis_rbi_atm_pos_skeleton_profile_json -->|generate_skeleton| n_analysis_rbi_sibc_merged_system_model_json
  n_analysis_rbi_sibc_skeleton_profile_json -->|generate_skeleton| n_analysis_rbi_atm_pos_merged_system_model_json
  n_analysis_rbi_sibc_skeleton_profile_json -->|generate_skeleton| n_analysis_rbi_sibc_merged_system_model_json
  n_analysis_signals_registry_json -->|compute_atm_pos_signals| n_analysis_rbi_atm_pos_signals_json
  n_analysis_signals_registry_json -->|generate_opportunities_feed| n_web_public_data_opportunities_feed_json
  n_analysis_signals_registry_json -->|generate_analysis_report| n_web_public_data_sibc_l1_annotations_json
  n_analysis_signals_signals_db -->|compute_atm_pos_signals| n_analysis_rbi_atm_pos_signals_json
  n_analysis_signals_signals_db -->|generate_opportunity_narrative| n_analysis_signals_narrative_cache_json
  n_analysis_signals_signals_db -->|generate_opportunities_feed| n_web_public_data_opportunities_feed_json
  n_analysis_signals_signals_db -->|generate_opportunity_narrative| n_web_public_data_opportunities_feed_json
  n_analysis_signals_signals_db -->|generate_analysis_report| n_web_public_data_sibc_l1_annotations_json
  n_web_public_data_atm_pos_consolidated_csv -->|compute_atm_pos_signals| n_analysis_rbi_atm_pos_signals_json
  n_web_public_data_atm_pos_consolidated_csv -->|generate_chart_series| n_web_public_data_atm_pos_chart_series_json
  n_web_public_data_atm_pos_insights_json -->|generate_atm_pos_insights| n_analysis_rbi_atm_pos_insights_json
  n_web_public_data_atm_pos_signals_json -->|compute_atm_pos_signals| n_analysis_rbi_atm_pos_signals_json
```

_Stadium nodes = external/authored inputs (no script writes them)._
_Edges are script-level: a script that reads A and writes B yields A→B, so a
script spanning both pipelines may show cross-pipeline edges. See §3 for the
exact per-artifact producer/consumer._

## 2. Gate call-graph

Scripts each orchestrator launches as a subprocess, in execution order.

### `hook_validate` → 3 steps
1. `pipelines/sibc/validate_annotations`
2. `core/validate_timeline`
3. `pipelines/sibc/validate_sections`

## 3. Artifact lineage

| Artifact | Kind | Producer(s) | Consumer(s) |
|---|---|---|---|
| `analysis/*/merged/system_state_*.json` | external/authored | — | `core/run_inference` |
| `analysis/COMPOSITION_SPEC.md` | external/authored | — | `crosssource/derive_cross_links` |
| `analysis/SYSTEM_MODEL_SPEC.md` | external/authored | — | `core/generate_skeleton` |
| `analysis/architecture/graph.json` | external/authored | — | `guards/check_derived_fresh` |
| `analysis/cross_source/candidates.json` | derived | `crosssource/derive_cross_links` | `core/run_inference`, `guards/check_derived_fresh` |
| `analysis/cross_source/composition.json` | external/authored | — | `core/run_inference`, `crosssource/compose_ecosystem`, `crosssource/validate_composition` |
| `analysis/cross_source/ecosystem_model.json` | external/authored | — | `crosssource/compose_ecosystem`, `crosssource/generate_opportunities_feed`, `crosssource/validate_composition` |
| `analysis/cross_source/ecosystem_state_*.json` | external/authored | — | `guards/check_derived_fresh` |
| `analysis/ontology/channels.json` | external/authored | — | `core/run_inference`, `core/validate_system_model`, `crosssource/derive_cross_links`, `crosssource/generate_opportunities_feed` |
| `analysis/ontology/concepts.json` | external/authored | — | `core/validate_system_model`, `crosssource/validate_composition` |
| `analysis/ontology/domains.json` | external/authored | — | `crosssource/validate_composition` |
| `analysis/rbi_atm_pos/insights.json` | derived | `pipelines/atm_pos/generate_atm_pos_insights` | `pipelines/atm_pos/validate_atm_pos_claims`, `pipelines/atm_pos/validate_atm_pos_insights` |
| `analysis/rbi_atm_pos/merged/opportunities_*.json` | external/authored | — | `guards/check_derived_fresh` |
| `analysis/rbi_atm_pos/merged/system_model.json` | derived | `core/generate_skeleton` | `guards/check_derived_fresh` |
| `analysis/rbi_atm_pos/merged/system_state_*.json` | external/authored | — | `guards/check_derived_fresh` |
| `analysis/rbi_atm_pos/signals.json` | derived | `pipelines/atm_pos/compute_atm_pos_signals` | `pipelines/atm_pos/generate_atm_pos_insights`, `pipelines/atm_pos/validate_atm_pos_claims`, `pipelines/atm_pos/validate_atm_pos_insights` |
| `analysis/rbi_atm_pos/skeleton_profile.json` | external/authored | — | `core/generate_skeleton` |
| `analysis/rbi_sibc/merged/annotations_merged.ts` | external/authored | — | `pipelines/sibc/validate_annotation_basis` |
| `analysis/rbi_sibc/merged/opportunities_*.json` | external/authored | — | `guards/check_derived_fresh` |
| `analysis/rbi_sibc/merged/sections_merged.json` | external/authored | — | `hook_validate`, `pipelines/sibc/detect_format`, `pipelines/sibc/generate_merge`, `pipelines/sibc/validate_content`, `pipelines/sibc/validate_web_series` |
| `analysis/rbi_sibc/merged/system_model.json` | derived | `core/generate_skeleton` | `guards/check_derived_fresh` |
| `analysis/rbi_sibc/merged/system_state_*.json` | external/authored | — | `guards/check_derived_fresh` |
| `analysis/rbi_sibc/skeleton_profile.json` | external/authored | — | `core/generate_skeleton` |
| `analysis/rbi_sibc/timeline.json` | external/authored | — | `core/validate_timeline`, `pipelines/sibc/generate_merge`, `signals/compute/sibc`, `signals/query` |
| `analysis/signals/narrative_cache.json` | derived | `crosssource/generate_opportunity_narrative` | — |
| `analysis/signals/registry.json` | derived | `signals/apply_status_rules`, `signals/rebuild_atm_pos_signals`, `signals/rebuild_sibc_signals`, `signals/update_registry` | `core/generate_signal_history`, `core/validate_opportunity_traceability`, `crosssource/generate_opportunities_feed`, `crosssource/validate_composition`, `guards/check_signal_freshness`, `guards/validate_signal_history`, `newsletter/newsletter_sources`, `pipelines/atm_pos/compute_atm_pos_signals`, `pipelines/atm_pos/validate_atm_pos_insights`, `pipelines/sibc/generate_analysis_report`, `pipelines/sibc/validate_sibc_traceability` |
| `analysis/signals/signals.db` | derived | `signals/db` | `core/derive_opportunities`, `core/gate`, `core/generate_system_state`, `core/validate_opportunity_traceability`, `crosssource/compose_ecosystem`, `crosssource/generate_opportunities_feed`, `crosssource/generate_opportunity_narrative`, `guards/check_derived_fresh`, `guards/validate_signal_history`, `newsletter/newsletter_sources`, `newsletter/validate_newsletter`, `pipelines/atm_pos/compute_atm_pos_signals`, `pipelines/atm_pos/validate_atm_pos_insights`, `pipelines/sibc/generate_analysis_report`, `pipelines/sibc/validate_sibc_traceability` |
| `web/lib/reports/rbi_sibc.ts` | derived | `pipelines/sibc/promote_annotations` | `hook_validate`, `pipelines/sibc/validate_annotation_basis`, `pipelines/sibc/validate_web_series` |
| `web/lib/reports/rbi_sibc_label_overrides.json` | external/authored | — | `pipelines/sibc/validate_web_series` |
| `web/public/data/atm_pos_chart_series.json` | derived | `core/generate_chart_series` | `guards/check_derived_fresh` |
| `web/public/data/atm_pos_consolidated.csv` | derived | `pipelines/atm_pos/consolidate_atm_pos` | `core/generate_chart_series`, `pipelines/atm_pos/compute_atm_pos_signals`, `signals/compute/atm_pos`, `signals/evaluate` |
| `web/public/data/atm_pos_insights.json` | external/authored | — | `newsletter/newsletter_sources`, `newsletter/validate_newsletter`, `pipelines/atm_pos/generate_atm_pos_insights` |
| `web/public/data/atm_pos_signals.json` | external/authored | — | `pipelines/atm_pos/compute_atm_pos_signals` |
| `web/public/data/opportunities_feed.json` | derived | `crosssource/generate_opportunities_feed`, `crosssource/generate_opportunity_narrative` | `core/validate_opportunity_traceability`, `guards/check_derived_fresh`, `newsletter/newsletter_sources`, `newsletter/validate_newsletter` |
| `web/public/data/rbi_sibc_consolidated.csv` | derived | `pipelines/sibc/update_web_data` | `pipelines/sibc/validate_web_series`, `signals/compute/sibc`, `signals/evaluate` |
| `web/public/data/sibc_l1_annotations.json` | derived | `pipelines/sibc/generate_analysis_report` | `newsletter/newsletter_sources`, `newsletter/validate_newsletter`, `pipelines/sibc/validate_sibc_traceability` |

## 4. Module-dependency map

Python import edges (sparse by design — the pipeline is subprocess-
orchestrated, not import-coupled).

- `core/derive_opportunities` → `core/generate_skeleton`
- `core/generate_system_state` → `core/generate_skeleton`
- `core/run_inference` → `core/generate_skeleton`
- `core/validate_system_model` → `core/generate_skeleton`
- `crosssource/compose_ecosystem` → `core/generate_skeleton`
- `crosssource/derive_cross_links` → `core/generate_skeleton`
- `crosssource/generate_opportunities_feed` → `core/generate_skeleton`
- `crosssource/generate_opportunity_narrative` → `core/generate_skeleton`
- `crosssource/validate_composition` → `core/generate_skeleton`
- `newsletter/generate_deep_read` → `newsletter/newsletter_render`, `newsletter/newsletter_sources`, `newsletter/validate_newsletter`
- `newsletter/generate_release_read` → `newsletter/newsletter_render`, `newsletter/newsletter_sources`, `newsletter/validate_newsletter`
- `newsletter/validate_newsletter` → `newsletter/newsletter_sources`
- `pipelines/atm_pos/extract_atm_pos` → `pipelines/atm_pos/detect_atm_pos_format`
- `pipelines/sibc/extract_sibc` → `pipelines/sibc/detect_format`
- `signals/compute/engine` → `signals/db`
- `signals/evaluate` → `signals/db`, `signals/query`
- `signals/migrate_to_db` → `signals/db`

## 5. Findings (drift signals)

### Multiple writers (verify intentional vs. dual-path smell)
- `analysis/signals/registry.json` ← `signals/apply_status_rules`, `signals/rebuild_atm_pos_signals`, `signals/rebuild_sibc_signals`, `signals/update_registry`
- `format_report.json` ← `pipelines/atm_pos/detect_atm_pos_format`, `pipelines/sibc/detect_format`
- `sections.json` ← `pipelines/atm_pos/extract_atm_pos`, `pipelines/sibc/extract_sibc`
- `web/public/data/opportunities_feed.json` ← `crosssource/generate_opportunities_feed`, `crosssource/generate_opportunity_narrative`

### Internal artifacts produced but never read (potential dead output)
- `analysis/signals/narrative_cache.json` ← `crosssource/generate_opportunity_narrative`
