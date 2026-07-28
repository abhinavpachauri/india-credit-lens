#!/usr/bin/env python3
"""
measure_groundedness.py — how good is a traceability gate, actually?
---------------------------------------------------------------------
Every published surface on this platform is guarded by a check that says "every
number here traces to a computed signal". Until now, not one of those checks had a
measured catch rate — and a gate that never fails looks identical to a gate that
cannot fail. On 2026-07-21 the distribution gate turned out to be catching 41.5% of
invented numbers while passing every hand-written negative test, because its
ground-truth pool was wide enough to account for almost anything.

So: measure them. For each gate, this injects numbers that should be rejected and
reports how many were, plus the error rate that matters just as much — how often the
gate rejects text that is true.

Two attacks, because they fail differently:

  near-miss     a real value nudged past rounding (8.5% → 9.1%). The realistic
                hallucination: right shape, wrong digit. Caught by tolerance.
  in-range      a fresh value drawn from the range the document already talks in.
                Caught only by SCOPE — a pool of thousands, or one that admits
                derived ratios, will wave these through however tight the tolerance.

WHY THIS FILE WAS REWRITTEN (2026-07-23). The old harness injected into the FIRST `p`
block of each document and then stopped. In the deep read that block is the intro,
which declares no signals, so it grounds nothing and fails closed — every one of 200
injections hit the single strongest block, and the 99.5% it reported measured "a
zero-scope block fails closed" (decision point D2), not the gate. The blocks that could
actually leak — the basis lines, scoped to thousands of candidate values — were never
touched. That is the fourth appearance of the narrow-negative-test failure class, this
time frozen into the instrument itself.

The rewrite attacks EVERY eligible block/claim, and never reports one pooled number.
A fabricated value's fate depends entirely on the scope of the block it lands in, so
results are sliced two ways that make scope visible:

  • by decision point   D1 long-form per-block · D2 zero-scope-fails-closed ·
                        D3 slot per-claim · D4 blurb union-scope
  • by scope band       0 · 1-50 · 51-200 · 201-1k · 1k+ candidate values

Plus a `--scope` report: the width of every block's ground truth, no injections needed.
Scope width is the LEADING indicator (any block whose scope runs to four figures is
unmeasured, not safe); catch rate is the lagging one.

    python3 analysis/measure_groundedness.py                 # every gate, full report
    python3 analysis/measure_groundedness.py --scope         # scope widths only (cheap)
    python3 analysis/measure_groundedness.py --gate newsletter --n 80

Add a gate by writing one `Target` — that is the point of this file. AI PM topic #1
(`analysis/distribution/ai_pm_register.json`); log what it prints, per decision point,
never one headline.
"""
import argparse
import copy
import random
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
sys.path.insert(0, str(ROOT / "analysis"))

from core.traceability import DISTRIBUTION as POLICY, extract_numbers, matches  # noqa: E402
import distribution.validate_distribution as vd                                # noqa: E402

SEED = 7
N_PER_SITE = 50   # injections per attack per injection site


# Ground truth is deterministic within one process, so memoise it once. Without this
# the rewrite (thousands of gate calls instead of a few hundred) would rebuild the same
# signals.db pools over and over. Transparent to the gate — same values, computed once.
_GT_CACHE: dict = {}
_declared = vd.declared_ground_truth


def _cached_ground_truth(declared_ids):
    key = tuple(declared_ids or ())
    if key not in _GT_CACHE:
        _GT_CACHE[key] = _declared(list(key))
    return _GT_CACHE[key]


vd.declared_ground_truth = _cached_ground_truth  # _scoped + check_slate resolve this


def scope_of(declared_ids):
    return _cached_ground_truth(declared_ids)


# ── The pieces a gate is described by ─────────────────────────────────────────

@dataclass
class Site:
    """One place a fabricated number could appear, and the scope that would judge it.

    dp            decision point this site exercises (D1/D2/D3/D4)
    scope         the ground-truth values the gate checks a number here against
    real_numbers  the numbers already legitimately in this block (for false-rejection
                  and for aiming the near-miss attack)
    inject        value → a fresh, fully-mutated case with `value` placed at this site,
                  ready to hand to the gate unchanged
    label         human tag for the site
    """
    dp: str
    scope: list
    real_numbers: list
    inject: Callable[[float], object]
    label: str = ""


@dataclass
class Target:
    """One gate, described well enough to attack at every site."""
    name: str
    cases: Callable[[], list]
    check: Callable[[object], list]        # the gate: case → list of failures
    sites: Callable[[object], list]        # case → every injectable site
    values: Callable[[object], list]       # case-wide numbers, for aiming in-range
    dp_names: dict = field(default_factory=dict)


