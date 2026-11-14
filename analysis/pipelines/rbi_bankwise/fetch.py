#!/usr/bin/env python3
"""
fetch.py — save a DBIE bank-wise export as one release per quarter (BANKWISE_SPEC.md §4)
──────────────────────────────────────────────────────────────────────────────────────────
The editor's Chrome downloads the export (DBIE cannot be scripted); this reads it (`reader.py`) and
saves each quarter as `releases/{quarter}/{saved-date}.json.gz` (deterministic gzip, so the same
content is the same bytes). DBIE prints no publication date, so a release is keyed by quarter.

Every quarter in an export is reported as NEW, UNCHANGED or REVISED, and three outcomes that would
otherwise look like a clean run fail instead:
  * no quarter is new (stale prompts, or the quarter not on DBIE yet) — unless
    `--no-new-quarter-expected`;
  * a quarter differs from what is saved — rows added, removed or changed are listed and nothing is
    written, unless `--accept-revision {quarter}` (the old release is kept beside the new one);
  * an export that adds the newest quarter but does not re-read the latest saved ones (up to 8): a
    revision check that compared nothing would read as "no revisions".

    python3 analysis/pipelines/rbi_bankwise/fetch.py --xlsx FILE [FILE …] [--no-new-quarter-expected]
        [--accept-revision 2025-06-30] [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime
import gzip
import hashlib
import io
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT  # noqa: E402


def _own(name: str, file: Path):
    """Load a module of THIS pipeline under its own name: `reader` and `fetch` also exist in
    pipelines/rbi_rates, and a bare `import reader` takes whichever was imported first."""
    import importlib.util
    if name in sys.modules:
        return sys.modules[name]
    spec = importlib.util.spec_from_file_location(name, file)
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


reader = _own("rbi_bankwise_reader", HERE / "reader.py")

RELEASES = ROOT / "analysis/rbi_bankwise/releases"
RECHECK = 8          # saved quarters a current-period export must re-read


class SaveRefused(SystemExit):
    pass


def dump(doc: dict) -> bytes:
    raw = json.dumps(doc, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb", mtime=0, compresslevel=9) as g:
        g.write(raw)
    return buf.getvalue()


def load(path: Path) -> dict:
    return json.loads(gzip.decompress(path.read_bytes()))


def saved_quarters(root: Path = RELEASES) -> dict[str, Path]:
    """quarter → its latest saved release (files sort by saved date)."""
    out = {}
    if root.exists():
        for d in sorted(root.iterdir()):
            files = sorted(d.glob("*.json.gz"))
            if files:
                out[d.name] = files[-1]
    return out


def content(q: dict, names: dict) -> dict:
    """What a quarter says, independent of which file or day it came from."""
    return {"banks": {b: {"group": v["group"], "name": names.get(b), "sheets": v["sheets"]} for b, v in q["banks"].items()},
            "groups": q["groups"]}


def diff(old: dict, new: dict) -> list[str]:
    """Every row added, removed or changed: (entity, sheet, column)."""
    out = []
    for kind in ("banks", "groups"):
        a, b = old.get(kind, {}), new.get(kind, {})
        for e in sorted(set(a) - set(b)):
            out.append(f"removed {kind[:-1]} {e}")
        for e in sorted(set(b) - set(a)):
            out.append(f"added {kind[:-1]} {e}")
        for e in sorted(set(a) & set(b)):
            sa, sb = a[e].get("sheets", {}), b[e].get("sheets", {})
            for s in sorted(set(sa) | set(sb)):
                ca, cb = sa.get(s, {}), sb.get(s, {})
                for c in sorted(set(ca) | set(cb)):
                    if ca.get(c) != cb.get(c):
                        out.append(f"changed {e} {s} {c}: {ca.get(c)} → {cb.get(c)}")
            if kind == "banks" and a[e].get("group") != b[e].get("group"):
                out.append(f"changed {e} group: {a[e].get('group')} → {b[e].get('group')}")
            if kind == "groups" and a[e].get("members") != b[e].get("members"):
                out.append(f"changed {e} members")
    return out


def history_start() -> str:
    """The declared first quarter (manifest `calendar.first_quarter`)."""
    from core import manifest
    return manifest.load("rbi_bankwise")["calendar"]["first_quarter"]


def save(paths: list[Path], no_new_expected: bool = False, accept: set[str] = frozenset(),
         dry_run: bool = False, root: Path = RELEASES, today: str | None = None,
         start: str | None = None) -> list[str]:
    today = today or datetime.date.today().isoformat()
    start = start or history_start()
    have = saved_quarters(root)
    report, writes, revised = [], [], []
    seen: dict[str, dict] = {}
    for p in paths:
        got = reader.read(p)
        sha = hashlib.sha256(p.read_bytes()).hexdigest()
        for quarter, q in got["quarters"].items():
            if quarter < start:
                report.append(f"SKIPPED    {quarter}: before the declared history start {start}")
                continue
            body = content(q, got["names"])
            if quarter in seen and seen[quarter] != body:
                raise SaveRefused(f"✗ {quarter} differs between two of the files given; export once and retry")
            seen[quarter] = body
            doc = {"quarter": quarter, "source_file": p.name, "sha256": sha, "saved": today, **body}
            if quarter not in have:
                report.append(f"NEW        {quarter}: {len(body['banks'])} banks")
                writes.append((quarter, doc))
                continue
            changes = diff({k: v for k, v in load(have[quarter]).items() if k in ("banks", "groups")}, body)
            if not changes:
                report.append(f"UNCHANGED  {quarter}")
            elif quarter in accept:
                report.append(f"REVISED    {quarter}: {len(changes)} change(s), accepted; previous release kept")
                writes.append((quarter, doc))
            else:
                revised.append((quarter, changes))
    new = [q for q in seen if q not in have]
    rechecked = sorted(q for q in seen if q in have)
    report.append(f"revisions checked: {len(rechecked)} saved quarter(s) re-read, {len(revised)} changed"
                  if rechecked else "revisions checked: not checked (no saved quarter re-read)")
    if revised:
        lines = [f"✗ {q} was revised ({len(c)} change(s)); nothing written. Decide, then re-run with "
                 f"--accept-revision {q}:\n    " + "\n    ".join(c[:12]) + ("\n    …" if len(c) > 12 else "")
                 for q, c in revised]
        raise SaveRefused("\n".join(report + lines))
    if not new and not no_new_expected:
        raise SaveRefused("\n".join(report + ["✗ no quarter in this export is new (stale prompts, or the "
                                              "quarter is not on DBIE yet); pass --no-new-quarter-expected "
                                              "if that is intended"]))
    if have and new and max(new) > max(have):
        latest = sorted(have)[-RECHECK:]
        missing = [q for q in latest if q not in seen]
        if missing:
            raise SaveRefused("\n".join(report + [f"✗ adds {max(new)} but does not re-read the latest saved "
                                                  f"quarter(s) {missing}; export them with it"]))
    if not dry_run:
        for quarter, doc in writes:
            target = root / quarter / f"{today}.json.gz"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(dump(doc))
    return report


def main() -> int:
    ap = argparse.ArgumentParser(description="Save a DBIE bank-wise export as one release per quarter")
    ap.add_argument("--xlsx", nargs="+", type=Path, required=True)
    ap.add_argument("--no-new-quarter-expected", action="store_true")
    ap.add_argument("--accept-revision", nargs="*", default=[])
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()
    try:
        for line in save(a.xlsx, a.no_new_quarter_expected, set(a.accept_revision), a.dry_run):
            print("  " + line)
    except SaveRefused as e:
        print(e, file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
