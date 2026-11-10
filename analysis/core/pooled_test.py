#!/usr/bin/env python3
"""
pooled_test.py — one driver, tested across every line that names it
────────────────────────────────────────────────────────────────────
SYSTEM_MODEL_SPEC §16 Step 6d (v3.3). A per-line driver test (Step 6c) reads ~17-33 monthly
changes, where only |r| ≳ 0.34-0.5 can pass, so a modest real link reads `too_short` or flips from
month to month (Medium Enterprises and Textiles: admitted 2026-10-26, withdrawn 2026-11-10). Many
hypotheses share one driver, so the driver is tested once across all of them.

What it can see. Every line is measured as its gap to its own group, and a group's parts' gaps
sum to about zero, so a response shared equally by every part cancels by construction; the group's
own line carries it (Step 6c). The parts can show that the driver SEPARATES them. Two forms:

  separation  mean over lines of r_i²: does the driver separate these lines more than chance?
              No sign needed. The effect is the excess over the shuffled mean, as an rms r.
  direction   mean over lines of s_i·r_i, s_i the line's declared sign. Refused when every line of
              one sibling set carries the same sign: that claim cancels in the gaps.

The month is the unit. The parts of a group move together in a month for reasons not removed, so
lines × months are not independent observations. The null shuffles the driver's months once and
applies that same shuffle to every line; the range resamples months, all lines together.

The delay is found on one window of months and confirmed on the months outside it (the Step 6c
split), frozen at first discovery by the caller.

Pure given its inputs (seeded). No LLM, no file access: `explainability.py pool` does the I/O.
"""
from __future__ import annotations

import numpy as np

ALPHA = 0.05
SHUFFLES = 10_000
BOOTSTRAPS = 2_000
SEED = 20261110
MIN_PAIRS = 10            # per line, as Step 6b
MIN_LINES = 3             # fewer is not a pool
MAX_LAG = 9               # as Step 6c discovery
R_POOL_PRACTICAL = 0.15   # user 2026-11-10: below this a link does not matter (~2% of a line's movement)
DOMINANT_SHARE = 0.5      # one line carrying half the statistic is checked by leaving it out

LIMIT = ("a response shared equally by every part of a group cancels in the gaps to that group; "
         "the group's own line carries it (Step 6c), so this test cannot see it")


class Refused(ValueError):
    """The form cannot answer the question as declared (e.g. one sign across a sibling set)."""


def _residual(y: np.ndarray, t: np.ndarray) -> np.ndarray:
    """y with its linear fit on t removed (the tide step of Step 6b)."""
    A = np.column_stack([t, np.ones_like(t)])
    coef, *_ = np.linalg.lstsq(A, y, rcond=None)
    return y - A @ coef


def _rows_corr(X: np.ndarray, y: np.ndarray) -> np.ndarray:
    """Pearson r of every row of X with y."""
    Xc = X - X.mean(axis=1, keepdims=True)
    yc = y - y.mean()
    den = np.sqrt((Xc ** 2).sum(axis=1) * (yc ** 2).sum())
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, (Xc @ yc) / den, 0.0)


def _weighted_corr(X: np.ndarray, y: np.ndarray, W: np.ndarray) -> np.ndarray:
    """Pearson r of x and y under each row of weights W (a bootstrap draw counts a month W times)."""
    s = W.sum(axis=1, keepdims=True)
    s = np.where(s > 0, s, 1)
    mx, my = (W * X).sum(1, keepdims=True) / s, (W * y).sum(1, keepdims=True) / s
    dx, dy = X - mx, y - my
    cov = (W * dx * dy).sum(1)
    den = np.sqrt((W * dx ** 2).sum(1) * (W * dy ** 2).sum(1))
    with np.errstate(invalid="ignore", divide="ignore"):
        return np.where(den > 0, cov / den, 0.0)


def prepare(a: dict[int, float], t_a: dict[int, float], lines: dict[str, dict[int, float]],
            t_b: dict[int, float], lag: int, keep=lambda month: True) -> tuple:
    """The pooled design at one delay. The driver's own tide is removed once, over all its months,
    so a shuffle moves one value per month for every line at once. Each line's tide is removed over
    its own paired months. `keep(target_month)` selects the months read (the confirmation window).

    Returns (months K, driver residual D over K, {line: (index into K, y residual)})."""
    K = sorted(k for k in a if k in t_a)
    if len(K) < MIN_PAIRS:
        return K, np.array([]), {}
    D = _residual(np.array([a[k] for k in K]), np.array([t_a[k] for k in K]))
    pos = {k: i for i, k in enumerate(K)}
    design = {}
    for line, b in lines.items():
        ks = [k for k in K if k + lag in b and k + lag in t_b and keep(k + lag)]
        if len(ks) < MIN_PAIRS:
            continue
        y = _residual(np.array([b[k + lag] for k in ks]), np.array([t_b[k + lag] for k in ks]))
        design[line] = (np.array([pos[k] for k in ks]), y)
    return K, D, design