# ── The attacks ───────────────────────────────────────────────────────────────

def near_miss(rng, real):
    """A real value nudged well past display rounding — wrong digit, right shape."""
    v = rng.choice(real)
    delta = max(abs(v) * rng.uniform(0.06, 0.30), 0.2)
    return round(v + delta * rng.choice([1, -1]), 1)


def in_range(rng, real):
    """A number this document could plausibly have said, but didn't."""
    lo, hi = min(real), max(real)
    if lo == hi:
        lo, hi = lo * 0.5, hi * 1.5
    return round(rng.uniform(lo, hi), 1)


ATTACKS = {"near-miss": near_miss, "in-range": in_range}


def band(scope):
    """Scope width bucket. Distinct candidate values, because dupes don't add cover."""
    w = len({round(v, 4) for v in scope})
    if w == 0:
        return "0"
    if w <= 50:
        return "1-50"
    if w <= 200:
        return "51-200"
    if w <= 1000:
        return "201-1k"
    return "1k+"


BANDS = ["0", "1-50", "51-200", "201-1k", "1k+"]


def measure(target, n=N_PER_SITE, seed=SEED):
    cases = target.cases()
    if not cases:
        return None

    baselines = [target.check(c) for c in cases]        # untouched → false rejections
    all_sites = [(ci, c, s) for ci, c in enumerate(cases) for s in target.sites(c)]
    if not all_sites:
        return None

    # Leading indicator + per-slice false rejection, no injections needed. A false
    # rejection here is localised: a number ALREADY in the block that its OWN scope
    # cannot account for — the gate rejecting something true, attributed to its site.
    widths = defaultdict(list)
    false_rej = defaultdict(lambda: [0, 0])   # ("dp"|"band", key) → [rejected, sites]
    for ci, c, s in all_sites:
        w = len({round(v, 4) for v in s.scope})
        b = band(s.scope)
        widths[s.dp].append(w)
        fr = any(not matches(x, s.scope, POLICY) for x in s.real_numbers)
        for key in (("dp", s.dp), ("band", b)):
            false_rej[key][0] += fr
            false_rej[key][1] += 1

    catch = defaultdict(lambda: [0, 0])       # (attack, "dp"|"band", key) → [caught, tried]
    for attack_name, attack in ATTACKS.items():
        rng = random.Random(seed)
        for ci, c, s in all_sites:
            case_vals = [v for v in target.values(c) if abs(v) > 0.5]
            near_aim = [v for v in s.real_numbers if abs(v) > 0.5] or case_vals
            aim = near_aim if attack_name == "near-miss" else (case_vals or near_aim)
            if not aim:
                continue
            base = len(baselines[ci])
            b = band(s.scope)
            for _ in range(n):
                value = attack(rng, aim)
                if matches(value, s.scope, POLICY):
                    continue                  # legit here — not an attack
                caught = len(target.check(s.inject(value))) > base
                for key in ((attack_name, "dp", s.dp), (attack_name, "band", b)):
                    catch[key][0] += caught
                    catch[key][1] += 1

    return {
        "cases": len(cases),
        "sites": len(all_sites),
        "case_false_rej": sum(1 for f in baselines if f),
        "widths": widths,
        "false_rej": false_rej,
        "catch": catch,
        "dp_names": target.dp_names,
    }


# ── Gate: the long-form issues (validate_distribution.check_doc) ──────────────

