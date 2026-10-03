#!/usr/bin/env python3
"""
fetch.py — MoSPI stage 0: pull each dataset and save the release, before anything reads it
─────────────────────────────────────────────────────────────────────────────────────────
Runs on every gate run unless the gate is given --offline. A revision overwrites MoSPI's old value
in place, so a release not saved on the day is history lost: this is the one stage where skipping
costs something that cannot be recovered later (signals/README, "saving every release").

For each API dataset the manifest declares:
  1. every declared request is fetched under the contract in `mospi_api` (any breach → nothing saved);
  2. rows the manifest declares dropped (WPI items) are dropped;
  3. the rows are compared with the dataset's last saved release. Unchanged → nothing is written
     (a release is what MoSPI SAID, not when we looked). Changed → a new file,
     `releases/{dataset}/{fetched}.json.gz`, never rewritten afterwards.

CPI is read from a press-release PDF (`--cpi-pdf`), because its 2024 base is not on the API. The PDF
itself is saved beside the parsed release, since it is the raw evidence.

Usage:
    python3 analysis/pipelines/mospi/fetch.py                     # every API dataset
    python3 analysis/pipelines/mospi/fetch.py --dataset wpi
    python3 analysis/pipelines/mospi/fetch.py --cpi-pdf ~/Downloads/CPI_Aug_2026.pdf
"""
from __future__ import annotations

import argparse
import hashlib
import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import mospi_api                                     # noqa: E402
import releases as R                                 # noqa: E402


def stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H%M%SZ")


def fetch_api(name: str, ds: dict, api: dict) -> list[dict]:
    rows = []
    for req in ds["requests"]:
        rows += mospi_api.fetch_request(api["base_url"], ds["endpoint"], req["filters"],
                                        api["page_size"], api.get("workers", 1),
                                        verify=req.get("verify", []))
    drop = ds.get("drop_rows_where_set", [])
    kept = [r for r in rows if not any(r.get(f) not in (None, "") for f in drop)]
    if not kept:
        raise mospi_api.FetchError(f"{name}: every row was dropped by {drop}")
    return kept


def save_if_changed(name: str, doc: dict, raw: bytes | None = None, raw_ext: str = "") -> str:
    """Write the release unless its rows equal the last saved one's. Returns what happened."""
    doc["rows"] = R.canonical_rows(doc["rows"])
    prior = R.saved(name)
    if prior and doc.get("scope") == "snapshot" and R.read(prior[-1])["rows"] == doc["rows"]:
        return f"unchanged since {prior[-1].name.split('.')[0]} ({len(doc['rows'])} rows)"
    if prior and doc.get("sha256") and any(R.read(p).get("sha256") == doc["sha256"] for p in prior):
        return f"already saved: {doc['source_file']}"
    out = R.releases_dir() / name / f"{doc['fetched']}.json.gz"
    out.parent.mkdir(parents=True, exist_ok=True)
    if out.exists():
        raise SystemExit(f"✗ {out} exists: a saved release is never rewritten")
    out.write_bytes(R.dump(doc))
    if raw is not None:
        out.with_name(f"{doc['fetched']}.{raw_ext}").write_bytes(raw)
    return f"saved {out.relative_to(R.releases_dir().parent.parent.parent)} ({len(doc['rows'])} rows)"


def cpi_doc(ds: dict, source: str, file_name: str, raw: bytes, published: str, rows: list) -> dict:
    return {"dataset": "cpi", "base_year": ds["base_year"], "scope": ds["release_scope"],
            "source": source, "published": published, "fetched": stamp(),
            "source_file": file_name, "sha256": hashlib.sha256(raw).hexdigest(), "rows": rows}


