"use client"

import type { SectionInsight } from "@/lib/insights"

interface Props {
  data: SectionInsight
}

// ─── Dot indicators ───────────────────────────────────────────────────────────

function InsightDot() {
  return (
    <span
      style={{
        display:      "inline-block",
        width:        8,
        height:       8,
        borderRadius: "50%",
        background:   "#2563EB",
        flexShrink:   0,
        marginTop:    5,
      }}
    />
  )
}

function GapDot() {
  return (
    <span
      style={{
        display:      "inline-block",
        width:        8,
        height:       8,
        borderRadius: "50%",
        border:       "2px solid #9CA3AF",
        background:   "transparent",
        flexShrink:   0,
        marginTop:    5,
      }}
    />
  )
}

function OpportunityDot() {
  return (
    <span
      style={{
        display:      "inline-block",
        width:        8,
        height:       8,
        borderRadius: "50%",
        background:   "#16A34A",
        flexShrink:   0,
        marginTop:    5,
      }}
    />
  )
}

// ─── Label chip ───────────────────────────────────────────────────────────────

function Label({ text, color }: { text: string; color: string }) {
  return (
    <span
      style={{
        fontSize:      10,
        fontWeight:    700,
        letterSpacing: "0.06em",
        textTransform: "uppercase",
        color,
        marginRight:   6,
        whiteSpace:    "nowrap",
      }}
    >
      {text}
    </span>
  )
}

// ─── Main component ───────────────────────────────────────────────────────────

export function InsightStrip({ data }: Props) {
  return (
    <div
      style={{
        borderTop:     "1px solid var(--border-card)",
        padding:       "12px 16px",
        display:       "flex",
        flexDirection: "column",
        gap:           8,
        background:    "var(--bg-card)",
      }}
    >
      {/* Insight */}
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <InsightDot />
        <p style={{ margin: 0, fontSize: 12, lineHeight: 1.55, color: "var(--font)" }}>
          <Label text="Insight" color="#2563EB" />
          {data.insight}
        </p>
      </div>

      {/* Gap */}
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <GapDot />
        <p style={{ margin: 0, fontSize: 12, lineHeight: 1.55, color: "var(--font-muted)" }}>
          <Label text="Gap" color="#9CA3AF" />
          {data.gap}
        </p>
      </div>

      {/* Opportunity */}
      <div style={{ display: "flex", gap: 8, alignItems: "flex-start" }}>
        <OpportunityDot />
        <p style={{ margin: 0, fontSize: 12, lineHeight: 1.55, color: "var(--font)" }}>
          <Label text="Opportunity" color="#16A34A" />
          {data.opportunity}
        </p>
      </div>
    </div>
  )
}
