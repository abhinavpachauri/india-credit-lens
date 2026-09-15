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
    """The pipeline's movement cut table, signal-id stem, and its rate-only dimensions.
    Imported from the generator that already owns them — a second table here is the drift this
    project keeps paying for."""
    if pipeline == "sibc":
        from pipelines.sibc.generate_analysis_report import MOVEMENT_CUTS, STATE_RATE_ONLY
        return MOVEMENT_CUTS, "sibc-", STATE_RATE_ONLY
    from pipelines.atm_pos.generate_atm_pos_insights import MOVEMENT_CUTS, MOVEMENT_PREFIX
    # Every payments dimension decomposes by bank category, so none is rate-only.
    return MOVEMENT_CUTS, MOVEMENT_PREFIX, []


REGISTRY = ROOT / "analysis" / "signals" / "registry.json"


def _registry() -> dict:
    return json.loads(REGISTRY.read_text())["signals"]


def _label(metric: str) -> str:
    """A payments metric, as a reader says it. Built from the metric's own parts rather than
    a second lookup table: the parts are what the metric IS."""
    t = metric.replace("cc_", "Credit card ").replace("dc_", "Debit card ")
    t = (t.replace("_txn_val", " spend value").replace("_txn_vol", " transactions")
          .replace("_withdrawal_val", " withdrawal value").replace("_withdrawal_vol", " withdrawals"))
    t = (t.replace("_", " ").replace("pos", "POS").replace("atm", "ATM")
          .replace("ecom", "eCommerce").replace("qr", "QR").replace("upi", "UPI"))
    return t[0].upper() + t[1:]


def derived_cuts(pipeline: str, declared, mix_states: dict):
    """The cuts that have a state to show and no row in the generator's table.

    THE BAND'S POPULATION IS NOW DERIVED. It was `MOVEMENT_CUTS` — a hand-written list of
    seven SIBC cuts and three payments ones — sitting beside a table layer that discovers its
    forty cuts from the registry. So Layer 2 computed forty mix states every ingestion and ten
    reached a browser, which is the same defect this arc opened with, one level down: a check
    or a surface whose population is a list is a surface that silently omits.

    A cut qualifies by having a mix state. What it needs to SPEAK is a parent rate, and the
    two pipelines hold that in different shapes — payments measures have their own total-YoY
    aggregate, a SIBC sub-cut's parent is one ROW of its parent table's scan — so both are
    resolved here from the registry rather than declared twice.
    """
    from core.movement_cards import MovementCut
    reg = _registry()
    known = {f"{c.slug}" for c in declared}
    out = []

    if pipeline == "atm_pos":
        # metric -> its total-YoY signal, the rate that speaks for the whole measure.
        yoy = {(s.get("compute") or {}).get("metric"): sid for sid, s in reg.items()
               if s.get("pipeline") == "atm_pos"
               and (s.get("compute") or {}).get("method") in ("csv_total_yoy", "csv_sum_yoy")}
        for sid, sig in reg.items():
            c = sig.get("compute") or {}
            if c.get("method") != "csv_category_momentum" or f"{sid[:-len('-momentum')]}" == "":
                continue
            stem = sid[: -len("-momentum")]
            metric = c.get("metric")
            group = "cc" if metric.startswith("cc_") else "dc" if metric.startswith("dc_") else "infra"
            slug = stem[len(MOVEMENT_PREFIX_FOR[group]):] if stem.startswith(MOVEMENT_PREFIX_FOR[group]) else stem
            if slug in known or sid not in mix_states:
                continue
            out.append(MovementCut(slug=slug, section=group, speed=f"{stem}-yoy-scan",
                                   subject=_label(metric), stem_full=stem,
                                   parent_yoy=yoy.get(metric), parent_label=_label(metric),
                                   no_mix_note="no mix computed for this measure"))
        return out

    # SIBC: a sub-cut hangs off a ROW of its parent cut's table (§19). Its dimension is the
    # parent's dimension, and its parent rate is that row inside the parent's YoY scan.
    parents = {(str((c.get("compute") or {}).get("parent_code")),
                (c.get("compute") or {}).get("statement")): sid[: -len("-momentum")]
               for sid, c in ((k, v) for k, v in reg.items())
               if (c.get("compute") or {}).get("method") == "csv_sector_momentum"
               for c in [c]}
    section_of = {c.slug: c.section for c in declared}
    import pandas as pd
    from core.manifest import consolidated_csv
    df = pd.read_csv(consolidated_csv("sibc"))
    for sid, sig in reg.items():
        c = sig.get("compute") or {}
        if c.get("method") != "csv_sector_momentum" or c.get("child_level") != 3:
            continue
        stem = sid[: -len("-momentum")]
        slug = stem[len("sibc-"):]
        if slug in known or sid not in mix_states:
            continue
        code, stmt = str(c.get("parent_code")), c.get("statement")
        grandparent = code.rsplit(".", 1)[0]
        parent_stem = parents.get((grandparent, stmt))
        rows = df[(df["code"].astype(str) == code) & (df["statement"] == stmt)]["sector"]
        if parent_stem is None or not len(rows):
            continue            # a sub-cut whose parent table we cannot name says nothing
        entity = rows.iloc[0]
        # RBI's parenthetical qualifiers are for a spreadsheet, not a sentence: the band
        # already trims them on the mix line's destination, so the speed line's subject uses
        # the same trim rather than a second idea of what a sector is called.
        label = state_lines._short(entity)
        out.append(MovementCut(
            slug=slug, section=section_of.get(parent_stem[len("sibc-"):], ""),
            speed=f"{stem}-yoy-scan", subject=label, stem_full=stem,
            parent_yoy=f"{parent_stem}-yoy-scan", parent_label=f"{label} credit",
            parent_entity=entity,
            no_mix_note="no mix computed for this cut"))
    return [c for c in out if c.section]


MOVEMENT_PREFIX_FOR = {"cc": "cc-", "dc": "dc-", "infra": "pos-"}


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
    cuts, prefix, rate_only = _cuts(pipeline)
    mix = _mix_states(pipeline, period)
    extra = derived_cuts(pipeline, cuts, mix)
    if isinstance(prefix, dict):
        prefix = {**prefix}          # derived payments cuts share their group's prefix
    with sqlite3.connect(DB) as con:
        blocks = state_lines.blocks(con, pipeline, period, [*cuts, *extra], prefix, mix,
                                    rate_only, anchors=cuts)
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