def fetch_cpi_pdf(pdf: Path, ds: dict) -> str:
    """A press release, read by hand: its URL is not predictable."""
    import cpi_release
    raw = pdf.read_bytes()
    text = cpi_release.pdf_text(pdf)
    doc = cpi_doc(ds, "release_pdf", pdf.name, raw, cpi_release.published(text),
                  cpi_release.parse(text))
    return save_if_changed("cpi", doc, raw, "pdf")


def the_workbook(listing: dict) -> dict:
    """The one Excel file the CPI page lists, or FetchError.

    `file_type` was "xlsx" until Oct 2026, then null with the same file listed; the name's
    extension is the fallback, so a PDF or CSV listed beside it still fails the count.
    """
    files = [f for f in (listing.get("data") or [])
             if (f.get("file_type") or Path(f.get("file_name") or "").suffix.lstrip(".")).lower() == "xlsx"]
    if not listing.get("exists") or len(files) != 1:
        raise mospi_api.FetchError(f"expected one CPI workbook, the page lists {listing.get('data')!r}")
    return files[0]


def fetch_cpi_workbook(ds: dict, local: Path | None = None) -> str:
    """The 'download data' workbook: fetched from MoSPI's CPI page, or read from a local copy.

    The page's own list endpoint names the current file; exactly one is expected. A second file,
    or none, is a change in how MoSPI publishes it, and raises rather than picking one.
    """
    import cpi_dashboard
    src = ds["sources"]["dashboard_xlsx"]
    if local is not None:
        name, raw = local.name, local.read_bytes()
    else:
        listed = the_workbook(mospi_api.get_json(src["list_url"]))
        name = listed["file_name"]
        raw = mospi_api.get_bytes(src["download_url"].format(id=listed["id"]))
    doc = cpi_doc(ds, "dashboard_xlsx", name, raw, cpi_dashboard.published(name),
                  cpi_dashboard.parse(raw))
    return save_if_changed("cpi", doc, raw, "xlsx")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--dataset", help="fetch one API dataset only")
    ap.add_argument("--cpi-pdf", type=Path, help="read a CPI press release PDF (base 2024)")
    ap.add_argument("--cpi-xlsx", type=Path, help="read a local copy of the CPI 'download data' workbook")
    args = ap.parse_args()
    man = R.load_manifest()

    if args.cpi_pdf or args.cpi_xlsx:
        ds = man["datasets"]["cpi"]
        msg = fetch_cpi_pdf(args.cpi_pdf, ds) if args.cpi_pdf else fetch_cpi_workbook(ds, args.cpi_xlsx)
        print(f"  ✓ cpi: {msg}")
        return 0

    names = [args.dataset] if args.dataset else list(man["datasets"])
    failed, fetched = False, 0
    for name in names:
        ds = man["datasets"][name]
        if ds["source"] == "release_files":
            try:
                print(f"  ✓ {name} workbook: {fetch_cpi_workbook(ds)}")
                fetched += 1
            except (mospi_api.FetchError, ValueError) as e:
                print(f"  ✗ {name} workbook: {e}", file=sys.stderr)
                failed = True
            print(f"  · {name} press releases are read by hand (fetch.py --cpi-pdf <file>); "
                  f"the calendar check (1b) says if one is overdue.")
            continue
        try:
            rows = fetch_api(name, ds, man["api"])
        except mospi_api.FetchError as e:
            print(f"  ✗ {name}: {e}", file=sys.stderr)
            failed = True
            continue
        doc = {"dataset": name, "base_year": ds["base_year"], "scope": ds["release_scope"],
               "fetched": stamp(), "endpoint": ds["endpoint"],
               "requests": [r["filters"] for r in ds["requests"]], "rows": rows}
        print(f"  ✓ {name}: {save_if_changed(name, doc)}")
        fetched += 1
    if failed:
        print("  ✗ fetch contract breached: nothing was saved for the failing dataset(s)", file=sys.stderr)
        return 1
    print(f"  ✓ releases current: {fetched} fetched automatically")
    return 0


if __name__ == "__main__":
    sys.exit(main())
