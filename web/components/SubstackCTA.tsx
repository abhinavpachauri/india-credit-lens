"use client";

// ── SubstackCTA ────────────────────────────────────────────────────────────────
// Contextual CTA — two modes:
//   compact=false (default) — strip below graph (trend/dist tabs)
//   compact=true            — floating pill overlaid on the canvas

import { SUBSYSTEMS } from "@/lib/system_model_data";

interface Props {
  activeSubsystemId: string | null;
  compact?:          boolean;
}

const SUBSTACK_ISSUE_URL = "https://indiacreditlens.substack.com";
const SUBSTACK_SUBSCRIBE = "https://indiacreditlens.substack.com/subscribe";

export default function SubstackCTA({ activeSubsystemId, compact = false }: Props) {
  const activeSub = activeSubsystemId
    ? SUBSYSTEMS.find((s) => s.id === activeSubsystemId)
    : null;

  const href  = activeSub?.newsletter ? SUBSTACK_ISSUE_URL : SUBSTACK_SUBSCRIBE;
  const label = activeSub?.newsletter ? "Read on Substack →" : "Subscribe →";
  const bg    = activeSub?.newsletter ? "#1E3A5F" : "#0F766E";

  // ── Compact pill — for the canvas overlay ──────────────────────────────────
  if (compact) {
    return (
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs font-semibold px-4 py-2 rounded-full"
        style={{
          background:     bg,
          color:          "#ffffff",
          textDecoration: "none",
          display:        "inline-block",
          boxShadow:      "0 2px 12px rgba(0,0,0,0.25)",
          whiteSpace:     "nowrap",
        }}
      >
        {label}
      </a>
    );
  }

  // ── Full strip — for below-graph placement ─────────────────────────────────
  const body = activeSub?.newsletter
    ? (<>
        <span className="mr-1">📬</span>
        <strong style={{ color: "var(--font)" }}>{activeSub.label}</strong>
        {" "}is covered in Issue #1 of India Credit Lens.
      </>)
    : activeSub
    ? (<>
        <span className="mr-1">📊</span>
        Full analysis of all 7 causal stories — including{" "}
        <strong style={{ color: "var(--font)" }}>{activeSub.label}</strong> — in the Monthly Digest.
      </>)
    : (<>
        <span className="mr-1">📈</span>
        See how this system evolves across periods — full causal model in the Monthly Digest.
      </>);

  return (
    <div
      className="flex items-center justify-between gap-4 px-4 py-3 rounded text-sm mt-3"
      style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)" }}
    >
      <p style={{ color: "var(--font-muted)" }}>{body}</p>
      <a
        href={href}
        target="_blank"
        rel="noopener noreferrer"
        className="text-xs font-semibold whitespace-nowrap px-3 py-1.5 rounded"
        style={{ background: bg, color: "#ffffff", textDecoration: "none" }}
      >
        {label}
      </a>
    </div>
  );
}
