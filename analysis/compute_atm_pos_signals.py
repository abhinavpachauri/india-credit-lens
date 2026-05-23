#!/usr/bin/env python3
"""
Stage 4a — ATM/POS Signal Computation
Reads atm_pos_consolidated.csv and computes fully deterministic signals:
  - MoM % and growth streak per metric (total level)
  - Category share and delta for primary metric per group
  - Top-10 bank rankings + rank changes for primary metric per group
  - Cross-metric shares within each group

Output: analysis/rbi_atm_pos/signals.json
        (also symlinked / copied to web/public/data/atm_pos_signals.json)

Usage:
    python3 analysis/compute_atm_pos_signals.py
"""

import csv
import json
import shutil
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────

ROOT      = Path(__file__).parent.parent
CSV_PATH  = ROOT / "web/public/data/atm_pos_consolidated.csv"
OUT_PATH  = ROOT / "analysis/rbi_atm_pos/signals.json"
WEB_PATH  = ROOT / "web/public/data/atm_pos_signals.json"

# ── Group definitions ─────────────────────────────────────────────────────────

GROUPS = {
    "cc": {
        "label":   "Credit Card",
        "primary": "credit_cards",
        "metrics": [
            "credit_cards",
            "cc_pos_txn_vol", "cc_pos_txn_val",
            "cc_ecom_txn_vol", "cc_ecom_txn_val",
            "cc_atm_withdrawal_vol", "cc_atm_withdrawal_val",
            "cc_other_txn_vol", "cc_other_txn_val",
        ],
        # Vol metrics used for cross-metric share computation
        "vol_metrics": [
            "cc_pos_txn_vol", "cc_ecom_txn_vol",
            "cc_atm_withdrawal_vol", "cc_other_txn_vol",
        ],
    },
    "dc": {
        "label":   "Debit Card",
        "primary": "debit_cards",
        "metrics": [
            "debit_cards",
            "dc_atm_withdrawal_vol", "dc_atm_withdrawal_val",
            "dc_pos_txn_vol", "dc_pos_txn_val",
            "dc_ecom_txn_vol", "dc_ecom_txn_val",
            "dc_pos_withdrawal_vol", "dc_pos_withdrawal_val",
            "dc_other_txn_vol", "dc_other_txn_val",
        ],
        "vol_metrics": [
            "dc_atm_withdrawal_vol", "dc_pos_txn_vol",
            "dc_ecom_txn_vol", "dc_pos_withdrawal_vol", "dc_other_txn_vol",
        ],
    },
    "infra": {
        "label":   "Digital Infrastructure",
        "primary": "pos_terminals",
        "metrics": [
            "pos_terminals", "upi_qr",
            "atm_onsite", "atm_offsite",
            "micro_atms", "bharat_qr",
        ],
        "vol_metrics": [],  # no vol/val split in infra
    },
}

CAT_FULL_TO_SHORT = {
    "Public Sector Banks":  "PSB",
    "Private Sector Banks": "Private",
    "Foreign Banks":        "Foreign",
    "Small Finance Banks":  "SFB",
    "Payment Banks":        "Payments",
}

TOP_N = 10

# ── Helpers ───────────────────────────────────────────────────────────────────

def fmt_month(iso: str) -> str:
    """'2026-03-31' → 'Mar 2026'"""
    d = datetime.strptime(iso, "%Y-%m-%d")
    return d.strftime("%b %Y")


def round2(v: float) -> float:
    return round(v, 2)


def mom_pct(latest: float, prior: float) -> float | None:
    if prior == 0:
        return None
    return round2((latest - prior) / prior * 100)


