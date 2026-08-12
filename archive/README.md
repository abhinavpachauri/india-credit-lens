# Archive

Files moved out of the live tree but deliberately **not deleted** — Risham reviews and deletes
at leisure. Nothing here is referenced by live code or living docs; `analysis/architecture/reconcile.py`
runs in both gates and is the guard that keeps it that way.

Layout mirrors the original paths, so anything can be restored with a `git mv` back.

## 2026-08-11 — refactor cycle cleanup

| What | Why | Where its content went |
|---|---|---|
| `ICL_RETAIL_90DAY_PLAN.md` | Mixed three concerns in one document | Strategy/pricing/gates → `STRATEGY_PLANNER.md` §17 · content mechanics → `DISTRIBUTION_SPEC.md` §15 · engineering notes EN-1/EN-2/EN-4 → `PLAN_2026-08-11.md` Part 2 |
| `web/components/` × 11 | Zero importers. Nine had none at all; `CytoscapeGraph` and `SubstackCTA` were imported only by the dead ones | — |
| `web/lib/system_model_data.ts` | Fed only the above | — |
| `cytoscape`, `cytoscape-dagre`, `@types/cytoscape` | Dependencies of an unrouted feature | Removed from `web/package.json` |
| `analysis/newsletter_v1/` | Retired 2026-07-04; no decision pending | Superseded by `analysis/distribution/` |
| `analysis/rebuild_{sibc,atm_pos}_signals.py` | Superseded by `generate_signal_history append`; in neither the live set nor `legacy/` | — |
| `docs/HANDOFF_*.md` × 4, `docs/FABLE_BRIEF_*.md` | Finished-work snapshots; their live content is already in CLAUDE.md and the specs | — |
| `raw_inputs/*.xlsx` | Byte-identical duplicates of the copies already in their period directories | The period copies are the originals |
| `trading_system.db` | Belongs to no pipeline in this project | — |

**Note on `SystemView` + `CytoscapeGraph`.** That is a whole causal-graph visualisation feature,
not stray code — it was simply never routed. Archiving it is a statement that it is not in use,
not that it was worthless: the v4.0 system model would now feed it far better data than existed
when it was written. Restoring it is a `git mv` and a route.
