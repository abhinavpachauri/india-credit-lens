#!/usr/bin/env python3
"""
explainability.py — the driver register: why might each line move, and has it been tested?
──────────────────────────────────────────────────────────────────────────────────────────
SYSTEM_MODEL_SPEC §16 Step 6c. One register per pipeline (`{data_dir}/driver_hypotheses.json`)
holds, for every line of the model, which kinds of reason apply to it (`applies`) and every
candidate driver (`hypotheses`), each declared before it is tested. Status is DERIVED from test
results, never typed. Claude drafts; the user approves; tests decide.

    python3 analysis/core/explainability.py seed --pipeline sibc      # draft register (refuses to overwrite)
    python3 analysis/core/explainability.py validate --pipeline sibc
    python3 analysis/core/explainability.py summary --pipeline sibc
    python3 analysis/core/explainability.py report --pipeline sibc    # the completeness grid
    python3 analysis/core/explainability.py test --pipeline sibc [--dry-run]   # step 3: test what has data

Step 1 of the build order (register, validator, seed). The completeness grid is step 2.
"""
from __future__ import annotations

import csv
import json
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import generate_skeleton as gs  # noqa: E402
from core import manifest  # noqa: E402
from core.paths import ROOT  # noqa: E402

# ── The taxonomy: the kinds of reason (closed; spec §16 Step 6c) ──────────────────────────
TAXONOMY = {
    "arithmetic":          "nothing happened; the year-on-year calculation moved",
    "artefact":            "a reporting or classification change, not lending",
    "structural":          "the same event seen twice in the tables",
    "within_system":       "one kind of lending replacing or feeding another",
    "input_prices":        "what borrowers buy or sell got dearer or cheaper",
    "credit_price":        "loans got cheaper or dearer",
    "demand":              "borrowers' business or income grew or shrank",
    "alternative_finance": "firms switch between banks and bonds, CP, foreign loans, NBFCs",
    "regulation":          "a rule, scheme or deadline",
    "funding":             "lenders short of deposits or capital lend less overall",
}
# Kinds 1-3 are computed for every line from our own tables (6a); they carry no hypotheses.
COMPUTED = ("arithmetic", "artefact", "structural")
# Kinds that need outside data: the columns of the completeness grid.
OUTSIDE = ("input_prices", "credit_price", "demand", "alternative_finance", "regulation", "funding")
MAX_LAG = 9                      # relationship_test.DISCOVERY_MAX_LAG

# Where a missing cell's data would come from (analysis/sources/README.md). A default per kind;
# a hypothesis may name a more precise source.
CLASS_SOURCE = {
    "input_prices": "MoSPI WPI at item level (dropped at fetch today), or a commodity price (gold: DBIE Bulletin Table 21)",
    "credit_price": "RBI Lending and Deposit Rates of SCBs (sources shortlist #1; files in hand, onboarding paused)",
    "demand": "MoSPI output not matched at this line; services and households: ISP, PLFS (MoSPI)",
    "alternative_finance": "DBIE flow of financial resources to the commercial sector, CP, ECB (shortlist #4-5)",
    "regulation": "a dated force, sourced through S4 or the regulatory watch (arc 3)",
    "funding": "DBIE SCB select aggregates; per-bank capital (bank-wise variables)",
}

# Step 3's verdict on a force edge, read as a test result (spec §16 Step 6c).
FORCE_VERDICT = {"working": "supported", "contradicted": "opposite", "unclear": "not_supported",
                 "unassessable": "too_short"}            # not_yet_due / faded: not testable now
# A force's kind of reason. policy_action is a rule; the rest are read case by case (draft).
FORCE_CLASS = {
    "policy_action": "regulation",
    "force_gold_price_surge": "input_prices",
    "force_msme_formalisation": "regulation",
    "force_msp_procurement_growth": "regulation",
    "force_infra_cycle_maturing": "demand",
    "force_vehicle_scrappage_replacement": "regulation",
}


def register_path(pipeline: str) -> Path:
    return ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "driver_hypotheses.json"


def lines(model: dict) -> list[dict]:
    """The lines of the grid: every entity but a root (the same population as Step 6a)."""
    return [n for n in model["nodes"]
            if n.get("tier") == "entity" and n.get("structural_role") != "root"]


# ── Seeding the draft (SIBC's groups; another pipeline declares its own) ───────────────────

