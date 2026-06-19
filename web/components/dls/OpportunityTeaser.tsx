"use client";

/**
 * DLS — OpportunityTeaser
 *
 * Compact gated strip shown below the InsightCTAStrip when a section has
 * one or more opportunities.
 *
 * - Signed out: title visible, "Sign in to read →" opens Clerk modal
 * - Signed in:  "View opportunities →" links to /opportunities#{sectionId}
 *
 * Not part of the insights carousel — opportunities live separately on
 * the /opportunities page.
 */

import Link from "next/link";
import { OPPORTUNITIES_GATED } from "@/lib/gating";
import { opportunitiesFor } from "@/lib/opportunities";

const OPP_COLOR = "#16A34A";  // TYPE_COLOR.opportunity

interface Props {
  pipeline:  "sibc" | "atm_pos";
  sectionId: string;
}

export default function OpportunityTeaser({ pipeline, sectionId }: Props) {
  // Clerk removed — gating is open by default. If re-gated later (NEXT_PUBLIC_
  // GATE_OPPORTUNITIES=true) without auth wired back, the locked state simply
  // hides the link rather than offering sign-in.
  const open = !OPPORTUNITIES_GATED;

  // Same feed the /opportunities page reads → IDs line up for deep-linking.
  const opps = opportunitiesFor(pipeline, sectionId);
  if (opps.length === 0) return null;

  // Deep-link straight to the (first) opportunity's card anchor on the page.
  const href = `/opportunities#${opps[0].id}`;
  const label =
    opps.length === 1
      ? opps[0].title
      : `${opps.length} opportunities in this section`;

  return (
    <div
      style={{
        display:      "flex",
        alignItems:   "center",
        gap:          10,
        padding:      "10px 14px",
        marginBottom: 12,
        borderRadius: 8,
        border:       `1px solid ${OPP_COLOR}30`,
        borderLeft:   `3px solid ${OPP_COLOR}`,
        background:   `${OPP_COLOR}08`,
      }}
    >
      <span style={{ fontSize: 14, flexShrink: 0 }}>{open ? "✨" : "🔒"}</span>

      <span
        style={{
          flex:       1,
          fontSize:   13,
          fontWeight: 500,
          color:      "var(--font)",
          overflow:   "hidden",
          display:    "-webkit-box",
          WebkitLineClamp: 1,
          WebkitBoxOrient: "vertical",
        }}
      >
        {label}
      </span>

      {/* Open (ungated) — link to the specific opportunity on the page */}
      {open && (
        <Link
          href={href}
          style={{
            flexShrink:     0,
            fontSize:       12,
            fontWeight:     600,
            color:          OPP_COLOR,
            textDecoration: "none",
            whiteSpace:     "nowrap",
          }}
        >
          View opportunity →
        </Link>
      )}
    </div>
  );
}
