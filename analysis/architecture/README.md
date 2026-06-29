# `architecture/` — architecture-as-code (the docs can't lie)

Structural architecture facts are **derived from code**, not hand-maintained — a parallel
prose copy would drift, which is the exact anti-pattern the engineering principle forbids.

- **`discover.py`** — derive the architecture graph from code: AST import graph + subprocess
  gate call-graph + artifact read/write lineage. Scans `SCAN_DIRS` (core, guards, crosssource,
  pipelines/{sibc,atm_pos}, signals, …) → `graph.json`.
- **`render.py`** — `graph.json` → `ARCHITECTURE.generated.md` (data-flow diagram, gate
  call-graph, artifact lineage, dependency map, drift findings). Generated — never hand-edit.
- **`reconcile.py`** — the guard: every `*.py` / artifact path named in a living doc must exist
  on disk. **`--strict` runs as a gate stage** (`5. architecture reconcile`) in both pipelines;
  `guards/check_derived_fresh` re-runs discover+render so a stale committed doc fails too.

Regenerate: `python3 analysis/architecture/discover.py && python3 analysis/architecture/render.py`.
The hand-written rationale half is `ARCHITECTURE.md` (invariants, layer model, guard purposes),
which links to the generated half.
