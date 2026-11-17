#!/usr/bin/env python3
"""
table_labels.py — each table's share columns, named by what they divide by (DASHBOARD_SPEC §17.6)
──────────────────────────────────────────────────────────────────────────────────────────────
"of cut" and "of book" named a mechanism, not a denominator, and "of book" meant a different thing
on each page: all bank credit (SIBC), all NBFC credit (NBFC), the bank's own lending (bank-wise).
Readers forgot which (user, 2026-11-17), and the explanation lived only in a hover hint that a
phone never shows.

So each table now carries, rendered here like every other string:
  * `col_labels` — "% of industry", "% of all banks", "% of bank's book";
  * `key` — one always-visible sentence per share column, with the table's top row as the example
    ("Infrastructure is 31.7% of it"), whose number is that row's own cell, checked by
    `guards/validate_cut_table.py` like the cell itself.

Every name is DERIVED: a sector table's parent and denominator come from the consolidated CSV by
the codes the registry declares; a per-bank table's denominator is all banks by construction.
"""
from __future__ import annotations

import json
import re
from functools import lru_cache

from core import manifest
from core.paths import ROOT

REGISTRY = ROOT / "analysis" / "signals" / "registry.json"
_NOUN = {"sector": "sectors"}          # what a cut's rows are called, by entity type; else "parts"


def _sentence(name: str) -> str:
    """'Non-food Credit' -> 'non-food credit'; acronyms stay ('NBFC Credit' -> 'NBFC credit')."""
    name = re.sub(r"\s*\(.*?\)", "", name).strip()
    return " ".join(w if (w.isupper() and len(w) > 1) else w.lower() for w in name.split())


@lru_cache(maxsize=None)
def _registry() -> dict:
    return json.loads(REGISTRY.read_text())["signals"]


@lru_cache(maxsize=None)
def _names(pipeline: str) -> dict:
    """{(code, statement): sector name} from the consolidated CSV, for sector pipelines."""
    import pandas as pd
    df = pd.read_csv(manifest.consolidated_csv(pipeline))
    stmt = df["statement"] if "statement" in df.columns else ""
    out = {}
    for code, st, name in zip(df["code"].astype(str), stmt if len(stmt) else [""] * len(df), df["sector"]):
        out.setdefault((code, st), name)
        out.setdefault((code, None), name)
    return out


def _sector_name(pipeline: str, code, statement) -> str | None:
    if code is None:
        return None
    names = _names(pipeline)
    return names.get((str(code), statement)) or names.get((str(code), None))


def _top(table: dict, col: str):
    """The first row (largest by size) with a reading in `col`: the key's example."""
    for p in table["parts"]:
        if (p.get(col) or {}).get("display"):
            return p.get("label") or p["entity"], p[col]["display"]
    return None, None


def _measure_noun(pipeline: str, metric: str | None, title: str | None) -> str:
    """What a per-bank table measures, in a sentence: 'housing', 'credit cards'."""
    if title:
        return "credit" if title.lower() == "all credit" else _sentence(title)
    if metric:
        from signals.stamp_state import _label
        return _sentence(_label(metric))
    return "this measure"


def label(pipeline: str, stem: str, table: dict, per_bank: bool, measure_title: str | None = None) -> None:
    """Attach `col_labels` and `key` to one table, in place. Columns the table lacks get neither."""
    reg = _registry()
    cols = table.get("columns", {})
    labels, key = {}, []

    if "of_cut" in cols:
        top, v = _top(table, "of_cut")
        if per_bank:
            noun = _measure_noun(pipeline, table.get("metric"), measure_title)
            lab = "% of all banks"
            who = "bank" if table.get("level") == "bank" else "bank group"
            key.append(f"{lab}: each {who}'s share of all banks' {noun}"
                       + (f" ({top} holds {v})." if top else "."))
        else:
            mom = reg.get(f"{stem}-momentum", {}).get("compute", {})
            parent = _sector_name(pipeline, mom.get("parent_code"),
                                  mom.get("parent_statement") or mom.get("statement"))
            n = len(table["parts"])
            noun = _NOUN.get(mom.get("entity_type"), "parts")
            if table.get("coverage") is not None and parent and n == 1:
                # RBI names one part of this cut (NBFC industry → infrastructure only).
                lab = "% of the part shown"
                key.append(f"{lab}: RBI names one part here, and it is "
                           f"{table['coverage']:.1f}% of {_sentence(parent)}.")
            elif table.get("coverage") is not None and parent:
                lab = f"% of the {n} {noun}"
                key.append(f"{lab}: a slice of the {n} {noun} added up, which are "
                           f"{table['coverage']:.1f}% of {_sentence(parent)}.")
            elif parent:
                lab = f"% of {_sentence(parent)}"
                key.append(f"{lab}: each row's slice of {_sentence(parent)}"
                           + (f" ({top} is {v} of it)." if top else "."))
            else:
                lab = f"% of the {n} {noun}"
                key.append(f"{lab}: each row's slice of the {n} {noun} added up.")
        labels["of_cut"] = lab

    if "of_book" in cols:
        sig = reg.get(cols["of_book"], {}).get("compute", {})
        top, v = _top(table, "of_book")
        if sig.get("method") == "csv_bank_ratio_scan":
            lab = "% of bank's book"
            noun = _measure_noun(pipeline, table.get("metric"), measure_title)
            key.append(f"{lab}: {noun} as a share of that bank's own lending"
                       + (f" ({v} of {top}'s)." if top else "."))
        else:
            denom = _sector_name(pipeline, sig.get("denominator_code"), sig.get("denominator_statement"))
            name = _sentence(denom) if denom else "the whole book"
            lab = f"% of {name}"
            key.append(f"{lab}: each row's slice of all {name}" if denom else f"{lab}: each row's slice of it")
            key[-1] += f" ({top} is {v} of it)." if top else "."
        labels["of_book"] = lab

    if labels:
        table["col_labels"] = labels
        table["key"] = key
