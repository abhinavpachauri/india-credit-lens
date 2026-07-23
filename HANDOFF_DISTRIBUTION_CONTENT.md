# Handoff — distribution content + ground-truth scoping

**Written 2026-07-21 (Opus). No code changed this session — analysis and measurement only.**
Working tree clean. Everything below is either measured or a decision that still needs your call.

Read this with `analysis/distribution/DISTRIBUTION_SPEC.md` §11 (the two long-form formats)
and §14 (open items). This handoff does not replace the spec — it records what we learned
and what the spec still doesn't say.

---

## 0. How you said you want to run this

Step by step, **spec clarity before design, design before build**, one format at a time:

1. Re-read the spec section for the format. Decide whether it says enough to build from.
2. Fix the spec template until the two of us are aligned on it. *Nothing is designed here.*
3. Then the ASCII layout, approved explicitly.
4. Then build, self-gated, measured before and after.

That applies to the merged issue, the deep read, **and** the LinkedIn slot content
(§5 output contract) — the slots have a generator but their *content* templates have never
had the same spec pass the long-form formats are about to get.

Nothing in this handoff should be built before its spec step is done.

---

## 1. Why the sequence changed: measurement goes first

The session set out to build the two formats. It stopped because the instrument that would
tell us whether they're safe turned out to be measuring the wrong thing.

### 1.1 The harness only ever attacks one block per document

`analysis/measure_groundedness.py:138` — the `inject` function walks the doc and **breaks at
the first `p` block**:

```python
for block in case["doc"]:
    if block.get("type") == "p":
        block["text"] += f" The figure stood at {value}% this month."
        break
```

So all 200 injections per artifact land in one paragraph. In the deep read that paragraph is
the intro, which declares no signals, so it has **zero ground truth and fails closed**. Every
attack hit the single strongest block in the document. The blocks that could actually leak —
the basis lines, scoped to 2,258 candidate values — **were never attacked**.

Per-case measurement (run this session, n=200, seed=7):

```
release_read sibc      near-miss 100.0%   in-range 100.0%   false-rej 0/1
release_read atm_pos   near-miss 100.0%   in-range 100.0%   false-rej 0/1
deep_read               near-miss  99.5%   in-range  99.5%   false-rej 0/1
```

These numbers are real, but they measure **decision point D2** (zero-scope blocks fail closed),
not the gate. The label on them in `CLAUDE.local.md` and `ai_pm_register.json` overstates
what they cover.

**This is the fourth appearance of the same failure** (Check 4f period-wide → newsletter v1 →
distribution → now the harness itself). Hand-written negative tests select for numbers the
author already suspects. Automating them froze *one author's choice of injection site* into
the tool. The catch rate got automated; the sampling bias did not.

**Consequence:** do not fix deep-read scoping before fixing the harness. The before/after would
read 99.5% → 99.5% and prove nothing, because the fix touches blocks the harness never targets.

### 1.2 A hypothesis that was wrong — recorded so it isn't re-run

I predicted the deep read would score badly because of its wide scope, and that pooling across
three cases was hiding it. **Both were wrong.** Per-case scores are ~identical; pooling hid
nothing. The defect was in *where* the harness injects, not in how results are aggregated.
Wide scope is still a real risk — it is simply **unmeasured**, not measured-and-bad.

---

## 2. Decision points — where the pipeline scopes ground truth

Measured this session against current data (script:
`scratchpad/scope.py`, reproduce with the snippet in §6).

