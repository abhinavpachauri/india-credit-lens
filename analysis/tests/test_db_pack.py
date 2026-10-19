"""signals/db_pack.py: the committed, compressed store and the working copy (signals/README.md,
"How the store is committed"). Every row of the state table, on throwaway files."""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from signals import db_pack as P          # noqa: E402


@pytest.fixture
def files(tmp_path):
    f = {k: tmp_path / n for k, n in (("db", "signals.db"), ("gz", "signals.db.gz"),
                                       ("sha", "signals.db.sha256"), ("synced", ".synced"))}
    f["db"].write_bytes(b"version-1" * 1000)
    return f


def st(f):
    return P.state(f["db"], f["sha"], f["synced"])


def pack(f):
    return P.pack(f["db"], f["gz"], f["sha"], f["synced"])


def unpack(f):
    return P.unpack(f["db"], f["gz"], f["sha"], f["synced"])


def test_first_pack_then_in_sync(files):
    assert st(files) == "not_packed"
    assert pack(files) and st(files) == "in_sync"
    assert pack(files) is False                        # nothing to do


def test_packing_is_byte_identical_for_the_same_store(files):
    pack(files)
    first = files["gz"].read_bytes()
    files["sha"].write_text("x\n"); files["synced"].write_text("x\n")
    pack(files)
    assert files["gz"].read_bytes() == first


def test_a_fresh_clone_unpacks(files):
    pack(files)
    files["db"].unlink(); files["synced"].unlink()
    assert st(files) == "missing" and unpack(files) and st(files) == "in_sync"


def test_a_pulled_newer_store_unpacks_over_an_untouched_working_copy(files):
    pack(files)
    v1 = files["db"].read_bytes()
    files["db"].write_bytes(b"version-2" * 1000); pack(files)        # "someone else" packs v2
    files["db"].write_bytes(v1); files["synced"].write_text(P.fingerprint(files["db"]) + "\n")
    assert st(files) == "pull_not_unpacked"
    assert unpack(files) and files["db"].read_bytes() == b"version-2" * 1000


def test_local_changes_are_never_overwritten_by_unpack(files):
    pack(files)
    files["db"].write_bytes(b"local-edit" * 1000)
    assert st(files) == "not_packed" and unpack(files) is False
    assert files["db"].read_bytes() == b"local-edit" * 1000


def test_both_sides_changed_stops_both_ways(files):
    pack(files)
    files["db"].write_bytes(b"remote" * 1000); pack(files)
    files["synced"].write_text("an-older-sync\n")
    files["db"].write_bytes(b"local" * 1000)
    assert st(files) == "conflict"
    with pytest.raises(SystemExit):
        pack(files)
    with pytest.raises(SystemExit):
        unpack(files)
    assert files["db"].read_bytes() == b"local" * 1000


def test_an_inconsistent_committed_pair_refuses_to_unpack(files):
    pack(files)
    files["db"].unlink(); files["sha"].write_text("0" * 64 + "\n")
    with pytest.raises(SystemExit):
        unpack(files)
    assert not files["db"].exists()
