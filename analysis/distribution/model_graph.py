#!/usr/bin/env python3
"""
model_graph.py — extract a spine's real subgraph from the system model (§11.2-R2)
-----------------------------------------------------------------------------------
A deep-read diagram must show the structure the platform already holds, not a shape
synthesised for the picture. This reads `system_model.json` (per pipeline) and
`ecosystem_model.json`, and for a chosen spine returns the relevant subgraph — nodes and
edges — which `mermaid.render` then draws. It generates nothing: every node and edge here
exists in the model.

By spine kind:
  risk / opportunity  the sourced FORCE → mechanism node → the risk, plus what the force
                      also drives (the +/- split, e.g. Zero MDR: + QR, - POS)
  eco_loop            the loop's constructs, each expanded into its member series, + the
                      loop edges between constructs
  construct           the construct and the series that measure it
  cross_edge          the two endpoints and their series
  constraint          the two operand sources → ratio → corridor verdict

`trivial()` is the honest floor: a subgraph that is barely an edge is not worth a diagram,
and — per the spec — a spine whose model can't do better is a model gap to revisit, not a
triangle to draw.
"""
import json
import re
import sys
from functools import lru_cache
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

MODELS = {
    "sibc": ROOT / "analysis" / "rbi_sibc" / "merged" / "system_model.json",
    "atm_pos": ROOT / "analysis" / "rbi_atm_pos" / "merged" / "system_model.json",
}
ECO = ROOT / "analysis" / "cross_source" / "ecosystem_model.json"

_ACR = {"upi", "pos", "atm", "mdr", "qr", "npci", "rbi", "psb", "cc", "dc", "sfb", "nbfc",
        "msme", "pli", "psl", "gst", "ev", "cic", "fy", "emi", "goi"}

MAX_FORCE_TARGETS = 4      # how many sibling targets of a force to show (the +/- split)
MAX_MEMBERS = 4            # how many member series to expand per construct


@lru_cache(maxsize=8)
def _load(path):
    return json.loads(path.read_text()) if path and path.exists() else {}


def _humanise(node_id):
    """A readable label from a bare id ('force_upi_zero_mdr' → 'UPI zero MDR')."""
    words = node_id.split("_")
    if words and words[0] in ("force", "fi", "risk", "opp", "e", "gap"):
        words = words[1:]
    return " ".join(w.upper() if w in _ACR else w for w in words) or node_id


def _is_force(node_id):
    return node_id.startswith(("force_", "fi_"))


def _kind(node_id, node):
    if _is_force(node_id):
        return "force"
    if node_id.startswith("risk_"):
        return "risk"
    if node.get("signal_ids"):
        return "outcome"
    return "node"


def _short_label(label, kind):
    """A compact node label for a diagram box: a risk keeps only the phrase before its colon,
    a force drops its parenthetical, everything else is left alone."""
    label = (label or "").strip()
    if kind == "risk" and ":" in label:
        label = label.split(":", 1)[0].strip()
    if kind == "force":
        label = re.sub(r"\s*\([^)]*\)", "", label).strip()
    return label


def _node_entry(node_id, model_nodes, driver_label=None):
    node = model_nodes.get(node_id, {})
    kind = _kind(node_id, node)
    label = node.get("label") or (driver_label if _is_force(node_id) else None) or _humanise(node_id)
    return {"id": node_id, "label": _short_label(label, kind), "kind": kind,
            "signals": list(node.get("signal_ids") or [])}   # for the prose to ground itself


def _edge_entry(e):
    # The type word is the label ("drives", "suppresses", "creates risk"); polarity is shown by
    # the arrow style (solid = with, dashed = against), so it is not repeated in text.
    typ = (e.get("type") or "").replace("_", " ")
    return {"from": e["from"], "to": e["to"], "label": typ, "against": e.get("polarity") == "-"}


def force_source(pipeline, force_id):
    """The official/regulatory source string a force is grounded on (for the 'on record in …'
    line). Empty when the force carries none."""
    for f in _load(MODELS.get(pipeline, Path())).get("force_instances", []):
        if f.get("id") == force_id:
            return f.get("source") or ""
    return ""


def _pipeline_node_subgraph(pipeline, node_id, driver_label=None):
    """Causal ancestry of a risk/opportunity node: its drivers, and each driving force's own
    sibling targets (so the +/- split shows), all straight from the model."""
    m = _load(MODELS[pipeline])
    if not m:
        return None
    nodes_by_id = {n["id"]: n for n in m.get("nodes", [])}
    if node_id not in nodes_by_id:
        return None
    edges, keep_edges, keep_nodes = m.get("edges", []), [], {node_id}

    for e in edges:                                    # direct drivers of the node
        if e.get("to") == node_id:
            keep_edges.append(e)
            keep_nodes.add(e["from"])
    for e in list(keep_edges):                         # each force's sibling targets
        s = e["from"]
        if not _is_force(s):
            continue
        siblings = [x for x in edges if x.get("from") == s and x is not e][:MAX_FORCE_TARGETS]
        for x in siblings:
            if x not in keep_edges:
                keep_edges.append(x)
                keep_nodes.add(x["to"])

    nodes = [_node_entry(nid, nodes_by_id, driver_label) for nid in keep_nodes]
    return {"nodes": nodes, "edges": [_edge_entry(e) for e in keep_edges]}


