#!/usr/bin/env python3
"""
stamp_state.py — ship each dimension's standing state, precomputed.
────────────────────────────────────────────────────────────────────
The dashboard's state band (DASHBOARD_SPEC.md §16) reads a cut's Layer-1 speed and
its Layer-2 mix state. Neither has ever reached a browser: the mix state lives in
`system_state_{period}.json`, which is computed every ingestion, validated by both
gates, and never leaves `analysis/`.

The browser must not re-derive any of it (compute-once-ship-compact) — it would need
signals.db, the registry, the movement cut tables and the state file client-side. So
the SENTENCES are rendered here, in Python, and shipped as strings. That is not only
cheaper: it is what lets the gate trace every number in the band exactly the way it
traces every number in a card. A browser that formats numbers is a publishing surface
no validator can see.

A SIDECAR, like `stamp_planes.py`: the card artifacts are owned and freshness-guarded
by the insight generators, and this is derived from signals.db + the state file, so it
lives in its own regenerated file rather than as a parallel copy inside theirs.

    python3 analysis/signals/stamp_state.py --pipeline sibc          # write the sidecar
    python3 analysis/signals/stamp_state.py --pipeline sibc --check  # fail on drift
"""
import argparse
import json
import sqlite3
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import state_lines                                       # noqa: E402
from core.manifest import path as manifest_path                    # noqa: E402

DATA = ROOT / "web" / "public" / "data"
DB = ROOT / "analysis" / "signals" / "signals.db"
SIDECAR = {p: DATA / f"{p}_state.json" for p in ("sibc", "atm_pos")}


def _cuts(pipeline):
    """The pipeline's movement cut table + signal-id stem. Imported from the generator
    that already owns it — a second table here is the drift this project keeps paying for."""
    if pipeline == "sibc":
        from pipelines.sibc.generate_analysis_report import MOVEMENT_CUTS
        return MOVEMENT_CUTS, "sibc-"
    from pipelines.atm_pos.generate_atm_pos_insights import MOVEMENT_CUTS, MOVEMENT_PREFIX
    return MOVEMENT_CUTS, MOVEMENT_PREFIX


def latest_period(pipeline: str) -> str:
    """The newest period in signals.db — the period the dashboard is showing."""
    with sqlite3.connect(DB) as con:
        row = con.execute("SELECT MAX(period) FROM signals WHERE pipeline=?", (pipeline,)).fetchone()
    if not row or not row[0]:
        raise SystemExit(f"no signals.db rows for {pipeline}")
    return row[0]


def _mix_states(pipeline: str, period: str) -> dict:
    """The Layer-2 mix states for the period. A missing state file is LOUD, not an
    empty dict: an absent causal layer and a layer that computed nothing look identical
    downstream, and this project has paid for that confusion more than once."""
    # The merged dir is wherever the manifest says the system model lives — never a second
    # hardcoded path beside a declaration that already exists.
    f = manifest_path(pipeline, "system_model").parent / f"system_state_{period}.json"
    if not f.exists():
        raise SystemExit(f"no system state for {pipeline} {period} ({f}) — run the gate's S3 stage first")
    return json.loads(f.read_text()).get("mix_states", {})


def build(pipeline: str) -> dict:
    """The sidecar payload: dimension id → the ordered state blocks under it."""
    period = latest_period(pipeline)
    cuts, prefix = _cuts(pipeline)
    with sqlite3.connect(DB) as con:
        blocks = state_lines.blocks(con, pipeline, period, cuts, prefix,
                                    _mix_states(pipeline, period))
    by_dim: dict[str, list[dict]] = {}
    for b in blocks:
        by_dim.setdefault(b.dimension, []).append(b.as_dict())
    return {
        "_meta": {
            "pipeline": pipeline,
            "period": period,
            "purpose": "Standing state band per dashboard dimension — Layer-1 speed + Layer-2 "
                       "mix state, rendered as sentences. Join on dimension id.",
            "spec": "analysis/DASHBOARD_SPEC.md §16",
            "renderer": "analysis/core/state_lines.py",
        },
        "dimensions": by_dim,
    }


def write(pipeline: str) -> dict:
    payload = build(pipeline)
    SIDECAR[pipeline].write_text(json.dumps(payload, indent=1, ensure_ascii=False) + "\n")
    return payload


def check(pipeline: str):
    """True when the on-disk sidecar equals a fresh recompute. Compares the blocks and the
    period, so a doc comment can change without tripping it but a stale period cannot."""
    if not SIDECAR[pipeline].exists():
        return False, "sidecar missing — run without --check"
    on_disk = json.loads(SIDECAR[pipeline].read_text())
    fresh = build(pipeline)
    if on_disk.get("dimensions") == fresh["dimensions"] and \
       on_disk.get("_meta", {}).get("period") == fresh["_meta"]["period"]:
        return True, None
    drift = {k for k in set(on_disk.get("dimensions", {})) | set(fresh["dimensions"])
             if on_disk.get("dimensions", {}).get(k) != fresh["dimensions"].get(k)}
    if not drift:
        return False, (f"period moved {on_disk.get('_meta', {}).get('period')} "
                       f"→ {fresh['_meta']['period']}")
    return False, f"{len(drift)} dimension(s) drifted: {sorted(drift)}"


def main():
    ap = argparse.ArgumentParser(description="Precompute each dimension's standing state band")
    ap.add_argument("--pipeline", choices=list(SIDECAR), required=True)
    ap.add_argument("--check", action="store_true", help="fail on drift instead of writing")
    args = ap.parse_args()

    if args.check:
        ok, why = check(args.pipeline)
        print(f"state sidecar {'FRESH' if ok else 'STALE'}: {args.pipeline}"
              + (f" — {why}" if why else ""))
        return 0 if ok else 1

    payload = write(args.pipeline)
    n = sum(len(v) for v in payload["dimensions"].values())
    print(f"stamped {n} state block(s) over {len(payload['dimensions'])} "
          f"{args.pipeline} dimension(s) @ {payload['_meta']['period']} "
          f"→ {SIDECAR[args.pipeline].name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
