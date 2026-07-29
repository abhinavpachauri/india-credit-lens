#!/usr/bin/env python3
"""
mermaid.py — a pure diagram renderer (DISTRIBUTION_SPEC §11.2-R2)
------------------------------------------------------------------
Representation only. It takes a graph — nodes and edges — and draws it as mermaid text.
It does NOT decide what the graph is: that comes from the system model (`model_graph.py`),
because the structure a deep read draws must be the structure the platform actually holds,
not a shape synthesised in the distribution layer. If the model cannot yield a graph worth
drawing, that is a model gap to revisit, not a triangle to invent here.

Renders inline (a ```mermaid fence Substack and the site both render). Structure and node
labels only — never data numbers; those live in the prose beside it, where the traceability
gate scopes them.

    nodes = [{"id": "...", "label": "...", "kind": "force|risk|node"}]
    edges = [{"from": "...", "to": "...", "label": "+ drives", "against": bool}]
"""
import re

# How a node's role shows up as a mermaid shape — a force is where a story starts, a risk is
# where it lands, everything between is a plain box.
_SHAPE = {
    "force":  ('(["', '"])'),      # stadium — an external push
    "risk":   ('{{"', '"}}'),      # hexagon — a watch-out
    "outcome": ('[/"', '"/]'),     # parallelogram — an observed series
}
_DEFAULT_SHAPE = ('["', '"]')


def _nid(raw, seen):
    """A stable mermaid-safe id for a node (letters/digits/underscore)."""
    base = re.sub(r"[^A-Za-z0-9]+", "_", raw).strip("_")[:28] or "n"
    nid, i = base, 2
    while nid in seen and seen[nid] != raw:
        nid, i = f"{base}_{i}", i + 1
    seen[nid] = raw
    return nid


def _clean(label):
    """A node label safe inside any mermaid shape: brackets/pipes/quotes removed, slashes and
    colons softened to spaces (some mermaid builds break on them even inside quotes)."""
    label = re.sub(r'[\[\]{}()|"<>]', "", label or "")
    label = re.sub(r"[/:]", " ", label)
    return re.sub(r"\s+", " ", label).strip()[:48] or "?"


def _edge_label(label):
    """An edge label mermaid's parser tolerates: letters, digits and spaces only. Punctuation
    like '(+)' or ':' breaks the link grammar, and the polarity it carried is already shown by
    the arrow style (solid = with, dashed = against)."""
    return re.sub(r"\s+", " ", re.sub(r"[^A-Za-z0-9 ]", "", label or "")).strip()


def render(nodes, edges, note=None):
    """Draw a graph. `nodes`/`edges` reference each other by `id`/`from`/`to`."""
    seen, id_of, lines = {}, {}, ["graph LR"]
    for n in nodes:
        nid = _nid(n["id"], seen)
        id_of[n["id"]] = nid
        open_, close_ = _SHAPE.get(n.get("kind"), _DEFAULT_SHAPE)
        lines.append(f'    {nid}{open_}{_clean(n.get("label") or n["id"])}{close_}')
    for e in edges:
        a, b = id_of.get(e["from"]), id_of.get(e["to"])
        if not (a and b):
            continue
        label = _edge_label(e.get("label"))
        # A dashed (against) link carries its text INSIDE the dots — `A -. text .-> B`; a pipe
        # label on a dotted arrow is a mermaid parse error. A solid link uses the pipe form.
        if e.get("against"):
            edge = f"    {a} -. {label} .-> {b}" if label else f"    {a} -. against .-> {b}"
        else:
            edge = f"    {a} -->|{label}| {b}" if label else f"    {a} --> {b}"
        lines.append(edge)
    if note:
        lines.append(f"    %% {_clean(note)}")
    return "\n".join(lines)


def block(code, caption=None):
    """Wrap diagram text as a `mermaid` render block (see longform_render)."""
    b = {"type": "mermaid", "code": code}
    if caption:
        b["caption"] = caption
    return b
