#!/usr/bin/env python3
"""
bank_sourcing.py — the deep read's bank "why" engine (DISTRIBUTION_SPEC §11.2)
--------------------------------------------------------------------------------
Part A of the deep read says WHICH banks moved, computed from the data. This engine adds
the WHY for the featured banks — and a why is a claim about the world, so it can never come
from the model. It comes from a source, with a link, verified before it can publish.

The contract (the S4 sourcing gate, same discipline as `run_inference`):

  * every claim carries a URL, a verbatim excerpt, and a verified date
  * `status` must be "verified" to publish — nothing is auto-trusted, ever
  * an entry that fails `validate_entry` never reaches the reader; the spine falls back to
    its computed basis and the force already attached to it

The store (`bank_sourcing.json`) starts EMPTY on purpose. A why is not something the pipeline
can compute or the model can infer, and it is not something to invent to fill a slot — so
until a real source is found, verified, and written down, `sourced_why` returns None and the
deep read renders the honest fallback. Populating it is the S4 build: find the source, read
it, record the excerpt and the link, mark it verified. This module is the gate that stands
between that record and the reader; it is not a place to paraphrase a plausible-sounding
reason.

The same shape carries the second reference each spine reserves — an independent corroborating
source (RBI bulletin, rating-agency note, financial press) that says the same thing, so the
read is triangulated, not ours alone.
"""
import json
from datetime import date
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
STORE = ROOT / "analysis" / "distribution" / "bank_sourcing.json"

# An excerpt shorter than this is not evidence — it is a label. The gate rejects it.
MIN_EXCERPT_CHARS = 40

REQUIRED = ("url", "excerpt", "verified_date", "tier")

# The tiered source allowlist (DISTRIBUTION_SPEC §11.2-R3). A source host must be on this list
# for its declared tier, or the entry is rejected — "reputed" is a controlled list, not a
# judgment call. Matching is by host suffix, so "economictimes.indiatimes.com" covers subpaths.
ALLOWLIST = {
    # T1 — official / regulatory
    "official": {"rbi.org.in", "pib.gov.in", "indiabudget.gov.in", "sebi.gov.in",
                 "npci.org.in", "bseindia.com", "nseindia.com", "finmin.nic.in",
                 # ministries/agencies whose releases back existing forces (MSME formalisation,
                 # UPI/digital-payments policy, macro stats) — added 2026-08-02.
                 "mospi.gov.in", "dea.gov.in", "meity.gov.in", "msme.gov.in",
                 "mca.gov.in", "data.gov.in", "cga.nic.in"},
    # T2 — reputed structured reports (bureaus, rating agencies, industry bodies, processors)
    "report": {"cibil.com", "transunioncibil.com", "crifhighmark.com", "crisil.com",
               "icra.in", "careedge.in", "careratings.com", "worldline.com",
               "iba.org.in", "pcipolicy.org", "npci.org.in",
               # completes the four RBI-licensed credit bureaus (Equifax, Experian) and the
               # rating-agency set (India Ratings/Fitch); MFIN = microfinance SRO; apex industry
               # bodies — added 2026-08-02.
               "equifax.co.in", "experian.in", "indiaratings.co.in", "mfinindia.com",
               "ficci.in", "assocham.org", "cii.in"},
    # T3 — named financial press (the fixed masthead allowlist, §11.2-R)
    "press": {"economictimes.indiatimes.com", "business-standard.com", "livemint.com",
              "thehindubusinessline.com", "financialexpress.com", "moneycontrol.com",
              "reuters.com", "bloomberg.com",
              # additional named financial-press mastheads at the same bar — added 2026-08-02.
              "ndtvprofit.com", "cnbctv18.com", "thehindu.com", "indianexpress.com",
              "fortuneindia.com", "forbesindia.com"},
}
TIER_LABEL = {"official": "official/regulatory", "report": "reputed report",
              "press": "financial press"}


def _host(url):
    from urllib.parse import urlparse
    return (urlparse(url).hostname or "").lower().lstrip("www.")


def tier_of(url):
    """The tier a URL's host belongs to (official/report/press), or None if off the allowlist."""
    host = _host(url)
    for tier, hosts in ALLOWLIST.items():
        if any(host == h or host.endswith("." + h) or host == h.replace("www.", "")
               for h in hosts):
            return tier
    return None


