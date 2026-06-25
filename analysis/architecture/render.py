#!/usr/bin/env python3
"""
render.py — graph.json → ARCHITECTURE.generated.md (the human-facing, never-lying doc)
-------------------------------------------------------------------------------------
Renders the DERIVED architecture graph into a Markdown reference: a mermaid data-flow
diagram, the gate call-graph, the artifact-lineage table, the module-dependency map,
and a findings section (orphans / dual-writers / docstring drift).

This file is GENERATED. The source of truth is code (via discover.py); the authored
rationale (layer model L1/L2/L3, design principles, why each guard exists) lives in
the hand-written ARCHITECTURE.md, which links to this. Regenerate, never hand-edit:
    python3 analysis/architecture/discover.py && python3 analysis/architecture/render.py
"""
import json
import re
from pathlib import Path

ANALYSIS = Path(__file__).resolve().parent.parent
ROOT = ANALYSIS.parent
GRAPH = ANALYSIS / "architecture" / "graph.json"
OUT = ROOT / "ARCHITECTURE.generated.md"

# Entry points to feature in the gate-sequence section, in this order.
# gate.py is the single manifest-driven gate (run_evals/run_atm_pos_evals retired to legacy/).
GATE_ROOTS = ["gate", "check_derived_fresh", "hook_validate"]


def load():
    return json.load(open(GRAPH))["scripts"]


def lineage(scripts):
    """artifact → {producers, consumers}."""
    prod, cons = {}, {}
    for name, s in scripts.items():
        if "error" in s:
            continue
        for w in s.get("writes", {}):
            prod.setdefault(w, []).append(name)
        for r in s.get("reads", {}):
            cons.setdefault(r, []).append(name)
    arts = sorted(set(prod) | set(cons))
    return prod, cons, arts


def is_canonical(a):
    return a.startswith(("web/", "analysis/"))


def mermaid_id(a):
    return "n_" + re.sub(r"[^A-Za-z0-9]", "_", a)


def short(a):
    return a.split("/")[-1]


def section_dataflow(scripts, prod, cons, arts):
    """Artifact DAG: edge B --script--> A whenever a script reads B and writes A."""
    edges = set()
    for name, s in scripts.items():
        if "error" in s:
            continue
        ws = [w for w in s.get("writes", {}) if is_canonical(w)]
        rs = [r for r in s.get("reads", {}) if is_canonical(r)]
        for w in ws:
            for r in rs:
                if r != w:
                    edges.add((r, w, name))
    nodes = sorted({n for e in edges for n in (e[0], e[1])})
    lines = ["## 1. Data-flow", "",
             "Artifact dependency DAG — nodes are artifacts, each edge is the script that",
             "transforms one into the next. Derived from read/write analysis of the code.",
             "", "```mermaid", "flowchart LR"]
    for n in nodes:
        shape = f'{mermaid_id(n)}["{short(n)}"]'
        # external inputs (no producer) get a distinct stadium shape
        if not prod.get(n):
            shape = f'{mermaid_id(n)}(["{short(n)}"])'
        lines.append("  " + shape)
    for r, w, name in sorted(edges):
        lines.append(f"  {mermaid_id(r)} -->|{short(name)}| {mermaid_id(w)}")
    lines += ["```", "",
              "_Stadium nodes = external/authored inputs (no script writes them)._",
              "_Edges are script-level: a script that reads A and writes B yields A→B, so a",
              "script spanning both pipelines may show cross-pipeline edges. See §3 for the",
              "exact per-artifact producer/consumer._", ""]
    return "\n".join(lines)


def section_callgraph(scripts):
    lines = ["## 2. Gate call-graph", "",
             "Scripts each orchestrator launches as a subprocess, in execution order.", ""]
    for root in GATE_ROOTS:
        s = scripts.get(root)
        if not s or "error" in s:
            continue
        inv = s.get("invokes", [])
        lines.append(f"### `{root}` → {len(inv)} steps")
        for i, t in enumerate(inv, 1):
            lines.append(f"{i}. `{t}`")
        lines.append("")
    return "\n".join(lines)