def compute_streak(values: list[float]) -> tuple[int, str]:
    """
    Given values in chronological order, return (streak_length, direction)
    for the consecutive run ending at the last value.
    Direction is 'up', 'down', or 'flat'.
    """
    if len(values) < 2:
        return 1, "flat"
    directions = []
    for i in range(1, len(values)):
        diff = values[i] - values[i - 1]
        if diff > 0:
            directions.append("up")
        elif diff < 0:
            directions.append("down")
        else:
            directions.append("flat")
    latest_dir = directions[-1]
    streak = 1
    for d in reversed(directions[:-1]):
        if d == latest_dir:
            streak += 1
        else:
            break
    return streak, latest_dir


def share(part: float, total: float) -> float | None:
    if total == 0:
        return None
    return round2(part / total * 100)


# ── Load CSV ──────────────────────────────────────────────────────────────────

def load_csv() -> tuple[list[str], dict]:
    """
    Returns:
        dates      : sorted list of ISO date strings
        data[date][record_type][bank_name][metric] = value
    """
    data: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(dict)))
    dates_set: set[str] = set()

    with open(CSV_PATH) as f:
        for row in csv.DictReader(f):
            date   = row["report_date"]
            rtype  = row["record_type"]
            bank   = row["bank_name"]
            metric = row["metric"]
            try:
                value = float(row["value"])
            except (ValueError, TypeError):
                value = 0.0
            data[date][rtype][bank][metric] = value
            dates_set.add(date)

    return sorted(dates_set), data


# ── Signal builders ───────────────────────────────────────────────────────────

def build_total_metric_signals(dates, data, metrics):
    """MoM%, streak, latest value for each metric at the Total level."""
    latest = dates[-1]
    prior  = dates[-2] if len(dates) > 1 else None
    out    = {}

    for metric in metrics:
        vals_by_date = {
            d: data[d]["total"].get("Total", {}).get(metric, 0.0)
            for d in dates
        }
        latest_val = vals_by_date[latest]
        prior_val  = vals_by_date[prior] if prior else None
        chron_vals = [vals_by_date[d] for d in dates]
        streak_len, streak_dir = compute_streak(chron_vals)

        out[metric] = {
            "latest":      round2(latest_val),
            "prior":       round2(prior_val) if prior_val is not None else None,
            "mom_pct":     mom_pct(latest_val, prior_val) if prior_val is not None else None,
            "mom_dir":     ("up" if latest_val > prior_val else "down" if latest_val < prior_val else "flat")
                           if prior_val is not None else "flat",
            "streak_months": streak_len,
            "streak_dir":  streak_dir,
        }
    return out


def build_cross_metric_signals(dates, data, vol_metrics):
    """Share of each vol metric within the group total volume."""
    if not vol_metrics:
        return {}

    latest = dates[-1]
    prior  = dates[-2] if len(dates) > 1 else None

    def vol_shares(date):
        vals = {
            m: data[date]["total"].get("Total", {}).get(m, 0.0)
            for m in vol_metrics
        }
        total = sum(vals.values())
        return vals, total

    l_vals, l_total = vol_shares(latest)
    p_vals, p_total = vol_shares(prior) if prior else ({}, 0)

    out = {}
    for m in vol_metrics:
        l_sh = share(l_vals[m], l_total)
        p_sh = share(p_vals.get(m, 0), p_total) if p_total > 0 else None
        out[m] = {
            "share_pct":       l_sh,
            "prior_share_pct": p_sh,
            "share_delta_pp":  round2(l_sh - p_sh) if (l_sh is not None and p_sh is not None) else None,
        }

    # Infra-specific: QR-to-POS ratio
    if "upi_qr" in vol_metrics and "pos_terminals" in vol_metrics:
        upi  = data[latest]["total"].get("Total", {}).get("upi_qr", 0)
        pos  = data[latest]["total"].get("Total", {}).get("pos_terminals", 0)
        pupi = data[prior]["total"].get("Total", {}).get("upi_qr", 0) if prior else 0
        ppos = data[prior]["total"].get("Total", {}).get("pos_terminals", 0) if prior else 0
        out["qr_per_pos"] = {
            "latest":  round2(upi / pos) if pos > 0 else None,
            "prior":   round2(pupi / ppos) if ppos > 0 else None,
        }

    return out


