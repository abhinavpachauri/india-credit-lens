"""One gate in front of every paid model call.

Spending the editor's API balance is not a technical decision, it is theirs. Asking each time
does not survive a session boundary — the same overspend has recurred across sessions because a
promise lives in a conversation and the code does not know about it. So the code knows now.

Any path that can bill goes through `require_approval()`, which refuses unless the run was
explicitly authorised for this invocation. There is no default-on mode and no remembered consent:
approval is per-process, because "you said yes last week" is exactly the reasoning that produced
the problem.

Approval also requires a PRICE. A caller must pass what the run is expected to cost, and a call
with no estimate is refused even when `ICL_LLM_OK=1` is set — approving an unknown amount is not
informed consent, it is a blank cheque. The estimate is built from this project's own recorded
token usage (`llm_cache.tokens_used`), so it reflects what these payloads actually cost rather
than a guess.

To authorise a run:

    ICL_LLM_OK=1 python3 analysis/core/run_inference.py --verify-api ...

Deterministic work is unaffected — computes, gates, validators and the Chrome sourcing path never
touch this. If a script stops with LLMSpendNotApproved, that is the guard working: decide whether
the call is worth it, then re-run with the variable set.
"""
from __future__ import annotations

import os

# USD per MILLION tokens (input, output), list price. Kept here rather than at the call sites so
# one edit re-prices every path that can bill.
PRICING = {
    "claude-opus-5":                (15.00, 75.00),
    "claude-sonnet-5":               (3.00, 15.00),
    "claude-sonnet-4-5-20250929":    (3.00, 15.00),
    "claude-haiku-4-5-20251001":     (1.00,  5.00),
}
DEFAULT_MODEL = "claude-sonnet-4-5-20250929"

# Hard ceiling for a single authorised run, set by the editor: "keep a limit of $5 as upper
# limit, in any case don't go beyond that" (2026-09-05). It is deliberately NOT overridable by
# an environment variable — a ceiling you can raise from the command line is a suggestion, and
# the whole reason this module exists is that a rule living outside the code kept failing. A run
# priced above this refuses even when ICL_LLM_OK=1; raising it is a deliberate edit here.
MAX_RUN_USD = 5.00

# These payloads are large-in / small-out (a full period series in, a paragraph per signal out).
# Measured across the recorded evaluate runs, output is a modest share of the total; the estimate
# leans conservative (assuming MORE output than typical) so an approved amount is an upper bound.
OUTPUT_SHARE = 0.20


def estimate_usd(total_tokens: float, model: str = DEFAULT_MODEL,
                 output_share: float = OUTPUT_SHARE) -> float:
    """Dollar cost of `total_tokens` split between input and output at list price.

    Deliberately takes a TOTAL, because that is what this project actually records
    (`llm_cache.tokens_used`); splitting by a measured share beats inventing two numbers.
    """
    inp, out = PRICING.get(model, PRICING[DEFAULT_MODEL])
    out_tok = total_tokens * output_share
    in_tok = total_tokens - out_tok
    return (in_tok * inp + out_tok * out) / 1_000_000


class LLMSpendNotApproved(RuntimeError):
    """Raised instead of billing. Carries what would have been spent on, so the human choosing
    whether to approve can see what they are approving rather than a bare refusal."""


def approved() -> bool:
    return os.environ.get("ICL_LLM_OK") == "1"


def require_approval(what: str, calls: str | int = "unknown",
                     est_usd: float | None = None, basis: str = "") -> None:
    """Refuse unless this process was explicitly authorised to spend a KNOWN amount.

    `what` names the work ("S4 source-finding", "Stage 5 evaluate"), `calls` its rough size, and
    `est_usd` what it is expected to cost. The size alone was not enough: "a hundred calls" does
    not tell the person approving whether they are spending cents or tens of dollars, and that is
    the question they are actually being asked.

    A missing estimate refuses EVEN WHEN APPROVED. Consent to an unnamed amount is a blank
    cheque, and the whole point of this module is that the amount is the editor's decision.
    """
    if est_usd is None:
        raise LLMSpendNotApproved(
            f"{what} has no cost estimate, so it cannot be approved.\n"
            f"Nothing was billed. Estimate the spend first (llm_budget.estimate_usd) and pass\n"
            f"est_usd — an approval without an amount is a blank cheque, not consent."
        )
    price = f"~${est_usd:,.2f}"
    if est_usd > MAX_RUN_USD:
        raise LLMSpendNotApproved(
            f"{what} is estimated at {price}, above the {MAX_RUN_USD:,.2f} USD ceiling for a "
            f"single run.\nNothing was billed. Split the work into smaller runs, or raise "
            f"MAX_RUN_USD in analysis/core/llm_budget.py deliberately."
        )
    if approved():
        return
    raise LLMSpendNotApproved(
        f"{what} would make ~{calls} paid model call(s) costing {price} and this run is not "
        f"authorised.\n"
        + (f"Estimate basis: {basis}\n" if basis else "")
        + f"Nothing was billed. To authorise THIS run: ICL_LLM_OK=1 <command>\n"
        f"(Per-process by design — consent is not remembered across runs.)"
    )
