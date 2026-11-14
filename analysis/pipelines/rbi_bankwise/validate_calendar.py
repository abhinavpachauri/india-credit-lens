#!/usr/bin/env python3
"""
validate_calendar.py — is the newest quarter saved, and how much of the declared history is?
──────────────────────────────────────────────────────────────────────────────────────────────
BANKWISE_SPEC.md §4-§5. The currency stage: the newest quarter older than the declared lag ceiling
must be saved, or the gate fails as overdue (an outage never reads as "not released yet"). The
history from the declared first quarter is counted against the saved quarters and every missing
quarter is named; until the backfill (phase 3) is declared done, a gap is printed, not failed,
and the line says so (`history_required` in the manifest turns it into a failure).
"""
from __future__ import annotations

import calendar
import datetime
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(next(p for p in HERE.parents if (p / ".git").is_dir()) / "analysis"))
from core import manifest  # noqa: E402

PIPELINE = "rbi_bankwise"


def quarter_ends(first: str, last: str) -> list[str]:
    y, m = int(first[:4]), int(first[5:7])
    out = []
    while f"{y}-{m:02d}" <= last[:7]:
        out.append(datetime.date(y, m, calendar.monthrange(y, m)[1]).isoformat())
        m += 3
        if m > 12:
            y, m = y + 1, m - 12
    return out


def latest_due(today: datetime.date, lag_days: int) -> str:
    cut = today - datetime.timedelta(days=lag_days)
    m = (cut.month - 1) // 3 * 3 + 3
    end = datetime.date(cut.year, m, calendar.monthrange(cut.year, m)[1])
    if end > cut:
        m -= 3
        y = cut.year if m > 0 else cut.year - 1
        m = m if m > 0 else 12
        end = datetime.date(y, m, calendar.monthrange(y, m)[1])
    return end.isoformat()


def check(saved: set[str], first: str, lag_days: int, required: bool,
          today: datetime.date | None = None) -> tuple[bool, list[str]]:
    today = today or datetime.date.today()
    due = latest_due(today, lag_days)
    want = quarter_ends(first, due)
    missing = [q for q in want if q not in saved]
    lines, ok = [], True
    if max(saved) < due:
        ok = False
        lines.append(f"✗ OVERDUE: {due} is past the {lag_days}-day lag ceiling and the newest saved quarter is {max(saved)}")
    else:
        lines.append(f"✓ current: newest saved {max(saved)} is at or past the latest due quarter {due}")
    if missing:
        head = ", ".join(missing[:4]) + (" …" if len(missing) > 4 else "")
        lines.append(f"{'✗' if required else '·'} history: {len(want) - len(missing)} of {len(want)} quarters "
                     f"from {first} saved; missing {len(missing)} ({head})"
                     + ("" if required else " — backfill pending, not yet required"))
        ok = ok and not required
    else:
        lines.append(f"✓ history: all {len(want)} quarters from {first} saved")
    return ok, lines


def main() -> int:
    man = manifest.load(PIPELINE)
    rel = manifest.path(PIPELINE, "releases")
    saved = {d.name for d in rel.iterdir() if any(d.glob("*.json.gz"))} if rel.exists() else set()
    if not saved:
        print("  ✗ no saved quarters")
        return 1
    cal = man["calendar"]
    ok, lines = check(saved, cal["first_quarter"], cal["lag_ceiling_days"], cal.get("history_required", False))
    for line in lines:
        print("  " + line)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