def build_category_signals(dates, data, primary_metric):
    """Category share and MoM for the primary metric."""
    latest = dates[-1]
    prior  = dates[-2] if len(dates) > 1 else None

    cats = {}
    l_total = data[latest]["total"].get("Total", {}).get(primary_metric, 0)
    p_total = data[prior]["total"].get("Total", {}).get(primary_metric, 0) if prior else 0

    for full_cat, short in CAT_FULL_TO_SHORT.items():
        l_val = sum(
            v.get(primary_metric, 0)
            for bname, v in data[latest]["bank"].items()
            if any(
                r.get(primary_metric) is not None
                for r in [v]
            )
            # filter by category: need cat info; rebuild below
        )
        # rebuild properly with category info
        break  # will redo below

    # Rebuild: index by (date, category) → total value
    cat_vals: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for date in dates:
        for bname, bdata in data[date]["bank"].items():
            # We lost bank_category — need to store it during load
            pass

    # NOTE: bank_category not stored in our data structure above; load raw CSV for cats
    return None  # flag to use raw_cat approach


def build_category_signals_raw(dates, raw_rows, primary_metric):
    """Category share using raw CSV rows (preserves bank_category)."""
    latest = dates[-1]
    prior  = dates[-2] if len(dates) > 1 else None

    def cat_totals(date):
        totals: dict[str, float] = defaultdict(float)
        for r in raw_rows:
            if r["report_date"] == date and r["metric"] == primary_metric and r["record_type"] == "bank":
                short = CAT_FULL_TO_SHORT.get(r["bank_category"], r["bank_category"])
                totals[short] += float(r["value"] or 0)
        return totals

    l_cats = cat_totals(latest)
    p_cats = cat_totals(prior) if prior else {}
    l_total = sum(l_cats.values())
    p_total = sum(p_cats.values())

    cats = {}
    for short in ["PSB", "Private", "Foreign", "SFB", "Payments"]:
        l_val = l_cats.get(short, 0)
        p_val = p_cats.get(short, 0)
        l_sh  = share(l_val, l_total)
        p_sh  = share(p_val, p_total) if p_total > 0 else None
        cats[short] = {
            "share_pct":       l_sh,
            "prior_share_pct": p_sh,
            "share_delta_pp":  round2(l_sh - p_sh) if (l_sh is not None and p_sh is not None) else None,
            "mom_pct":         mom_pct(l_val, p_val) if p_val else None,
        }

    # Top gainer / loser by share_delta_pp
    deltas = {k: v["share_delta_pp"] for k, v in cats.items() if v["share_delta_pp"] is not None}
    top_gainer = max(deltas, key=deltas.get) if deltas else None
    top_loser  = min(deltas, key=deltas.get) if deltas else None

    return {
        "primary_metric": primary_metric,
        "categories":     cats,
        "top_gainer":     top_gainer,
        "top_loser":      top_loser,
    }


