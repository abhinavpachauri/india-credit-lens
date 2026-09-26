"""
test_freshness_population.py — what the freshness check measures itself against
───────────────────────────────────────────────────────────────────────────────
`check_signal_freshness` recomputes every period from the CSV and fails on drift. It read the
period set OFF THE COMMITTED DATABASE — so a period with no rows was never in the set, never
recomputed, never compared. Deleting an entire month left it reporting
"fresh — 46,013 rows match (sibc:10p)".

Stale VALUES were caught; an absent PERIOD was not. An absent period is the June failure's own
shape, and the check asked the thing it was checking which questions to ask.

The population is now timeline.json — each pipeline's declared record of what it has ingested,
and the only statement of what the store OUGHT to contain that does not come from the store.
"""
import json
import sys
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from guards import check_signal_freshness as F                       # noqa: E402
from core import manifest                                             # noqa: E402


def test_the_timeline_is_the_population():
    """Every period a pipeline says it ingested must be one the check will recompute."""
    declared = F._declared_periods()
    assert declared, "no timeline resolved — the check would fall back to the DB's own word"
    for pipeline in manifest.discover_pipeline_ids():
        key = manifest.load(pipeline)["period_key"]
        doc = json.loads(manifest.path(pipeline, "timeline").read_text())
        rows = doc["periods"] if isinstance(doc, dict) else doc
        want = {r.get(key) for r in rows} - {None}
        assert declared.get(pipeline) == want, f"{pipeline}: declared set does not match its timeline"


def test_every_pipeline_is_in_the_population():
    """The population of pipelines is the manifests', not a list typed into the guard.

    It was the pair (sibc, atm_pos) until 2026-09-26, and NBFC — the third pipeline — fell back
    to the database's own list of periods. This test used the same hand-written pair, so it
    shared the blind spot it was meant to police.
    """
    assert set(F._declared_periods()) == set(manifest.discover_pipeline_ids())


def test_a_missing_timeline_fails_rather_than_drops_out(monkeypatch, tmp_path):
    """A pipeline whose declared timeline is gone must stop the check, not shrink it."""
    real = manifest.path
    monkeypatch.setattr(manifest, "path",
                        lambda pl, key: tmp_path / "gone.json" if key == "timeline" else real(pl, key))
    import pytest
    with pytest.raises(SystemExit, match="missing"):
        F._declared_periods()


def test_a_declared_period_absent_from_the_store_is_not_silently_skipped():
    """The property, driven on the real sets: every timeline period is present in signals.db.

    If this fails, either a period was never appended or one was appended and lost — and either
    way the old form of the check would have said "fresh" while measuring less.
    """
    import sqlite3
    con = sqlite3.connect(ROOT / "analysis/signals/signals.db")
    try:
        for pipeline, declared in F._declared_periods().items():
            have = {p for (p,) in con.execute(
                "SELECT DISTINCT period FROM signals WHERE pipeline=?", (pipeline,))}
            missing = declared - have
            assert not missing, f"{pipeline}: timeline declares {sorted(missing)}, store has none"
    finally:
        con.close()


def test_recompute_is_parallel_but_falls_back():
    """A guard that cannot run is worse than a slow one, so the pool is not load-bearing."""
    import inspect
    src = inspect.getsource(F._recompute)
    assert "ProcessPoolExecutor" in src
    assert "falling back to serial" in src, "no fallback — a pool failure would take the guard out"