def _stat(r: np.ndarray, signs: np.ndarray | None) -> np.ndarray:
    """r: (..., lines). Separation: mean r². Direction: mean s·r."""
    return (r * signs).mean(axis=-1) if signs is not None else (r ** 2).mean(axis=-1)


def _line_r(Dmat: np.ndarray, design: dict, names: list[str]) -> np.ndarray:
    """(rows of Dmat, lines) correlations; Dmat is (P, |K|), one driver series per row."""
    return np.column_stack([_rows_corr(Dmat[:, design[n][0]], design[n][1]) for n in names])


def evaluate(K: list[int], D: np.ndarray, design: dict, signs: dict[str, int] | None = None,
             family: int = 1, shuffles: int = SHUFFLES, bootstraps: int = BOOTSTRAPS,
             seed: int = SEED, attribute: bool = True) -> dict:
    """The pooled verdict on a prepared design. `signs` given → direction form, else separation."""
    names = sorted(design)
    alpha = ALPHA / family
    n_months = int(np.median([len(design[n][1]) for n in names])) if names else 0
    base = {"form": "direction" if signs else "separation", "family": family, "alpha": round(alpha, 4),
            "lines_n": len(names), "months_per_line": n_months, "limit": LIMIT}
    if len(names) < MIN_LINES:
        return {**base, "verdict": "too_short",
                "why": f"{len(names)} lines with ≥{MIN_PAIRS} paired months; a pool needs {MIN_LINES}"}
    s = np.array([signs[n] for n in names], dtype=float) if signs else None
    rng = np.random.default_rng(seed)

    r_obs = _line_r(D[None, :], design, names)[0]
    obs = float(_stat(r_obs, s))
    perms = np.array([rng.permutation(len(K)) for _ in range(shuffles)])
    null = _stat(_line_r(D[perms], design, names), s)
    if s is None:
        hits = int((null >= obs).sum())                            # one-sided: more separation
    else:
        hits = int((np.abs(null) >= abs(obs)).sum())               # two-sided, then the sign
    p = (hits + 1) / (shuffles + 1)          # the observed order counts as one shuffle: exact, not optimistic
    null_mean = float(null.mean())
    bar = float(np.quantile(null, 1 - alpha)) if s is None else float(np.quantile(np.abs(null), 1 - alpha))

    def effect(v):                                                  # in r units
        return np.sqrt(np.clip(v - null_mean, 0, None)) if s is None else v
    eff = float(effect(np.array(obs)))

    # The range: months resampled with replacement, all lines together (block = month). A resample
    # repeats months, and repeated months inflate r² (measured 2026-11-10: on SIBC a range of
    # [0.15, 0.48] beside p = 0.065). So the separation range subtracts the null mean measured UNDER
    # the same resamples (each draw also read with the driver shuffled), not the plain shuffled mean.
    # `bootstraps=0` skips the range (rate measurements).
    lo = hi = None
    if bootstraps:
        counts = rng.multinomial(len(K), np.full(len(K), 1 / len(K)), size=bootstraps).astype(float)

        def boot(Dmat):
            return _stat(np.column_stack([_weighted_corr(Dmat[:, design[n][0]], design[n][1],
                                                         counts[:, design[n][0]]) for n in names]), s)
        sb = boot(np.broadcast_to(D, (bootstraps, len(K))))
        if s is None:
            nb = boot(D[np.array([rng.permutation(len(K)) for _ in range(bootstraps)])])
            eb = np.sqrt(np.clip(sb - nb.mean(), 0, None))
        else:
            eb = sb
        lo, hi = (float(x) for x in np.quantile(eb, [0.025, 0.975]))

    # Months needed: the bar shrinks as months grow (separation: excess ∝ 1/n; direction: ∝ 1/√n).
    excess_bar = (bar - null_mean) if s is None else bar
    excess_obs = (obs - null_mean) if s is None else obs * 1.0
    if s is not None:
        excess_obs = abs(excess_obs)
    needed = None
    if excess_obs > 0 and excess_obs < excess_bar:
        n_total = n_months * (excess_bar / excess_obs) ** (1 if s is None else 2)
        needed = int(np.ceil(n_total - n_months))

    share = (r_obs ** 2 if s is None else s * r_obs)
    tot = share.sum()
    per_line = [{"line": n, "n": int(len(design[n][1])), "r": round(float(r), 3),
                 "share": round(float(sh / tot), 3) if tot else None}
                for n, r, sh in zip(names, r_obs, share)]

    if p < alpha:
        verdict = "linked" if (s is None or obs > 0) else "opposite"
    elif hi is not None and hi < R_POOL_PRACTICAL:
        verdict = "no_meaningful_link"
    else:
        verdict = "too_short"
    res = {**base, "verdict": verdict, "statistic": round(obs, 4), "null_mean": round(null_mean, 4),
           "bar": round(bar, 4), "p": round(p, 4),
           "effect": {"value": round(eff, 3),
                      "range": [round(lo, 3), round(hi, 3)] if hi is not None else None,
                      "unit": "rms excess r over the shuffled mean" if s is None else "mean signed r",
                      "practical": R_POOL_PRACTICAL},
           "months_needed": needed, "lines": per_line}

    # Attribute, don't suppress: a pool carried by one line is that line's finding.
    if attribute and verdict in ("linked", "opposite") and tot:
        top = max(per_line, key=lambda x: x["share"] or 0)
        if (top["share"] or 0) >= DOMINANT_SHARE:
            rest = {n: v for n, v in design.items() if n != top["line"]}
            loo = evaluate(K, D, rest, {n: signs[n] for n in rest} if signs else None, family,
                           shuffles, 0, seed, attribute=False) if len(rest) >= MIN_LINES else None
            res["leave_one_out"] = {"line": top["line"], "share": top["share"],
                                    "verdict_without": loo["verdict"] if loo else "too_short",
                                    "p_without": loo.get("p") if loo else None}
            if not loo or loo["verdict"] not in ("linked", "opposite"):
                res["verdict"] = "one_line"
                res["why"] = f"passes only with {top['line']} ({top['share']:.0%} of the statistic)"
    return res


