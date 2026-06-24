#!/usr/bin/env python3
"""
discover.py — derive the architecture graph from code (the structural spine)
----------------------------------------------------------------------------
Architecture-as-code, per the engineering principle "single source of truth, no
parallel copies that agree-today-but-drift". A hand-written ARCHITECTURE.md is
exactly that anti-pattern for *structural facts* (lineage, module deps, gate
call-graph): it rots silently with no freshness guard. So we DERIVE those facts
from the code that actually runs, and reconcile the prose docs against the result.

What is derived (and at what confidence):
  - import graph        : AST parse, local-module imports                 (HIGH)
  - gate call-graph     : subprocess `[sys.executable, str(ANALYSIS/"x.py"), …]`
                          and `["x.py", …]` idioms                         (HIGH)
  - IO path references  : path-shaped string literals + read/write intent  (HEURISTIC)
  - docstring claims    : `Output:`/`Input:` lines in module docstrings     (AUTHORED)

IO is HEURISTIC by design: access is often indirect (`open(cfg["out"], "w")`), so
this layer is meant to VALIDATE a manifest's declared inputs/outputs, not to be the
sole source of lineage. Import graph + call-graph are authoritative.

Layout-agnostic: resolves the repo root by walking up to `.git`, and discovers
edges rather than hardcoding paths — so it survives the §4 restructure untouched.

Usage:
    python3 analysis/architecture/discover.py            # write graph.json + summary
    python3 analysis/architecture/discover.py --quiet
    python3 analysis/architecture/discover.py --json     # print graph to stdout
"""
import argparse
import ast
import json
import re
import sys
from pathlib import Path


def repo_root(start: Path) -> Path:
    """Walk up until we find the .git dir — layout-agnostic root resolution."""
    p = start.resolve()
    for cand in [p, *p.parents]:
        if (cand / ".git").exists():
            return cand
    raise RuntimeError("could not locate repo root (.git) above " + str(start))


ROOT = repo_root(Path(__file__))
ANALYSIS = ROOT / "analysis"
OUT = ANALYSIS / "architecture" / "graph.json"

# Directories under analysis/ to scan for python sources. (`core`/`guards`/`crosssource`
# are the §4 relocation targets — generic engines, freshness guards, cross-system pass.
# NB `crosssource` is the CODE dir; `cross_source` is the DATA dir.)
SCAN_DIRS = [ANALYSIS, ANALYSIS / "signals", ANALYSIS / "cross_source",
             ANALYSIS / "newsletter", ANALYSIS / "signals" / "compute",
             ANALYSIS / "core", ANALYSIS / "guards", ANALYSIS / "crosssource"]

# Tokens that mark a string literal as an artifact path worth tracking.
PATH_TOKENS = ("web/public/data", "merged/", "rbi_sibc", "rbi_atm_pos",
               "signals/", "signals.db", "cross_source", "ontology",
               "skeleton_profile", "registry.json", "timeline.json",
               "evaluations/", "system_model", "system_state", "opportunities")
PATH_SUFFIXES = (".json", ".csv", ".db", ".ts", ".md", ".mmd")
# Data artifacts worth tracking as lineage nodes. Excludes .py (those are
# subprocess invocations, captured separately) and directory paths (no suffix).
DATA_SUFFIXES = (".json", ".csv", ".db", ".ts", ".tsx", ".mmd", ".html", ".md")

# Idioms that mark a write at the site of a path literal / variable.
WRITE_HINTS = ("json.dump", "to_csv", "to_json", "write_text", "write_bytes",
               '"w"', "'w'", '"wb"', "'wb'", "savefig", "csv.writer",
               ".writer(", ".write(")
# Dict/var key names that conventionally denote an output target.
WRITE_KEYS = ("out", "output", "dest", "target", "model", "writes")
# SQL verbs that mark a sqlite path as written (not just read).
SQL_WRITE = ("insert into", "update ", "create table", "create index",
             "replace into", "delete from", "drop table")


def py_files():
    seen = set()
    for d in SCAN_DIRS:
        if not d.exists():
            continue
        for f in sorted(d.glob("*.py")):
            if f.name == "__init__.py" or "__pycache__" in f.parts:
                continue
            if f in seen:
                continue
            seen.add(f)
            yield f


