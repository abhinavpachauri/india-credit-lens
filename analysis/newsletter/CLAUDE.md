# Newsletter — India Credit Lens

> Execution context for newsletter and LinkedIn post generation.
> Pipeline context: `PIPELINE_ARCHITECTURE.md § Stage 8`
> Distribution strategy: `STRATEGY_PLANNER.md § 4. Distribution Strategy`

---

## What this folder is

A rendering layer on top of the validated merged pipeline outputs. It takes
`newsletter_config.json` (authored from merged system_model + subsystems) and
produces two distribution artefacts:

1. **Newsletter** — full Substack issue (HTML) via `generate_newsletter.py`
2. **LinkedIn posts** — 7 post packages (1 anchor + 6 signal posts) via `generate_linkedin.py`

**No new claims are generated here.** Every factual statement must trace to
`newsletter_config.json`, which itself traces to validated merged outputs.

---

## Inputs

| File | What it provides |
|---|---|
| `newsletter_config.json` | Editorial signals for the current issue — authored once per report cycle |
| `signal_registry.json` | Cumulative tracker of every signal ever published (all issues) — updated each cycle |
| `output/images/` | Chart PNGs generated from mermaid diagrams — one per subsystem driver |

`newsletter_config.json` drives the **current issue** (new signals, hero narrative, config).
`signal_registry.json` drives the **Prior Signals tracker** section automatically.
Do not read subsystems.json or system_model.json directly from this folder.

---

## signal_registry.json

Single source of truth for every signal ever published. Lives at
`analysis/newsletter/signal_registry.json`. **Update this at every issue.**

```json
{
  "_meta": { "last_updated_issue": N, "report_id": "rbi_sibc" },
  "signals": [
    {
      "id": "unique_snake_case_id",
      "story_arc": "Current arc name (may evolve across issues)",
      "theme": "MSME | Gold Economy | Infrastructure | ...",
      "introduced_issue": 1,
      "introduced_url": "https://indiacreditlens.substack.com/p/issue-1",
      "history": [
        { "issue": 1, "status": "new",       "story_arc": "Original arc name", "stat": "key number" },
        { "issue": 3, "status": "confirmed",  "story_arc": "Updated arc name",  "stat": "latest number",
          "url": "https://indiacreditlens.substack.com/p/issue-3" }
      ]
    }
  ]
}
```

**Status values:** `new` | `confirmed` | `stronger` | `unchanged` | `weakening` | `refuted`

**Rendered output (Prior Signals section):** Every signal with `introduced_issue < current_issue`
appears as a compact list item with status icon, latest stat, and dual links
(birth issue · latest update). The generator reads the registry automatically when
`_meta.signal_registry_path` is set in `newsletter_config.json`.

---

## newsletter_config.json structure

```
_meta
  signal_registry_path    ← "signal_registry.json" — enables cumulative tracker
  prior_published_opportunity_ids  ← node IDs from system_model already surfaced in prior issues
editorial
  issue_title
  hero_narrative    ← anchor post copy (release week)
  tldr[]            ← newsletter summary bullets
  system_narrative  ← newsletter opening section
  signals[]         ← NEW signals only; prior signals auto-rendered from registry
    type            new | correction   (confirmed entries no longer needed)
    story_arc       narrative frame (LinkedIn hook context)
    signal          one-liner finding (LinkedIn hook)
    stat            key number — exact, sourced
    body            2–3 sentence context
    implication     one sentence — what lenders should do
    image_url       path to paired PNG in output/images/
  what_to_watch     newsletter closing section
cta            — dashboard + Substack URLs
branding       — site, author
```

**`image_url` is the canonical image assignment per signal.** It is set when
authoring `newsletter_config.json` — do not infer or override it in scripts.

---

## Scripts

| Script | Input | Output |
|---|---|---|
| `validate_newsletter_config.py` | `newsletter_config.json` + `sections_merged.json` | Pass/fail — exits 1 on errors |
| `generate_images.py` | Stage 4 mermaid `.mmd` files | `output/images/*.png` — one per diagram |
| `generate_newsletter.py` | `newsletter_config.json` | `output/newsletter_YYYY-MM-DD.html` + `_substack.html` |
| `generate_linkedin.py` | `newsletter_config.json` + `output/images/` | `output/linkedin/YYYY-MM-DD/` — 7 post packages (txt + png) |

---

## generate_images.py

Renders all relevant Stage 4 Mermaid `.mmd` diagrams to PNG images for use
in newsletter and LinkedIn posts. Must run **before** authoring `image_url`
fields in `newsletter_config.json`.

Discovers the latest `analysis/output/mermaid/rbi_sibc/YYYY-MM-DD/` directory
automatically. Renders: `overview.mmd`, `sub_NN_*.mmd`, `quadrant.mmd`.
Overwrites prior period images in `output/images/`.

Prints a manifest to guide `image_url` assignment — which diagram fits which
signal type.

Run: `python3 analysis/newsletter/generate_images.py`

---

## generate_newsletter.py

Script-only (no Claude). Reads `newsletter_config.json`, renders the delta_v2
HTML format. Produces two files: standard HTML and a Substack-compatible version
with inline styles.

Run: `python3 analysis/newsletter/generate_newsletter.py`

---

## generate_linkedin.py

Reads `newsletter_config.json` and produces one post package per signal plus
one anchor post, ordered for a 7-week publishing schedule.

