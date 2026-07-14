# India Credit Lens — Research & Practice Backlog

> A considered list of LLM-engineering work to pull from when time allows — so exploration
> is deliberate, not shiny-link-of-the-week. Two kinds of entries:
> **Area 1** = deep, primary: apply & maintain known best practices on ICL (start here).
> **Areas 2+** = lighter novel bets: each has a use case + how to approach, tagged by whether
> it's *uniquely-ours* (our deterministic ground truth enables it) or *crowded* (others can too).
>
> Meta-note: this backlog is itself content. "The running list of experiments I want to run on a
> high-stakes-AI platform" is a post the AI-PM audience would follow. Build in the open.

---

## Area 1 — Apply & maintain LLM-product best practices on ICL  *(PRIMARY — start here)*

The honest headline: **ICL is mature on the correctness/CI side and immature on the
quality-measurement side.** We built the assertion layer instinctively (gates that refuse to ship a
wrong number) but have never *measured whether the prose is any good*. That gap is the whole first
tranche of work — and it's a great story: "I built the correctness layer before I named it, and
never measured quality until I did."

### 1.1 Where ICL stands today (maturity map)

| Practice | ICL state | Gap → next step |
|---|---|---|
| **Assertion / unit-test evals** | ✅ Strong — Check 2g/4f traceability, SEBI lint, 2f freshness. These *are* Hamel level-1 evals. | Reframe explicitly as evals; extend to narrative-quality assertions (jargon list, contradiction check). |
| **Evals in CI** | ✅ Strong — run inside `core/gate.py` every ingestion. Most teams never get here. | Add the new quality assertions to the same gate. |
| **Prompt versioning** | ✅ Have it — `prompt_version` (v1.11), stored per eval. | Keep; tie version bumps to measured eval deltas, not vibes. |
| **Prompt caching / cost** | ✅ Partial — payload-hash cache in `evaluate`, narrative cache. | Add token/cost tracking per run; see 1.6. |
| **LLM-as-judge (aligned)** | ❌ **None** — narrative quality is unmeasured. | The core build: 1.2→1.4. Judge aligned to *your* labels. |
| **Error analysis / failure taxonomy** | ❌ Ad hoc — found the self-contradicting card + "fully engaged" loop bug *by accident*. | Make it systematic: 1.2. |
| **"Look at your data"** | ❌ Not done as a discipline. | The honest first move: 1.2. |
| **Human-in-the-loop** | ✅ Strong — S4 sourcing gate, reply desk (human posts). | Keep as the model. |
| **Observability / tracing** | 🟡 Partial — cache tables, no full trace log. | 1.5. |
| **Model routing (cheap/expensive by task)** | ❌ None — Claude for everything. | 1.6 (also links to Area 6). |
| **Structured outputs / schema** | ✅ JSON eval outputs, validated downstream. | Fine; tighten schema validation at the call site. |

### 1.2 Implementation path (in order — each is real product gain + skill + content)

1. **"Look at your data" pass.** Pull every current LLM narrative (SIBC ~84 + payments + opportunity
   cards) into one readable sheet. Read them. Hand-label: `good / consulting-speak / contradicts-
   computed-state / hedged / other`. No tooling — just eyes. *(This is the step everyone skips.)*
2. **Build the failure taxonomy** from what you actually saw (not assumed). Likely buckets: jargon,
   narrative-vs-computed contradiction, over-hedging, invented emphasis.
3. **Assertion evals for the mechanical failures** → into the gate. Jargon wordlist; a
   contradiction check (title/status direction-word vs body direction-word — would have caught both
   past bugs). Cheap, deterministic, same pattern as existing gates.
4. **Aligned LLM-as-judge for the subjective bucket (tone/quality).** Build the judge, then
   **measure it against your step-1 labels** — only trust it once it agrees with you. This is the
   advanced, non-generic piece. *Payoff:* the pending **v1.12 tone rule** stops being a guess — change
   the prompt, re-run the judge, *measure* whether tone improved. The flywheel closes.
5. **(then) Observability** (1.5) and **cost/routing** (1.6) as maturity follows.

### 1.3 Deliverables that fall out
- v1.12 tone prompt, evidence-backed.
- A `validate_narrative_quality` gate step (assertions) + an aligned judge harness.
- Content: "How I built an aligned LLM judge to grade AI-written financial analysis" (Hamel-register).

### 1.4 Staying current — source list *(verify links as things move; these are the durable ones)*

**Evals & applied-LLM foundations (the core register):**
- **Hamel Husain — hamel.dev** — the evals canon; esp. "Your AI Product Needs Evals," "Creating a
  LLM-as-a-Judge That Drives Business Value," "Look at Your Data."
- **applied-llms.org — "What We Learned from a Year of Building with LLMs"** (Yan, Husain, Bornstein,
  Shankar et al.) — the single best practitioner synthesis.