def module_name(path: Path) -> str:
    """Stable node id for a script: path relative to analysis/, no suffix."""
    return str(path.relative_to(ANALYSIS).with_suffix(""))


def local_module_set():
    return {p.stem: module_name(p) for p in py_files()}


# --- path canonicalization ---------------------------------------------------
# Path literals are written as different relative fragments across scripts
# (`ROOT / "web/public/data/x"`, a config dict `"signals/signals.db"`, a bare
# `registry.json`, a glob `system_state_*.json`). To join producers↔consumers
# they must resolve to ONE canonical repo-relative key. We do that by (1) testing
# the literal against real on-disk locations, then (2) suffix-matching against an
# index of artifacts that actually exist in the repo.

_ART_GLOBS = [
    "web/public/data/*.csv", "web/public/data/*.json",
    "analysis/signals/*.db", "analysis/signals/*.json",
    "analysis/signals/evaluations/**/*.json",
    "analysis/**/merged/*.json", "analysis/**/timeline.json",
    "analysis/**/skeleton_profile.json", "analysis/**/signals.json",
    "analysis/ontology/*.json", "analysis/cross_source/*.json",
    "web/lib/reports/*.ts",
]


def artifact_index():
    arts = set()
    for pat in _ART_GLOBS:
        for f in ROOT.glob(pat):
            if f.is_file():
                arts.add(str(f.relative_to(ROOT)))
    return arts


def canonicalize(lit, script_dir, arts):
    """Resolve a path literal to a canonical repo-relative key (best effort)."""
    s = lit.strip().lstrip("./")
    if "*" in s:  # glob — canonicalize the directory, keep the pattern
        for base in (ROOT, ANALYSIS, script_dir):
            if (base / s).parent.exists():
                try:
                    return str((base / s).resolve().relative_to(ROOT))
                except ValueError:
                    pass
        return s
    for base in (ROOT, ANALYSIS, script_dir):  # exists on disk → authoritative
        cand = base / s
        if cand.exists():
            try:
                return str(cand.resolve().relative_to(ROOT))
            except ValueError:
                pass
    parts = s.split("/")  # suffix-match against real artifacts (unique only)
    for n in range(len(parts), 0, -1):
        suf = "/".join(parts[-n:])
        matches = [a for a in arts if a == suf or a.endswith("/" + suf)]
        if len(matches) == 1:
            return matches[0]
    return s  # unresolved — keep the raw literal (still a node, just not joined)


def parse_imports(tree, locals_by_stem):
    """Local-module imports only (ignore stdlib / third-party)."""
    deps = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for a in node.names:
                stem = a.name.split(".")[0]
                if stem in locals_by_stem:
                    deps.add(locals_by_stem[stem])
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                root = node.module.split(".")[0]
                if root in locals_by_stem:
                    deps.add(locals_by_stem[root])
                # `from signals.query import ...` / `from compute.sibc import ...`
                for a in node.names:
                    if a.name in locals_by_stem:
                        deps.add(locals_by_stem[a.name])
    return sorted(deps)


SUBPROC_RE = re.compile(r'["\']([A-Za-z0-9_]+\.py)["\']')


def parse_invocations(src, locals_by_stem):
    """Scripts this script launches as a subprocess, in source (≈execution) order.
    Deduped keeping first occurrence so the gate sequence stays meaningful."""
    out = []
    for m in SUBPROC_RE.finditer(src):
        stem = m.group(1)[:-3]
        if stem in locals_by_stem:
            name = locals_by_stem[stem]
            if name not in out:
                out.append(name)
    return out


PATHLIT_RE = re.compile(r'["\']([^"\']*?)["\']')


def _flatten_div(node, parts):
    """Flatten a `a / b / c` BinOp chain into ordered components (str or None)."""
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        _flatten_div(node.left, parts)
        _flatten_div(node.right, parts)
    elif isinstance(node, ast.Constant) and isinstance(node.value, str):
        parts.append(node.value)
    else:
        parts.append(None)  # a base var (ROOT/ANALYSIS/cfg[...]) — dropped


