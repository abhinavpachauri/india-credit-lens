"""generate_delta.py — Diff two system_model.json files and produce a delta_model.json.

Captures both stat changes and structural changes (nodes, edges, subsystems).
Output is written to the report type's deltas/ directory and registered in timeline.json.

Usage:
    python3 generate_delta.py rbi_sibc/2026-02-27/system_model.json rbi_sibc/2026-05-15/system_model.json

Output:
    rbi_sibc/deltas/2026-02-27_to_2026-05-15.json
    rbi_sibc/timeline.json  (deltas[] entry appended)
"""

import json
import os
import re
import sys
from pathlib import Path


# ── Helpers ───────────────────────────────────────────────────────────────────

def load_model(path):
    with open(path) as f:
        return json.load(f)

def real_nodes(model):
    return [n for n in model.get("nodes", []) if not n.get("_comment")]

def real_edges(model):
    return [e for e in model.get("edges", []) if not e.get("_comment")]

def stat_magnitude(stat_str):
    """Extract absolute numeric value from stat string like '+128.8% YoY'."""
    m = re.search(r"[-+]?\d+\.?\d*", stat_str or "")
    return abs(float(m.group())) if m else 0.0

def stat_direction(prev_str, curr_str):
    """Classify how a stat changed between two periods."""
    prev = stat_magnitude(prev_str)
    curr = stat_magnitude(curr_str)
    # Sign change (positive ↔ negative growth)
    prev_sign = "-" in (prev_str or "") and not prev_str.startswith("+")
    curr_sign = "-" in (curr_str or "") and not curr_str.startswith("+")
    if prev_sign != curr_sign:
        return "reversing"
    if curr > prev * 1.10:
        return "accelerating"
    if curr < prev * 0.90:
        return "decelerating"
    return "stable"

def stat_magnitude_label(prev_str, curr_str):
    prev = stat_magnitude(prev_str)
    curr = stat_magnitude(curr_str)
    diff = abs(curr - prev)
    if diff > 20:
        return "large"
    if diff > 5:
        return "moderate"
    return "small"


# ── Node diff ─────────────────────────────────────────────────────────────────

def diff_nodes(prev_nodes, curr_nodes):
    prev_map = {n["id"]: n for n in prev_nodes}
    curr_map = {n["id"]: n for n in curr_nodes}

    added   = [curr_map[i] for i in curr_map if i not in prev_map]
    removed = [prev_map[i] for i in prev_map if i not in curr_map]

    tier_changed = []
    for nid in set(prev_map) & set(curr_map):
        p, c = prev_map[nid], curr_map[nid]
        if p.get("tier") != c.get("tier"):
            tier_changed.append({
                "id":         nid,
                "label":      c.get("label", nid),
                "prev_tier":  p.get("tier"),
                "curr_tier":  c.get("tier"),
            })

    return {
        "added":        [{"id": n["id"], "tier": n.get("tier"), "label": n.get("label")} for n in added],
        "removed":      [{"id": n["id"], "tier": n.get("tier"), "label": n.get("label")} for n in removed],
        "tier_changed": tier_changed,
    }


# ── Edge diff ─────────────────────────────────────────────────────────────────

def edge_key(e):
    return (e["from"], e["to"])

def diff_edges(prev_edges, curr_edges):
    prev_map = {edge_key(e): e for e in prev_edges}
    curr_map = {edge_key(e): e for e in curr_edges}

    added   = [curr_map[k] for k in curr_map if k not in prev_map]
    removed = [prev_map[k] for k in prev_map if k not in curr_map]

    type_changed = []
    for k in set(prev_map) & set(curr_map):
        p, c = prev_map[k], curr_map[k]
        if p.get("type") != c.get("type"):
            type_changed.append({
                "from":      k[0],
                "to":        k[1],
                "prev_type": p.get("type"),
                "curr_type": c.get("type"),
            })

    def edge_summary(e):
        return {"from": e["from"], "to": e["to"], "type": e.get("type")}

    return {
        "added":        [edge_summary(e) for e in added],
        "removed":      [edge_summary(e) for e in removed],
        "type_changed": type_changed,
    }


# ── Stat diff ─────────────────────────────────────────────────────────────────

