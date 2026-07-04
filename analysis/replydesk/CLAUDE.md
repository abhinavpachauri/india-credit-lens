# Reply Desk — X distribution ritual

> The daily 10-minute assisted reply routine (@indiacreditlens on X). A session
> ritual + a gated drafting module — NOT an automation. A human posts every reply.

---

## What this is

The reply-guy strategy from `ICL_RETAIL_90DAY_PLAN.md` (Phase 1 distribution), made
fast and safe: Claude reads the user's logged-in X tabs via the **Claude-in-Chrome
extension**, shortlists reply-worthy tweets, drafts grounded replies from the
validated engine, and the **user presses Post** on each. No X API, no scraping,
no batch posting — the account must never behave like a bot.

`reply_desk.py` is the deterministic core: topic routing → signal/card ammunition
→ a hard gate (traceability + SEBI lint) that blocks bad drafts before review.

## The session ritual (how any session — including Opus — runs the desk)

Preconditions: user has Chrome open with the extension active, logged into X,
with their Following feed + saved-search tabs open. User is present throughout.

1. User says: **"Reply desk"** (optionally pasting tweet texts instead of using the browser).
2. Load the Chrome tools via ToolSearch (one call: tabs_context, read_page/get_page_text,
   navigate, form_input). Read the open X tabs.
3. Shortlist **3–5 candidate tweets**: topic matches a `TOPICS` entry, fresh (<24h),
   real engagement, no data already in the thread. Show the list.
4. For each candidate the user picks:
   - `python3 analysis/replydesk/reply_desk.py brief "<tweet text>"` → the ammunition
     (exact signal values + verbatim validated card lines).
   - Draft 1–2 reply options (≤280 chars, ONE number quoted exactly, no links,
     no hashtag spam, plain conversational English).
   - `python3 analysis/replydesk/reply_desk.py check "<draft>" --topics <ids>` —
     a draft that fails is fixed or dropped, never shown as postable.
5. On approval: type the reply into X's compose box via the browser tools —
   **the user clicks Post**. One reply at a time, naturally spaced.
6. Log each posted reply:
   `python3 analysis/replydesk/reply_desk.py log --url <tweet> --topic <id> --text "<reply>"`
   — `reply_log.json` is the engagement-learning record (which topics/accounts convert).

## Hard rules (non-negotiable)

- **A human clicks Post. Always.** No API posting, no batch send, no unattended runs.
- **2–3 replies/day max.** Volume is a spam signal; consistency is the asset.
- **No links in replies** (the profile does the conversion). No advice language —
  the SEBI lint in `check` hard-blocks buy/sell/target vocabulary.
- **Every number quoted exactly as `brief` printed it.** The gate enforces this;
  don't paraphrase figures.
- Discovery automation (X API watchlists) is deliberately deferred until
  `reply_log.json` shows which replies convert — see the plan's publish-before-build rule.

## Files

| File | Purpose |
|---|---|
| `reply_desk.py` | `brief` (ammunition) · `check` (traceability + SEBI gate) · `log` |
| `reply_log.json` | Append-only record of posted replies (the learning data) |
| `../newsletter/newsletter_sources.py` | Shared distribution data layer (signals + validated cards) |
| `../tests/test_reply_desk.py` | Gate semantics locked by unit tests |

Topic coverage: bank_credit, gold_loans, credit_cards, unsecured_retail, msme,
vehicle_auto, housing, payments_infra, agriculture, nbfc_services. Extend `TOPICS`
when a new lane appears (keywords + registered signal ids + card sections).