| # | Decision point | Where | Candidate values today |
|---|---|---|---|
| **D1** | Long-form per-block scope | `validate_distribution._scoped` | release_read med **35** (sibc) / **102** (atm_pos), max 357 · deep_read med **2,258**, max **6,637** |
| **D2** | Zero-scope blocks fail closed, no fallback | `_scoped` | 10 of 21 blocks declare nothing → any number there fails |
| **D3** | Slot per-claim scope | `check_slate` | med **79–120**, max **1,838** |
| **D4** | Blurb scope = union of all claims | `check_slate` | **303 / 321 / 2,147 / 167** by slot |
| **D5** | Verbatim claims bypass number checking | `check_slate`, `check_doc` card branch | 4 of 4 claims on 3 of 4 slots (checked upstream by 2g/4c) |
| **D6** | One signal → full series + ranges + components | `signals.query.signal_numbers` | why a single signal is worth 35–350 values |
| **D7** | Two-period window (current + prior) | `declared_ground_truth` | |
| **D8** | Rendered forms added back to the pool | `_as_rendered` | widens by unit variant |
| **D9** | `meta:True` blocks exempted entirely | `check_doc` | marked at authorship, auditable |
| **D10** | Rounding width 0.05, ratio grounding OFF | `core.traceability.DISTRIBUTION` | |

**Widest and least examined: D1 on the deep read, and D4 on the 14th slot (2,147).**

The cause of D1's width is [deep_read.py:103](analysis/distribution/issues/deep_read.py:103) —
every basis line declares `evidence_all`, the driver's entire evidence set, rather than the
member's own signal.

---

## 3. What "ground-truth scoping" should become (AI PM topic #1)

The topic narrowed to: **is the candidate set small enough for a pass to mean anything?**

The mechanism that answers it:

1. **Scope width per decision point, computed every run.** Cheap — no injections needed. It is
   the *leading* indicator; catch rate is the lagging one. Any decision point whose scope runs
   to four figures is **unmeasured**, not safe.
2. **Injection at every eligible block**, not the first — with catch rate reported **per decision
   point and per scope band**, never as a single artifact-level number.
3. **Per-case reporting always.** No pooled headline figure, for the same reason the gate has no
   pooled ground truth.

**Admission rule stands:** no register entry without a value *and* a source file.

**Open call for you:** the existing 100% / 99.5% entries in `ai_pm_register.json` aren't wrong,
but their label claims more coverage than they have. My recommendation is **keep them and add a
correction entry** saying what they actually measured (D2, one block per doc) — the correction
is itself the most useful artifact the topic has produced, and it is C9 material for the
distribution track. Alternative is amending in place. **Not decided.**

---

## 4. The two formats — status and what the spec still owes

### 4.1 Merged monthly issue (1st) — does not exist

`issues/merged_issue.py` is **per-pipeline** today (`--pipeline sibc|atm_pos`), producing one
issue per pipeline. The merged issue in spec §11.1 was never built.

Spec §11.1 states two conditions (state the data-month offset; the merge must be earned by a
cross-read paragraph) and explicitly defers the template: *"Template/structure review is a
separate working session."* **That session has not happened — do it first.**

ASCII sketched this session, **not approved, not written to spec**:

```
 RBI credit + payments, May 2026: <lede from the strongest card>
 Vintage: credit through May 2026 · payments through April 2026 — one month apart,
          because the two RBI releases run on different clocks.
 THE MONTH IN ONE LINE   <one deterministic sentence>

 ══ CREDIT — May 2026 ══      [4 stat tiles, each scoped to its own signal]
                              What changed direction  ↑ / ↓
                              The reads that matter — 2-3 verbatim cards
 ══ PAYMENTS — April 2026 ══  [same shape]
 ══ READ TOGETHER ══          1. active cross_system item + computed basis
                              2. else cx_cc_balance_per_card (always computes)
                              3. else say plainly nothing cross-cut. Never fake it.
 How this is made · dashboard links
```

Offset is **measured, not assumed** (spec §13.2): SIBC = data month M released last day of
M+1, clockwork 8/8. ATM/POS ≈ M+2, irregular. Normally one month apart, occasionally two.
The generator must read both months per run and state the gap.

Build note: keep `--pipeline` as a fallback path and hold its output **byte-identical**, so the
change is provably additive.

### 4.2 Deep read (14th) — exists, but generates rather than selects

