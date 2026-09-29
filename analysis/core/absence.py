"""
core/absence.py — why a cell has no value: one closed list, defined once
───────────────────────────────────────────────────────────────────────
An absent reading carries a reason CODE, never a blank or a zero, and the sentence a reader sees is
rendered from the code (DASHBOARD_SPEC §21.4). Both specs cite this module and neither copies it
(signals/README §1f, COMPOSITION_SPEC §24.1).

Two kinds, and who may use each:
  * STATIC — a property of the match, declared in a concordance file and checked by
    `cross/validate_concordance.py`. It does not change from month to month.
  * PER_PERIOD — decided by compute for one period (phase 3). A concordance may not declare one:
    "not released" written into a file stays true long after MoSPI publishes.

Anything outside these lists raises. In particular "overdue" is not a reason: a reference value past
its expected date fails the gate, because an outage must never read as a legitimate absence.
"""

STATIC = {
    "no_counterpart":    "MoSPI publishes no series that measures this part",
    "shared_group":      "MoSPI's nearest series pools this part with others, so it is not a match",
    "cadence_mismatch":  "MoSPI measures this part only at another frequency than this table's",
    "weights_unsourced": "the part combines several MoSPI series, and their weights are not yet sourced",
    "mapping_undecided": "which MoSPI series match this part is an open decision",
}

PER_PERIOD = {
    "not_released":       "MoSPI's figure for this period is not yet due",
    "credit_history_gap": "the credit data has no reading for this period",
}

#: An aggregate compared with a MoSPI aggregate that is RBI's convention but not exact
#: (COMPOSITION_SPEC §24.1). The note's share is computed each period in phase 4, never typed.
APPROXIMATIONS = {
    "industry_includes_infra_services": "industry credit includes infrastructure that national accounts count as services",
    "services_includes_nbfc_onlending": "services credit includes lending to NBFCs, which is lent on rather than spent",
    "nonfood_vs_gdp":                   "non-food credit is compared with the whole economy's output",
}