def check_direction(signs: dict[str, int], groups: dict[str, str]) -> None:
    """Refuse the direction form where it cannot answer: a sibling set whose lines all carry one sign
    claims a response that cancels in the gaps to that set's group."""
    by = {}
    for line, g in groups.items():
        if line in signs:
            by.setdefault(g, set()).add(signs[line])
    uniform = sorted(g for g, ss in by.items() if len(ss) == 1 and
                     sum(1 for l, gg in groups.items() if gg == g and l in signs) > 1)
    if uniform:
        raise Refused("one sign across every line of a sibling set (" + ", ".join(uniform) +
                      "): that claim cancels in the gaps; give each line a differential reason "
                      "or use the separation form")


def pooled(a: dict[int, float], t_a: dict[int, float], lines: dict[str, dict[int, float]],
           t_b: dict[int, float], signs: dict[str, int] | None = None,
           groups: dict[str, str] | None = None, family: int = 1, frozen: dict | None = None,
           shuffles: int = SHUFFLES, bootstraps: int = BOOTSTRAPS, seed: int = SEED) -> dict:
    """Find the family's delay on one window of months, confirm on every month outside it.

    `frozen` = {"from", "cutoff", "lag"} from the family's first result: later runs only re-confirm,
    on a set that grows as months arrive or history is backfilled (the Step 6c rule)."""
    if signs is not None:
        check_direction(signs, groups or {})
    usable = sorted({m for b in lines.values() for m in b if m in t_b})
    if frozen and frozen.get("lag") is not None:
        start, cutoff, lag, profile = frozen["from"], frozen["cutoff"], frozen["lag"], {}
    else:
        if len(usable) < 2 * MIN_PAIRS:
            return {"verdict": "too_short", "limit": LIMIT, "discovery": {"lag": None},
                    "why": f"{len(usable)} change months; discovery and confirmation need {MIN_PAIRS} each"}
        start, cutoff = usable[0], usable[len(usable) // 2 - 1]
        inside = lambda m: start <= m <= cutoff  # noqa: E731
        profile = {}
        for L in range(MAX_LAG + 1):
            K, D, design = prepare(a, t_a, lines, t_b, L, inside)
            if len(design) < MIN_LINES:
                profile[L] = {"lines": len(design)}
                continue
            names = sorted(design)
            r = _line_r(D[None, :], design, names)[0]
            st = float(_stat(r, np.array([signs[n] for n in names], float) if signs else None))
            profile[L] = {"lines": len(design), "statistic": round(st, 4)}
        scored = {L: v["statistic"] for L, v in profile.items() if "statistic" in v}
        if not scored:
            return {"verdict": "too_short", "limit": LIMIT,
                    "discovery": {"from": start, "cutoff": cutoff, "lag": None, "profile": profile},
                    "why": "no delay had enough lines before the cutoff"}
        lag = max(scored, key=scored.get)
    outside = lambda m: m < start or m > cutoff  # noqa: E731
    K, D, design = prepare(a, t_a, lines, t_b, lag, outside)
    res = evaluate(K, D, design, {n: signs[n] for n in design} if signs else None, family,
                   shuffles, bootstraps, seed)
    return {**res, "at_lag": lag, "discovery": {"from": start, "cutoff": cutoff, "lag": lag, "profile": profile}}
