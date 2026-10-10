#!/usr/bin/env python3
"""core/keep_awake.py holds the Mac awake for exactly the life of the run that asks.

The 2026-10-09 paid run "hung" because the Mac slept (lid closed); a held assertion that
outlived the run would be its own bug, so both ends are checked. macOS only.

Run: python3 -m pytest analysis/tests/test_keep_awake.py -q
"""
import subprocess
import sys
import time
from pathlib import Path

import pytest

ANALYSIS = Path(__file__).resolve().parents[1]
pytestmark = pytest.mark.skipif(sys.platform != "darwin", reason="caffeinate is macOS")


def _caffeinate_for(pid: int) -> bool:
    out = subprocess.run(["pgrep", "-f", f"caffeinate -i -w {pid}"], capture_output=True, text=True)
    return bool(out.stdout.strip())


def test_the_run_is_held_awake_while_alive_and_released_when_it_ends():
    child = subprocess.Popen(
        [sys.executable, "-c",
         "import sys, time; sys.path.insert(0, sys.argv[1]);"
         "from core.keep_awake import keep_awake; keep_awake('test'); time.sleep(3)",
         str(ANALYSIS)],
        stdout=subprocess.PIPE, text=True)
    time.sleep(1.5)
    assert _caffeinate_for(child.pid), "no caffeinate held for the running process"
    out, _ = child.communicate(timeout=10)
    assert "holding the Mac awake" in out
    for _ in range(20):                       # caffeinate -w exits shortly after its pid does
        if not _caffeinate_for(child.pid):
            break
        time.sleep(0.25)
    assert not _caffeinate_for(child.pid), "caffeinate outlived the run it was holding awake"
