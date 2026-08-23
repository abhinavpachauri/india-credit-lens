"""One gate in front of every paid model call.

Spending the editor's API balance is not a technical decision, it is theirs. Asking each time
does not survive a session boundary — the same overspend has recurred across sessions because a
promise lives in a conversation and the code does not know about it. So the code knows now.

Any path that can bill goes through `require_approval()`, which refuses unless the run was
explicitly authorised for this invocation. There is no default-on mode and no remembered consent:
approval is per-process, because "you said yes last week" is exactly the reasoning that produced
the problem.

To authorise a run:

    ICL_LLM_OK=1 python3 analysis/core/run_inference.py --verify-api ...

Deterministic work is unaffected — computes, gates, validators and the Chrome sourcing path never
touch this. If a script stops with LLMSpendNotApproved, that is the guard working: decide whether
the call is worth it, then re-run with the variable set.
"""
from __future__ import annotations

import os


class LLMSpendNotApproved(RuntimeError):
    """Raised instead of billing. Carries what would have been spent on, so the human choosing
    whether to approve can see what they are approving rather than a bare refusal."""


def approved() -> bool:
    return os.environ.get("ICL_LLM_OK") == "1"


def require_approval(what: str, calls: str | int = "unknown") -> None:
    """Refuse unless this process was explicitly authorised to spend.

    `what` names the work (\"S4 source-finding\", \"Stage 5 evaluate\") and `calls` its rough
    size, because the size is usually the thing that matters: three calls to draft proposals and
    a hundred to hunt sources are not the same request.
    """
    if approved():
        return
    raise LLMSpendNotApproved(
        f"{what} would make ~{calls} paid model call(s) and this run is not authorised.\n"
        f"Nothing was billed. To authorise THIS run: ICL_LLM_OK=1 <command>\n"
        f"(Per-process by design — consent is not remembered across runs.)"
    )