ROMAN = {"i", "ii", "iii", "iv", "v", "vi", "vii", "viii", "ix", "x"}
NO = "not_applicable"


def _sibc_group(n: dict) -> str:
    st, code = n.get("statement", ""), str(n.get("code", ""))
    if code in ROMAN:
        return "psl"
    if code == "II":
        return "food"
    if code == "III":
        return "nonfood"
    if st == "Statement 2":
        return "industry_type"
    return {"1": "agri", "2": "industry_size", "3": "services", "4": "personal"}.get(code.split(".")[0], "other")


ALT_FINANCE_SERVICES = ("Non-Banking", "Housing Finance", "Public Financial", "Other NBFCs",
                        "Commercial Real Estate", "Services")
FUEL_SERVICES = ("Aviation", "Shipping", "Transport Operators")


def _sibc_applies(n: dict) -> dict:
    """A DRAFT of which kinds of reason apply to a SIBC line, each with a reason when not."""
    g, label = _sibc_group(n), n["label"]
    yes = {"status": "applies"}

    def no(reason):
        return {"status": NO, "reason": reason}
    a = {k: yes for k in OUTSIDE}
    a["funding"] = no("measured against its group, so the common funding tide is removed; "
                      "funding applies to totals and per-bank lines")
    if g == "agri":
        a["alternative_finance"] = no("farm borrowers have no bond or commercial-paper market")
    elif g == "industry_size" and label in ("Micro and Small", "Medium"):
        a["alternative_finance"] = no("small and mid-sized firms rarely issue bonds or CP")
    elif g == "services":
        if not label.startswith(ALT_FINANCE_SERVICES):
            a["alternative_finance"] = no("these borrowers rarely use bond or CP markets")
        if not label.startswith(FUEL_SERVICES):
            a["input_prices"] = no("no single priceable input drives this line's borrowing")
    elif g == "personal":
        a["alternative_finance"] = no("households do not borrow in markets; NBFC competition is a "
                                      "within-system or cross-pipeline link")
        if not label.startswith(("Loans against gold", "Housing")):
            a["input_prices"] = no("no asset or input price drives this loan's size")
    elif g == "psl":
        a["input_prices"] = no("a lens over the main tree; prices act on the underlying line")
        a["alternative_finance"] = no("a lens over the main tree; markets act on the underlying line")
    elif g == "food":
        a["credit_price"] = no("food credit is lent to FCI on administered terms")
        a["alternative_finance"] = no("FCI's market borrowing is a fiscal decision, not a credit substitute")
    return {k: {**v, "approved": None} for k, v in a.items()}


def _concordance_parts(pipeline: str) -> dict:
    """urn -> concordance part, over every concordance this pipeline is the credit side of."""
    out = {}
    for f in sorted((ROOT / "analysis/ontology/concordance").glob(f"{pipeline}__*.json")):
        doc = json.loads(f.read_text())
        ref = doc.get("reference_pipeline")
        for urn, part in doc.get("parts", {}).items():
            out[urn] = (ref, part)
    return out


def _tests(path: Path) -> list[dict]:
    return json.loads(path.read_text()).get("tests", []) if path.exists() else []