def section_lineage_table(prod, cons, arts):
    lines = ["## 3. Artifact lineage", "",
             "| Artifact | Kind | Producer(s) | Consumer(s) |",
             "|---|---|---|---|"]
    for a in arts:
        if not is_canonical(a):
            continue
        p, c = prod.get(a, []), cons.get(a, [])
        kind = "derived" if p else "external/authored"
        pp = ", ".join(f"`{x}`" for x in p) or "—"
        cc = ", ".join(f"`{x}`" for x in c) or "—"
        lines.append(f"| `{a}` | {kind} | {pp} | {cc} |")
    lines.append("")
    return "\n".join(lines)


def section_depmap(scripts):
    lines = ["## 4. Module-dependency map", "",
             "Python import edges (sparse by design — the pipeline is subprocess-",
             "orchestrated, not import-coupled).", ""]
    any_dep = False
    for name in sorted(scripts):
        s = scripts[name]
        if "error" in s:
            continue
        imp = s.get("imports", [])
        if imp:
            any_dep = True
            lines.append(f"- `{name}` → " + ", ".join(f"`{i}`" for i in imp))
    if not any_dep:
        lines.append("_(none)_")
    lines.append("")
    return "\n".join(lines)


def section_findings(scripts, prod, cons, arts):
    lines = ["## 5. Findings (drift signals)", ""]

    dual = {a: p for a, p in prod.items() if len(p) > 1}
    lines.append("### Multiple writers (verify intentional vs. dual-path smell)")
    if dual:
        for a, p in sorted(dual.items()):
            lines.append(f"- `{a}` ← " + ", ".join(f"`{x}`" for x in p))
    else:
        lines.append("_(none)_")
    lines.append("")

    # Internal artifacts produced but consumed by nothing (web outputs excluded —
    # they're consumed by the front-end, not by python).
    orphans = [a for a in arts
               if prod.get(a) and not cons.get(a)
               and a.startswith("analysis/")]
    lines.append("### Internal artifacts produced but never read (potential dead output)")
    if orphans:
        for a in orphans:
            lines.append(f"- `{a}` ← " + ", ".join(f"`{x}`" for x in prod[a]))
    else:
        lines.append("_(none)_")
    lines.append("")

    # NB: a docstring-`Output:` vs detected-writes check was tried here and removed —
    # the discoverer can't see f-string/.html write paths, so empty/partial detections
    # produced false "drift". Doc-vs-code reconciliation lives in reconcile.py, which
    # only asserts things it can check deterministically (script/artifact existence).
    return "\n".join(lines)


def main():
    scripts = load()
    prod, cons, arts = lineage(scripts)
    n_scripts = sum(1 for s in scripts.values() if "error" not in s)
    header = [
        "# Architecture (generated)", "",
        "> ⚠ **GENERATED — do not edit by hand.** Source of truth is the code, via",
        "> `analysis/architecture/discover.py`. Regenerate:",
        "> ```",
        "> python3 analysis/architecture/discover.py && python3 analysis/architecture/render.py",
        "> ```",
        "> Authored rationale (layer model, design principles, guard purposes) lives in the",
        "> hand-written `ARCHITECTURE.md`. This file is the structural, drift-guarded half.",
        "",
        f"_Derived from {n_scripts} scripts._", "",
    ]
    body = "\n".join([
        "\n".join(header),
        section_dataflow(scripts, prod, cons, arts),
        section_callgraph(scripts),
        section_lineage_table(prod, cons, arts),
        section_depmap(scripts),
        section_findings(scripts, prod, cons, arts),
    ])
    OUT.write_text(body)
    print(f"→ wrote {OUT.relative_to(ROOT)} ({n_scripts} scripts, {len(arts)} artifacts)")


if __name__ == "__main__":
    main()