- **Eugene Yan — eugeneyan.com** — eval patterns, LLM-as-judge, applied write-ups.
- **Shreya Shankar** — eval research (data-centric eval, SPADE/EvalGen) — the rigorous edge.
- **Chip Huyen — huyenchip.com + "AI Engineering" (book)** — systems view.

**Provider engineering (Anthropic-first, since we run on Claude):**
- **anthropic.com/engineering** and **/research** — esp. "Building Effective Agents" (the
  determinism-first, don't-over-agent argument — matches ICL's philosophy).
- **docs.anthropic.com** — prompt engineering guide, tool use, prompt caching, structured outputs.
- **github.com/anthropics/anthropic-cookbook** — runnable patterns (evals, judges, tool use).

**Trends / breadth (skim, don't chase):**
- **Simon Willison — simonwillison.net** — the best practical running log of what's new.
- **Latent Space — latent.space** — trends, model releases, interviews.
- **Hugging Face blog — huggingface.co/blog** — open-weight ecosystem (relevant to Areas 5–7).
- **Jason Liu — jxnl.co / `instructor`** — structured outputs / schema discipline.

*Cadence suggestion:* one source-skim per week (rotate), not daily. Log anything worth trying here.

---

## Area 2 — Correctness scaffolding as a model-quality equalizer  *(uniquely-ours, Use B)*
- **Use case:** Quantify how much *model* quality the narration actually needs when a deterministic
  layer already guarantees the facts. If small/cheap models narrate "well enough" behind the gate,
  that's a real cost + control finding (and a novel one).
- **Approach:** Swap the narration model (Claude → a small open weight) with the gate holding
  correctness constant; measure the *pure quality drop* using the Area-1 judge. Frontier vs 8B vs 3B.
- **Why ours:** almost nobody can isolate the quality variable this cleanly — the gate is the control.
- **Compute:** small models only (on-device / cheap API). Blocked on Area 1's judge existing.

## Area 3 — Auto-generated evals from ground truth  *(uniquely-ours, Use B)*
- **Use case:** Because signals.db is an oracle, synthesize *thousands* of eval cases with
  known-correct answers — probe exactly where models hallucinate on financial reasoning.
- **Approach:** Template questions off signals.db facts (with true answers); run candidate models;
  score against the oracle. Builds a large eval set for free.
- **Why ours:** the oracle. Feeds Area 7.

## Area 4 — LLM reasoning over the causal graph (not just signals)  *(uniquely-ours, frontier-ish)*
- **Use case:** Can a model propose *causal structure* (edges, forces) that survives the S4 sourcing
  gate? Structured reasoning with a hard verifier.
- **Approach:** Extend S4 — LLM proposes candidate edges from data patterns; the existing sourcing
  gate is the verifier; measure proposal precision. Never auto-promote (existing rule).
- **Compute:** frontier model for the reasoning; the verifier is deterministic.

## Area 5 — Open-weight agentic coding model for the *build*  *(crowded, Use A)*
- **Use case:** Can an open-weight/on-device coder (e.g. **Laguna XS** from Poolside, or Llama-class
  code models) do real ICL pipeline build work vs frontier (Claude Code)?
- **Approach:** Give it a real, scoped ICL task; compare against the frontier baseline on the same
  task; note where it holds/breaks.
- **Caveat:** *crowded* — everyone benchmarks coding assistants. Edge is only "on *my* real work,"
  not generic benchmarks. Lower priority than the uniquely-ours lines.
- **Note:** Laguna is a *coding* model — build tooling (Use A), **not** a pipeline narration component.

## Area 6 — Small open-weight narration swap  *(Use B, links Area 2)*
- **Use case:** The practical arm of Area 2 — run narration on a small open model via **Hugging Face**
  (local or HF inference); the "how small before quality breaks?" question.
- **Approach:** HF-hosted small model behind the gate; A/B the narrative-quality judge scores.
- **Compute:** small models; HF as enabler.

## Area 7 — Open-source a financial-analysis eval dataset on Hugging Face  *(uniquely-ours, high-signal)*
- **Use case:** Release a public eval set — "N cases with known-correct answers testing whether an
  LLM hallucinates on Indian credit reasoning," built from the RBI oracle. Little high-stakes-financial
  LLM eval data exists publicly.
- **Approach:** Curate/generate from Area 3; document; push to HF Datasets with a card.
- **Why ours:** the oracle + the domain. "I released an eval set on HF" is a stronger AI-PM credential
  than any volume of takes — and it points straight back to the ICL platform.
- **Depends on:** Area 3 (generation) + Area 1 (labeling discipline).

---

## Sequencing (honest)
Area 1 is the spine — do it properly and it *creates* the tools (the judge, the labeled data) that
Areas 2, 3, 6, 7 all depend on. So the order isn't arbitrary: **1 → then 3/7 (data) → then 2/6
(model swaps) → 4 (frontier reasoning); 5 anytime, low priority.** Don't start a downstream area
before Area 1's judge exists — you'd be measuring with no ruler.
