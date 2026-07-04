#!/usr/bin/env python3
"""
generate_images.py — India Credit Lens
----------------------------------------
Stage 4b of the newsletter pipeline. Renders Mermaid .mmd files from the
latest Stage 4 output (generate_mermaid.py) into PNG images for use in
newsletter and LinkedIn posts.

Images are written to output/images/ (relative to this script's directory).
After running, assign image_url fields in newsletter_config.json — one per
signal — then run generate_newsletter.py and generate_linkedin.py.

What it does:
  1. Discovers the latest dated mermaid output directory under
     analysis/output/mermaid/rbi_sibc/YYYY-MM-DD/
  2. Renders: overview.mmd, sub_NN_*.mmd, quadrant.mmd → PNG
  3. Writes PNGs to output/images/ (replaces prior period images)
  4. Prints a manifest so the author can assign image_url fields

Requires: mmdc (Mermaid CLI — `npm install -g @mermaid-js/mermaid-cli`)

Usage:
    python3 analysis/newsletter/generate_images.py
    python3 analysis/newsletter/generate_images.py --mermaid-dir path/to/dir

Exit codes:
    0 = images written
    1 = error (mmdc not found, no mermaid dir, render failure)
"""

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
REPO_ROOT    = SCRIPT_DIR.parent.parent
MERMAID_ROOT = REPO_ROOT / "analysis" / "output" / "mermaid" / "rbi_sibc"
OUT_IMAGES   = SCRIPT_DIR / "output" / "images"

# Which .mmd files to render (in priority order for the manifest display)
# overview  — full system map; good for Synchronisation/system-wide signals
# sub_NN_*  — per-subsystem causal diagrams; pair to the matching signal
# quadrant  — opportunity map; good for comparative / laggard signals
RENDER_PATTERNS = ["overview", "sub_*", "quadrant"]

# mmdc render settings
RENDER_WIDTH = 1200
RENDER_BG    = "white"
RENDER_THEME = "default"


def find_mmdc() -> str:
    """Return path to mmdc binary or exit with error."""
    path = shutil.which("mmdc")
    if path:
        return path
    print(
        "ERROR: mmdc not found. Install with:\n"
        "  npm install -g @mermaid-js/mermaid-cli",
        file=sys.stderr,
    )
    sys.exit(1)


def discover_mermaid_dir(override: str | None) -> Path:
    """Return the mermaid output directory to use."""
    if override:
        d = Path(override).resolve()
        if not d.is_dir():
            print(f"ERROR: --mermaid-dir not found: {d}", file=sys.stderr)
            sys.exit(1)
        return d

    # Latest dated subdirectory under MERMAID_ROOT
    candidates = sorted(
        [d for d in MERMAID_ROOT.iterdir() if d.is_dir()],
        key=lambda d: d.name,
        reverse=True,
    )
    if not candidates:
        print(
            f"ERROR: No mermaid output directories found under {MERMAID_ROOT}",
            file=sys.stderr,
        )
        sys.exit(1)
    return candidates[0]


def collect_mmds(mermaid_dir: Path) -> list[Path]:
    """Return list of .mmd files to render, in display order."""
    mmds: list[Path] = []
    for pattern in RENDER_PATTERNS:
        matches = sorted(mermaid_dir.glob(f"{pattern}.mmd"))
        for m in matches:
            if m not in mmds:
                mmds.append(m)
    return mmds


def render(mmdc_bin: str, src: Path, dest: Path) -> bool:
    """Render a single .mmd file to PNG. Returns True on success."""
    result = subprocess.run(
        [
            mmdc_bin,
            "-i", str(src),
            "-o", str(dest),
            "-w", str(RENDER_WIDTH),
            "-b", RENDER_BG,
            "-t", RENDER_THEME,
            "-q",
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  [ERROR] mmdc failed for {src.name}:", file=sys.stderr)
        print(result.stderr, file=sys.stderr)
        return False
    return True


def main():
    ap = argparse.ArgumentParser(
        description="Render Stage 4 Mermaid diagrams to PNG for newsletter/LinkedIn"
    )
    ap.add_argument(
        "--mermaid-dir",
        metavar="DIR",
        help="Path to mermaid output directory (default: latest under analysis/output/mermaid/rbi_sibc/)",
    )
    args = ap.parse_args()

    mmdc_bin    = find_mmdc()
    mermaid_dir = discover_mermaid_dir(args.mermaid_dir)
    mmds        = collect_mmds(mermaid_dir)

    if not mmds:
        print(f"ERROR: No .mmd files found in {mermaid_dir}", file=sys.stderr)
        sys.exit(1)

    OUT_IMAGES.mkdir(parents=True, exist_ok=True)

    print(f"\n  India Credit Lens — Mermaid → PNG renderer")
    print(f"  Source : {mermaid_dir}")
    print(f"  Output : {OUT_IMAGES}")
    print(f"  Files  : {len(mmds)} diagrams\n")

    ok = 0
    failed = 0
    manifest: list[tuple[str, str]] = []  # (png_name, suggested_use)

    for src in mmds:
        dest = OUT_IMAGES / f"{src.stem}.png"
        success = render(mmdc_bin, src, dest)
        status = "✓" if success else "✗"
        size   = f"{dest.stat().st_size // 1024}K" if success and dest.exists() else "—"
        print(f"  {status} {src.stem}.png  ({size})")
        if success:
            ok += 1
            manifest.append((f"output/images/{dest.name}", _suggest(src.stem)))
        else:
            failed += 1

    print(f"\n  {'✅' if failed == 0 else '⚠️ '} {ok} rendered, {failed} failed\n")

    # Print manifest for image_url assignment
    print("  ── image_url assignment guide ──────────────────────────────────")
    print("  Copy the relevant path into newsletter_config.json signal.image_url\n")
    for path, suggestion in manifest:
        print(f"  {path}")
        print(f"    → {suggestion}")
    print()
    print("  After assigning image_url fields:")
    print("    python3 analysis/newsletter/validate_newsletter_config.py")
    print("    python3 analysis/newsletter/generate_linkedin.py")

    if failed:
        sys.exit(1)


def _suggest(stem: str) -> str:
    """Return a one-line suggestion for which signal type to pair with this diagram."""
    s = stem.lower()
    if s == "overview":
        return "System-wide / Synchronisation signals — shows all causal stories"
    if s == "quadrant":
        return "Comparative / laggard signals — positions sectors by size vs growth"
    if s == "flowchart":
        return "Full causal chain — use for deep-dive or anchor posts"
    if s == "sankey":
        return "Flow / allocation signals — shows credit stock distribution"
    # sub_NN_*
    label = stem.replace("_", " ").title()
    return f"Subsystem: {label}"


if __name__ == "__main__":
    main()
