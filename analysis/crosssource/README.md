# `crosssource/` — Layer 2b cross-pipeline composition

The **federated** composition layer: each pipeline maps its entities to the shared ontology
hub (`analysis/ontology/{concepts,channels}.json`) once; cross-system edges are *derived* and
*projected*, never authored as a monolith. Runs after the per-pipeline S3 each ingestion.

- **`derive_cross_links.py`** — derive cross-system candidate edges through shared concepts
  (stock↔flow + shared-channel) → `cross_source/candidates.json`.
- **`compose_ecosystem.py`** — project the combined ecosystem state from both pipelines'
  system_state + confirmed cross-edges (`cross_source/composition.json`).
- **`validate_composition.py`** — enforce the no-monolith rule on cross-edges.
- **`generate_opportunities_feed.py`** — build `web/public/data/opportunities_feed.json`
  (single source for the `/opportunities` page AND the per-section teasers on both dashboards).
- **`generate_opportunity_narrative.py`** — plain-English, numbers-grounded copy for each
  opportunity (post-gate, cached; preserved across regen).

Spec: `analysis/COMPOSITION_SPEC.md`.
