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
}

export default function AnnotationPanel({
  activeLens, activeAnnotation, activeIndex, total, next, prev,
}: AnnotationPanelProps) {
  const [touchStartX, setTouchStartX] = useState<number | null>(null);

  if (!activeLens || !activeAnnotation) return null;

  const color = LENS_COLOR[activeLens];
  const label = LENS_LABEL[activeLens];
  const remaining = total - 1;

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
      className="mb-4 p-5"
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
      {/* Badge + progress dots */}
      <div className="flex items-center justify-between mb-3">
        <span
          className="text-xs font-bold uppercase tracking-widest px-2 py-0.5 rounded-full"
          style={{ color, background: `${color}18` }}
        >
          {label}
        </span>

        {total > 1 && (
          <div className="flex items-center gap-1.5">
            {Array.from({ length: total }, (_, i) => (
              <span
                key={i}
                className="inline-block rounded-full transition-all duration-200"
                style={{
                  width:      i === activeIndex ? "18px" : "6px",
                  height:     "6px",
                  background: i === activeIndex ? color : `${color}35`,
                }}
              />
            ))}
          </div>
        )}
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
          style={{ borderTop: `1px solid ${color}20` }}
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

      {/* Newsletter CTA */}
      <div
        className="mt-4 pt-3"
        style={{ borderTop: "1px solid var(--border-card)" }}
      >
        <p className="text-xs" style={{ color: "var(--font-muted)" }}>
          {remaining > 0
            ? `${remaining} more ${label.toLowerCase()}${remaining > 1 ? "s" : ""} in this section. `
            : ""}
          <a
            href="https://indiacreditlens.substack.com"
            target="_blank"
            rel="noopener noreferrer"
            style={{ color, textDecoration: "underline" }}
          >
            Get all 45 free →
          </a>
        </p>
      </div>

      {/* Nav arrows */}
      {total > 1 && (
        <div className="mt-4 flex items-center justify-center gap-4">
          <button
            onClick={prev}
            disabled={activeIndex === 0}
            className="px-5 py-2 rounded-lg text-sm font-semibold disabled:opacity-25 transition-opacity"
            style={{ border: `1.5px solid ${color}`, color, cursor: "pointer" }}
          >
            ←
          </button>
          <span className="text-xs tabular-nums" style={{ color: "var(--font-muted)" }}>
            {activeIndex + 1} of {total}
          </span>
          <button
            onClick={next}
            disabled={activeIndex === total - 1}
            className="px-5 py-2 rounded-lg text-sm font-semibold disabled:opacity-25 transition-opacity"
            style={{ border: `1.5px solid ${color}`, color, cursor: "pointer" }}
          >
            →
          </button>
        </div>
      )}
    </div>
  );
}
