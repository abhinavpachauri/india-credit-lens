#!/usr/bin/env python3
"""
db_pack.py — keep the committed, compressed signal store and the local working copy in step.
─────────────────────────────────────────────────────────────────────────────────────────────
signals/README.md, "How the store is committed". The repo commits `signals.db.gz` (deterministic
gzip) and `signals.db.sha256`; `signals.db` is the local working copy. Three fingerprints decide
what to do, and the one case where both sides changed stops instead of overwriting either.

    python3 analysis/signals/db_pack.py status
    python3 analysis/signals/db_pack.py pack       # after local changes (the pre-commit hook does it)
    python3 analysis/signals/db_pack.py unpack     # after a clone or pull (post-merge/checkout hooks)
"""
from __future__ import annotations

import gzip
import hashlib
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
DB, PACK, SHA, SYNCED = (HERE / "signals.db", HERE / "signals.db.gz",
                         HERE / "signals.db.sha256", HERE / ".signals.db.synced")
CHUNK = 1 << 20


def fingerprint(path: Path) -> str | None:
    if not path.exists():
        return None
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(CHUNK), b""):
            h.update(block)
    return h.hexdigest()


def _read(path: Path) -> str | None:
    return path.read_text().strip() or None if path.exists() else None


def state(db: Path = DB, sha: Path = SHA, synced: Path = SYNCED) -> str:
    """in_sync · missing · pull_not_unpacked · not_packed · conflict · nothing_committed."""
    committed, local, last = _read(sha), fingerprint(db), _read(synced)
    if committed is None:
        return "nothing_committed" if local is None else "not_packed"
    if local is None:
        return "missing"
    if local == committed:
        return "in_sync"
    if local == last:
        return "pull_not_unpacked"          # the working copy is untouched since its last sync
    if committed == last:
        return "not_packed"                 # only the working copy moved
    return "conflict"                       # both moved since the last sync


def pack(db: Path = DB, gz: Path = PACK, sha: Path = SHA, synced: Path = SYNCED) -> bool:
    """Write the deterministic .gz and its fingerprint from the working copy. True if they changed."""
    st = state(db, sha, synced)
    if st == "missing":
        raise SystemExit("✗ there is no signals.db to pack: run `db_pack.py unpack` to restore it")
    if st == "conflict":
        raise SystemExit("✗ signals.db and the committed store both changed since the last sync; "
                         "decide which wins before packing (nothing was written)")
    if st == "in_sync":
        return False
    if st == "pull_not_unpacked":
        raise SystemExit("✗ the committed store is newer than signals.db: run `db_pack.py unpack` first")
    tmp = gz.with_suffix(".gz.tmp")
    with open(db, "rb") as src, open(tmp, "wb") as raw:
        # filename '' and mtime 0: identical content gives identical bytes, so no spurious diffs.
        with gzip.GzipFile(filename="", mode="wb", compresslevel=6, fileobj=raw, mtime=0) as out:
            shutil.copyfileobj(src, out, CHUNK)
    tmp.replace(gz)
    fp = fingerprint(db)
    sha.write_text(fp + "\n")
    synced.write_text(fp + "\n")
    return True


def unpack(db: Path = DB, gz: Path = PACK, sha: Path = SHA, synced: Path = SYNCED) -> bool:
    """Restore the working copy from the committed store when it is safe. True if it was written."""
    st = state(db, sha, synced)
    if st in ("in_sync", "nothing_committed"):
        return False
    if st == "not_packed":
        return False                        # local work is newer; never overwrite it
    if st == "conflict":
        raise SystemExit("✗ signals.db and the committed store both changed since the last sync; "
                         "decide which wins (nothing was overwritten)")
    tmp = db.with_suffix(".db.tmp")
    with gzip.open(gz, "rb") as src, open(tmp, "wb") as out:
        shutil.copyfileobj(src, out, CHUNK)
    if fingerprint(tmp) != _read(sha):
        tmp.unlink()
        raise SystemExit("✗ signals.db.gz does not match signals.db.sha256: the committed pair is inconsistent")
    tmp.replace(db)
    synced.write_text(_read(sha) + "\n")
    return True


def require_in_sync() -> None:
    """For checks that read the store as if it were the committed one (freshness, 2f)."""
    st = state()
    if st != "in_sync" and st != "not_packed":
        raise SystemExit(f"✗ signals.db is {st}: run `python3 analysis/signals/db_pack.py "
                         f"{'unpack' if st in ('missing', 'pull_not_unpacked') else 'status'}` first")


def main() -> int:
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd == "status":
        print(f"  signals.db: {state()}")
        return 0
    if cmd == "pack":
        print("  ✓ packed signals.db.gz" if pack() else "  · signals.db.gz already matches")
        return 0
    if cmd == "unpack":
        print("  ✓ unpacked signals.db" if unpack() else f"  · nothing to unpack ({state()})")
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main())
