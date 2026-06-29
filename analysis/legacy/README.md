# `legacy/` — frozen archive (retired, do not run)

Scripts superseded by the v4.0 system model + the single manifest-driven gate. Kept for
reference/history only. **They are FROZEN** — many reference pre-§4 module paths and will not
fully run. Do not wire anything here back into the gate; if you need their behaviour, it lives
in the current engines.

| Archived | Superseded by |
|---|---|
| `run_evals.py`, `run_atm_pos_evals.py` | `core/gate.py` (single manifest-driven gate, all modes) |
| `validate.py` (checks 4/5), `validate_claims.py`, `source_claims.py` | `core/validate_system_model.py` (sourcing built in) |
| `generate_mermaid.py` | retired (subsystem diagrams detached from the gate) |
| `build_behavioral_layer.py`, `migrate_forces_to_instances.py` | one-time v4.0 build helpers (done) |
| `generate_atm_pos_analysis_report.py` | Stage 4b (`pipelines/atm_pos/generate_atm_pos_insights.py`) — the no-op "Stage 5.5" |
| `generate_delta.py`, `backfill_sibc_basis.py` | one-off / orphan tools |

Not scanned by the architecture discoverer; mentions of these names in docs resolve by basename.
