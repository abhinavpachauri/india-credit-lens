#!/usr/bin/env python3
"""
validate_concordance.py — is the credit ↔ real-economy join what it says it is?
──────────────────────────────────────────────────────────────────────────────
A concordance (`analysis/ontology/concordance/{credit}__{reference}.json`, COMPOSITION_SPEC §24)
says which MoSPI series measures each credit part. Every later number that sets credit against
the real economy is only as right as this file, and nothing downstream could tell a wrong match
from a right one: a mismatched series still produces a plausible-looking percentage.

Population, derived and never circular (§24.3). What must be covered is never read from the file:
  * the files: every concordance on disk;
  * the cuts: the credit pipeline's manifest declares which of its tables carry real-economy
    columns (`reference_cuts: {reference: [stems]}`). The file must declare exactly those: a cut
    dropped from both `cuts` and `parts` fails here (absence review, 2026-09-29), instead of passing
    as a smaller but complete file;
  * the parts of each declared cut: the cut's parent and its children IN THE CREDIT CSV
    (never the table sidecar, which will be built from the 1f output being checked). A part the file
    leaves out FAILS, instead of vanishing; a part the file names that the CSV does not have FAILS;
  * the series: every code must exist in the reference CSV, with the measure its role reads.

Structural rules, every run:
  * each series is `<dataset>/<code>` in the reference CSV, carrying the measure its role reads
    (output: IIP index / NAS constant prices; deflator: WPI/CPI index, or NAS current AND constant);
  * a part is matched at the cadence of the cut it is a child of, or absent `cadence_mismatch`
    (a cut's parent row inherits the cadence of ITS parent cut: a total row is a different signal);
  * several series need `combine`: `sum` for NAS levels only (additive as published), `weighted`
    with weights whose codes equal the series and each equal to the cited source table's value;
  * absences use a STATIC reason from core/absence.py only; `approximate` names a declared
    approximation and sits on an aggregate (a part with children), never on a leaf;
  * both pipelines exist, the credit one `primary` and the reference one `reference`;
  * each cut stem is a real cut: the credit registry has signals on that statement and parent.
  * with `requires_signals: true` (phase 3): every cut has both 1f registry entries and every 1f
    entry names a cut. While false, the check says so rather than passing on zero entries.

It also prints coverage per cut: the share of the cut's latest credit whose part has an output or a
deflator. Printed, not gated: coverage moves when a decision is made, not when something breaks.

    python3 analysis/cross/validate_concordance.py [--reference mospi | --credit sibc]
"""
from __future__ import annotations

import argparse
import csv
import json
import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir()) / "analysis"))
from core import manifest, absence                                    # noqa: E402
from core.paths import ANALYSIS                                       # noqa: E402

CONCORDANCE_DIR = ANALYSIS / "ontology" / "concordance"
REGISTRY = ANALYSIS / "signals" / "registry.json"
OUTPUT_MEASURE = {"iip": "index", "nas": "constant_price"}
DEFLATOR_MEASURE = {"wpi": "index", "cpi": "index"}
F1_METHODS = ("csv_sector_real_growth", "csv_sector_output_growth")


def urn(pipeline: str, statement: str, code: str) -> str:
    return f"icl:{pipeline}/{statement.replace(' ', '')}/{code}"


def credit_rows(pipeline: str) -> tuple[list[dict], str]:
    """The credit CSV's rows at its latest date, and that date."""
    man = manifest.load(pipeline)
    date_col = man["schema"]["date_column"]
    with manifest.consolidated_csv(pipeline).open() as f:
        rows = list(csv.DictReader(f))
    latest = max(r[date_col] for r in rows)
    return [r for r in rows if r[date_col] == latest], latest


def reference_series(pipeline: str) -> dict:
    """{(dataset, code): {measures}} from the reference CSV, and each dataset's cadence."""
    out: dict = {}
    with manifest.consolidated_csv(pipeline).open() as f:
        for r in csv.DictReader(f):
            out.setdefault((r["dataset"], r["code"]), set()).add(r["measure"])
    return out