def seed(pipeline: str) -> dict:
    """The draft register: applies per line, and every hypothesis already implied by the model,
    the concordance and the recorded tests; a placeholder for every applicable cell left empty."""
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    if pipeline != "sibc":
        raise SystemExit(f"{pipeline}: no seeding rules yet (SIBC first, spec §16 Step 6c)")
    by_urn = {n.get("urn"): n for n in model["nodes"] if n.get("tier") == "entity"}
    by_id = {n["id"]: n for n in model["nodes"] if n.get("tier") == "entity"}
    ls = lines(model)
    hyps: list[dict] = []
    applies = {n["urn"]: {"label": n["label"], "applies": _sibc_applies(n)} for n in ls}

    def applies_to(n, cls):
        return applies[n["urn"]]["applies"].get(cls, {}).get("status") == "applies"

    def add(line, cls, driver, sign, lag, reason, tests=(), note=None):
        hyps.append({"id": f"h{len(hyps) + 1:04d}", "line": line["urn"], "line_label": line["label"],
                     "class": cls, "driver": driver, "sign": sign, "lag": lag, "reason": reason,
                     "proposed_by": "claude", "approved": None, "admitted": None,
                     "tests": list(tests), **({"note": note} if note else {})})

    # 1. The concordance: each matched price and output series is a hypothesis at lag 0.
    parts = _concordance_parts(pipeline)
    for n in ls:
        ref, part = parts.get(n.get("urn"), (None, None))
        if not part:
            continue
        for role, cls, why in (("deflator", "input_prices", "the price of what this line's borrowers "
                                                             "sell or hold moves their borrowing"),
                               ("output", "demand", "this line's borrowers' output moves their borrowing")):
            spec = part.get(role, {})
            series = spec.get("series") or spec.get("implicit")
            # A deflator exists to show REAL credit; it is a driver claim only where this kind of
            # reason applies to the line (CPI on personal loans is a deflator, not a cause).
            if not applies_to(n, cls):
                continue
            if series:
                add(n, cls, {"pipeline": ref, "series": series}, 1, 0, why,
                    note="tested at lag 0 by Step 6a's prices_activity coverage check only")
            elif spec.get("absent"):
                add(n, cls, {"source": CLASS_SOURCE[cls], "absent": spec["absent"]}, None, None, why)

    # 2. Recorded reference tests (a price series tested against a credit line).
    cross = ROOT / "analysis/cross_source/relationship_tests.json"
    for t in _tests(cross):
        src = t.get("source", "")
        if not src.startswith("mospi:"):
            continue
        tgt = by_id.get(t["target"].split(":", 1)[1])
        if tgt:
            add(tgt, "input_prices", {"pipeline": "mospi", "series": [src.split(":", 1)[1]]},
                t["predicted_sign"], t.get("at_lag") or 0, t.get("reason", ""),
                tests=[f"cross_source:{t.get('edge_id')}"])

    # 3. The model's dated forces: Step 3 judges each force edge every period.
    for f in model.get("force_instances", []):
        cls = FORCE_CLASS.get(f["id"]) or FORCE_CLASS.get(f.get("force_type"))
        for e in model["edges"]:
            if e["from"] != f["id"] or e["type"] not in ("drives", "suppresses", "amplifies"):
                continue
            n = by_id.get(e["to"])
            if n and n in ls and cls:
                add(n, cls, {"force": f["id"]}, -1 if e.get("polarity") == "-" else 1,
                    f.get("delay_months", 0), f.get("label", ""),
                    tests=[f"force_check:{f['id']}:{e['id'] if 'id' in e else f['id'] + '__' + e['type'] + '__' + e['to']}"])

    # 4. Recorded within-system tests (one line pushing another).
    seen = set()
    for t in reversed(_tests(ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "relationship_tests.json")):
        key = (t.get("source"), t.get("target"))
        if key in seen or t.get("target") not in by_id:
            continue
        seen.add(key)
        tgt, src = by_id[t["target"]], by_id.get(t.get("source"))
        add(tgt, "within_system", {"line": src["urn"] if src else t.get("source")},
            t.get("predicted_sign"), t.get("lag", t.get("at_lag", 0)), t.get("reason", ""),
            tests=[f"{pipeline}:{t.get('source')}->{t.get('target')}"])

    # 5. Every applicable cell still empty gets a placeholder naming where its data would come from.
    filled = {(h["line"], h["class"]) for h in hyps}
    for n in ls:
        for cls, cell in applies[n["urn"]]["applies"].items():
            if cell["status"] == "applies" and (n["urn"], cls) not in filled:
                add(n, cls, {"source": CLASS_SOURCE[cls]}, None, None, "")
    return {"_meta": {"spec": "SYSTEM_MODEL_SPEC §16 Step 6c", "pipeline": pipeline,
                      "seeded": date.today().isoformat(),
                      "status": "DRAFT: every applies-cell and hypothesis awaits the user's approval",
                      "taxonomy": TAXONOMY},
            "lines": applies, "hypotheses": hyps}


# ── Status: derived from tests, never typed ────────────────────────────────────────────────

def _verdicts(pipeline: str) -> dict:
    """test ref -> verdict, from the recorded tests and the latest Step 3 force check."""
    out = {}
    for t in _tests(ROOT / "analysis/cross_source/relationship_tests.json"):
        out[f"cross_source:{t.get('edge_id')}"] = t["verdict"]
    for t in _tests(ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "relationship_tests.json"):
        if t.get("test_id"):                                   # a generic driver test (step 3)
            out[f"driver:{t['test_id']}"] = t["verdict"]
        else:
            out[f"{pipeline}:{t.get('source')}->{t.get('target')}"] = t["verdict"]    # latest wins
    states = sorted((ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "merged").glob("system_state_*.json"))
    if states:
        for fid, f in json.loads(states[-1].read_text()).get("force_check", {}).items():
            for eid, e in f.get("edges", {}).items():
                v = FORCE_VERDICT.get(e.get("verdict"))
                if v:
                    out[f"force_check:{fid}:{eid}"] = v
    return out


