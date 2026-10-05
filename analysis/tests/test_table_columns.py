"""The table's columns are declared once (core/table_columns.py) and the TypeScript is generated.
A drifted copy is the failure §21.5 exists to remove: a column built and drawn that the gate never reads."""
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core import table_columns as TC                       # noqa: E402
from guards import validate_cut_table as V                  # noqa: E402


def test_the_generated_typescript_is_current():
    assert TC.TS_OUT.read_text() == TC.render_ts(), "run: python3 analysis/core/table_columns.py --write"


def test_the_gate_reads_every_declared_column():
    assert tuple(V.CELLS) == TC.KEYS


def test_no_component_retypes_the_column_list():
    for f in (ROOT / "web" / "lib" / "table.ts", ROOT / "web" / "components" / "read" / "parts.tsx"):
        src = f.read_text()
        assert '["size", "of_cut"' not in src, f"{f.name} types the column list again"
        assert "const COL_LABEL" not in src, f"{f.name} types the column labels again"
