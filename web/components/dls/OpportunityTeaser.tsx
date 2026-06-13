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
import { useAuth, SignInButton } from "@clerk/nextjs";
import type { FlatAnnotation } from "@/hooks/useSectionInsights";
import { OPPORTUNITIES_GATED } from "@/lib/gating";

const OPP_COLOR = "#16A34A";  // TYPE_COLOR.opportunity

interface Props {
  opps:      FlatAnnotation[];
  sectionId: string;
}

export default function OpportunityTeaser({ opps, sectionId }: Props) {
  const { isSignedIn } = useAuth();
  // Open when gating is disabled, or when the user is signed in.
  const open = !OPPORTUNITIES_GATED || !!isSignedIn;

  if (opps.length === 0) return null;

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

      {/* Gated + signed out — modal sign-in */}
      {!open && (
        <SignInButton mode="modal">
          <button
            style={{
              flexShrink:  0,
              fontSize:    12,
              fontWeight:  600,
              color:       OPP_COLOR,
              background:  "transparent",
              border:      "none",
              cursor:      "pointer",
              padding:     0,
              whiteSpace:  "nowrap",
            }}
          >
            Sign in to read →
          </button>
        </SignInButton>
      )}

      {/* Open (ungated or signed in) — link to opportunities page */}
      {open && (
        <Link
          href={`/opportunities#${sectionId}`}
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
