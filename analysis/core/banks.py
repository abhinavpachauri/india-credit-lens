#!/usr/bin/env python3
"""
banks.py — one identity for every bank, across every source
───────────────────────────────────────────────────────────
BANKWISE_SPEC.md §6. RBI names the same bank differently in different releases ("HDFC BANK LTD."
on DBIE, "HDFC BANK LTD" in the card statistics, "Bank Of Baroda" on one DBIE sheet and "BANK OF
BARODA" on the next). A bank view that sets one bank's credit book beside its card book needs one
id per bank, and a missing alias must never look like "this source does not cover the bank".

The roster (`analysis/ontology/banks.json`) holds, for every bank and every registered source,
EITHER the names that source uses (each optionally dated, for renames) OR `not_in_source` with a
reason. A name no entry claims raises; so does a bank with neither for some source. A bank's group
is not stored here: it is the block RBI printed the bank in, read per quarter (§6).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core.paths import ROOT  # noqa: E402

ROSTER = ROOT / "analysis/ontology/banks.json"


class UnknownBank(KeyError):
    """A name no roster entry claims for this source (or claims outside its dates)."""


def key(name: str) -> str:
    """How two spellings of one name compare: case, spacing, punctuation and a trailing '.' ignored
    ("KRISHNA  BHIMA  SAMRUDDHI   LAB LTD." = "Krishna Bhima Samruddhi Lab Ltd")."""
    return " ".join(re.sub(r"[^A-Z0-9&]+", " ", name.upper()).split())


def load(path: Path = ROSTER) -> dict:
    return json.loads(path.read_text())


def validate(roster: dict) -> list[str]:
    """Every bank answers for every registered source; ids and (source, name) pairs are unique."""
    errs, ids, claimed = [], set(), {}
    sources = roster["_meta"]["sources"]
    for b in roster["banks"]:
        if b["id"] in ids:
            errs.append(f"duplicate id {b['id']}")
        ids.add(b["id"])
        for s in sources:
            entry = b.get("sources", {}).get(s)
            if not entry or (not entry.get("names") and not entry.get("not_in_source")):
                errs.append(f"{b['id']}: no names and no not_in_source for {s}")
                continue
            if entry.get("names") and entry.get("not_in_source"):
                errs.append(f"{b['id']}: both names and not_in_source for {s}")
            for n in entry.get("names", []):
                k = (s, key(n["name"]))
                if k in claimed and claimed[k] != b["id"]:
                    errs.append(f"{s} name {n['name']!r} claimed by {claimed[k]} and {b['id']}")
                claimed[k] = b["id"]
        for s in b.get("sources", {}):
            if s not in sources:
                errs.append(f"{b['id']}: unregistered source {s}")
    return errs


class Resolver:
    """name (as a source prints it) → bank id, for one source."""

    def __init__(self, source: str, roster: dict | None = None):
        roster = roster or load()
        if source not in roster["_meta"]["sources"]:
            raise KeyError(f"source {source!r} is not registered in {ROSTER.name}")
        errs = validate(roster)
        if errs:
            raise ValueError(f"{ROSTER.name}: " + "; ".join(errs[:5]))
        self.source, self._by = source, {}
        for b in roster["banks"]:
            for n in b["sources"][source].get("names", []):
                self._by.setdefault(key(n["name"]), []).append((b["id"], n.get("from"), n.get("to")))

    def __call__(self, name: str, on: str | None = None) -> str:
        """The bank id; `on` (ISO date) applies an alias's validity dates. Unknown raises."""
        hits = self._by.get(key(name), [])
        ok = sorted({bid for bid, f, t in hits if on is None or ((f is None or f <= on) and (t is None or on <= t))})
        if len(ok) == 1:
            return ok[0]
        if not hits:
            raise UnknownBank(f"{self.source}: {name!r} is in no roster entry; add it to {ROSTER.name}")
        raise UnknownBank(f"{self.source}: {name!r} on {on} matches {len(ok)} entries (aliases dated "
                          f"{[(f, t) for _, f, t in hits]})")


# ── how a bank is named on screen ─────────────────────────────────────────────────────────────
# The roster's `name` is RBI's own spelling, title-cased ("Hdfc Bank Ltd.", "Icici Bank Limited"):
# right for matching, wrong for reading. The display name is DERIVED from it by one rule (legal
# suffixes dropped, acronyms and small words restored); a bank the rule gets wrong carries a
# `short` in the roster, so the exception is data and the rule stays one rule.
_SUFFIX = re.compile(r"[\s,]*(?:\b(?:limited|ltd|plc|pjsc|psc|ag|nv|n\.?v|n\.?a|s\.?a\.?o\.?g|b\.?s\.?c|q\.?p\.?s\.?c"
                     r"|p\.?j\.?s\.?c|tbk|u\.?a|co)\b\.?|\((?:q\.?p\.?s\.?c|p\.?j\.?s\.?c\.?)\)|[\s.,])+$", re.I)
_ACRONYM = {"hdfc", "icici", "idfc", "idbi", "sbm", "au", "dcb", "rbl", "uco", "csb", "esaf", "dbs",
            "bnp", "hsbc", "ubs", "jsc", "vtb", "kbc", "keb", "mufg", "nbd", "jpmorgan", "ctbc",
            "nsdl", "pt", "anz", "lab", "sbi"}
_SMALL = {"of", "and", "the"}


def display(entry: dict) -> str:
    """A bank's name as a reader says it: "HDFC Bank", "State Bank of India", "J&K Bank"."""
    if entry.get("short"):
        return entry["short"]
    words = _SUFFIX.sub("", " ".join(entry["name"].split())).split()
    out = []
    for i, w in enumerate(words):
        lw = w.lower()
        if lw in _ACRONYM:
            out.append("JPMorgan" if lw == "jpmorgan" else lw.upper())
        elif i and lw in _SMALL:
            out.append(lw)
        else:
            out.append(w)
    return " ".join(out)


def labels(path: Path = ROSTER) -> dict[str, str]:
    """{roster id: display name} for every bank."""
    return {b["id"]: display(b) for b in load(path)["banks"]}