def status(h: dict, verdicts: dict) -> str:
    if h.get("admitted"):
        return "admitted"
    results = [verdicts[t] for t in h.get("tests", []) if t in verdicts]
    if results:
        return results[-1]
    if "source" in h["driver"]:
        return "data_missing"
    return "ready"


# ── Validation (spec: guards, measured before they gate) ───────────────────────────────────

def validate(pipeline: str, reg: dict | None = None) -> list[str]:
    reg = reg or json.loads(register_path(pipeline).read_text())
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    urns = {n.get("urn") for n in model["nodes"] if n.get("tier") == "entity"}
    errs = []
    for n in lines(model):
        cells = reg["lines"].get(n["urn"], {}).get("applies")
        if not cells:
            errs.append(f"line {n['label']} ({n['urn']}) has no applies list")
            continue
        for cls in OUTSIDE:
            c = cells.get(cls)
            if not c or c.get("status") not in ("applies", NO):
                errs.append(f"{n['label']}: kind {cls} is neither applies nor not_applicable")
            elif c["status"] == NO and not c.get("reason"):
                errs.append(f"{n['label']}: kind {cls} not applicable without a reason")
    ref_series = _reference_series()
    tp = ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "relationship_tests.json"
    ids = [r["test_id"] for r in _tests(tp) if r.get("test_id")]
    dup_ids = {i for i in ids if ids.count(i) > 1}
    known = set(ids)
    seen = set()
    for h in reg["hypotheses"]:
        where = f"{h.get('id')} ({h.get('line_label')}, {h.get('class')})"
        if h["id"] in seen:
            errs.append(f"{where}: duplicate id")
        seen.add(h["id"])
        refs = [x[7:] for x in h.get("tests", []) if x.startswith("driver:")]
        if any(x not in known for x in refs):
            errs.append(f"{where}: references a driver result that is not recorded")
        if len(refs) != len(set(refs)) or any(x in dup_ids for x in refs):
            errs.append(f"{where}: a driver result id is not unique")
        if h["line"] not in urns:
            errs.append(f"{where}: line {h['line']} is not in the model")
        if h["class"] not in TAXONOMY or h["class"] in COMPUTED:
            errs.append(f"{where}: class must be one of {list(TAXONOMY)[3:]}")
        elif h["class"] in OUTSIDE:
            cell = reg["lines"].get(h["line"], {}).get("applies", {}).get(h["class"], {})
            if cell.get("status") != "applies":
                errs.append(f"{where}: a hypothesis in a cell marked not applicable")
        if h.get("approved"):
            if h.get("sign") not in (1, -1):
                errs.append(f"{where}: approved without a declared sign")
            if h.get("lag") is not None and (not isinstance(h["lag"], int) or not 0 <= h["lag"] <= MAX_LAG):
                errs.append(f"{where}: a fixed lag must be 0-{MAX_LAG}")
        d = h["driver"]
        if d.get("pipeline") == "mospi":
            for s in d.get("series", []):
                if tuple(s.split("/", 1)) not in ref_series:
                    errs.append(f"{where}: series {s} is not in the MoSPI CSV")
        if h.get("admitted") and status({**h, "admitted": None}, _verdicts(pipeline)) != "supported":
            errs.append(f"{where}: admitted without a supported test")
    return errs


def _reference_series() -> set:
    path = manifest.consolidated_csv("mospi")
    return {(r["dataset"], r["code"]) for r in csv.DictReader(open(path))}


def summary(pipeline: str) -> str:
    reg = json.loads(register_path(pipeline).read_text())
    v = _verdicts(pipeline)
    from collections import Counter
    by = Counter((h["class"], status(h, v)) for h in reg["hypotheses"])
    out = [f"{pipeline}: {len(reg['lines'])} lines, {len(reg['hypotheses'])} hypotheses "
           f"({sum(1 for h in reg['hypotheses'] if h.get('approved'))} approved)"]
    for cls in ("within_system", *OUTSIDE):
        cells = Counter(st for (c, st), k in by.items() if c == cls for _ in range(k))
        applies = sum(1 for l in reg["lines"].values() if l["applies"].get(cls, {}).get("status") == "applies")
        out.append(f"  {cls:20} applies on {applies:2} lines · " +
                   " · ".join(f"{s} {n}" for s, n in sorted(cells.items())))
    return "\n".join(out)


