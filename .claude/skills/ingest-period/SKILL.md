---
name: ingest-period
description: Ingest a new RBI release (SIBC, ATM/POS or NBFC) from its raw XLSX through the manifest gate to a verified dashboard. Use when the user has a new source file to ingest or asks to add a period.
disable-model-invocation: true
---

# Ingest a period

**Inputs:** pipeline id (`sibc` | `atm_pos` | `nbfc`, or any id in `analysis/pipelines/*/pipeline.json`)
and the raw XLSX path. The period is read FROM the file (`period_resolver`), never typed.
`{period}` below is always an ISO date: the timeline's `dataDate` (SIBC, NBFC) or `report_date`
(ATM/POS). The `period` field there is a label ("July 2026"), and passing it fails the gate.

**Done when:** `gate.py --pipeline {p} --merged` (SIBC) or `--period {date}` (others) passes ALL
stages including the build, and the dashboard page for this pipeline is checked in the preview at
1440 and 375 with a clean console. Then `/model-pass` + `/s4-source` (standing rule, DECISIONS.md).

The engine does the work. This skill only orders it and stops at every ⏸ for the user.

## 0. Preconditions

```bash
git status --short                    # clean, or the user knows why not
df -h .                               # the build + freshness recompute need scratch room
python3 analysis/core/gate.py --pipeline {p} --skip-build   # green BEFORE touching anything
```
A red gate before ingesting means you cannot tell your breakage from the existing one.

**SIBC depends on MoSPI** (`depends_on`, since 2026-10-03): its gate's stage D fails when a MoSPI
release is overdue. Bring MoSPI current first (`python3 analysis/core/gate.py --pipeline mospi`; its
fetch pulls CPI's press-release annex from the eSankhyiki catalogue. If the catalogue lags a release,
read the PDF by hand: `python3 analysis/pipelines/mospi/fetch.py --cpi-pdf {file}`).

## 1. Format + extract + consolidate, through the gate

```bash
echo "A" | python3 analysis/pipelines/sibc/detect_format.py {xlsx}   # SIBC only: A = confirm, B = abort
python3 analysis/core/gate.py --pipeline {p} --xlsx {xlsx} --skip-build
```
- The prompt takes `A`/`B`, not `y`: a `y` records an ABORT (`confirmed=false`) and stage 0.5
  then blocks. Read the report before confirming: dates NEW vs overlap, renamed series (a
  wording change with the same code is normal; a code change is not), sample values.
- ⏸ **SIBC date remap.** If the gate stops at stage 0.7 it names an unclassified raw date and
  writes NOTHING. Show the user the table (`update_web_data.py --check`), let them classify each
  date (CLAUDE.md § SIBC date normalisation), then `python3 analysis/pipelines/sibc/update_web_data.py --approve`
  and re-run. Never approve on their behalf: a wrong remap misdates data and nothing downstream notices.
- **SIBC only:** add the period to `analysis/rbi_sibc/timeline.json` by hand (`dataDate`,
  `csv_date` = month-end the data belongs to, `is_fy_end` = true only for the March file). NBFC and
  ATM/POS consolidate registers the timeline itself.
- **NBFC:** stage 1c checks our computed YoY against RBI's own printed column. Also compare the
  press-release headline numbers (monthly NBFC press release) by eye before trusting the file.
- ⚠ Check the bank count for ATM/POS (the roster is time-aware: closures and renames are in
  `canonical_banks.json`). A changed count is a finding, not noise.