def _empty():
    return {
        "_meta": {
            "purpose": "Verified, sourced 'why' claims for featured banks and independent "
                       "corroborating references for deep-read spines. Every entry is S4-gated: "
                       "URL + verbatim excerpt + verified date, status must be 'verified' to "
                       "publish. Starts empty — a why is sourced, never inferred or invented.",
            "spec": "analysis/distribution/DISTRIBUTION_SPEC.md §11.2",
            "gate": "analysis/distribution/bank_sourcing.py :: validate_entry",
        },
        "bank_claims": [],
        "corroborations": [],
    }


def load():
    return json.loads(STORE.read_text()) if STORE.exists() else _empty()


def save(store):
    STORE.write_text(json.dumps(store, indent=1, ensure_ascii=False) + "\n")


def validate_entry(e):
    """Return a list of reasons this entry may NOT publish. Empty = it passes the S4 gate."""
    problems = []
    for field in REQUIRED:
        if not (e.get(field) or "").strip():
            problems.append(f"missing {field}")
    url = (e.get("url") or "").strip()
    if url and not url.startswith(("http://", "https://")):
        problems.append(f"url is not a link: {url!r}")
    tier = e.get("tier")
    if url and tier:
        host_tier = tier_of(url)
        if host_tier is None:
            problems.append(f"host {_host(url)!r} is not on any tier's allowlist")
        elif host_tier != tier:
            problems.append(f"declared tier {tier!r} but host {_host(url)!r} is tier {host_tier!r}")
    excerpt = (e.get("excerpt") or "").strip()
    if excerpt and len(excerpt) < MIN_EXCERPT_CHARS:
        problems.append(f"excerpt too short to be evidence ({len(excerpt)} < {MIN_EXCERPT_CHARS})")
    if not e.get("excerpt_verified"):
        problems.append("excerpt not WebFetch-verified on the page (excerpt_verified is false)")
    if e.get("status") != "verified":
        problems.append(f"status is {e.get('status')!r}, not 'verified' — never auto-trusted")
    return problems


def _publishable(entries):
    """Only the entries that clear the gate. A failing entry is not an error here — it is a
    record that has not been verified yet, and it simply does not publish."""
    return [e for e in entries if not validate_entry(e)]


def sourced_why(bank, dimension=None):
    """The verified 'why' for a bank (optionally scoped to a dimension), or None.

    Matches on the reader-case bank name so callers pass what Part A shows. None means no
    verified source exists — the caller renders the computed fallback."""
    store = load()
    for e in _publishable(store.get("bank_claims", [])):
        if e.get("bank") == bank and (dimension is None or e.get("dimension") == dimension):
            return e
    return None


def corroborations(spine_id):
    """All verified corroborating references for a spine (may be several tiers)."""
    return [e for e in _publishable(load().get("corroborations", []))
            if e.get("spine_id") == spine_id]


def corroboration(spine_id):
    """The first verified corroborating reference for a spine, or None (back-compat)."""
    return next(iter(corroborations(spine_id)), None)


# ── Verification — the free, deterministic step that kills a hallucinated URL ──────────────

def _normalise(text):
    import re
    return re.sub(r"\s+", " ", (text or "")).lower().strip()


def excerpt_on_page(excerpt, page_text):
    """True iff the verbatim excerpt actually appears on the page (whitespace-insensitive).

    This is the check that makes the sourcing trustworthy: an LLM can propose a plausible URL
    and a plausible quote, but only a real page that literally contains the quote passes. Kept
    pure (takes the already-fetched page text) so it is deterministic and unit-testable; the
    caller does the fetch (WebFetch here, urllib in a headless cadence run)."""
    ex = _normalise(excerpt)
    return len(ex) >= MIN_EXCERPT_CHARS and ex in _normalise(page_text)


def add_bank_claim(entry, page_text):
    """Verify an excerpt against the fetched page, stamp the result, gate it, and write it only
    if it passes. Returns (ok, problems). Never writes an entry that fails the gate."""
    entry = dict(entry)
    entry["excerpt_verified"] = excerpt_on_page(entry.get("excerpt", ""), page_text)
    if not entry.get("tier"):
        entry["tier"] = tier_of(entry.get("url", ""))
    entry["status"] = "verified" if entry["excerpt_verified"] else "unverified"
    problems = validate_entry(entry)
    if problems:
        return False, problems
    store = load()
    store.setdefault("bank_claims", [])
    # idempotent per (bank, dimension, url)
    store["bank_claims"] = [c for c in store["bank_claims"]
                            if not (c.get("bank") == entry.get("bank")
                                    and c.get("dimension") == entry.get("dimension")
                                    and c.get("url") == entry.get("url"))]
    store["bank_claims"].append(entry)
    save(store)
    return True, []