def diff_stats(prev_nodes, curr_nodes):
    prev_map = {n["id"]: n for n in prev_nodes if n.get("tier") == "sector"}
    curr_map = {n["id"]: n for n in curr_nodes if n.get("tier") == "sector"}

    changes = []
    for nid in set(prev_map) & set(curr_map):
        p_stat = prev_map[nid].get("stat") or ""
        c_stat = curr_map[nid].get("stat") or ""
        if p_stat == c_stat:
            continue
        changes.append({
            "node_id":   nid,
            "label":     curr_map[nid].get("label", nid),
            "prev_stat": p_stat,
            "curr_stat": c_stat,
            "direction": stat_direction(p_stat, c_stat),
            "magnitude": stat_magnitude_label(p_stat, c_stat),
        })

    # Sort: reversing first, then by magnitude
    order = {"reversing": 0, "accelerating": 1, "decelerating": 2, "stable": 3}
    mag   = {"large": 0, "moderate": 1, "small": 2}
    changes.sort(key=lambda x: (order[x["direction"]], mag[x["magnitude"]]))
    return changes


# ── Subsystem diff ────────────────────────────────────────────────────────────

def derive_subsystem_fingerprints(model):
    """Return subsystem fingerprints: frozenset of (driver_ids, sector_ids) per subsystem."""
    from generate_mermaid import derive_subsystems
    subs = derive_subsystems(model)
    return {
        sub["id"]: {
            "label":   sub["label"],
            "drivers": frozenset(sub["drivers"]),
            "sectors": frozenset(sub["sectors"]),
        }
        for sub in subs
    }

def diff_subsystems(prev_model, curr_model):
    prev_subs = derive_subsystem_fingerprints(prev_model)
    curr_subs = derive_subsystem_fingerprints(curr_model)

    def fingerprint(sub):
        return (sub["drivers"], sub["sectors"])

    prev_fps = {sid: fingerprint(s) for sid, s in prev_subs.items()}
    curr_fps = {sid: fingerprint(s) for sid, s in curr_subs.items()}

    # Match by fingerprint overlap — exact or near match
    matched_prev = set()
    matched_curr = set()
    persisted    = []
    merged       = []   # N prev → 1 curr
    split        = []   # 1 prev → N curr

    for cid, (c_drv, c_sec) in curr_fps.items():
        matches = [
            pid for pid, (p_drv, p_sec) in prev_fps.items()
            if (p_drv & c_drv) or (p_sec & c_sec)
        ]
        if len(matches) == 1 and matches[0] not in matched_prev:
            persisted.append({
                "prev_id":    matches[0],
                "curr_id":    cid,
                "prev_label": prev_subs[matches[0]]["label"],
                "curr_label": curr_subs[cid]["label"],
                "label_changed": prev_subs[matches[0]]["label"] != curr_subs[cid]["label"],
            })
            matched_prev.add(matches[0])
            matched_curr.add(cid)
        elif len(matches) > 1:
            merged.append({
                "prev_ids":    matches,
                "prev_labels": [prev_subs[m]["label"] for m in matches],
                "curr_id":     cid,
                "curr_label":  curr_subs[cid]["label"],
            })
            matched_prev.update(matches)
            matched_curr.add(cid)

    # Check for splits: one prev matching multiple curr
    for pid in set(prev_fps) - matched_prev:
        p_drv, p_sec = prev_fps[pid]
        child_curr = [
            cid for cid, (c_drv, c_sec) in curr_fps.items()
            if cid not in matched_curr and ((p_drv & c_drv) or (p_sec & c_sec))
        ]
        if len(child_curr) > 1:
            split.append({
                "prev_id":     pid,
                "prev_label":  prev_subs[pid]["label"],
                "curr_ids":    child_curr,
                "curr_labels": [curr_subs[c]["label"] for c in child_curr],
            })
            matched_prev.add(pid)
            matched_curr.update(child_curr)

    emerged  = [{"id": cid, "label": curr_subs[cid]["label"]} for cid in curr_fps if cid not in matched_curr]
    dissolved = [{"id": pid, "label": prev_subs[pid]["label"]} for pid in prev_fps if pid not in matched_prev]

    return {
        "persisted": persisted,
        "emerged":   emerged,
        "dissolved": dissolved,
        "merged":    merged,
        "split":     split,
    }


# ── Timeline registration ─────────────────────────────────────────────────────