- **ATM/POS format detect prompts `[y/N]` when it has warnings**, and inside the gate that prompt
  fails as `EOFError`. Run it by hand first (`echo n | python3 analysis/pipelines/atm_pos/detect_atm_pos_format.py {xlsx}`),
  explain every warning, and only then re-run the gate. The expected bank count is read from the
  roster since 2026-10-02 (it was a stale literal 64; the roster says 63 since Paytm's removal).
- **ATM/POS stage 4a needs the period's signals in signals.db**: append (step 2) before the gate
  can pass, then re-run the gate.

## 2. Layer 1: signals

```bash
python3 analysis/core/generate_signal_history.py append --pipeline {p} --period {period}
python3 analysis/pipelines/sibc/generate_merge.py          # SIBC only
```
If the source REVISED history (RBI does), freshness fails on prior periods. The fix is to
re-append **every** period, never only the latest (`check_signal_freshness.py` names them).

## 3. Layer 1 narration: ⏸ PAID (SIBC + ATM/POS only; NBFC has no card layer)

```bash
python3 analysis/core/generate_signal_history.py evaluate --pipeline {p} --period {period}
```
This refuses without approval and prints its estimate (`Estimated cost: ~$…`), on both the API
and the `claude -p` CLI path. Until 2026-10-02 the CLI path (no `ANTHROPIC_API_KEY`) skipped the
guard and started evaluating; if a run here ever takes more than a few seconds without printing a
refusal, stop it: it is calling the model. ⏸ **Tell the user the estimate and wait for a yes in
THIS conversation**, then re-run with `ICL_LLM_OK=1` prefixed. The hard ceiling is
$5 per run and is not overridable. Without an eval, Stage 5.5 warns "STALE NARRATIVE LAYER";
that is acceptable for shipping, but say so.
- **`✗ INCOMPLETE` (exit 1)** means a domain failed or signals went unanswered. Each gap is listed
  with its reason in the output file (`failed_domains`, per-domain `missing_signals`). Re-running
  re-asks only the unanswered chunks; answered ones replay from cache. Do not ship a period
  whose evaluation is incomplete without telling the user which signals have no narrative.

## 4. The full gate

```bash
python3 analysis/core/gate.py --pipeline sibc --merged              # SIBC
python3 analysis/core/gate.py --pipeline {p} --period {period}      # ATM/POS, NBFC
```
Then open the pipeline's dashboard in the preview (`/`, `/payments`, `/nbfc`) at 1440 and 375:
new latest month in the band and tables, console clean, no horizontal scroll.

## Traps (each one happened)

- **A slow paid call is not a hung call until the sleep log says so** (2026-10-09). The Aug SIBC
  re-narration took two hours, and one call looked stuck for 18 minutes: the Mac had slept
  (lid closed) for an hour of it, and Python's timeout clock stops while macOS sleeps. Stopping the
  "hung" call left two signals unanswered and the re-run cost extra. Paid runs now hold the Mac
  awake (`core/keep_awake.py`) and print a stamped line per call; still, before stopping one,
  run `pmset -g log | grep -E "Entering Sleep|Wake from"`. Closing the lid on battery still sleeps.
- **A re-run pays only for what is missing** (fixed 2026-10-10): a chunk whose split halves are
  cached is served from them. Before the fix, a re-run re-asked the whole chunk.

- **An ingest that ingests nothing must not look like success.** Confirm the new period is in
  `timeline.json` AND in signals.db (`generate_signal_history.py status`). Both pipelines once
  re-ingested the previous month and printed a green "registered".
- **Read the number, not just the gate.** A `/100` vs `/1e4` unit bug once drew ₹219 lakh crore
  and passed every check because the stored value was right. Ask "could that be true?"
- **A move owned by one entity** (POS −15.8% was ~98% ICICI) is attributed, not published as the
  market. `signals/dominance.py` does it; check the band says so.
- **Tests pinned to last month's data fail on new data** without anything being broken. Refresh a
  golden deliberately (`analysis/tests/golden/refresh_atm_pos_cards.py`), after verifying every
  dropped card is an honest null.
- **SIBC annual signals** (FY acceleration) only change at the March file.
- **A MoSPI release changes SIBC rows already stored.** The 1f cells of past periods flip from
  `not_released` to a value, so freshness reports SIBC drift after any MoSPI fetch. That is
  correct: re-append every SIBC period, then restamp the tables (`python3 analysis/signals/stamp_table.py --pipeline sibc`).

## Record

`/session-close` at the end: the period ingested, anything the skill got wrong (fix it HERE, in
this file, in the same session), and gate measurements for `ai_pm_register.json`.
