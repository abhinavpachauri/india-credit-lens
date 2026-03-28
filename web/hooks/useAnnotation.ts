import { useState, useCallback } from "react";
import type { ReportSection, Annotation, AnnotationEffect } from "@/lib/types";

export type LensType = "insights" | "gaps" | "opportunities";

export interface AnnotationState {
  activeLens:       LensType | null;
  activeIndex:      number;
  activeAnnotation: Annotation | null;
  highlightConfig:  AnnotationEffect | null;
  counts: {
    insights:      number;
    gaps:          number;
    opportunities: number;
  };
  total:   number;
  setLens: (lens: LensType) => void;
  reset:   () => void;
  next:    () => void;
  prev:    () => void;
}

export function useAnnotation(section: ReportSection): AnnotationState {
  const [activeLens,  setActiveLensState] = useState<LensType | null>(null);
  const [activeIndex, setActiveIndex]     = useState(0);

  const counts = {
    insights:      section.annotations.insights.length,
    gaps:          section.annotations.gaps.length,
    opportunities: section.annotations.opportunities.length,
  };

  const activeList: Annotation[] =
    activeLens ? section.annotations[activeLens] : [];
  const total            = activeList.length;
  const activeAnnotation = activeList[activeIndex] ?? null;
  const highlightConfig  = activeAnnotation?.effect ?? null;

  const setLens = useCallback((lens: LensType) => {
    setActiveLensState((prev) => {
      if (prev === lens) { setActiveIndex(0); return null; }  // toggle off
      setActiveIndex(0);
      return lens;
    });
  }, []);

  const reset = useCallback(() => {
    setActiveLensState(null);
    setActiveIndex(0);
  }, []);

  const next = useCallback(() =>
    setActiveIndex((i) => Math.min(i + 1, total - 1)), [total]);

  const prev = useCallback(() =>
    setActiveIndex((i) => Math.max(i - 1, 0)), []);

  return {
    activeLens, activeIndex, activeAnnotation,
    highlightConfig, counts, total,
    setLens, reset, next, prev,
  };
}
