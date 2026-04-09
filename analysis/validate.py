#!/usr/bin/env python3
"""
validate.py — India Credit Lens
---------------------------------
Validates system_model.json before any diagram or content generation.
Enforces correctness at the data layer so diagrams never claim more
than the underlying analysis supports.

Checks:
  1. Schema          — required fields present on nodes, edges, _meta
  2. Valid values    — tier and edge type are from allowed sets
  3. Referential integrity — all edge from/to IDs exist as nodes
  4. Annotation IDs  — all annotation_ids exist in the annotations file
  5. Data ranges     — growth rates parseable and within credible bounds
  6. Completeness    — model has minimum required tiers and connectivity
  7. Diagram readiness — which nodes have data for each diagram type

Usage:
    python3 validate.py rbi_sibc_2026-02-27/system_model.json
    python3 validate.py rbi_sibc_2026-02-27/system_model.json \\
        --annotations ../web/lib/reports/rbi_sibc.ts
    python3 validate.py rbi_sibc_2026-02-27/system_model.json \\
        --output output/mermaid/rbi_sibc_2026-04-09

Exit codes:
    0 = passed (errors=0; warnings are non-blocking)
    1 = failed (one or more critical errors)
"""

import json
import os
import re
import sys
import argparse
from pathlib import Path
from datetime import date


# ── Constants ─────────────────────────────────────────────────────────────────

VALID_TIERS = {"driver", "sector", "gap", "opportunity", "pressure"}

VALID_EDGE_TYPES = {
    "causes", "suppresses", "reroutes_demand_to", "reinforces",
    "creates_risk", "creates_opportunity", "is_data_gap", "creates_gap",
    "signals", "contrast",
}

GROWTH_RATE_MIN = -100.0
GROWTH_RATE_MAX = 500.0


# ── Helpers ───────────────────────────────────────────────────────────────────

def parse_growth_pct(stat_str):
    """Extract first numeric growth rate from a stat string.
    '+128.8% YoY' → 128.8 | '-4.0% YoY' → -4.0 | None → None
    """
    if not stat_str:
        return None
    m = re.search(r"([+-]?\d+\.?\d*)\s*%", stat_str)
    return float(m.group(1)) if m else None


def real_nodes(model):
    # The JSON uses _comment as an inline field on the first item of each group.
    # A real node always has an "id" field.
    return [n for n in model.get("nodes", []) if "id" in n]


def real_edges(model):
    # A real edge always has a "from" field.
    return [e for e in model.get("edges", []) if "from" in e]


def extract_annotation_ids(ts_path):
    """Parse annotation IDs from a TypeScript annotations file.
    Looks for:  id: "some-annotation-id"
    """
    try:
        with open(ts_path) as f:
            content = f.read()
        ids = re.findall(r'id:\s*"([^"]+)"', content)
        return set(ids)
    except FileNotFoundError:
        return None


# ── Result collector ──────────────────────────────────────────────────────────

class ValidationResult:
    def __init__(self):
        self.errors   = []
        self.warnings = []
        self.info     = []

    def error(self, check, msg):
        self.errors.append({"check": check, "level": "ERROR", "message": msg})

    def warn(self, check, msg):
        self.warnings.append({"check": check, "level": "WARNING", "message": msg})

    def note(self, check, msg):
        self.info.append({"check": check, "level": "INFO", "message": msg})

    @property
    def passed(self):
        return len(self.errors) == 0


# ── Check 1: Schema ───────────────────────────────────────────────────────────

def check_schema(model, result):
    meta = model.get("_meta", {})
    for field in ["report_id", "period", "total_credit_lcr", "yoy_growth_pct"]:
        if field not in meta:
            result.error("schema", f"_meta missing required field: '{field}'")

    if "nodes" not in model or not isinstance(model["nodes"], list):
        result.error("schema", "model must have a 'nodes' array")
        return

    if "edges" not in model or not isinstance(model["edges"], list):
        result.error("schema", "model must have an 'edges' array")
        return

    for i, node in enumerate(real_nodes(model)):
        for field in ["id", "tier", "label"]:
            if field not in node:
                result.error("schema", f"Node[{i}] '{node.get('id','?')}' missing required field: '{field}'")

    for i, edge in enumerate(real_edges(model)):
        for field in ["from", "to", "type", "label"]:
            if field not in edge:
                result.error("schema", f"Edge[{i}] missing required field: '{field}'")


# ── Check 2: Valid values ─────────────────────────────────────────────────────

def check_valid_values(model, result):
    for node in real_nodes(model):
        tier = node.get("tier")
        if tier and tier not in VALID_TIERS:
            result.error(
                "valid_values",
                f"Node '{node['id']}' has invalid tier '{tier}'. "
                f"Must be one of: {sorted(VALID_TIERS)}",
            )

    for edge in real_edges(model):
        etype = edge.get("type")
        if etype and etype not in VALID_EDGE_TYPES:
            result.error(
                "valid_values",
                f"Edge '{edge.get('from')}' → '{edge.get('to')}' "
                f"has invalid type '{etype}'. "
                f"Must be one of: {sorted(VALID_EDGE_TYPES)}",
            )