def register_delta(timeline_path, prev_date, curr_date, delta_path_relative):
    if not os.path.exists(timeline_path):
        print(f"  ⚠  timeline.json not found at {timeline_path} — skipping registration")
        return

    with open(timeline_path) as f:
        timeline = json.load(f)

    entry = {
        "from_date": prev_date,
        "to_date":   curr_date,
        "path":      delta_path_relative,
    }

    # Avoid duplicate entries
    existing = [(d["from_date"], d["to_date"]) for d in timeline.get("deltas", [])]
    if (prev_date, curr_date) not in existing:
        timeline.setdefault("deltas", []).append(entry)
        with open(timeline_path, "w") as f:
            json.dump(timeline, f, indent=2)
        print(f"  ✓  Registered in timeline.json")
    else:
        print(f"  ✓  Already registered in timeline.json")


# ── Entry point ───────────────────────────────────────────────────────────────

def generate_delta(prev_path_str, curr_path_str):
    prev_path = Path(prev_path_str).resolve()
    curr_path = Path(curr_path_str).resolve()

    print("\n" + "─" * 64)
    print("India Credit Lens — Delta Generator")
    print("─" * 64)

    prev_model = load_model(prev_path)
    curr_model = load_model(curr_path)

    prev_meta = prev_model.get("_meta", {})
    curr_meta = curr_model.get("_meta", {})

    prev_date = prev_meta.get("generated", "unknown")
    curr_date = curr_meta.get("generated", "unknown")
    report_id = curr_meta.get("report_id", "report")

    print(f"\n  From : {prev_meta.get('period', prev_date)} ({prev_date})")
    print(f"  To   : {curr_meta.get('period', curr_date)} ({curr_date})")
    print(f"  Type : {report_id}\n")

    # Run diffs
    prev_nodes = real_nodes(prev_model)
    curr_nodes = real_nodes(curr_model)
    prev_edges = real_edges(prev_model)
    curr_edges = real_edges(curr_model)

    print("  Diffing nodes...")
    node_changes = diff_nodes(prev_nodes, curr_nodes)

    print("  Diffing edges...")
    edge_changes = diff_edges(prev_edges, curr_edges)

    print("  Diffing stats...")
    stat_changes = diff_stats(prev_nodes, curr_nodes)

    print("  Diffing subsystems...")
    try:
        subsystem_changes = diff_subsystems(prev_model, curr_model)
    except Exception as e:
        print(f"  ⚠  Subsystem diff failed: {e}")
        subsystem_changes = {}

    delta = {
        "_meta": {
            "prev_period":  prev_meta.get("period"),
            "curr_period":  curr_meta.get("period"),
            "prev_date":    prev_date,
            "curr_date":    curr_date,
            "report_id":    report_id,
            "schema_version": "1.0",
        },
        "stat_changes":      stat_changes,
        "structural_changes": {
            "nodes": node_changes,
            "edges": edge_changes,
        },
        "subsystem_changes": subsystem_changes,
    }

    # Write output
    script_dir    = Path(__file__).parent
    deltas_dir    = script_dir / report_id / "deltas"
    deltas_dir.mkdir(parents=True, exist_ok=True)
    delta_filename = f"{prev_date}_to_{curr_date}.json"
    delta_out      = deltas_dir / delta_filename

    with open(delta_out, "w") as f:
        json.dump(delta, f, indent=2)

    print(f"\n  ✓  Delta written: {delta_out}")

    # Summary
    print("\n  ── Summary ──────────────────────────────────────────")
    print(f"  Stat changes    : {len(stat_changes)} sectors moved")
    print(f"  Node changes    : +{len(node_changes['added'])} added  -{len(node_changes['removed'])} removed  {len(node_changes['tier_changed'])} tier-changed")
    print(f"  Edge changes    : +{len(edge_changes['added'])} added  -{len(edge_changes['removed'])} removed  {len(edge_changes['type_changed'])} type-changed")
    if subsystem_changes:
        print(f"  Subsystems      : {len(subsystem_changes.get('persisted', []))} persisted  {len(subsystem_changes.get('emerged', []))} emerged  {len(subsystem_changes.get('dissolved', []))} dissolved")
    print()

    # Register in timeline.json
    timeline_path = script_dir / report_id / "timeline.json"
    register_delta(str(timeline_path), prev_date, curr_date, f"deltas/{delta_filename}")

    print("─" * 64 + "\n")
    return delta


if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 generate_delta.py <prev_system_model.json> <curr_system_model.json>")
        sys.exit(1)
    generate_delta(sys.argv[1], sys.argv[2])
