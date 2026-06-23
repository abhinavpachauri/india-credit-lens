"""
core.paths — single source of truth for repo-relative path roots
----------------------------------------------------------------
Historically every script computed the repo root with `Path(__file__).parent.parent`
(or `.parent.parent.parent.parent` deeper in the tree). That assumption is depth-
dependent and breaks the moment a script moves into a different subfolder — exactly
what the analysis/ restructure (§4) does. Centralising root resolution here, resolved
by walking up to the `.git` directory, makes it location-independent: this module (and
every script that imports it) keeps resolving the same ROOT no matter where the file
lives after a move.

Exports:
    ROOT      repo root (the dir containing .git)
    ANALYSIS  ROOT / "analysis"

Import from any script, at any depth, via the bootstrap (see core/__init__-less note):
    import sys
    from pathlib import Path
    for _p in Path(__file__).resolve().parents:
        if (_p / ".git").is_dir():
            sys.path.insert(0, str(_p / "analysis"))
            break
    from core.paths import ROOT, ANALYSIS

The bootstrap is depth- and move-independent (it finds the repo by .git, then puts
ROOT/analysis on sys.path so `core.paths` resolves). It deliberately reimplements the
.git walk inline because it must run *before* this module can be imported.
"""
from pathlib import Path


def find_root(start: Path) -> Path:
    """Walk up from `start` to the directory containing `.git`."""
    start = start.resolve()
    for cand in [start, *start.parents]:
        if (cand / ".git").is_dir():
            return cand
    raise RuntimeError(f"could not locate repo root (.git) above {start}")


ROOT = find_root(Path(__file__))
ANALYSIS = ROOT / "analysis"