# ── Check 3: Referential integrity ────────────────────────────────────────────

def check_referential_integrity(model, result):
    node_ids = {n["id"] for n in real_nodes(model)}
    for edge in real_edges(model):
        src = edge.get("from")
        dst = edge.get("to")
        if src and src not in node_ids:
            result.error("referential_integrity", f"Edge 'from' '{src}' — node does not exist")
        if dst and dst not in node_ids:
            result.error("referential_integrity", f"Edge 'to' '{dst}' — node does not exist")


# ── Check 4: Annotation IDs ───────────────────────────────────────────────────

def check_annotation_ids(model, known_ids, result):
    if known_ids is None:
        result.warn(
            "annotation_ids",
            "Annotations file not found — skipping annotation ID cross-check. "
            "Pass --annotations path/to/report.ts to enable this check.",
        )
        return

    for node in real_nodes(model):
        aids = node.get("annotation_ids", [])
        if not aids:
            result.warn(
                "annotation_ids",
                f"Node '{node['id']}' has no annotation_ids — "
                "this node's claims are unsourced and will not be auditable.",
            )
        for aid in aids:
            if aid not in known_ids:
                result.error(
                    "annotation_ids",
                    f"Node '{node['id']}' references unknown annotation_id '{aid}'. "
                    "Either the annotation was removed or the ID was mistyped.",
                )


# ── Check 5: Data ranges ──────────────────────────────────────────────────────

def check_data_ranges(model, result):
    meta        = model.get("_meta", {})
    total_credit = meta.get("total_credit_lcr")

    for node in real_nodes(model):
        nid = node["id"]

        # value_lcr sanity
        vcr = node.get("value_lcr")
        if vcr is not None:
            if vcr <= 0:
                result.error("data_ranges", f"Node '{nid}' has non-positive value_lcr: {vcr}")
            if total_credit and vcr > total_credit * 1.05:
                result.error(
                    "data_ranges",
                    f"Node '{nid}' value_lcr {vcr} exceeds total credit {total_credit} — "
                    "sector credit cannot exceed system total.",
                )

        # Growth rate sanity
        stat = node.get("stat")
        if stat:
            pct = parse_growth_pct(stat)
            if pct is not None:
                if pct < GROWTH_RATE_MIN:
                    result.warn(
                        "data_ranges",
                        f"Node '{nid}' growth {pct}% is below {GROWTH_RATE_MIN}% — "
                        "verify this is not a data series break (e.g. reclassification).",
                    )
                if pct > GROWTH_RATE_MAX:
                    result.warn(
                        "data_ranges",
                        f"Node '{nid}' growth {pct}% exceeds {GROWTH_RATE_MAX}% — "
                        "verify this is not a base-effect artifact.",
                    )


# ── Check 6: Completeness and connectivity ────────────────────────────────────

def check_completeness(model, result):
    nodes  = real_nodes(model)
    edges  = real_edges(model)

    by_tier = {}
    for node in nodes:
        by_tier.setdefault(node.get("tier"), []).append(node)

    # Minimum tiers required
    for required_tier in ["driver", "sector", "opportunity"]:
        if not by_tier.get(required_tier):
            result.error(
                "completeness",
                f"Model has no '{required_tier}' nodes — "
                "a valid system model requires at least drivers, sectors, and opportunities.",
            )

    outbound_ids = {e["from"] for e in edges}
    inbound_ids  = {e["to"]   for e in edges}

    # Drivers must have outbound edges
    for node in by_tier.get("driver", []):
        if node["id"] not in outbound_ids:
            result.warn(
                "completeness",
                f"Driver node '{node['id']}' has no outbound edges — "
                "causal chain is disconnected. Add at least one edge from this driver.",
            )

    # Opportunities must have inbound edges
    for node in by_tier.get("opportunity", []):
        if node["id"] not in inbound_ids:
            result.warn(
                "completeness",
                f"Opportunity node '{node['id']}' has no inbound edges — "
                "its origin is unexplained. Add a creates_opportunity edge leading to it.",
            )

    # Pressure nodes must have creates_risk inbound edges
    risk_targets = {e["to"] for e in edges if e.get("type") == "creates_risk"}
    for node in by_tier.get("pressure", []):
        if node["id"] not in risk_targets:
            result.warn(
                "completeness",
                f"Pressure node '{node['id']}' has no 'creates_risk' inbound edge — "
                "risk is flagged but origin is not modelled.",
            )

    # Gap nodes must have is_data_gap or creates_gap inbound edges
    gap_edge_targets = {
        e["to"] for e in edges
        if e.get("type") in ("is_data_gap", "creates_gap")
    }
    for node in by_tier.get("gap", []):
        if node["id"] not in gap_edge_targets:
            result.warn(
                "completeness",
                f"Gap node '{node['id']}' has no 'is_data_gap' or 'creates_gap' inbound edge — "
                "data gap is flagged but its source is not modelled.",
            )


# ── Check 7: Diagram readiness ────────────────────────────────────────────────