def joined_paths(tree):
    """Reconstruct `BASE / "a" / "b.json"` path-joins the flat literal scan misses.
    Returns {lineno: [reconstructed_relpath, ...]}. Only the OUTERMOST Div of each
    chain is used (inner Divs are children) so we don't emit partial prefixes."""
    div_nodes = [n for n in ast.walk(tree)
                 if isinstance(n, ast.BinOp) and isinstance(n.op, ast.Div)]
    children = set()
    for n in div_nodes:
        for side in (n.left, n.right):
            if isinstance(side, ast.BinOp) and isinstance(side.op, ast.Div):
                children.add(id(side))
    out = {}
    for n in div_nodes:
        if id(n) in children:
            continue
        parts = []
        _flatten_div(n, parts)
        strs = [p for p in parts if p]
        if not strs:
            continue
        rel = "/".join(strs)
        if looks_like_path(rel) or any(looks_like_path(s) for s in strs):
            out.setdefault(getattr(n, "lineno", 0), []).append(rel)
    return out


def looks_like_path(s: str) -> bool:
    # Reject prose: argparse help / log strings ("Path to timeline.json") contain
    # spaces or template/format markers; real path literals don't.
    if not s or " " in s or "{" in s or "%" in s or "\\n" in s:
        return False
    if any(s.endswith(suf) for suf in PATH_SUFFIXES):
        return True
    return any(tok in s for tok in PATH_TOKENS) and "/" in s


# --- AST variable-binding write detection ------------------------------------
# The path is often bound to a var/constant (`OUT = ROOT / "…csv"`) and WRITTEN
# elsewhere (`df.to_csv(OUT)`) — intent and literal on different lines, invisible
# to a line-local scan. Resolve a path expression (constant, `/`-join, or a bound
# var) to a canonical key, then attribute writes from write-calls to their target.
WRITE_ATTRS = {"to_csv", "to_json", "write_text", "write_bytes", "savefig"}


def resolve_expr(node, var2path, script_dir, arts):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return canonicalize(node.value, script_dir, arts) if looks_like_path(node.value) else None
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Div):
        parts = []
        _flatten_div(node, parts)
        strs = [p for p in parts if p]
        if strs:
            rel = "/".join(strs)
            if looks_like_path(rel) or any(looks_like_path(s) for s in strs):
                return canonicalize(rel, script_dir, arts)
        return None
    if isinstance(node, ast.Name):
        return var2path.get(node.id)
    return None


def build_var2path(tree, script_dir, arts):
    """Map var names bound to a path expression → canonical key (best effort)."""
    m = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            val = resolve_expr(node.value, m, script_dir, arts)
            if val:
                for t in node.targets:
                    if isinstance(t, ast.Name):
                        m[t.id] = val
    return m


def ast_writes(tree, var2path, script_dir, arts):
    """Writes inferred from write-calls: `x.to_csv()`, `p.write_text()`, open(p,'w')."""
    w = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        f = node.func
        if isinstance(f, ast.Attribute) and f.attr in WRITE_ATTRS:
            for cand in [f.value, *node.args]:
                r = resolve_expr(cand, var2path, script_dir, arts)
                if r:
                    w.add(r)
        elif isinstance(f, ast.Name) and f.id == "open" and len(node.args) >= 2:
            mode = node.args[1]
            if isinstance(mode, ast.Constant) and isinstance(mode.value, str) \
                    and any(c in mode.value for c in ("w", "a", "x")):
                r = resolve_expr(node.args[0], var2path, script_dir, arts)
                if r:
                    w.add(r)
    return w