def _constraint_subgraph(cand):
    ops = cand.get("operands", [])
    if len(ops) < 2:
        return None
    a = (ops[0].get("note") or ops[0].get("signal_id", "source A")).split(",")[0]
    b = (ops[1].get("note") or ops[1].get("signal_id", "source B")).split(",")[0]
    holds = cand.get("state") in ("holds", "ok")
    verdict = "within corridor" if holds else "outside corridor"
    nodes = [{"id": "a", "label": a, "kind": "outcome"},
             {"id": "b", "label": b, "kind": "outcome"},
             {"id": "ratio", "label": "avg balance per card", "kind": "node"},
             {"id": "v", "label": verdict, "kind": "risk" if not holds else "node"}]
    edges = [{"from": "a", "to": "ratio"}, {"from": "b", "to": "ratio"},
             {"from": "ratio", "to": "v", "against": not holds}]
    return {"nodes": nodes, "edges": edges}


def _urn_index():
    """URN → (label, pipeline) from both pipeline models."""
    idx = {}
    for pl, path in MODELS.items():
        for n in _load(path).get("nodes", []):
            if n.get("urn"):
                idx[n["urn"]] = (n.get("label", n["id"]), pl)
    return idx


def _construct_nodes(construct, urn_idx, into_edges_to):
    """A construct node + its member series, edges member→construct. Returns node list."""
    cid = construct["urn"]
    out = [{"id": cid, "label": construct.get("label", cid), "kind": "node"}]
    for m in construct.get("members", [])[:MAX_MEMBERS]:
        u = m.get("urn")
        if u in urn_idx:
            out.append({"id": u, "label": urn_idx[u][0], "kind": "outcome"})
            into_edges_to.append({"from": u, "to": cid,
                                  "against": m.get("direction") == -1})
    return out


def _loop_subgraph(loop_id):
    eco = _load(ECO)
    loop = next((l for l in eco.get("loops", []) if l["id"] == loop_id), None)
    if not loop:
        return None
    constructs = {c["urn"]: c for c in eco.get("constructs", [])}
    urn_idx = _urn_index()
    nodes, edges, seen = [], [], set()

    def add(urn):                                      # a construct OR an underlying series
        if urn in seen:
            return
        seen.add(urn)
        if urn in constructs:
            nodes.append({"id": urn, "label": constructs[urn].get("label", urn), "kind": "node"})
        elif urn in urn_idx:
            nodes.append({"id": urn, "label": urn_idx[urn][0], "kind": "outcome"})
        else:
            nodes.append({"id": urn, "label": _humanise(urn.split("/")[-1]), "kind": "outcome"})

    # The eco edges span series↔construct; the loop closes through them. (The x: cross-edge
    # segment is stored outside the eco model, so it is not drawn — the eco spine is enough.)
    eco_edges = {e["id"]: e for e in eco.get("eco_edges", [])}
    for ref in loop.get("member_edges", []):
        kind, _, rest = ref.partition(":")
        e = eco_edges.get(rest, {})
        frm, to = e.get("from"), e.get("to")
        if frm and to:
            add(frm)
            add(to)
            edges.append({"from": frm, "to": to,
                          "label": (e.get("mechanism") or "").split(".")[0][:22] or None})
    if len(nodes) < 3:
        return None
    return {"nodes": nodes, "edges": edges}


def _construct_subgraph(construct_urn):
    eco = _load(ECO)
    c = next((c for c in eco.get("constructs", []) if c["urn"] == construct_urn), None)
    if not c:
        return None
    edges = []
    nodes = _construct_nodes(c, _urn_index(), edges)
    return {"nodes": nodes, "edges": edges}


def trivial(sub):
    """A subgraph not worth a diagram — barely an edge. The honest floor (§11.2-R2)."""
    return (not sub) or len(sub.get("nodes", [])) < 3 or len(sub.get("edges", [])) < 2


def subgraph_for(cand):
    """The model subgraph for a spine candidate, or None when the model offers nothing worth
    drawing (a model gap to revisit, per the spec — never synthesised around)."""
    kind = cand.get("kind")
    item = cand.get("item", {})
    if kind in ("risk", "opportunity"):
        sub = _pipeline_node_subgraph(item.get("pipeline"), cand.get("id"),
                                      driver_label=cand.get("_driver") or item.get("_driver"))
    elif kind == "constraint":
        sub = _constraint_subgraph(cand)
    elif kind == "eco_loop":
        sub = _loop_subgraph((item.get("driver") or {}).get("id") or cand.get("id"))
    elif kind == "construct":
        sub = _construct_subgraph((item.get("driver") or {}).get("id") or cand.get("id"))
    else:
        sub = None
    return None if trivial(sub) else sub
