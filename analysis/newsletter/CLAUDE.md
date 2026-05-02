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
| `newsletter_config.json` | Editorial signals, stats, body copy, image_url — authored once per report cycle |
| `output/images/` | Chart PNGs generated from mermaid diagrams — one per subsystem driver |

`newsletter_config.json` is the single source of truth for both artefacts.
Do not read subsystems.json or system_model.json directly from this folder.

---

## newsletter_config.json structure

```
_meta          — report period, paths, prev issue URL
editorial
  issue_title
  hero_narrative    ← anchor post copy (release week)
  tldr[]            ← newsletter summary bullets
  system_narrative  ← newsletter opening section
  signals[]         ← 6 entries; one LinkedIn post each
    type            new | correction | confirmed
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
□  Author newsletter_config.json — signals[], hero_narrative
     └─ assign image_url per signal from the generate_images.py manifest
        overview.png       → system-wide / synchronisation signals
        sub_NN_*.png       → the matching subsystem's causal signal
        quadrant.png       → comparative / laggard signals
□  python3 analysis/newsletter/validate_newsletter_config.py   ← GATE: fix all errors before proceeding
□  python3 analysis/newsletter/generate_newsletter.py
□  Review output/newsletter_YYYY-MM-DD_substack.html — adjust prose, keep numbers exact
□  python3 analysis/newsletter/generate_linkedin.py
□  Review output/linkedin/YYYY-MM-DD/ — each post has .txt + .png; check image–copy pairing
□  Publish newsletter to Substack (week 1)
□  Update _meta.current_issue_url in newsletter_config.json with published Substack URL
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
