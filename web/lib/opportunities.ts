/**
 * The Layer 2 feed — the deeper reading behind an insight.
 *
 * This is the causal layer: what the system model says is driving a movement, with the
 * measurements that decided it. It used to be a separate `/opportunities` page, which made a
 * *depth* look like a *category* — the reader was told there was another section rather than
 * shown another layer of the thing they were already reading. It now renders inside the insight
 * it belongs to, at the Deep rung of the depth ladder.
 *
 * Register note: the model's own vocabulary is `tier: opportunity | risk`, and that stays — it
 * is how the system model classifies a node. It is deliberately NOT what the reader sees. We
 * report what the data shows and why; we do not tell anyone what to do about it.
 */

import feed from "../public/data/opportunities_feed.json";

export type Pipeline = "sibc" | "atm_pos";
export type OppStatus = "active" | "watch" | "closed" | "retired";

/** The deterministic replay of a meta-model computation: member signals → directions → state.
 *  Never LLM-touched (COMPOSITION_SPEC §23.2), which is why it can be shown as "How we know". */
export interface BasisMember { role: string; label: string; direction: number | null; value?: string }
export interface Basis { headline: string; coverage?: string; members?: BasisMember[]; chain: string[] }

export interface OppFeedItem {
  id: string;
  pipeline?: Pipeline;
  scope: "pipeline" | "cross_source";
  tier: "opportunity" | "risk";
  status: OppStatus;
  section?: { id: string | null; title: string; icon: string };
  title: string;
  body: string;
  implication?: string | null;
  chain: string[];
  basis?: Basis;
  badge?: string;
}

interface Feed {
  cross_system: OppFeedItem[];
  pipelines: Record<string, OppFeedItem[]>;
  _meta: { periods: Record<string, string> };
}

const FEED = feed as unknown as Feed;
const PIPELINES = FEED.pipelines ?? {};
const CROSS = FEED.cross_system ?? [];

/** Retired is a lifecycle decision; closed means the driver stopped firing. Neither is a read. */
const isLive = (o: OppFeedItem) => o.status !== "retired" && o.status !== "closed";

/** The pipeline's own findings for one dashboard dimension. */
export function opportunitiesFor(pipeline: string, sectionId: string): OppFeedItem[] {
  return (PIPELINES[pipeline] ?? []).filter(
    (o) => isLive(o) && (o.section?.id ?? null) === sectionId,
  );
}

/**
 * Cross-system findings that touch this dimension, each with the local measurement that anchors
 * it here.
 *
 * A construct spanning five member signals would otherwise appear identically on five
 * dimensions. The anchor is what makes each appearance specific: on Personal Loans it says which
 * personal-loan measurement participates, so the reader sees why this finding surfaced *here*
 * rather than meeting the same paragraph five times.
 */
export interface CrossFinding { item: OppFeedItem; anchor?: BasisMember }

export function crossSystemFor(pipeline: string, sectionTitle: string): CrossFinding[] {
  const out: CrossFinding[] = [];
  for (const item of CROSS) {
    if (!isLive(item)) continue;
    const anchor = matchAnchor(item, pipeline, sectionTitle);
    if (anchor) out.push({ item, anchor });
  }
  return out;
}

/** The feed labels members like "Credit Card Outstanding (Credit)" / "(Payments)". Match a member
 *  to this dimension by that suffix plus a word from the dimension's own title — deliberately
 *  loose, because a miss costs a missing cross-reference, never a wrong number. */
function matchAnchor(item: OppFeedItem, pipeline: string, sectionTitle: string): BasisMember | undefined {
  const members = item.basis?.members ?? [];
  if (!members.length) return undefined;
  const side = pipeline === "sibc" ? "(Credit)" : "(Payments)";
  const words = sectionTitle.toLowerCase().split(/[^a-z]+/).filter((w) => w.length > 3);
  return members.find((m) => {
    if (!m.label.includes(side)) return false;
    const label = m.label.toLowerCase();
    return words.some((w) => label.includes(w));
  });
}

/** Does this dimension have any deeper reading at all? Drives the Deep rung's availability. */
export function hasDeepReading(pipeline: string, sectionId: string, sectionTitle: string): boolean {
  return opportunitiesFor(pipeline, sectionId).length > 0
      || crossSystemFor(pipeline, sectionTitle).length > 0;
}

/** "Payments @ 2026-06-30 · Credit @ 2026-07-31" — the vintage of the feed itself. */
export function feedPeriods(): Record<string, string> {
  return FEED._meta?.periods ?? {};
}
