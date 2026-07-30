#!/usr/bin/env python3
"""
render.py — one reader-facing number formatter, shared everywhere
------------------------------------------------------------------
`fmt_value` turns a stored signal value into the string a reader sees — lakh/crore for big
counts, `%`/`pp` for rates, `₹…L Cr` for outstanding. It has to be ONE function, because
several layers must agree on it exactly:

  * the distribution layer renders numbers with it (`distribution_sources.fmt_value`);
  * the opportunity narrative gives the LLM these strings to copy verbatim, so the prose
    reads "13.6 lakh micro ATMs", not "1358241.0";
  * Check 4f (`validate_opportunity_traceability`) accepts these rendered forms as grounded,
    so the reader-formatted number still traces to its signal.

If each kept its own copy they would drift, and a number that reads fine would fail to
trace (or vice-versa). So it lives here, with no heavy dependencies, and everyone imports it.
"""


def fmt_value(value, unit):
    """Render a db value the way the dashboards and issues do — the reader's form."""
    if value is None:
        return ""
    if unit == "pct":
        return f"{value:.1f}%"
    if unit == "pp":
        return f"{value:.1f}pp"
    if unit == "lcr_cr":                       # stored in ₹ crore → shown in lakh crore
        return f"₹{value / 1e5:.1f}L Cr"
    if unit == "count":
        if abs(value) >= 1e7:
            return f"{value / 1e7:.1f} crore"
        if abs(value) >= 1e5:
            return f"{value / 1e5:.1f} lakh"
        return f"{value:,.0f}"
    # Default (streaks, ratios, …): an integer shows as "12", not "12.0" — a bare "N.0" reads
    # as a raw float to the reader (and to the unformatted-number lint).
    return f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