def add_corroboration(entry, page_text):
    """Same verify → gate → write as add_bank_claim, for a spine's independent corroborating
    reference (the 'others are seeing it too' second source). Keyed by spine_id."""
    entry = dict(entry)
    entry["excerpt_verified"] = excerpt_on_page(entry.get("excerpt", ""), page_text)
    if not entry.get("tier"):
        entry["tier"] = tier_of(entry.get("url", ""))
    entry["status"] = "verified" if entry["excerpt_verified"] else "unverified"
    problems = validate_entry(entry)
    if problems:
        return False, problems
    store = load()
    store.setdefault("corroborations", [])
    store["corroborations"] = [c for c in store["corroborations"]
                               if not (c.get("spine_id") == entry.get("spine_id")
                                       and c.get("url") == entry.get("url"))]
    store["corroborations"].append(entry)
    save(store)
    return True, []


def validate_store():
    """Every entry that CLAIMS to be verified must actually pass the gate. Guards against a
    hand-edit that sets status='verified' but forgets the excerpt or the link. Returns a list
    of failure strings; empty = the store is publishable."""
    store = load()
    fails = []
    for kind in ("bank_claims", "corroborations"):
        for e in store.get(kind, []):
            if e.get("status") == "verified":
                for p in validate_entry(e):
                    who = e.get("bank") or e.get("spine_id") or "?"
                    fails.append(f"{kind}[{who}]: {p}")
    return fails


def _cmd_add(a):
    """Verify one claim against page text and write it only if the excerpt is literally there.

    Page text comes from `--page-file` (what a real browser/editor extracted — the channel the
    blocked sites permit) or, when a source is reachable, a plain urllib fetch. Either way the
    trust anchor is the same: the verbatim excerpt must appear on the page."""
    page = ""
    if a.page_file:
        page = Path(a.page_file).read_text(errors="ignore")
    else:
        import urllib.request
        try:
            req = urllib.request.Request(a.url, headers={"User-Agent": "curl/8"})
            page = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
        except Exception as e:                        # a 403/timeout is an honest 'unverifiable'
            print(f"could not fetch {a.url}: {e}\n→ provide --page-file from a browser that can "
                  f"reach it (the crawler is blocked; that is the point of the check).")
            return 1
    entry = {"bank": a.bank, "dimension": a.dimension, "why": a.why, "url": a.url,
             "excerpt": a.excerpt, "verified_date": date.today().isoformat(), "date": a.date}
    ok, problems = add_bank_claim(entry, page)
    if ok:
        print(f"✓ verified + written: {a.bank} — tier {tier_of(a.url)} — {a.url}")
        return 0
    print("✗ not written:")
    for p in problems:
        print("   ", p)
    return 1


def main():
    import argparse
    ap = argparse.ArgumentParser(description="S4a bank-sourcing store (DISTRIBUTION_SPEC §11.2-R3)")
    sub = ap.add_subparsers(dest="cmd")
    add = sub.add_parser("add", help="verify + write one sourced bank why")
    for f in ("bank", "dimension", "why", "url", "excerpt"):
        add.add_argument(f"--{f}", required=True)
    add.add_argument("--date", default="")
    add.add_argument("--page-file", help="path to page text (from a browser that can reach it)")
    a = ap.parse_args()
    if a.cmd == "add":
        return _cmd_add(a)

    store = load()
    bank = len(_publishable(store.get("bank_claims", [])))
    corr = len(_publishable(store.get("corroborations", [])))
    fails = validate_store()
    print(f"bank_sourcing: {bank} verified bank claim(s), {corr} verified corroboration(s)")
    if fails:
        print("\nentries marked verified that do NOT pass the gate:")
        for f in fails:
            print("  ✗", f)
        return 1
    if bank == 0 and corr == 0:
        print("store is empty — the deep read falls back to computed basis (§11.2). Populate with "
              "`add` (URL + verbatim excerpt + a page text a browser can reach; the crawler is blocked).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