def parse_io(src, tree, script_dir, arts):
    """Heuristic path-literal extraction with read/write intent, canonicalized.
    Combines flat string literals with AST-reconstructed `BASE / "a" / "b"` joins
    (matched by line number). Indirect IO (open(cfg['out']), sqlite, pandas) is
    approximated via co-located write hints, write-ish dict keys, and a file-level
    sqlite-write scan; flagged by confidence so the manifest stays authoritative."""
    reads, writes = {}, {}
    low = src.lower()
    sqlite_writer = "sqlite3.connect" in src and any(v in low for v in SQL_WRITE)
    joins = joined_paths(tree)  # {lineno: [relpath, ...]}
    for i, line in enumerate(src.splitlines(), start=1):
        line_has_write = any(h in line for h in WRITE_HINTS)
        line_has_writekey = any(re.search(r'["\']' + k + r'["\']\s*:', line) for k in WRITE_KEYS)
        flats = [m.group(1) for m in PATHLIT_RE.finditer(line)
                 if m.group(1) and looks_like_path(m.group(1))]
        for lit in flats + joins.get(i, []):
            key = canonicalize(lit, script_dir, arts)
            # Track data artifacts only — not .py invocations or bare directories.
            if not key.endswith(DATA_SUFFIXES):
                continue
            # A .db touched by a file that issues write SQL is a write.
            db_write = key.endswith(".db") and sqlite_writer
            if line_has_write or line_has_writekey or db_write:
                conf = "high" if (line_has_write or db_write) else "low"
                writes[key] = conf
            else:
                reads.setdefault(key, "low")
    # AST variable-binding writes (path bound to a var, written elsewhere).
    var2path = build_var2path(tree, script_dir, arts)
    for k in ast_writes(tree, var2path, script_dir, arts):
        if k.endswith(DATA_SUFFIXES):
            writes[k] = "high"
    for k in list(reads):  # write classification wins if both seen
        if k in writes:
            reads.pop(k)
    return reads, writes


DOC_IO_RE = re.compile(r'^\s*(Input|Inputs|Output|Outputs|Writes|Reads)\s*:\s*(.+)$',
                       re.IGNORECASE | re.MULTILINE)


def parse_doc_claims(tree):
    doc = ast.get_docstring(tree) or ""
    return [{"kind": m.group(1).lower(), "text": m.group(2).strip()}
            for m in DOC_IO_RE.finditer(doc)]


def discover():
    locals_by_stem = local_module_set()
    arts = artifact_index()
    scripts = {}
    for f in py_files():
        src = f.read_text(encoding="utf-8")
        try:
            tree = ast.parse(src)
        except SyntaxError as e:
            scripts[module_name(f)] = {"error": f"parse failed: {e}"}
            continue
        reads, writes = parse_io(src, tree, f.parent, arts)
        scripts[module_name(f)] = {
            "path": str(f.relative_to(ROOT)),
            "imports": parse_imports(tree, locals_by_stem),
            "invokes": parse_invocations(src, locals_by_stem),
            "reads": reads,
            "writes": writes,
            "doc_claims": parse_doc_claims(tree),
        }
    return {"root": str(ROOT), "scripts": scripts}


def summarize(graph):
    s = graph["scripts"]
    n = len(s)
    errs = [k for k, v in s.items() if "error" in v]
    invokers = {k: v["invokes"] for k, v in s.items() if v.get("invokes")}
    # Entry points = scripts nobody imports and nobody invokes (top of the graph).
    invoked = {t for v in s.values() for t in v.get("invokes", [])}
    imported = {t for v in s.values() for t in v.get("imports", [])}
    referenced = invoked | imported
    entrypoints = sorted(k for k in s if k not in referenced and "error" not in s[k])
    print(f"discovered {n} scripts  ({len(errs)} parse errors)")
    print(f"  gate call-graph: {len(invokers)} scripts invoke others; "
          f"{len(invoked)} distinct scripts are invoked")
    print(f"  entry points (invoked/imported by nobody): {len(entrypoints)}")
    for ep in entrypoints:
        inv = s[ep].get("invokes", [])
        print(f"    • {ep}" + (f"  → invokes {len(inv)}" if inv else ""))
    if errs:
        print("  parse errors:")
        for e in errs:
            print(f"    ✗ {e}: {s[e]['error']}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    ap.add_argument("--json", action="store_true", help="print graph to stdout")
    args = ap.parse_args()

    graph = discover()
    if args.json:
        print(json.dumps(graph, indent=2))
        return 0
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(graph, indent=2, ensure_ascii=False))
    if not args.quiet:
        summarize(graph)
        print(f"\n→ wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
