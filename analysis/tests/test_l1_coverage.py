"""
test_l1_coverage.py — every cut the dashboard renders must be fully described by Layer 1.
─────────────────────────────────────────────────────────────────────────────────────────
Layer 1 held 229 computed signals and could not state the SIZE of a single sector. Every
one was a rate or a share, so the platform could say industry grew 20.0% and could not say,
from any stored value, that industry is Rs 48 lakh crore — the first number a reader looks
for. Coverage was also ragged: share-of-parent existed on four credit cuts and not on the
other three, for no reason anyone had decided.

Neither gap was visible, because nothing asked the question these tests ask: not "is this
signal correct" but "is this CUT completely described". A missing family is an absence, and
absence is the failure shape this codebase keeps paying for.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

DB = ROOT / "analysis" / "signals" / "signals.db"
REGISTRY = json.loads((ROOT / "analysis" / "signals" / "registry.json").read_text())["signals"]

MOMENTUM = ("csv_sector_momentum", "csv_category_momentum")

# The families every rendered cut must carry, and the column each one fills in the table.
# PSL is the one documented exception and it is named, not silently skipped.
REQUIRED = {"-size-scan": "size", "-share-of-credit-scan": "share of all bank credit"}
NO_PARENT_TOTAL = {"sibc-psl"}   # a memo lens; `gap_psl_totals_methodology` says its parts
                                 # are non-additive, so it has no total to be a share OF.


def _cuts():
    """Every cut the platform computes a mix for — the momentum signal IS the cut."""
    return {sid[: -len("-momentum")]: sig for sid, sig in REGISTRY.items()
            if sig.get("compute", {}).get("method") in MOMENTUM}


def test_the_cut_list_is_not_empty():
    """Guards the guard: a broken selector here would make every test below vacuous."""
    assert len(_cuts()) >= 10, _cuts().keys()


@pytest.mark.parametrize("stem", sorted(_cuts()))
def test_every_cut_has_a_size_signal(stem):
    """The rupee amount is a stored value, not arithmetic done in a browser."""
    assert f"{stem}-size-scan" in REGISTRY, (
        f"{stem} has no size scan — its table would open with a blank first column")


@pytest.mark.parametrize("stem", sorted(_cuts()))
def test_every_cut_can_state_a_share_of_something_published(stem):
    """Either share-of-parent or share-of-root, against a denominator RBI actually publishes."""
    pipeline = REGISTRY[f"{stem}-momentum"]["pipeline"]
    if pipeline != "sibc":
        return          # a payments cut's parent IS its root — one share is the whole story
    # EITHER denominator satisfies this — the assert used to demand share-of-root only,
    # which contradicted this test's own docstring and failed the seven sub-cuts that
    # carry a perfectly good share of their parent.
    assert (f"{stem}-share-of-credit-scan" in REGISTRY
            or f"{stem}-share-scan" in REGISTRY
            or stem in NO_PARENT_TOTAL), f"{stem} cannot state a share of anything published"


@pytest.mark.parametrize("stem", sorted(_cuts()))
def test_every_declared_signal_actually_produced_rows(stem):
    """A registry entry with no rows is the exact shape of a failure that looks like an absence
    — the 12 unwired payments signals passed every check while computing nothing."""
    con = sqlite3.connect(DB)
    try:
        for suffix in REQUIRED:
            sid = f"{stem}{suffix}"
            if sid not in REGISTRY:
                continue
            n = con.execute("SELECT COUNT(*) FROM signals WHERE metric_id=?", (sid,)).fetchone()[0]
            assert n > 0, f"{sid} is declared in the registry and computes nothing"
    finally:
        con.close()


def test_a_cut_has_exactly_one_id_stem():
    """One cut, one stem — so its six families can be found by name, not by lookup table.

    Until 2026-09-12 services was `sibc-svcs-*` for three families and `sibc-services-*` for the
    other three, because the movement family arrived four months after the scans and coined a
    shorter label for its own table. Nothing broke: `MovementCut` declares its speed signal, so
    the one place that had to bridge the spellings hand-carried the other one. It surfaced only
    when THIS file became the first code to build ids from a stem — and it reported a false gap,
    naming two fully-covered cuts as missing share and growth.

    A check that cannot tell a naming quirk from a real hole is one people stop believing, so the
    convention is now asserted rather than assumed.
    """
    stems = sorted(_cuts())
    for stem in stems:
        # No other cut's stem may be a prefix of this one's, except the deliberate sub-cut
        # pattern (`sibc-industry-type` vs `sibc-industry-type-sub`), which is a different cut.
        shadowed = [o for o in stems
                    if o != stem and stem.startswith(o + "-") is False and o.startswith(stem + "-")]
        assert not shadowed or all("-sub" in o for o in shadowed), (
            f"{stem} is shadowed by {shadowed} — two cuts cannot share a prefix ambiguously")

    # The families of a cut must all exist under ITS stem, never a variant spelling.
    import re
    variants = {"sibc-svcs": "sibc-services", "sibc-ind-type": "sibc-industry-type"}
    for old, new in variants.items():
        stale = [k for k in REGISTRY if k.startswith(old + "-")]
        assert not stale, (
            f"'{old}-*' is a retired spelling of '{new}-*'; {stale} reintroduce it")


def test_the_mix_comparison_uses_one_denominator():
    """`weight` (share of the cut a year ago) and `weight_now` (share today) must come from the
    same family, because the share SCAN divides by the parent's published row while these divide
    by the sum of the parts — and for main sectors those differ by 4.9%. Reading "then" from one
    and "now" from the other would compare two different questions."""
    con = sqlite3.connect(DB)
    try:
        for stem in _cuts():
            alloc = f"{stem}-allocation"
            has = {r[0] for r in con.execute(
                "SELECT DISTINCT entity_type FROM signals WHERE metric_id=?", (alloc,))}
            if "weight" in has:
                assert "weight_now" in has, f"{alloc} stores the old share but not today's"
    finally:
        con.close()
