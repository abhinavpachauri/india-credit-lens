"use client";

/**
 * DLS — InsightCard
 *
 * Unified card for a single insight / gap / opportunity.
 * Used by both the SIBC and Payments dashboards.
 *
 * Props:
 *   type        — drives colour + badge label
 *   chain       — optional numbered inference steps (tap to expand)
 *   footerSlot  — optional extra content rendered above nav (e.g. newsletter CTA)
 *   key={activeIndex} on the parent resets internal state on navigation
 */

import { useState } from "react";
import type { ReactNode } from "react";

export type InsightType = "insight" | "gap" | "opportunity";

export const TYPE_COLOR: Record<InsightType, string> = {
  insight:     "#4e8ef7",
  gap:         "#D97706",
  opportunity: "#16A34A",
};

const TYPE_LABEL: Record<InsightType, string> = {
  insight:     "Insight",
  gap:         "Gap",
  opportunity: "Opportunity",
};

export interface InsightCardProps {
  type:         InsightType;
  title:        string;
  body:         string;
  implication?: string;
  chain?:       string[];       // inference steps — renders expand toggle when present
  activeIndex:  number;
  total:        number;
  onNext:       () => void;
  onPrev:       () => void;
  footerSlot?:  ReactNode;      // rendered above nav (e.g. newsletter CTA for SIBC)
}

export default function InsightCard({
  type, title, body, implication, chain,
  activeIndex, total, onNext, onPrev, footerSlot,
}: InsightCardProps) {
  const [showChain, setShowChain] = useState(false);
  const [touchStartX, setTouchStartX] = useState<number | null>(null);

  const color = TYPE_COLOR[type];
  const label = TYPE_LABEL[type];

  function handleTouchStart(e: React.TouchEvent) {
    setTouchStartX(e.touches[0].clientX);
  }
  function handleTouchEnd(e: React.TouchEvent) {
    if (touchStartX === null) return;
    const delta = e.changedTouches[0].clientX - touchStartX;
    if (delta < -50) onNext();
    if (delta > 50)  onPrev();
    setTouchStartX(null);
  }

  return (
    <div
      className="mb-4"
      style={{
        background:   "var(--bg-card)",
        border:       "1px solid var(--border-card)",
        borderLeft:   `4px solid ${color}`,
        borderRadius: "0 10px 10px 0",
        padding:      "14px 16px",
      }}
      onTouchStart={handleTouchStart}
      onTouchEnd={handleTouchEnd}
    >
      {/* Type badge + progress dots */}
      <div className="flex items-center justify-between gap-2 mb-3">
        <span
          className="text-xs font-bold uppercase tracking-widest px-2.5 py-0.5 rounded-full flex-shrink-0"
          style={{ color, background: `${color}18` }}
        >
          {label}
        </span>
        {total > 1 && (
          <div className="flex items-center flex-wrap gap-1.5 justify-end">
            {Array.from({ length: total }, (_, i) => (
              <span
                key={i}
                className="inline-block rounded-full transition-all duration-200"
                style={{
                  width:      i === activeIndex ? "18px" : "6px",
                  height:     "6px",
                  background: i === activeIndex ? color : `${color}35`,
                  flexShrink: 0,
                }}
              />
            ))}
          </div>
        )}
      </div>

      {/* Title */}
      <p className="text-base font-bold leading-snug mb-2" style={{ color: "var(--font)" }}>
        {title}
      </p>

      {/* Body */}
      <p className="text-sm leading-relaxed" style={{ color: "var(--font-muted)" }}>
        {body}
      </p>

      {/* For lenders */}
      {implication && (
        <div className="mt-4 pt-4" style={{ borderTop: `1px solid ${color}20` }}>
          <p
            className="text-xs font-bold uppercase tracking-widest mb-1.5"
            style={{ color }}
          >
            For lenders
          </p>
          <p className="text-sm leading-relaxed" style={{ color: "var(--font)" }}>
            {implication}
          </p>

          {/* Inference chain expand */}
          {chain && chain.length > 0 && (
            <div className="mt-3">
              <button
                onClick={() => setShowChain((s) => !s)}
                className="flex items-center gap-1.5 text-xs font-semibold"
                style={{
                  color:      "var(--font-muted)",
                  background: "none",
                  border:     "none",
                  padding:    0,
                  cursor:     "pointer",
                }}
              >
                <span
                  style={{
                    display:    "inline-block",
                    transition: "transform 0.2s",
                    transform:  showChain ? "rotate(90deg)" : "rotate(0deg)",
                    fontSize:   9,
                  }}
                >
                  ▶
                </span>
                {showChain ? "Hide inference" : "Inference chain"}
              </button>

              {showChain && (
                <div
                  className="mt-2 rounded-lg text-sm"
                  style={{
                    background: `${color}08`,
                    border:     `1px solid ${color}25`,
                    padding:    "10px 12px",
                  }}
                >
                  <ol
                    className="flex flex-col gap-2"
                    style={{ paddingLeft: 0, listStyle: "none", margin: 0 }}
                  >
                    {chain.map((step, i) => (
                      <li key={i} className="flex gap-2" style={{ lineHeight: 1.6 }}>
                        <span
                          className="flex-shrink-0 font-bold"
                          style={{ color, minWidth: 16 }}
                        >
                          {i + 1}.
                        </span>
                        <span style={{ color: "var(--font)" }}>{step}</span>
                      </li>
                    ))}
                  </ol>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {/* Footer slot — e.g. newsletter CTA for SIBC */}
      {footerSlot && (
        <div className="mt-4 pt-3" style={{ borderTop: "1px solid var(--border-card)" }}>
          {footerSlot}
        </div>
      )}

      {/* Prev / next nav */}
      {total > 1 && (
        <div
          className="flex items-center gap-3 mt-4 pt-3"
          style={{ borderTop: "1px solid var(--border-card)" }}
        >
          <button
            onClick={onPrev}
            disabled={activeIndex === 0}
            className="px-4 py-1.5 rounded-lg text-sm font-semibold disabled:opacity-25 transition-opacity"
            style={{ border: `1.5px solid ${color}`, color, cursor: "pointer" }}
          >
            ←
          </button>
          <span className="text-xs tabular-nums" style={{ color: "var(--font-muted)" }}>
            {activeIndex + 1} of {total}
          </span>
          <button
            onClick={onNext}
            disabled={activeIndex === total - 1}
            className="px-4 py-1.5 rounded-lg text-sm font-semibold disabled:opacity-25 transition-opacity"
            style={{ border: `1.5px solid ${color}`, color, cursor: "pointer" }}
          >
            →
          </button>
        </div>
      )}
    </div>
  );
}
