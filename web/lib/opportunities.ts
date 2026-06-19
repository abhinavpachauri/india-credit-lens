/**
 * Opportunities data layer — ONE source across the dashboard teasers and the
 * /opportunities page: the Layer 2 derived feed (opportunities_feed.json).
 *
 * Reading the same feed everywhere means the teaser IDs line up with the page,
 * so a teaser can deep-link to a specific opportunity (#<opp.id>).
 */

import feed from "../public/data/opportunities_feed.json";

export interface OppFeedItem {
  id:        string;
  pipeline?: "sibc" | "atm_pos";
  tier:      "opportunity" | "risk";
  status:    string;
  section?:  { id: string | null; title: string; icon: string };
  title:     string;
}

const PIPELINES =
  (feed as { pipelines?: Record<string, OppFeedItem[]> }).pipelines ?? {};

/** Non-retired opportunities for a pipeline + dashboard section id. */
export function opportunitiesFor(pipeline: string, sectionId: string): OppFeedItem[] {
  return (PIPELINES[pipeline] ?? []).filter(
    (o) =>
      o.tier === "opportunity" &&
      o.status !== "retired" &&
      (o.section?.id ?? null) === sectionId,
  );
}