def check_diagram_readiness(model, result):
    sector_nodes = [n for n in real_nodes(model) if n.get("tier") == "sector"]

    quadrant_ready   = []
    quadrant_missing = []
    sankey_ready     = []
    sankey_missing   = []

    for node in sector_nodes:
        nid        = node["id"]
        has_volume = node.get("value_lcr") is not None
        has_growth = parse_growth_pct(node.get("stat")) is not None

        if has_volume and has_growth:
            quadrant_ready.append(nid)
        else:
            missing = []
            if not has_volume: missing.append("value_lcr")
            if not has_growth: missing.append("parseable stat")
            quadrant_missing.append(f"{nid} (missing: {', '.join(missing)})")

        if has_volume:
            sankey_ready.append(nid)
        else:
            sankey_missing.append(nid)

    result.note(
        "diagram_readiness",
        f"Flowchart   : all {len(sector_nodes)} sector nodes renderable (no extra data needed)",
    )
    result.note(
        "diagram_readiness",
        f"Quadrant    : {len(quadrant_ready)} sectors plottable"
        + (f", {len(quadrant_missing)} excluded" if quadrant_missing else ""),
    )
    if quadrant_missing:
        result.note("diagram_readiness", f"  Excluded from quadrant: {'; '.join(quadrant_missing)}")

    result.note(
        "diagram_readiness",
        f"Sankey      : {len(sankey_ready)} sectors plottable"
        + (f", {len(sankey_missing)} excluded (no value_lcr)" if sankey_missing else ""),
    )

    if len(quadrant_ready) < 3:
        result.warn(
            "diagram_readiness",
            "Fewer than 3 sectors have both volume and growth data — "
            "quadrant chart will be sparse. Add value_lcr to more sector nodes.",
        )


# ── Orchestrator ──────────────────────────────────────────────────────────────

def validate(model_path, annotations_path=None):
    """Run all validation checks. Returns (ValidationResult, model dict)."""
    with open(model_path) as f:
        model = json.load(f)

    # Auto-detect annotations file from report_id
    if not annotations_path:
        report_id  = model.get("_meta", {}).get("report_id", "")
        base       = Path(model_path).resolve().parent.parent  # analysis/
        candidates = [
            base.parent / "web" / "lib" / "reports" / f"{report_id}.ts",
        ]
        for c in candidates:
            if c.exists():
                annotations_path = str(c)
                break

    known_ids = extract_annotation_ids(annotations_path) if annotations_path else None

    result = ValidationResult()

    checks = [
        ("Schema",                check_schema),
        ("Valid values",          check_valid_values),
        ("Referential integrity", check_referential_integrity),
        ("Annotation IDs",        lambda m, r: check_annotation_ids(m, known_ids, r)),
        ("Data ranges",           check_data_ranges),
        ("Completeness",          check_completeness),
        ("Diagram readiness",     check_diagram_readiness),
    ]

    for name, fn in checks:
        fn(model, result)

    return result, model


# ── Output ────────────────────────────────────────────────────────────────────

def print_report(result, model_path):
    w = 64
    print(f"\n{'═' * w}")
    print(f"  India Credit Lens — Validation Report")
    print(f"  Model : {model_path}")
    print(f"{'═' * w}")

    if result.errors:
        print(f"\n  ❌  ERRORS ({len(result.errors)}) — generation blocked\n")
        for e in result.errors:
            print(f"     [{e['check']}] {e['message']}")

    if result.warnings:
        print(f"\n  ⚠️   WARNINGS ({len(result.warnings)})\n")
        for w_ in result.warnings:
            print(f"     [{w_['check']}] {w_['message']}")

    if result.info:
        print(f"\n  ℹ️   DIAGRAM READINESS\n")
        for i in result.info:
            print(f"     {i['message']}")

    print(f"\n{'═' * w}")
    if result.passed:
        print(f"  ✅  PASSED — {len(result.warnings)} warning(s), ready to generate")
    else:
        print(f"  ❌  FAILED — {len(result.errors)} error(s) must be resolved")
    print(f"{'═' * w}\n")


def write_report(result, model_path, output_dir):
    os.makedirs(output_dir, exist_ok=True)
    out_path = os.path.join(output_dir, "validation_report.json")
    payload  = {
        "passed":     result.passed,
        "model_path": str(model_path),
        "generated":  str(date.today()),
        "summary": {
            "errors":   len(result.errors),
            "warnings": len(result.warnings),
            "info":     len(result.info),
        },
        "errors":   result.errors,
        "warnings": result.warnings,
        "info":     result.info,
    }
    with open(out_path, "w") as f:
        json.dump(payload, f, indent=2)
    return out_path


# ── CLI ───────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Validate system_model.json")
    parser.add_argument("model",         help="Path to system_model.json")
    parser.add_argument("--annotations", help="Path to annotations .ts file (auto-detected if omitted)")
    parser.add_argument("--output",      help="Directory to write validation_report.json")
    args = parser.parse_args()

    result, _ = validate(args.model, args.annotations)
    print_report(result, args.model)

    if args.output:
        out = write_report(result, args.model, args.output)
        print(f"  Report written: {out}\n")

    sys.exit(0 if result.passed else 1)
