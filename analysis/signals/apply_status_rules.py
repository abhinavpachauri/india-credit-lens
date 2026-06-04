"""
Apply momentum-based status_rules to all Layer 1 signals in registry.json.

Six rule templates keyed by signal type (determined by compute method):
  yoy        — series_yoy, csv_total_yoy, csv_category_yoy, csv_sum_yoy,
                section_scan_yoy
  share      — series_share, multi_series_share, csv_ratio_sum,
                csv_category_share, csv_category_scan_share, section_scan_share
  absolute   — series_abs, csv_total_abs, abs_undercount
  spread     — yoy_spread, yoy_spread_named
  ratio      — csv_total_ratio
  breadth    — count_positive_yoy
  bank_scan  — csv_bank_scan (value_type determines yoy vs absolute sub-type)

Run once. Safe to re-run (idempotent — overwrites status_rules).
After running, re-run append for all periods to recompute statuses in DB.
"""

import json
from pathlib import Path

REPO     = Path(__file__).resolve().parent.parent.parent
REG_PATH = REPO / "analysis" / "signals" / "registry.json"

# ── Rule templates ────────────────────────────────────────────────────────────

RULES: dict[str, list[dict]] = {

    "yoy": [
        {"if": "value > prev_value and value > 0", "then": "strengthening"},
        {"if": "value > 0",                        "then": "active"},
        {"if": "true",                             "then": "declining"},
    ],

    "share": [
        {"if": "value > prev_value + 0.5", "then": "strengthening"},
        {"if": "value < prev_value - 0.5", "then": "weakening"},
        {"if": "true",                     "then": "active"},
    ],

    "absolute": [
        {"if": "value > prev_value", "then": "strengthening"},
        {"if": "value < prev_value", "then": "weakening"},
        {"if": "true",               "then": "active"},
    ],

    "spread": [
        {"if": "value > prev_value", "then": "strengthening"},
        {"if": "value < prev_value", "then": "weakening"},
        {"if": "true",               "then": "active"},
    ],

    "ratio": [
        {"if": "value > prev_value", "then": "strengthening"},
        {"if": "value < prev_value", "then": "weakening"},
        {"if": "true",               "then": "active"},
    ],

    "breadth": [
        {"if": "value > prev_value", "then": "strengthening"},
        {"if": "value == 0",         "then": "declining"},
        {"if": "value < prev_value", "then": "weakening"},
        {"if": "true",               "then": "active"},
    ],
}

# ── Method → rule type mapping ────────────────────────────────────────────────

METHOD_TYPE: dict[str, str] = {
    # YoY
    "series_yoy":          "yoy",
    "csv_total_yoy":       "yoy",
    "csv_category_yoy":    "yoy",
    "csv_sum_yoy":         "yoy",
    "section_scan_yoy":    "yoy",
    # Share / composition
    "series_share":        "share",
    "multi_series_share":  "share",
    "csv_ratio_sum":       "share",
    "csv_category_share":  "share",
    "csv_category_scan_share": "share",
    "section_scan_share":  "share",
    # Absolute level
    "series_abs":          "absolute",
    "csv_total_abs":       "absolute",
    "abs_undercount":      "absolute",
    # Spread
    "yoy_spread":          "spread",
    "yoy_spread_named":    "spread",
    # Ratio
    "csv_total_ratio":     "ratio",
    # Breadth count
    "count_positive_yoy":  "breadth",
    # static_active — no rules needed (always "active")
    "static_active":       None,
    # is_max_series — no rules (binary 0/1 index signal)
    "is_max_series":       None,
}


def signal_type(sig: dict) -> str | None:
    method = sig.get("compute", {}).get("method", "")
    if method == "csv_bank_scan":
        vt = sig.get("compute", {}).get("value_type", "value")
        return "yoy" if vt == "yoy" else "absolute"
    return METHOD_TYPE.get(method)


def main():
    with open(REG_PATH) as f:
        reg = json.load(f)

    patched = 0
    skipped_no_compute = 0
    skipped_no_method = 0
    by_type: dict[str, int] = {}

    for sid, sig in reg["signals"].items():
        if sig.get("layer") != 1:
            continue
        compute = sig.get("compute")
        if not compute:
            skipped_no_compute += 1
            continue

        stype = signal_type(sig)
        if stype is None:
            # static_active / is_max_series — leave status_rules empty
            skipped_no_method += 1
            continue

        rules = RULES.get(stype)
        if rules is None:
            skipped_no_method += 1
            continue

        sig["compute"]["status_rules"] = rules
        by_type[stype] = by_type.get(stype, 0) + 1
        patched += 1

    with open(REG_PATH, "w") as f:
        json.dump(reg, f, indent=2, ensure_ascii=False)
        f.write("\n")

    print(f"Patched {patched} Layer 1 signals with status_rules")
    print(f"Skipped {skipped_no_compute} (no compute spec)  "
          f"{skipped_no_method} (no rules needed)")
    print("Breakdown by type:")
    for t, n in sorted(by_type.items()):
        print(f"  {t:<12} {n:>3} signals  →  {RULES[t]}")


if __name__ == "__main__":
    main()
