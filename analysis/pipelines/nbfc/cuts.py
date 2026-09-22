"""
NBFC dashboard cuts — the dimension table, and nothing else.

The other two pipelines keep their cut table inside their CARD generator, because both have
one. NBFC deliberately does not (PLAN_2026-09-16_NBFC.md D2: table + band for v1, cards
deferred until the series is long enough to support "fastest in N periods"). So the table
lives on its own here, which is arguably where it always belonged: a cut declares a DIMENSION
— what pane a reader finds it under — and that is a presentation decision, independent of
whether anything writes news cards about it.

`section` is the dashboard dimension id. Everything else about a cut — its parts, its
families, whether its parts sum to its parent — is discovered from the registry and the data.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(next(p for p in Path(__file__).resolve().parents
                            if (p / ".git").is_dir()) / "analysis"))

from core.movement_cards import MovementCut                            # noqa: E402

#: Signal-id stem prefix. Every NBFC cut follows it, so no cut needs `stem_full`.
MOVEMENT_PREFIX = "nbfc-"

#: Why two cuts carry no mix, in the reader's words. RBI names exactly ONE child of Industry
#: (Infrastructure) and ONE of Infrastructure (Power), and a mix needs something to be a mix
#: BETWEEN — with a single part the tilt is trivially that part, and "steered toward Power,
#: away from Power" is what the causal layer produced before it learned to decline.
_ONE_PART = ("RBI names only one part of this cut, so there is no mix between parts to state "
             "— only how that one part is moving.")

MOVEMENT_CUTS = [
    MovementCut("main", "mainSectors", "nbfc-main-yoy-scan", "NBFC credit",
                parent_yoy="nbfc-credit-yoy", parent_label="NBFC credit"),
    MovementCut("industry", "industry", "nbfc-industry-yoy-scan", "NBFC industry credit",
                parent_yoy="nbfc-industry-yoy", parent_label="Industry credit",
                no_mix_note=_ONE_PART),
    MovementCut("infra", "infrastructure", "nbfc-infra-yoy-scan", "NBFC infrastructure credit",
                parent_yoy="nbfc-infra-yoy", parent_label="Infrastructure credit",
                no_mix_note=_ONE_PART),
    MovementCut("services", "services", "nbfc-services-yoy-scan", "NBFC services credit",
                parent_yoy="nbfc-services-yoy", parent_label="Services credit"),
    MovementCut("retail", "retail", "nbfc-retail-yoy-scan", "NBFC retail credit",
                parent_yoy="nbfc-retail-yoy", parent_label="Retail credit"),
]

#: Dimensions with a parent rate but no decomposition of their own. NBFC has none: every cut
#: this source publishes breaks into at least one named part.
STATE_RATE_ONLY: list = []