def _newsletter_target():
    from distribution.issues import monthly_issue as monthly
    from distribution.issues import deep_read as deep

    cards = vd.legit_card_texts()

    def reals_of(text):
        return extract_numbers(vd._strip_presentation(text, cards), POLICY)

    def cases():
        out = []
        doc, declared, period = monthly.build_doc()
        out.append({"doc": doc, "declared": declared, "label": f"monthly_issue {period}"})
        doc, _, declared = deep.build_doc()
        out.append({"doc": doc, "declared": declared, "label": "deep_read"})
        return out

    def check(case):
        return vd.check_doc(case["doc"], case["declared"], label=case["label"])

    def _text_inject(bi):
        def inject(case, value):
            c = copy.deepcopy(case)
            b = c["doc"][bi]
            b["text"] = (b.get("text", "") or "") + \
                f" The figure stood at {value}% this month."
            return c
        return inject

    def _item_inject(bi, ii):
        def inject(case, value):
            c = copy.deepcopy(case)
            it = c["doc"][bi]["items"][ii]
            it["note"] = (it.get("note", "") or "") + \
                f" The figure stood at {value}% this month."
            return c
        return inject

    def _row_inject(bi, ri):
        def inject(case, value):
            c = copy.deepcopy(case)
            cells = c["doc"][bi]["rows"][ri]["cells"]
            cells[-1] = f"{cells[-1]} {value}%"       # append to the last cell
            return c
        return inject

    def sites(case):
        out = []
        for bi, b in enumerate(case["doc"]):
            if b.get("meta") or b["type"] in ("card", "chart"):
                continue
            if b["type"] == "statgrid":
                for ii, it in enumerate(b.get("items", [])):
                    sig = [it["signal"]] if it.get("signal") else b.get("signals")
                    scope = scope_of(sig or [])
                    text = f"{it.get('value','')} {it.get('label','')} {it.get('note','')}"
                    dp = "D1" if scope else "D2"
                    out.append(Site(dp, scope, reals_of(text),
                                    lambda v, bi=bi, ii=ii: _item_inject(bi, ii)(case, v),
                                    f"{case['label']}:statgrid[{ii}]"))
            elif b["type"] == "table":
                for ri, row in enumerate(b.get("rows", [])):
                    if row.get("header") or row.get("meta"):
                        continue
                    sig = row.get("signals") or b.get("signals")
                    scope = scope_of(sig or [])
                    text = " ".join(str(c) for c in row.get("cells", []))
                    dp = "D1" if scope else "D2"
                    out.append(Site(dp, scope, reals_of(text),
                                    lambda v, bi=bi, ri=ri: _row_inject(bi, ri)(case, v),
                                    f"{case['label']}:table[{ri}]"))
            elif b.get("text") is not None or b.get("label") is not None:
                scope = scope_of(b.get("signals") or [])
                text = b.get("label", "") or ""
                text = f"{text} {b.get('text', '')}".strip()
                dp = "D1" if scope else "D2"
                out.append(Site(dp, scope, reals_of(text),
                                lambda v, bi=bi: _text_inject(bi)(case, v),
                                f"{case['label']}:{b['type']}[{bi}]"))
        return out

    def values(case):
        nums = []
        for b in case["doc"]:
            if b.get("type") == "statgrid":
                for it in b.get("items", []):
                    nums += extract_numbers(it.get("value", ""), POLICY)
            elif b.get("type") in ("p", "li", "stat", "h1", "h2", "quote", "small"):
                nums += extract_numbers(f"{b.get('label','')} {b.get('text','')}", POLICY)
        return nums

    return Target("newsletter", cases, check, sites, values,
                  {"D1": "per-block scope", "D2": "zero-scope, fails closed"})


# ── Gate: the distribution slots (validate_distribution.check_slate) ──────────

def _distribution_target():
    from distribution import generate_slot as gen
    from distribution import slot_render

    cards = vd.legit_card_texts()

    def reals_of(text):
        return extract_numbers(vd._strip_presentation(text, cards), POLICY)

    def cases():
        out = []
        for slot, cats in (("1st", ["C1", "C5"]), ("7th", ["C2", "C3"]),
                           ("14th", ["C6", "C7"]), ("28th", ["C8"])):
            slate = gen.build_slate(slot, "2026-08-01", cats, False)
            if slate and any(not c.get("verbatim") for c in slate["claims"]):
                out.append(slate)
        return out

    def _claim_inject(idx):
        def inject(slate, value):
            s = copy.deepcopy(slate)
            s["claims"][idx]["body"] += f" The gap stood at {value} pp this month."
            return s
        return inject

    def _blurb_inject(slate, value):
        # The blurb reads a claim's `lede` in preference to its body, and the per-claim
        # (D3) check never reads `lede`. So a number planted there reaches the blurb —
        # judged at the WIDER union scope (D4) — without disturbing any claim check.
        s = copy.deepcopy(slate)
        for c in s["claims"]:
            if not c.get("verbatim"):
                base = (c.get("lede") or c.get("body") or c["title"]).rstrip(". ")
                c["lede"] = base + f". The gap stood at {value} pp this month"
                break
        return s

    def sites(slate):
        out = []
        for idx, c in enumerate(slate["claims"]):
            if c.get("verbatim"):
                continue                      # verbatim → checked upstream (D5), no number attack
            scope = scope_of(c.get("signal_ids", [])) + list(c.get("extra_numbers", []))
            text = " ".join(x for x in (c["title"], c["body"],
                                        c.get("implication", "")) if x)
            out.append(Site("D3", scope, reals_of(text),
                            lambda v, idx=idx: _claim_inject(idx)(slate, v),
                            f"claim {c['id']}"))
        declared = sorted({s for c in slate["claims"] for s in c.get("signal_ids", [])})
        extra = [n for c in slate["claims"] for n in c.get("extra_numbers", [])]
        scope = scope_of(declared) + extra
        out.append(Site("D4", scope, reals_of(slot_render.blurb(slate)),
                        lambda v: _blurb_inject(slate, v), "blurb"))
        return out

    def values(slate):
        nums = []
        for c in slate["claims"]:
            nums += extract_numbers(f"{c['title']} {c['body']}", POLICY)
        return nums

    return Target("distribution", cases, vd.check_slate, sites, values,
                  {"D3": "per-claim scope", "D4": "blurb union scope"})