# ── Step 2: the completeness grid (spec §16 Step 6c) ───────────────────────────────────────

TESTED = ("supported", "not_supported", "opposite", "too_short", "admitted")
SHORT = {"input_prices": "input prices", "credit_price": "price of credit", "demand": "demand",
         "alternative_finance": "other finance", "regulation": "rules & dates", "funding": "lenders' capacity"}
GROUPS = [("agri", "Agriculture"), ("industry_size", "Industry by size"), ("industry_type", "Industry by type"),
          ("services", "Services"), ("personal", "Personal loans"), ("psl", "Priority sector (lens)"),
          ("food", "Food credit"), ("nonfood", "Non-food credit")]


def cell(hyps: list[dict], verdicts: dict, applies: dict) -> tuple[str, bool]:
    """(symbol, complete) for one (line, kind). Complete = every hypothesis in it tested."""
    if applies.get("status") != "applies":
        return "–", True
    st = [status(h, verdicts) for h in hyps]
    done = bool(st) and all(s in TESTED for s in st)
    if done:
        sym = "✓" if any(s in ("supported", "admitted") for s in st) else \
              "?" if all(s == "too_short" for s in st) else "✗"
    elif any(s in TESTED for s in st):
        sym = "✓…" if any(s in ("supported", "admitted") for s in st) else "✗…"
    elif any(s == "ready" for s in st):
        sym = "○"
    else:
        sym = "·"
    return sym, done


def unexplained_moves(pipeline: str) -> dict:
    """urn -> number of unexplained moves over the whole history (Step 6a, live)."""
    from core import coverage as C, force_check as fc
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    series, periods = fc.growth_series(pipeline, model), fc.periods_of(pipeline)
    out: dict[str, int] = {}
    for p in periods:
        for m in C.for_period(pipeline, model, p, series, periods)["moves"]:
            if m["filed_under"] == "unexplained":
                out[m["urn"]] = out.get(m["urn"], 0) + 1
    return out


def detectability(pipeline: str) -> tuple[int, float | None]:
    """(usable monthly changes, smallest |r| detectable at p < 0.05) for the root's growth: the
    series every test removes as the tide, so no test can use more changes than it has."""
    from core import force_check as fc
    from scipy.stats import t as tdist
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    series = fc.growth_series(pipeline, model)
    root = next(n["id"] for n in model["nodes"] if n.get("structural_role") == "root" and n["id"] in series)
    months = sorted(fc._months(fc.resolve_csv_date(pipeline, p)) for p in series[root])
    n = sum(1 for a, b in zip(months, months[1:]) if b - a == 1)
    if n < 4:
        return n, None
    tc = tdist.ppf(0.975, n - 2)
    return n, round(tc / (n - 2 + tc ** 2) ** 0.5, 2)