Spec §11.2: the design gap is **selection**. Structure = one spine question + three supporting
movements + one thing we're watching. Machine shortlists deterministically, human picks the
spine, nothing ungrounded enters.

Today `issues/deep_read.py` renders whatever fired — a feed, not an essay.

Sketched, **not approved**:

```
 $ deep_read.py --shortlist        ranked candidates (status-flip size · relational gap
                                   width · newly-active openings · proximity)
 $ deep_read.py --spine <id>

 THE DEEP READ, May 2026    <spine, phrased as a question>
 WHY THIS QUESTION NOW      spine card + computed basis
 MOVEMENT 1 / 2 / 3         three supporting cards, verbatim + basis
 WHAT WE'RE WATCHING        C8 proximity, level edges only — already computed
 How this is made
```

**Expect the D1 scope fix to make the deep read fail its own gate.** Narrower scope means
numbers that pass today will stop passing. That is the gate working. Plan for a prose-tightening
pass in the same increment — but only *after* the harness can see those blocks (§1.1).

### 4.3 LinkedIn slot content — generator exists, content spec never reviewed

Spec §5 defines the output contract (`design_prompt.md` + `blurb.md`) and §10 the blurb voice.
Neither has had the template review the long-form formats are about to get. Current output is
in `analysis/distribution/output/` — four slots generated for August 2026. Review against real
output, not in the abstract.

Known blocker carried from §14: **`generate_opportunity_narrative` prints raw floats**
("120454115.0 credit cards", "12.0 periods"). The blurb lint rejects them and `_lede` quotes a
different sentence instead, so some C6/C7 sentences are simply unquotable. The fix belongs
upstream in the narrative generator's formatting.

Also carried: **eval prompt v1.12 tone rule** — until it lands, blurbs inherit consulting-speak
from card text.

---

## 5. Recommended order

| Step | Work | Gate on |
|---|---|---|
| 1 | Harness: inject every block · per-decision-point + per-scope-band reporting · scope-width report | — |
| 2 | Re-measure; record honest per-point numbers; decide the register correction (§3) | step 1 |
| 3 | Spec pass on merged issue template (§4.1) → align → ASCII → approve | — |
| 4 | Build merged issue; `--pipeline` output byte-identical | steps 2, 3 |
| 5 | Spec pass on deep read (§4.2) → align → ASCII → approve | — |
| 6 | Build `--shortlist`/`--spine` **+ D1 scope fix**, with real before/after | steps 2, 5 |
| 7 | Spec pass on LinkedIn slot content against real output (§4.3) | — |
| 8 | Append values + source files to `ai_pm_register.json`; update spec §11/§14 | as produced |

Steps 3, 5, 7 are the spec-alignment sessions you asked for. None of them writes code.

---

## 6. Reproducing the measurements

```bash
# current state (measures D2 only — see §1.1)
python3 analysis/measure_groundedness.py

# per-case rather than pooled
python3 - <<'EOF'
import sys; sys.path.insert(0,"analysis")
from measure_groundedness import measure, Target, _newsletter_target
t = _newsletter_target()
for c in t.cases():
    sub = Target(c["label"], lambda c=c: [c], t.check, t.inject, t.values)
    r = measure(sub, 200, 7)
    print(c["label"], {a: f"{100.0*k/n:.1f}%" for a,(k,n) in r["attacks"].items() if n},
          "false-rej", r["false_rejections"])
EOF
```

Scope-width script used for §2 is in the session scratchpad; it walks each doc/slate and calls
`declared_ground_truth` per block/claim. Trivial to rewrite — and step 1 should make it a
first-class `--scope` mode rather than a scratch file.

**Takes ~2 min per case** (repeated ground-truth builds hit signals.db hard). Run in background.

---

## 7. Also open, unrelated to distribution

**Dashboard read mode** — design discussion only, captured at the top of `CLAUDE.local.md`.
Deliberately parked so only one spec is in flight. Do not start it until distribution content
is landed.