GATES = {"newsletter": _newsletter_target, "distribution": _distribution_target}


# ── Reporting ─────────────────────────────────────────────────────────────────

def _pct(caught, tried):
    return f"{100.0 * caught / tried:>5.1f}%" if tried else "    –"


def _scope_report(name, result):
    print(f"\n[{name}] scope width — the leading indicator "
          f"({result['sites']} sites over {result['cases']} cases)")
    print(f"  {'decision point':<34} {'sites':>5} {'min':>5} {'med':>6} {'max':>6}")
    for dp in sorted(result["widths"]):
        w = sorted(result["widths"][dp])
        med = w[len(w) // 2]
        tag = result["dp_names"].get(dp, "")
        print(f"  {dp+' '+tag:<34} {len(w):>5} {w[0]:>5} {med:>6} {w[-1]:>6}")


def _catch_report(name, result):
    fr = result["false_rej"]
    print(f"\n[{name}] catch rate by decision point  "
          f"(false-rej = true numbers the block's own scope rejects)")
    hdr = "  ".join(f"{a:>9}" for a in ATTACKS)
    print(f"  {'decision point':<34} {hdr}  {'false-rej':>10}")
    dps = sorted({k[2] for k in result["catch"] if k[1] == "dp"})
    for dp in dps:
        cells = "  ".join(_pct(*result["catch"][(a, "dp", dp)]) for a in ATTACKS)
        rej, tot = fr[("dp", dp)]
        tag = result["dp_names"].get(dp, "")
        print(f"  {dp+' '+tag:<34} {cells}  {rej:>4}/{tot:<5}")

    print(f"\n[{name}] catch rate by scope band  (wider scope should catch less)")
    print(f"  {'candidate values':<34} {hdr}  {'false-rej':>10}")
    for b in BANDS:
        if not any((a, "band", b) in result["catch"] for a in ATTACKS):
            continue
        cells = "  ".join(_pct(*result["catch"][(a, "band", b)]) for a in ATTACKS)
        rej, tot = fr[("band", b)]
        print(f"  {b:<34} {cells}  {rej:>4}/{tot:<5}")
    print(f"  (whole-artifact false rejections: "
          f"{result['case_false_rej']}/{result['cases']} untouched cases rejected)")


def main():
    ap = argparse.ArgumentParser(description="Measure traceability gates by injection")
    ap.add_argument("--gate", choices=list(GATES), action="append")
    ap.add_argument("--n", type=int, default=N_PER_SITE,
                    help="injections per attack per site")
    ap.add_argument("--seed", type=int, default=SEED)
    ap.add_argument("--scope", action="store_true",
                    help="scope-width report only — no injections, cheap")
    args = ap.parse_args()

    for name in (args.gate or list(GATES)):
        target = GATES[name]()
        if args.scope:
            cases = target.cases()
            if not cases:
                print(f"[{name}] no cases")
                continue
            all_sites = [s for c in cases for s in target.sites(c)]
            widths = defaultdict(list)
            for s in all_sites:
                widths[s.dp].append(len({round(v, 4) for v in s.scope}))
            _scope_report(name, {"sites": len(all_sites), "cases": len(cases),
                                 "widths": widths, "dp_names": target.dp_names})
            continue
        result = measure(target, args.n, args.seed)
        if not result:
            print(f"[{name}] no cases / no sites")
            continue
        _scope_report(name, result)
        _catch_report(name, result)

    print(f"\nn={args.n} injections per attack per site, seed={args.seed}. "
          "Catch = share of fabricated numbers the gate rejected.\n"
          "Never read one gate as a single number — a fabricated value's fate is set "
          "by the scope of the block it lands in.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
