# Sourced by every git hook: the one Python interpreter the hooks run.
#
# Why pinned: the hooks used to run whichever `python3` came first on PATH. The system 3.9
# (numpy 2.0) recomputes 18 signal rows differently from Anaconda 3.12 (numpy 1.26) in the 4th
# decimal, so the freshness guard failed on an unchanged store; 3.9 also cannot import the code
# (`dict | None`). The store is computed under numpy 1.x, so the hooks must be too.
#
# Override for another machine: export ICL_PYTHON=/path/to/python3
# A missing or wrong interpreter is loud (the hook stops and says why), never silently swapped.
ICL_PYTHON="${ICL_PYTHON:-/opt/anaconda3/bin/python3}"

icl_python_ok() {
  if [ ! -x "$ICL_PYTHON" ]; then
    echo "[hooks] interpreter not found: $ICL_PYTHON (set ICL_PYTHON to a Python >= 3.10 with numpy 1.x)" >&2
    return 1
  fi
  if ! "$ICL_PYTHON" -c 'import sys, numpy; sys.exit(0 if sys.version_info >= (3, 10) and numpy.__version__.startswith("1.") else 1)' 2>/dev/null; then
    echo "[hooks] $ICL_PYTHON is not Python >= 3.10 with numpy 1.x; the signal store would recompute differently" >&2
    return 1
  fi
}
