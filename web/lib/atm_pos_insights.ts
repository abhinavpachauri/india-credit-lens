"use client";

// ── Types ─────────────────────────────────────────────────────────────────────

export type InsightCut   = "total" | "by_type" | "top_n";
export type InsightGroup = "cc" | "dc" | "infra";

export interface InsightEffect {
  highlight:   string[];                        // series to keep visible (dim others)
  tab:         "trend" | "distribution";
  trendMode?:  "absolute" | "mom";
  distMode?:   "absolute" | "pct";
  focusCard?:  string;                          // SECTION_DEF id to scroll to
}

export interface InsightExploreAction {
  mode: "by_type" | "top_n";
  topN?: number;
}

export interface InsightReasoningSignal {
  key:   string;   // dot-path into signals.json  e.g. "groups.cc.top_n.top5_share_pct"
  value: number;   // live value at generation time — validated by Stage 4d
}

export interface InsightReasoning {
  signals: InsightReasoningSignal[];   // data points that back this claim
  chain:   string[];                   // step-by-step inference: signal → meaning → lender action
}

export interface AtmPosInsight {
  id:             string;
  group:          InsightGroup;
  cut:            InsightCut;
  period:         string;
  type:           "insight" | "gap";
  title:          string;
  body:           string;
  implication?:   string;
  reasoning?:     InsightReasoning;    // Stage 4d: claim sourcing for the implication
  sourceSignals?: string[];
  effect:         InsightEffect;
  exploreAction:  InsightExploreAction | null;
}

// ── Loader ────────────────────────────────────────────────────────────────────

let _cache: AtmPosInsight[] | null = null;

export async function loadAtmPosInsights(): Promise<AtmPosInsight[]> {
  if (_cache) return _cache;
  const res = await fetch("/data/atm_pos_insights.json");
  _cache = await res.json();
  return _cache!;
}

// ── Filter helpers ────────────────────────────────────────────────────────────

/** Return the cuts relevant to a given group mode. */
export function cutsForMode(mode: "by_type" | "individual" | "top_n"): InsightCut[] {
  if (mode === "by_type")    return ["total", "by_type"];
  if (mode === "top_n")      return ["total", "top_n"];
  return ["total"];   // individual — only total-level insights apply
}

export function filterInsights(
  all:   AtmPosInsight[],
  group: InsightGroup,
  mode:  "by_type" | "individual" | "top_n",
): AtmPosInsight[] {
  const cuts = cutsForMode(mode);
  return all.filter((i) => i.group === group && cuts.includes(i.cut));
}