def registry_cuts(pipeline: str) -> tuple[set, dict]:
    """(the (statement, parent) pairs the registry scans, {stem: [1f methods]} of live 1f entries)."""
    reg = json.loads(REGISTRY.read_text())
    sig = reg["signals"] if isinstance(reg, dict) and "signals" in reg else reg
    items = sig.values() if isinstance(sig, dict) else sig
    scanned, f1 = set(), {}
    for s in items:
        c = s.get("compute") or {}
        if s.get("pipeline") != pipeline or s.get("retire_period"):
            continue
        if c.get("parent_code"):
            scanned.add((c.get("statement"), c["parent_code"]))
        if c.get("method") in F1_METHODS:
            f1.setdefault(c.get("cut"), []).append(c["method"])
    return scanned, f1


def check_series(where: str, role: str, spec: dict, cadence: str, ref: dict, ref_man: dict,
                 sources: dict, errs: list) -> None:
    datasets = ref_man["datasets"]
    if "absent" in spec:
        if spec["absent"] not in absence.STATIC:
            errs.append(f"{where} {role}: {spec['absent']!r} is not a static reason in core/absence.py")
        return
    implicit = "implicit" in spec
    refs = spec.get("implicit" if implicit else "series")
    if not refs:
        errs.append(f"{where} {role}: declares neither series, implicit nor absent")
        return
    parsed = []
    for s in refs:
        ds, _, code = s.partition("/")
        if ds not in datasets:
            errs.append(f"{where} {role}: {s!r} names no reference dataset")
            continue
        parsed.append((ds, code))
        if implicit:
            want = {"current_price", "constant_price"}
            if ds != "nas":
                errs.append(f"{where} {role}: an implicit deflator needs NAS series, not {s!r}")
        else:
            want = {(OUTPUT_MEASURE if role == "output" else DEFLATOR_MEASURE).get(ds)}
            if None in want:
                errs.append(f"{where} {role}: dataset {ds!r} cannot serve as {role}")
                continue
        missing = want - ref.get((ds, code), set())
        if missing:
            errs.append(f"{where} {role}: {s!r} has no {sorted(missing)} in the reference CSV")
        if datasets[ds]["cadence"] != cadence:
            errs.append(f"{where} {role}: {s!r} is {datasets[ds]['cadence']}, the part is {cadence}; "
                        f"declare it absent (cadence_mismatch)")
    if len(refs) > 1 and not implicit:
        how = spec.get("combine")
        if how == "sum":
            if any(ds != "nas" for ds, _ in parsed):
                errs.append(f"{where} {role}: only NAS levels are additive; {refs} cannot be summed")
        elif how == "weighted":
            weights, src = spec.get("weights") or {}, spec.get("weight_source")
            if set(weights) != set(refs):
                errs.append(f"{where} {role}: weights name {sorted(weights)}, series are {sorted(refs)}")
            table = (sources.get(src) or {}).get("weights")
            assign = ((sources.get(src) or {}).get("assign") or {}).get(where)
            if not table:
                errs.append(f"{where} {role}: weight_source {src!r} is not a cited source with a table")
            else:
                for s, w in weights.items():
                    if table.get(s) != w:
                        errs.append(f"{where} {role}: weight {s}={w} differs from {src}'s {table.get(s)}")
            # Which codes make up the part is stated by the source, not the part: moving nic:27
            # from Engineering to Vehicles, with its correct weight, must fail (§24.3).
            if assign is None or set(assign) != set(refs):
                errs.append(f"{where} {role}: series {sorted(refs)} differ from {src}'s assignment "
                            f"{sorted(assign) if assign else None}")
        else:
            errs.append(f"{where} {role}: {len(refs)} series need combine 'sum' or 'weighted'")