def report(pipeline: str, with_moves: bool = True) -> tuple[str, str]:
    """(terminal summary, markdown page) of the completeness grid."""
    reg = json.loads(register_path(pipeline).read_text())
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    v = _verdicts(pipeline)
    by_cell: dict[tuple, list] = {}
    for h in reg["hypotheses"]:
        by_cell.setdefault((h["line"], h["class"]), []).append(h)
    moves = unexplained_moves(pipeline) if with_moves else {}
    n_changes, r_min = detectability(pipeline)
    group_of = {n["urn"]: _sibc_group(n) for n in lines(model)}

    col = {k: {"applies": 0, "complete": 0, "sources": {}} for k in OUTSIDE}
    rows = {g: [] for g, _ in GROUPS}
    for urn, line in reg["lines"].items():
        cells = []
        for k in OUTSIDE:
            hs = by_cell.get((urn, k), [])
            sym, done = cell(hs, v, line["applies"].get(k, {}))
            cells.append(sym)
            if line["applies"].get(k, {}).get("status") == "applies":
                col[k]["applies"] += 1
                col[k]["complete"] += done
                for h in hs:
                    if status(h, v) == "data_missing":
                        s = col[k]["sources"].setdefault(h["driver"]["source"], {"lines": 0, "moves": 0})
                        s["lines"] += 1
                        s["moves"] += moves.get(urn, 0)
        ws = [status(h, v) for h in by_cell.get((urn, "within_system"), [])]
        rows.setdefault(group_of.get(urn, "other"), []).append(
            (line["label"], moves.get(urn, 0), cells, f"{len(ws)} tested" if ws else ""))

    md = [f"# Explainability grid — {pipeline}",
          "",
          f"> Generated by `python3 analysis/core/explainability.py report --pipeline {pipeline}` "
          f"({date.today().isoformat()}). Spec: SYSTEM_MODEL_SPEC §16 Step 6c. **Every cell is a draft** "
          f"until approved. The target: every column complete.",
          "",
          "`✓` tested, explains · `✗` tested, does not explain · `?` tested, history too short to tell · "
          "`○` data in hand, not yet tested · `·` data missing · `–` does not apply · `…` partly tested",
          "",
          f"**History:** {n_changes} usable monthly changes; a test can detect a link of |r| ≥ {r_min} "
          f"(p < 0.05). Weaker links read `?` or `✗` until the history grows.",
          "",
          "## Columns: how complete is each kind of reason",
          "",
          "| kind | complete | where the missing data would come from (lines · unexplained moves on them) |",
          "|---|---|---|"]
    term = [f"{pipeline}: completeness grid ({n_changes} monthly changes, detectable |r| ≥ {r_min})"]
    for k in OUTSIDE:
        c = col[k]
        src = "; ".join(f"{s} ({d['lines']} · {d['moves']})" for s, d in
                        sorted(c["sources"].items(), key=lambda x: -x[1]["moves"])) or "—"
        md.append(f"| {SHORT[k]} | {c['complete']}/{c['applies']} | {src} |")
        term.append(f"  {SHORT[k]:17} complete {c['complete']:2}/{c['applies']:2}"
                    f"   missing-data lines {sum(d['lines'] for d in c['sources'].values()):2}, "
                    f"unexplained moves on them {sum(d['moves'] for d in c['sources'].values())}")
    md += ["", "## The grid", ""]
    head = "| line | unexplained moves | " + " | ".join(SHORT[k] for k in OUTSIDE) + " | within system |"
    for g, title in GROUPS:
        if not rows.get(g):
            continue
        md += [f"### {title}", "", head, "|" + "---|" * (len(OUTSIDE) + 3)]
        for label, mv, cells, ws in sorted(rows[g], key=lambda r: -r[1]):
            md.append(f"| {label} | {mv or ''} | " + " | ".join(cells) + f" | {ws} |")
        md.append("")
    review = reg["_meta"].get("review_later", [])
    if review:
        md += ["## To review later", "", "| cells | why |", "|---|---|"]
        md += [f"| {x['cells']} | {x['why']} |" for x in review]
        md.append("")
    md += ["## Where a kind of reason does not apply", "",
           "Grouped by reason, so each row is one decision. `approved` = the user agreed; `draft` = awaiting review.", "",
           "| kind | reason | lines | state |", "|---|---|---|---|"]
    na: dict[tuple, list] = {}
    for urn, line in reg["lines"].items():
        for k, c in line["applies"].items():
            if c.get("status") == NO:
                na.setdefault((k, c["reason"], "approved" if c.get("approved") else "draft"), []).append(line["label"])
    for (k, why, state), ls in sorted(na.items(), key=lambda x: (OUTSIDE.index(x[0][0]), -len(x[1]))):
        shown = ", ".join(sorted(ls)) if len(ls) <= 12 else f"{len(ls)} lines (all of: " + \
            ", ".join(sorted(set(_sibc_group_label(l, reg, model) for l in ls))) + ")"
        md.append(f"| {SHORT[k]} | {why} | {shown} | {state} |")
    return "\n".join(term), "\n".join(md) + "\n"


def _sibc_group_label(label: str, reg: dict, model: dict) -> str:
    n = next(n for n in lines(model) if n["label"] == label)
    return dict(GROUPS).get(_sibc_group(n), "other")


# ── Step 3: run the generic driver test on every hypothesis with data in hand ─────────────