def build_top_n_signals(dates, raw_rows, primary_metric):
    """Top-N bank rankings + rank changes."""
    latest = dates[-1]
    prior  = dates[-2] if len(dates) > 1 else None

    def bank_totals(date):
        totals: dict[str, float] = defaultdict(float)
        for r in raw_rows:
            if r["report_date"] == date and r["metric"] == primary_metric and r["record_type"] == "bank":
                totals[r["bank_name"]] += float(r["value"] or 0)
        return totals

    l_banks = bank_totals(latest)
    p_banks = bank_totals(prior) if prior else {}

    l_sorted = sorted(l_banks.items(), key=lambda x: -x[1])
    p_sorted = sorted(p_banks.items(), key=lambda x: -x[1])
    p_ranks  = {name: i + 1 for i, (name, _) in enumerate(p_sorted)}

    l_total = sum(l_banks.values())
    p_total = sum(p_banks.values())

    banks = []
    rank_changes = []
    for rank, (name, val) in enumerate(l_sorted[:TOP_N], 1):
        p_rank = p_ranks.get(name)
        p_val  = p_banks.get(name, 0)
        l_sh   = share(val, l_total)
        p_sh   = share(p_val, p_total) if p_total > 0 else None
        changed = p_rank is not None and p_rank != rank
        entry = {
            "rank":         rank,
            "prior_rank":   p_rank,
            "name":         name,
            "value":        round2(val),
            "share_pct":    l_sh,
            "prior_share_pct": p_sh,
            "share_delta_pp":  round2(l_sh - p_sh) if (l_sh and p_sh) else None,
            "mom_pct":      mom_pct(val, p_val) if p_val else None,
            "rank_changed": changed,
        }
        banks.append(entry)
        if changed:
            rank_changes.append({"name": name, "from_rank": p_rank, "to_rank": rank})

    top5_share       = share(sum(v for _, v in l_sorted[:5]), l_total)
    top5_share_prior = share(sum(p_banks.get(n, 0) for n, _ in l_sorted[:5]), p_total) if p_total > 0 else None

    return {
        "n":                   TOP_N,
        "primary_metric":      primary_metric,
        "banks":               banks,
        "top5_share_pct":      top5_share,
        "top5_share_prior_pct": top5_share_prior,
        "top5_share_delta_pp": round2(top5_share - top5_share_prior)
                               if (top5_share and top5_share_prior) else None,
        "rank_changes":        rank_changes,
    }


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    print("Loading CSV…")
    dates, data = load_csv()
    print(f"  {len(dates)} periods: {dates[0]} → {dates[-1]}")

    # Also load raw rows for category + top-N (need bank_category)
    with open(CSV_PATH) as f:
        raw_rows = list(csv.DictReader(f))

    latest = dates[-1]
    prior  = dates[-2] if len(dates) > 1 else None

    signals = {
        "meta": {
            "generated_at":  datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ"),
            "latest_period": latest,
            "latest_month":  fmt_month(latest),
            "prior_period":  prior,
            "prior_month":   fmt_month(prior) if prior else None,
            "all_periods":   dates,
            "all_months":    [fmt_month(d) for d in dates],
        },
        "groups": {},
    }

    for group_id, gdef in GROUPS.items():
        print(f"Computing signals: {group_id}…")
        primary  = gdef["primary"]
        metrics  = gdef["metrics"]
        vol_mets = gdef["vol_metrics"]

        total_sigs  = build_total_metric_signals(dates, data, metrics)
        cross_sigs  = build_cross_metric_signals(dates, data, vol_mets)
        cat_sigs    = build_category_signals_raw(dates, raw_rows, primary)
        topn_sigs   = build_top_n_signals(dates, raw_rows, primary)

        signals["groups"][group_id] = {
            "label":      gdef["label"],
            "primary":    primary,
            "total":      {"metrics": total_sigs, "cross": cross_sigs},
            "by_type":    cat_sigs,
            "top_n":      topn_sigs,
        }

    # Write
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(signals, f, indent=2)
    shutil.copy(OUT_PATH, WEB_PATH)

    print(f"\n✓ signals.json written → {OUT_PATH}")
    print(f"✓ copied              → {WEB_PATH}")

    # Quick sanity print
    for gid in signals["groups"]:
        g = signals["groups"][gid]
        pm = g["primary"]
        pm_sig = g["total"]["metrics"][pm]
        print(f"\n  [{gid}] {pm}: {pm_sig['latest']:,.0f} | MoM {pm_sig['mom_pct']}% | streak {pm_sig['streak_months']}m {pm_sig['streak_dir']}")
        print(f"         top gainer: {g['by_type']['top_gainer']} | top loser: {g['by_type']['top_loser']}")
        print(f"         #1 bank: {g['top_n']['banks'][0]['name']} ({g['top_n']['banks'][0]['share_pct']}%)")


if __name__ == "__main__":
    main()
