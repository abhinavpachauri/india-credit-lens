#!/usr/bin/env python3
"""
keep_awake.py — hold the Mac awake for as long as a paid run is alive.
──────────────────────────────────────────────────────────────────────
The Aug 2026 SIBC re-narration (2026-10-09) took two hours for 23 calls, and one call looked hung
for 18 minutes. Neither was a fault: the Mac slept for about an hour of it (pmset log, lid closed
20:50–21:37 and 21:58–22:13). Python's subprocess timeout runs on a clock that stops while macOS
sleeps, so a call that spanned a sleep was well inside its 300 s limit while `ps` showed it 18
minutes old. Read as a hang, the call was stopped, two signals went unanswered, and the re-run
cost extra.

So a paid run asks macOS to stay awake (`caffeinate -i -w <pid>`: no idle sleep until this
process exits), and says so in one line. The limit is said too: closing the lid on battery still
sleeps a Mac, and nothing a process asks for overrides that.

One call per process. Elsewhere than macOS it is a no-op that says so.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys

_started = False


def keep_awake(what: str) -> bool:
    """Keep the machine awake while this process runs. True if it is being held awake."""
    global _started
    if _started:
        return True
    if sys.platform != "darwin":
        print(f"  · {what}: not macOS, nothing to hold awake", flush=True)
        return False
    exe = shutil.which("caffeinate")
    if not exe:
        # Loud, not silent: a run that may sleep must not look like one that cannot.
        print(f"  ⚠ {what}: caffeinate not found — the Mac may sleep mid-run, and a call that "
              f"spans a sleep will look hung", flush=True)
        return False
    subprocess.Popen([exe, "-i", "-w", str(os.getpid())],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    _started = True
    print(f"  · {what}: holding the Mac awake until this run ends (closing the lid on battery "
          f"still sleeps it; check `pmset -g log` before calling a slow call hung)", flush=True)
    return True
