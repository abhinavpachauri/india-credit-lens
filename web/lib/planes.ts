// Read-mode data layer (DASHBOARD_SPEC.md).
//
// The signal layer already decided each card's plane — read / composition / subject — and
// shipped it precomputed in `{pipeline}_planes.json` (see analysis/signals/stamp_planes.py).
// The browser never re-derives that; it joins the sidecar onto the cards by id and reshapes
// them into the three tiers the read view renders.

import type { Annotation, ReportSection, Report } from "@/lib/types";

export type Plane = "read" | "composition" | "subject";

export type ReadReason = "record" | "reversal" | "surge" | "shift";
export type Direction = "up" | "down" | "flat";

export interface CardPlane {
  plane:      Plane;
  news_score: number | null;   // is_news score — orders the read tier
  subject:    string | null;   // chart series / focusCard — groups the accordion
  reason?:    ReadReason | null;   // why the read surfaced — the chip (reads only)
  direction?: Direction | null;    // which way it moved — the ▲▼ glyph (reads only)
}

export type PlanesMap = Record<string, CardPlane>;

export async function loadPlanes(pipeline: "sibc" | "atm_pos"): Promise<PlanesMap> {
  const res = await fetch(`/data/${pipeline}_planes.json`);
  if (!res.ok) return {};
  const doc = await res.json();
  return (doc?.planes ?? {}) as PlanesMap;
}

// ── The three tiers, organised from a report + its planes ─────────────────────

export interface ReadEntry {
  card:         Annotation;
  section:      ReportSection;
  newsScore:    number;
  reason:       ReadReason | null;
  direction:    Direction | null;
}

export interface SubjectGroup {
  name:  string;              // the subject label (a chart series name); "" → ungrouped
  cards: Annotation[];        // every card on this subject, in feed order (nested, never merged)
}

export interface SectionView {
  section:          ReportSection;
  subjects:         SubjectGroup[];   // Tier 3 — all cards, grouped by subject
  compositionCards: Annotation[];     // Tier 2 caption source — the structural residue
  cardCount:        number;           // every insight+gap on the section (what the badge shows)
}

export interface ReadModeModel {
  reads:    ReadEntry[];      // Tier 1 — page-level, ranked, most newsworthy first
  sections: SectionView[];    // Tier 3 — the accordion
}

const READ_FLOOR = 2.0;       // mirrors is_news.READ_FLOOR — a read must clear one strong factor

/** Every insight + gap on a section (opportunities are the Deep plane, joined separately). */
function sectionCards(section: ReportSection): Annotation[] {
  return [
    ...section.annotations.insights.filter((a) => !a.hidden),
    ...section.annotations.gaps.filter((a) => !a.hidden),
  ];
}

function planeOf(planes: PlanesMap, id: string): CardPlane {
  return planes[id] ?? { plane: "subject", news_score: null, subject: null };
}

/**
 * Reshape the report into the read view's three tiers. Pure — selection/depth state lives in
 * the component. The read tier is page-level (the whole pipeline's "what changed"); subjects and
 * composition are per-section, because the chart the reader drops into is a section's chart.
 */
export function organizeReadMode(report: Report, planes: PlanesMap): ReadModeModel {
  const reads: ReadEntry[] = [];
  const sections: SectionView[] = [];

  for (const section of report.sections) {
    const cards = sectionCards(section);
    const bySubject = new Map<string, Annotation[]>();
    const compositionCards: Annotation[] = [];

    for (const card of cards) {
      const p = planeOf(planes, card.id);
      if (p.plane === "read" && (p.news_score ?? 0) >= READ_FLOOR) {
        reads.push({
          card, section, newsScore: p.news_score ?? 0,
          reason: p.reason ?? null, direction: p.direction ?? null,
        });
      }
      if (p.plane === "composition") compositionCards.push(card);

      // Every card is addressable in the accordion regardless of plane (nothing hidden).
      const subj = p.subject ?? card.effect?.highlight?.[0] ?? "";
      if (!bySubject.has(subj)) bySubject.set(subj, []);
      bySubject.get(subj)!.push(card);
    }

    sections.push({
      section,
      subjects: [...bySubject.entries()].map(([name, cards]) => ({ name, cards })),
      compositionCards,
      cardCount: cards.length,
    });
  }

  // Tier 1 ordering: prominence = news score alone for v1 (decision 3), id as a stable tiebreak.
  reads.sort((a, b) => b.newsScore - a.newsScore || a.card.id.localeCompare(b.card.id));
  return { reads, sections };
}
