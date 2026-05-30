"use client";

/**
 * DLS — InsightCTAStrip
 *
 * Entry / exit strip that appears above a chart or section.
 * Entry mode: count summary + animated headline ticker + "tap to explore" CTA.
 * Active mode: "Exit insights" strip with current position.
 *
 * Ticker is managed internally. Callers pass the flat item list.
 * Used by both SIBC (SectionWithAnnotations) and Payments (AtmPosGroupSection).
 */

import { useEffect, useState } from "react";
import type { InsightType } from "./InsightCard";
import { TYPE_COLOR } from "./InsightCard";

const ACCENT = "#4e8ef7";

const TYPE_EMOJI: Record<InsightType, string> = {
  insight:     "💡",
  gap:         "⚠️",
  opportunity: "✅",
};

export interface InsightCTAStripItem {
  type:  InsightType;
  title: string;
}

interface InsightCTAStripProps {
  items:    InsightCTAStripItem[];
  counts:   { insight: number; gap: number; opportunity: number };
  isActive: boolean;
  activeIdx: number;
  total:    number;
  onEnter:  () => void;
  onExit:   () => void;
}

const STRIP_STYLE: React.CSSProperties = {
  background:   "#4e8ef712",
  border:       "1.5px solid #4e8ef740",
  borderLeft:   "5px solid #4e8ef7",
  borderRadius: "0 10px 10px 0",
  padding:      "14px 16px",
};

const ARROW_STYLE: React.CSSProperties = {
  width:      34,
  height:     34,
  background: ACCENT,
  color:      "#fff",
  fontSize:   16,
  flexShrink: 0,
};

export default function InsightCTAStrip({
  items, counts, isActive, activeIdx, total, onEnter, onExit,
}: InsightCTAStripProps) {
  const [tickerIdx,     setTickerIdx]     = useState(0);
  const [tickerVisible, setTickerVisible] = useState(true);

  // Reset ticker when the item list changes (mode/group switch)
  useEffect(() => {
    setTickerIdx(0);
    setTickerVisible(true);
  }, [items.length]);

  // Cycle through headlines when not in active mode
  useEffect(() => {
    if (isActive || items.length <= 1) return;
    const id = setInterval(() => {
      setTickerVisible(false);
      setTimeout(() => {
        setTickerIdx((prev) => (prev + 1) % items.length);
        setTickerVisible(true);
      }, 350);
    }, 3200);
    return () => clearInterval(id);
  }, [isActive, items.length]);

  if (items.length === 0) return null;

  const { insight, gap, opportunity } = counts;

  // ── Active / exit strip ────────────────────────────────────────────────────
  if (isActive) {
    return (
      <div
        onClick={onExit}
        className="cursor-pointer mb-4 flex items-center justify-between gap-3"
        style={STRIP_STYLE}
      >
        <div className="min-w-0 flex-1">
          <p className="text-sm font-bold leading-snug" style={{ color: ACCENT }}>
            ← Exit insights
          </p>
          <p className="text-sm mt-1" style={{ color: "var(--font-muted)", fontWeight: 500 }}>
            {activeIdx + 1} of {total} · Insights mode active
          </p>
        </div>
        <div
          className="flex-shrink-0 flex items-center justify-center rounded-full font-bold"
          style={ARROW_STYLE}
        >
          ×
        </div>
      </div>
    );
  }

  // ── Entry strip ────────────────────────────────────────────────────────────
  const tickerItem = items[tickerIdx];

  return (
    <div
      onClick={onEnter}
      className="cursor-pointer mb-4 flex items-center justify-between gap-3"
      style={STRIP_STYLE}
    >
      <div className="min-w-0 flex-1">
        {/* Count summary */}
        <p className="text-sm font-bold leading-snug" style={{ color: "var(--font)" }}>
          {insight > 0 && (
            <span>{`💡 ${insight} insight${insight !== 1 ? "s" : ""}`}</span>
          )}
          {insight > 0 && (gap > 0 || opportunity > 0) && (
            <span style={{ color: "var(--font-muted)", fontWeight: 400 }}> · </span>
          )}
          {gap > 0 && (
            <span style={{ color: TYPE_COLOR.gap }}>
              {`⚠️ ${gap} gap${gap !== 1 ? "s" : ""}`}
            </span>
          )}
          {gap > 0 && opportunity > 0 && (
            <span style={{ color: "var(--font-muted)", fontWeight: 400 }}> · </span>
          )}
          {opportunity > 0 && (
            <span style={{ color: TYPE_COLOR.opportunity }}>
              {`✅ ${opportunity} opportunit${opportunity !== 1 ? "ies" : "y"}`}
            </span>
          )}
          <span style={{ color: "var(--font-muted)", fontWeight: 400 }}> in this view</span>
        </p>

        {/* Animated ticker */}
        <div style={{ minHeight: 40, overflow: "hidden", marginTop: 5, marginBottom: 4 }}>
          <p
            className="text-sm font-medium leading-snug"
            style={{
              color:           TYPE_COLOR[tickerItem?.type ?? "insight"],
              opacity:         tickerVisible ? 1 : 0,
              transform:       tickerVisible ? "translateY(0)" : "translateY(-7px)",
              transition:      "opacity 0.35s ease, transform 0.35s ease",
              display:         "-webkit-box",
              WebkitLineClamp: 2,
              WebkitBoxOrient: "vertical",
              overflow:        "hidden",
            } as React.CSSProperties}
          >
            {TYPE_EMOJI[tickerItem?.type ?? "insight"]}{" "}
            {tickerItem?.title}
          </p>
        </div>

        {/* CTA */}
        <p className="text-sm" style={{ color: ACCENT, fontWeight: 500 }}>
          What they mean for lenders — tap to explore →
        </p>
      </div>

      <div
        className="flex-shrink-0 flex items-center justify-center rounded-full font-bold"
        style={ARROW_STYLE}
      >
        →
      </div>
    </div>
  );
}