def run_tests(pipeline: str, dry_run: bool = False) -> list[dict]:
    """Every hypothesis with a series and a sign: its delay found on earlier months and confirmed
    on later ones (spec §16 Step 6c). The delay and cutoff are frozen at first discovery; later runs
    re-confirm on every month after the cutoff. A run with nothing new since the last result for a
    hypothesis records nothing for it. All hypotheses for one line form its family. Results,
    nulls included, are appended to relationship_tests.json and linked from the hypothesis."""
    from core import relationship_test as rt
    reg_path = register_path(pipeline)
    reg = json.loads(reg_path.read_text())
    model = gs.load_json(gs.pipeline_cfg(pipeline)["model"])
    node_of = {n.get("urn"): n["id"] for n in model["nodes"] if n.get("tier") == "entity"}
    tp = ROOT / manifest.load(pipeline)["paths"]["data_dir"] / "relationship_tests.json"
    doc = json.loads(tp.read_text()) if tp.exists() else {"tests": []}
    last = {}
    for r in doc["tests"]:
        if r.get("hypothesis_id") and "discover" in r.get("protocol", ""):
            last[r["hypothesis_id"]] = r
    todo = [h for h in reg["hypotheses"] if "series" in h["driver"] and h.get("sign") in (1, -1)]
    family = {}
    for h in todo:
        family[h["line"]] = family.get(h["line"], 0) + 1
    results = []
    for h in todo:
        r = rt.run_driver(h, pipeline, node_of[h["line"]], family[h["line"]], discover=True)
        prev = last.get(h["id"])
        if prev and prev.get("through_period") == r["through_period"]:
            continue                                       # nothing new since its last result
        results.append(r)
        if not dry_run:
            h.setdefault("tests", []).append(f"driver:{r['test_id']}")
            d = r.get("discovery") or {}
            if d.get("lag") is not None and not h.get("discovery"):
                h["discovery"] = {"cutoff": d["cutoff"], "lag": d["lag"], "found": r["tested"]}
    if not dry_run and results:
        doc["tests"].extend(results)
        tp.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
        reg_path.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
    return results

def main() -> int:
    import argparse
    ap = argparse.ArgumentParser(description="Driver register (SYSTEM_MODEL_SPEC §16 Step 6c)")
    ap.add_argument("command", choices=("seed", "validate", "summary", "report", "test"))
    ap.add_argument("--dry-run", action="store_true", help="test: run and print, record nothing")
    ap.add_argument("--pipeline", required=True)
    a = ap.parse_args()
    if a.command == "seed":
        path = register_path(a.pipeline)
        if path.exists():
            print(f"  ✗ {path} exists: the register holds the user's approvals and is never reseeded")
            return 1
        reg = seed(a.pipeline)
        errs = validate(a.pipeline, reg)
        path.write_text(json.dumps(reg, indent=1, ensure_ascii=False) + "\n")
        print(f"  ✓ seeded {path.relative_to(ROOT)}: {len(reg['lines'])} lines, "
              f"{len(reg['hypotheses'])} draft hypotheses; {len(errs)} validation error(s)")
        for e in errs[:20]:
            print("   ·", e)
        return 0
    if a.command == "validate":
        errs = validate(a.pipeline)
        print(f"  {'✓' if not errs else '✗'} {a.pipeline} register: {len(errs)} error(s)")
        for e in errs[:40]:
            print("   ·", e)
        return 1 if errs else 0
    if a.command == "test":
        res = run_tests(a.pipeline, a.dry_run)
        from collections import Counter
        print(f"  {a.pipeline}: {len(res)} hypotheses tested{' (dry run, nothing recorded)' if a.dry_run else ''}: "
              + ", ".join(f"{k} {n}" for k, n in Counter(r['verdict'] for r in res).most_common()))
        for r in sorted(res, key=lambda r: (r["verdict"] != "supported", r["target_label"])):
            m = r.get("lags", {}).get(r.get("at_lag"), {}) if r.get("lags") else {}
            d = r.get("discovery") or {}
            peak = d.get("profile", {}).get(d.get("lag"), {}) if d.get("lag") is not None else {}
            print(f"   {r['verdict']:13} {r['target_label'][:30]:30} ← {r['source'][:38]:38} "
                  f"delay {d.get('lag', '—')} (found r {peak.get('r', '—')}) · confirmed on n {m.get('n', '—')} "
                  f"r {m.get('r', '—')} p {m.get('p', '—')}")
        return 0
    if a.command == "report":
        term, md = report(a.pipeline)
        out = register_path(a.pipeline).with_name("explainability_grid.md")
        out.write_text(md)
        print(term)
        print(f"  → {out.relative_to(ROOT)}")
        return 0
    print(summary(a.pipeline))
    return 0


if __name__ == "__main__":
    sys.exit(main())
