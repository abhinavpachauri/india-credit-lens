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
      className="mt-4 rounded-lg p-4 text-sm"
      style={{
        borderLeft:  `4px solid ${color}`,
        background:  "var(--bg-page)",
        border:      `1px solid ${color}30`,
        borderLeftWidth: "4px",
        borderLeftColor: color,
      }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Header row: lens label + navigation + close */}
      <div className="flex items-center justify-between mb-2">
        <span
          className="text-xs font-semibold uppercase tracking-wide"
          style={{ color }}
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
                className="px-1.5 py-0.5 rounded disabled:opacity-30"
                style={{ border: `1px solid var(--border-card)` }}
              >
                ‹
              </button>
              <span>{activeIndex + 1} / {total}</span>
              <button
                onClick={next}
                disabled={activeIndex === total - 1}
                className="px-1.5 py-0.5 rounded disabled:opacity-30"
                style={{ border: `1px solid var(--border-card)` }}
              >
                ›
              </button>
            </div>
          )}

          {/* Close */}
          <button
            onClick={() => setLens(activeLens)}
            className="text-xs px-1.5 py-0.5 rounded"
            style={{ color: "var(--font-muted)", border: "1px solid var(--border-card)" }}
          >
            ✕
          </button>
        </div>
      </div>

      {/* Title */}
      <p className="font-semibold mb-1" style={{ color: "var(--font)" }}>
        {activeAnnotation.title}
      </p>

      {/* Body */}
      <p className="leading-relaxed" style={{ color: "var(--font)", fontSize: "0.8rem" }}>
        {activeAnnotation.body}
      </p>

      {/* Implication */}
      {activeAnnotation.implication && (
        <p
          className="mt-2 pt-2 text-xs leading-relaxed italic"
          style={{
            color:       "var(--font-muted)",
            borderTop:   "1px solid var(--border-card)",
          }}
        >
          For lenders: {activeAnnotation.implication}
        </p>
      )}

      {/* Mobile swipe hint — only show on first annotation */}
      {total > 1 && activeIndex === 0 && (
        <p className="mt-2 text-xs text-center" style={{ color: "var(--font-muted)" }}>
          swipe to navigate
        </p>
      )}
    </div>
  );
}
