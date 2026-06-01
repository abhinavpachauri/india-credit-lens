import { useState } from "react";
import type { ReportSection, Annotation, AnnotationEffect } from "@/lib/types";
import type { InsightType } from "@/components/dls/InsightCard";

/**
 * useSectionInsights
 *
 * Flat annotation hook for SIBC sections.
 * Merges insights + gaps into a single navigable list (the carousel).
 * Opportunities are returned separately as `opps` — they are gated and
 * rendered via OpportunityTeaser, not in the carousel.
 */

export interface FlatAnnotation extends Annotation {
  _type: InsightType;
}

export interface SectionInsightsState {
  flat:            FlatAnnotation[];   // insights + gaps — navigable carousel
  opps:            FlatAnnotation[];   // opportunities — gated, not in carousel
  counts:          { insight: number; gap: number; opportunity: number };
  isActive:        boolean;
  activeIdx:       number;
  current:         FlatAnnotation | null;
  highlightConfig: AnnotationEffect | null;
  total:           number;
  enter:           () => void;
  exit:            () => void;
  next:            () => void;
  prev:            () => void;
}

export function useSectionInsights(section: ReportSection): SectionInsightsState {
  // Carousel: insights + gaps only
  const flat: FlatAnnotation[] = [
    ...section.annotations.insights.filter((a) => !a.hidden).map((a) => ({ ...a, _type: "insight" as InsightType })),
    ...section.annotations.gaps.filter((a) => !a.hidden).map((a) => ({ ...a, _type: "gap" as InsightType })),
  ];

  // Gated: opportunities separate
  const opps: FlatAnnotation[] = section.annotations.opportunities
    .filter((a) => !a.hidden)
    .map((a) => ({ ...a, _type: "opportunity" as InsightType }));

  const counts = {
    insight:     section.annotations.insights.filter((a) => !a.hidden).length,
    gap:         section.annotations.gaps.filter((a) => !a.hidden).length,
    opportunity: opps.length,
  };

  const [isActive,  setIsActive]  = useState(false);
  const [activeIdx, setActiveIdx] = useState(0);

  const total           = flat.length;
  const current         = isActive ? (flat[activeIdx] ?? null) : null;
  const highlightConfig = current?.effect ?? null;

  const enter = () => { setIsActive(true);  setActiveIdx(0); };
  const exit  = () => { setIsActive(false); setActiveIdx(0); };
  const next  = () => setActiveIdx((i) => Math.min(i + 1, total - 1));
  const prev  = () => setActiveIdx((i) => Math.max(i - 1, 0));

  return { flat, opps, counts, isActive, activeIdx, current, highlightConfig, total, enter, exit, next, prev };
}
