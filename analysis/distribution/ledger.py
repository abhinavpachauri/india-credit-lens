#!/usr/bin/env python3
"""
ledger.py — the record of what was published, and the check that it didn't repeat
----------------------------------------------------------------------------------
DISTRIBUTION_SPEC §7. The ledger does not decide what to publish. The category
partition (§2) does that. The ledger's three jobs are all after the fact:

  1. verify the partition held — the same signal surfacing in two slots inside a
     window is the symptom that the design leaked somewhere
  2. record skips, so a run of empty slots is visible rather than quietly forgotten
  3. carry the status each published signal had at the time, which is what lets C9
     later notice that our earlier read has since been overturned

It also stores the link once a post goes live, for engagement learning later.
"""
import json
from datetime import date, datetime
from pathlib import Path

ROOT = next(p for p in Path(__file__).resolve().parents if (p / ".git").is_dir())
LEDGER = ROOT / "analysis" / "distribution" / "distribution_ledger.json"

# How long a signal must rest before it may appear in another slot.
#
# Set just inside the calendar's own widest intra-month gap (7th → 28th = 21 days).
# At 21 it would be inclusive of that pair, which quietly starves the 28th of anything
# the 7th touched — the watchlist and the divergence post ask genuinely different
# questions and may share a signal at opposite ends of the month. At 20, the calendar's
# extremes are legal and everything tighter than a full cycle is still caught.
REUSE_WINDOW_DAYS = 20


def _empty():
    return {
        "_meta": {
            "purpose": "Record of published distribution items and skipped slots. "
                       "Spec: analysis/distribution/DISTRIBUTION_SPEC.md §7.",
            "version": "1.0",
            "reuse_window_days": REUSE_WINDOW_DAYS,
        },
        "entries": [],
        "skips": [],
    }


def load():
    return json.loads(LEDGER.read_text()) if LEDGER.exists() else _empty()


def save(ledger):
    LEDGER.write_text(json.dumps(ledger, indent=1, ensure_ascii=False) + "\n")


def entries():
    return load().get("entries", [])


def record(slot, category, claims, statuses, artifacts, is_fallback=False,
           when=None, link=None):
    """Append a published item. Idempotent per (date, slot) — re-running a generator
    replaces that slot's entry rather than growing a second one."""
    ledger = load()
    when = when or date.today().isoformat()
    entry = {
        "date": when,
        "slot": slot,
        "channel": "linkedin" if slot != "1st" else "newsletter+linkedin",
        "category": category,
        "is_fallback": is_fallback,
        "claim_ids": [c["id"] for c in claims],
        "signal_ids": sorted({s for c in claims for s in c.get("signal_ids", [])}),
        "statuses": statuses,
        "artifacts": artifacts,
        "link": link,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    }
    ledger["entries"] = [e for e in ledger.get("entries", [])
                         if not (e["date"] == when and e["slot"] == slot)]
    ledger["entries"].append(entry)
    ledger["entries"].sort(key=lambda e: (e["date"], e["slot"]))
    save(ledger)
    return entry


def record_skip(slot, category, fallback_category, reason, when=None):
    """A skipped slot is a result, not an absence — §4 says so, so it gets written down."""
    ledger = load()
    when = when or date.today().isoformat()
    ledger["skips"] = [s for s in ledger.get("skips", [])
                       if not (s["date"] == when and s["slot"] == slot)]
    ledger["skips"].append({
        "date": when, "slot": slot, "category": category,
        "fallback_category": fallback_category, "reason": reason,
        "recorded_at": datetime.now().isoformat(timespec="seconds"),
    })
    ledger["skips"].sort(key=lambda s: (s["date"], s["slot"]))
    save(ledger)


def _days_between(a, b):
    return abs((date.fromisoformat(a) - date.fromisoformat(b)).days)


def overlaps(candidate_signal_ids, when=None, slot=None):
    """Signals in this candidate that a recent entry already used — the §7 check.

    Returns a list of (signal_id, earlier_entry). Empty means the partition held.
    """
    when = when or date.today().isoformat()
    hits = []
    for e in entries():
        if e["slot"] == slot and e["date"] == when:
            continue                       # a re-run of this same slot is not a repeat
        if _days_between(e["date"], when) > REUSE_WINDOW_DAYS:
            continue
        for sid in candidate_signal_ids:
            if sid in e.get("signal_ids", []):
                hits.append((sid, e))
    return hits


def verify():
    """Full-history audit: every case where one signal appeared twice inside the window."""
    problems = []
    all_entries = entries()
    for i, a in enumerate(all_entries):
        for b in all_entries[i + 1:]:
            if _days_between(a["date"], b["date"]) > REUSE_WINDOW_DAYS:
                continue
            shared = set(a.get("signal_ids", [])) & set(b.get("signal_ids", []))
            if shared:
                problems.append(
                    f"{a['date']} {a['slot']} ({a['category']}) and "
                    f"{b['date']} {b['slot']} ({b['category']}) share: "
                    f"{', '.join(sorted(shared))}")
    return problems


def main():
    problems = verify()
    ledger = load()
    print(f"ledger: {len(ledger.get('entries', []))} published, "
          f"{len(ledger.get('skips', []))} skipped")
    if problems:
        print(f"\n{len(problems)} category-partition overlap(s) within "
              f"{REUSE_WINDOW_DAYS} days:")
        for p in problems:
            print("  -", p)
        return 1
    print("no signal reused across slots inside the window — partition held")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