def check_file(path: Path) -> tuple[list[str], list[str]]:
    doc = json.loads(path.read_text())
    errs, notes = [], []
    credit, reference = doc.get("credit_pipeline"), doc.get("reference_pipeline")
    if path.stem != f"{credit}__{reference}":
        errs.append(f"{path.name}: names {credit}__{reference}")
    for p, k in ((credit, "primary"), (reference, "reference")):
        if p not in manifest.PIPELINE_IDS or manifest.kind(p) != k:
            errs.append(f"{path.name}: {p!r} must be a {k} pipeline")
    if errs:
        return errs, notes

    rows, latest = credit_rows(credit)
    schema = manifest.load(credit)["schema"]
    scope = schema.get("scope_column")
    by_urn = {urn(credit, r.get(scope, ""), r["code"]): r for r in rows if r.get("code")}
    ref, ref_man = reference_series(reference), manifest.load(reference)
    parts, sources = doc["parts"], doc.get("sources", {})
    scanned, f1 = registry_cuts(credit)

    decl = (manifest.load(credit).get("reference_cuts") or {}).get(reference) or {}
    required = set(decl.get("include", []))
    excluded = decl.get("exclude", {})
    if not required:
        errs.append(f"{credit}'s manifest declares no reference_cuts.include for {reference}: nothing "
                    f"says which tables this concordance must cover")
    # Every cut the registry scans is classified: covered here, or excluded with a reason. A cut
    # added later cannot slip past as "not declared" (population review, 2026-09-29).
    classified = {(c["statement"], c["parent_code"]) for c in doc["cuts"].values()} | \
                 {(x["statement"], x["parent_code"]) for x in excluded.values()}
    for st, parent in sorted(scanned - classified, key=str):
        errs.append(f"{credit}'s registry scans {st} / {parent}; reference_cuts neither includes nor "
                    f"excludes it")
    for stem, x in excluded.items():
        if not x.get("why"):
            errs.append(f"excluded cut {stem}: no `why`")
        if (x["statement"], x["parent_code"]) not in scanned:
            errs.append(f"excluded cut {stem}: {x['statement']} / {x['parent_code']} is not a cut")
    for stem in sorted(required - doc["cuts"].keys()):
        errs.append(f"cut {stem}: {credit}'s manifest requires it, the concordance does not declare it")
    for stem in sorted(doc["cuts"].keys() - required):
        errs.append(f"cut {stem}: declared by the concordance, not in {credit}'s reference_cuts")

    expected, cadence_of = set(), {}
    for stem, cut in doc["cuts"].items():
        st, parent = cut["statement"], cut["parent_code"]
        if (st, parent) not in scanned:
            errs.append(f"cut {stem}: the {credit} registry has no signal on {st} / {parent}")
        children = [u for u, r in by_urn.items()
                    if r.get(scope, "") == st and r.get("parent_code") == parent]
        if not children:
            errs.append(f"cut {stem}: no children of {parent} in {st} in the credit CSV")
        parent_urn = cut.get("parent_urn") or urn(credit, st, parent)
        if parent_urn not in by_urn:
            errs.append(f"cut {stem}: parent {parent_urn} is not in the credit CSV")
        for u in children:
            cadence_of[u] = cut["cadence"]
        expected |= set(children) | {parent_urn}
        cut["_children"], cut["_parent"] = children, parent_urn
    for stem, cut in doc["cuts"].items():            # a top parent takes its own cut's cadence
        cadence_of.setdefault(cut["_parent"], cut["cadence"])

    for u in sorted(expected - parts.keys()):
        errs.append(f"{u}: a part of a declared cut, missing from the concordance")
    for u in sorted(parts.keys() - expected):
        errs.append(f"{u}: in the concordance, but not a part of any declared cut in the credit CSV")

    has_children = {(r.get(scope, ""), r.get("parent_code")) for r in rows}
    weighted_use: dict = {}
    for u, p in parts.items():
        for role in ("output", "deflator"):
            spec = p.get(role) or {}
            if spec.get("combine") == "weighted":
                for s in spec.get("series", []):
                    weighted_use.setdefault((role, s), []).append(u)
    for (role, s), users in sorted(weighted_use.items()):
        if len(users) > 1:
            errs.append(f"{role} {s} is weighted into {len(users)} parts {users}: a code serves one part")
    for u, p in parts.items():
        if u not in expected:
            continue
        for role in ("output", "deflator"):
            if role not in p:
                errs.append(f"{u}: declares no {role}")
                continue
            check_series(u, role, p[role], cadence_of[u], ref, ref_man, sources, errs)
        if "approximate" in p:
            if p["approximate"] not in absence.APPROXIMATIONS:
                errs.append(f"{u}: approximate {p['approximate']!r} is not declared in core/absence.py")
            if (by_urn[u].get(scope, ""), by_urn[u]["code"]) not in has_children:
                errs.append(f"{u}: a leaf row may not be an approximation")

    if doc.get("requires_signals"):
        for stem in doc["cuts"]:
            got = set(f1.get(stem, []))
            if got != set(F1_METHODS):
                errs.append(f"cut {stem}: 1f registry entries {sorted(got)}, need {list(F1_METHODS)}")
        for stem in sorted(set(f1) - set(doc["cuts"])):
            errs.append(f"1f registry entries name cut {stem!r}, which the concordance does not declare")
    elif f1:
        errs.append(f"{sum(map(len, f1.values()))} 1f registry entries exist but requires_signals is "
                    f"false: set it to true so they are checked against the cuts")
    else:
        notes.append("registry ↔ cuts not enforced (requires_signals: false; phase 3 turns it on)")

    value = schema["value_column"]
    for stem, cut in doc["cuts"].items():
        kids = cut["_children"]
        total = sum(float(by_urn[u][value] or 0) for u in kids)
        def share(role):
            n = [u for u in kids if u in parts and "absent" not in parts[u].get(role, {"absent": 1})]
            amt = sum(float(by_urn[u][value] or 0) for u in n)
            return f"{len(n)}/{len(kids)} parts, {100 * amt / total:.0f}%" if total else "n/a"
        notes.append(f"{stem}: output {share('output')} · deflator {share('deflator')} of credit @ {latest}")
    return errs, notes


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    ap.add_argument("--reference", help="only concordances whose reference pipeline is this")
    ap.add_argument("--credit", help="only concordances whose credit pipeline is this")
    args = ap.parse_args()
    files = sorted(CONCORDANCE_DIR.glob("*__*.json"))
    if args.reference:
        files = [f for f in files if f.stem.split("__")[1] == args.reference]
    if args.credit:
        files = [f for f in files if f.stem.split("__")[0] == args.credit]
    if not files:
        print(f"  ✗ no concordance file for {args.reference or args.credit or 'any pipeline'} "
              f"under {CONCORDANCE_DIR}", file=sys.stderr)
        return 1
    failed, unenforced = False, []
    for f in files:
        errs, notes = check_file(f)
        if not json.loads(f.read_text()).get("requires_signals"):
            unenforced.append(f.stem)
        for n in notes:
            print(f"  · {f.stem}: {n}")
        for e in errs:
            print(f"  ✗ {f.stem}: {e}", file=sys.stderr)
        failed |= bool(errs)
    if failed:
        return 1
    # The verdict line is what the gate summary shows, so a check that is off says so HERE, first:
    # a note on another line never reaches the summary (absence review, 2026-09-29).
    off = f"registry check OFF ({', '.join(unenforced)}) · " if unenforced else ""
    print(f"  ✓ {off}{len(files)} concordance(s) valid: every part of every required cut matched "
          f"or absent with a reason")
    return 0


if __name__ == "__main__":
    sys.exit(main())
