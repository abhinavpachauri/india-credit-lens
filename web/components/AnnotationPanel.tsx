"use client";

import { useState } from "react";
import type { LensType, AnnotationState } from "@/hooks/useAnnotation";
import type { Annotation } from "@/lib/types";

const LENS_COLOR: Record<LensType, string> = {
  insights:      "#2563EB",
  gaps:          "#D97706",
  opportunities: "#16A34A",
};

const LENS_LABEL: Record<LensType, string> = {
  insights:      "Insight",
  gaps:          "Gap",
  opportunities: "Opportunity",
};

interface AnnotationPanelProps {
  activeLens:       AnnotationState["activeLens"];
  activeAnnotation: Annotation | null;
  activeIndex:      number;
  total:            number;
  next:             () => void;
  prev:             () => void;
  setLens:          AnnotationState["setLens"];
}

export default function AnnotationPanel({
  activeLens, activeAnnotation, activeIndex, total, next, prev, setLens,
}: AnnotationPanelProps) {
  const [touchStartX, setTouchStartX] = useState<number | null>(null);

  if (!activeLens || !activeAnnotation) return null;

  const color = LENS_COLOR[activeLens];
  const label = LENS_LABEL[activeLens];

  function handleTouchStart(e: React.TouchEvent) {
    setTouchStartX(e.touches[0].clientX);
  }

  function handleTouchEnd(e: React.TouchEvent) {
    if (touchStartX === null) return;
    const delta = e.changedTouches[0].clientX - touchStartX;
    if (delta < -50) next();
    if (delta > 50)  prev();
    setTouchStartX(null);
  }

  return (
    <div
      className="mt-4 p-5"
      style={{
        background:        "var(--bg-page)",
        borderTopWidth:    "1px",
        borderRightWidth:  "1px",
        borderBottomWidth: "1px",
        borderLeftWidth:   "4px",
        borderStyle:       "solid",
        borderTopColor:    `${color}30`,
        borderRightColor:  `${color}30`,
        borderBottomColor: `${color}30`,
        borderLeftColor:   color,
        borderRadius:      "0.5rem",
      }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Header row: lens badge + navigation + close */}
      <div className="flex items-center justify-between mb-3">
        <span
          className="text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
          style={{ color, background: `${color}18` }}
        >
          {label}
        </span>

        <div className="flex items-center gap-3">
          {/* Navigation — only show if more than 1 */}
          {total > 1 && (
            <div className="flex items-center gap-2 text-xs" style={{ color: "var(--font-muted)" }}>
              <button
                onClick={prev}
                disabled={activeIndex === 0}
                className="px-2 py-0.5 rounded disabled:opacity-30"
                style={{ border: `1px solid var(--border-card)` }}
              >
                ‹
              </button>
              <span>{activeIndex + 1} / {total}</span>
              <button
                onClick={next}
                disabled={activeIndex === total - 1}
                className="px-2 py-0.5 rounded disabled:opacity-30"
                style={{ border: `1px solid var(--border-card)` }}
              >
                ›
              </button>
            </div>
          )}

          {/* Close */}
          <button
            onClick={() => setLens(activeLens)}
            className="text-xs px-2 py-0.5 rounded"
            style={{ color: "var(--font-muted)", border: "1px solid var(--border-card)" }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Title */}
      <p className="text-base font-bold mb-2 leading-snug" style={{ color: "var(--font)" }}>
        {activeAnnotation.title}
      </p>

      {/* Body */}
      <p className="text-sm leading-relaxed" style={{ color: "var(--font)" }}>
        {activeAnnotation.body}
      </p>

      {/* Implication */}
      {activeAnnotation.implication && (
        <div
          className="mt-4 pt-4"
          style={{ borderTop: "1px solid var(--border-card)" }}
        >
          <p
            className="text-xs font-bold uppercase tracking-widest mb-1.5"
            style={{ color }}
          >
            For lenders
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--font)" }}>
            {activeAnnotation.implication}
          </p>
        </div>
      )}

      {/* Mobile swipe hint — only show on first annotation */}
      {total > 1 && activeIndex === 0 && (
        <p className="mt-3 text-xs text-center" style={{ color: "var(--font-muted)" }}>
          swipe to navigate
        </p>
      )}
    </div>
  );
}