### Post types

| Post | Source field | When to publish |
|---|---|---|
| Anchor | `hero_narrative` | Release week (week 1) — no image |
| New signal | `signal` + `body` + `implication` | Week 1–2 |
| Correction | `signal` + `prev_read` + `curr_read` + `implication` | Week 2–3 — high engagement |
| Confirmed | `signal` + `note` + `implication` + `badge` | Weeks 3–7 — credibility arc |

### Output per post package

```
output/linkedin/YYYY-MM-DD/
    post_00_anchor.txt
    post_01_new.txt
    post_01_new.png          ← copy of image_url target
    post_02_new.txt
    post_02_new.png
    post_03_correction.txt
    post_03_correction.png
    post_04_confirmed.txt
    post_04_confirmed.png
    post_05_confirmed.txt
    post_05_confirmed.png
    post_06_confirmed.txt
    post_06_confirmed.png
    schedule.md              ← suggested week-by-week posting order
```

### Post format (LinkedIn short-form)

```
[Hook — signal one-liner, 1 line]

[Stat — exact number from stat field]

[Context — 1–2 sentences from body]

[Implication — 1 sentence]

Full breakdown in [issue_title] → [Substack URL]
```

Run: `python3 analysis/newsletter/generate_linkedin.py`

### Hard rules (same contract as newsletter)

1. **Use exact stat field values** — do not paraphrase or round beyond what the source shows
2. **Correction posts must include the prev/curr read framing** — never present a corrected read without the prior read context
3. **Confirmed posts carry the badge** — "▲ Stronger / Corroborated / Extended" is the credibility signal; include it
4. **Substack is the only CTA destination** — link format: `Full breakdown in [issue_title] → [substack URL]`
5. **Insight-first** — hook is always the finding, never "India Credit Lens reports..." or "RBI data shows..."
6. **Hypothesis elements must carry a caveat** — if any part of a signal's causal chain is a working hypothesis (not independently sourced), add a `caveat` field to that signal in `newsletter_config.json`. The generator renders it as `⚠ ...` before the CTA. A post that asserts a hypothesis as fact without a caveat is a guardrail breach.

### caveat field

Add `caveat` to any signal where the mechanism (not the data) is unverified:

```json
{
  "type": "confirmed",
  "signal": "...",
  "caveat": "Note: the volume shift is confirmed data. The demand migration path is a working hypothesis — not independently sourced."
}
```

When to add: whenever a `note` or `body` field asserts a causal mechanism that has `claim_type: "hypothesis"` in `system_model.json`, or whenever the note itself contains language like "working hypothesis", "likely", "early signal", "not independently sourced".

When not to add: when the causal mechanism is backed by an RBI circular, PIB note, or other cited source in `system_model.json`.

---

## Workflow per report cycle

```
□  Merged pipeline complete (Stage 7 evals passing)
□  python3 analysis/newsletter/generate_images.py   ← renders Stage 4 Mermaid .mmd → output/images/*.png

□  UPDATE signal_registry.json  ← REQUIRED before authoring config
     For each existing signal:
       └─ Add a history entry: { "issue": N, "status": "confirmed|stronger|unchanged|weakening|refuted",
                                  "story_arc": "...", "stat": "latest number", "url": "..." }
     For each new signal being introduced this issue:
       └─ Add a new top-level signal entry with introduced_issue: N and history[0].status: "new"
     Update _meta.last_updated_issue: N
     Rule: every signal that appears in newsletter_config.json signals[] as type:"new"
           must also exist in signal_registry.json with a history entry for this issue.

□  Author newsletter_config.json — signals[] (new signals only), hero_narrative
     └─ signals[] contains ONLY type:"new" and type:"correction" entries
        Confirmed/prior signals are auto-rendered from signal_registry.json — do not duplicate
     └─ assign image_url per signal from the generate_images.py manifest
        overview.png       → system-wide / synchronisation signals
        sub_NN_*.png       → the matching subsystem's causal signal
        quadrant.png       → comparative / laggard signals
     └─ add to prior_published_opportunity_ids any opportunity node IDs surfaced in prior issues

□  python3 analysis/newsletter/validate_newsletter_config.py   ← GATE: fix all errors before proceeding
□  python3 analysis/newsletter/generate_newsletter.py
□  Review output/newsletter_YYYY-MM-DD_substack.html
     └─ Verify "📡 New This Issue" — only genuinely new signals
     └─ Verify "📋 Signal Tracker" — all prior signals present, statuses correct, links valid
     └─ Keep numbers exact — no paraphrasing of stat fields
□  python3 analysis/newsletter/generate_linkedin.py
□  Review output/linkedin/YYYY-MM-DD/ — each post has .txt + .png; check image–copy pairing
□  Publish newsletter to Substack (week 1)
□  Update signal_registry.json history entries with the published Substack URL for this issue
□  Regenerate LinkedIn posts (CTAs will now link to the specific issue)
□  Schedule LinkedIn posts per schedule.md (weeks 1–7, 1–2 posts/week)
```

---

## Adding a new signal type

If a future newsletter introduces a new signal type beyond new / correction / confirmed:

1. Add the type to `newsletter_config.json` signals schema
2. Add a formatting branch in `generate_linkedin.py`
3. Add the post format spec to this CLAUDE.md
4. The image_url contract and hard rules remain unchanged
