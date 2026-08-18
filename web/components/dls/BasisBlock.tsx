"use client";

// ── BasisBlock (DLS) ──────────────────────────────────────────────────────────
// "How we know" — the deterministic replay of a finding's computation: which measurements went
// in, which way each moved, and the chain that produced the state. Never LLM-touched
// (COMPOSITION_SPEC §23.2), which is exactly why it can be shown to a reader as evidence.
//
// It lived inside the /opportunities page until that page was retired. It is the one piece of
// that page with no DLS equivalent — nothing else renders member rows with directions — so it
// moved here rather than being replaced.

import { useState } from "react";
import type { Basis } from "@/lib/opportunities";
import { FS, R } from "@/lib/tokens";

const DIR_GLYPH: Record<string, { glyph: string; color: string }> = {
  "1":  { glyph: "▲", color: "#16A34A" },
  "-1": { glyph: "▼", color: "#DC2626" },
  "0":  { glyph: "▬", color: "var(--font-muted)" },
};

/**
 * The direction the VALUE itself shows — mirrors `core.voice.observed_dir` on the Python side.
 *
 * `member.direction` is the member's CONTRIBUTION to the construct, which is not always the sign
 * of its number: a contra-indicator is deliberately flipped, and a member can move against the
 * read it belongs to. Rendering that contribution as an arrow beside the observed figure produced
 * "Consumer Durables ▲ −0.6% YoY" — an up-arrow on a fall. The long-form side hit exactly this in
 * July and resolved it the same way: read the arrow off the number, and say in words when the
 * member is moving against its read rather than drawing an arrow that argues with the figure.
 */
function observedDir(value?: string): number | null {
  if (!value) return null;
  const word: Record<string, number> = {
    rising: 1, running: 1, growing: 1, expanding: 1, up: 1,
    falling: -1, shrinking: -1, contracting: -1, unwinding: -1, reversed: -1, down: -1,
  };
  const v = value.trim().toLowerCase();
  if (v in word) return word[v];
  const signs = new Set([...value.matchAll(/([-+−])\d/g)].map((m) => (m[1] === "+" ? 1 : -1)));
  return signs.size === 1 ? [...signs][0] : null;
}

export default function BasisBlock({ basis }: { basis: Basis }) {
  const [open, setOpen] = useState(false);
  return (
    <div style={{ marginTop: 12 }}>
      <button
        onClick={() => setOpen((o) => !o)}
        className="flex items-center gap-1.5 text-xs font-semibold"
        style={{ color: "var(--font-muted)", background: "none", border: "none", padding: 0, cursor: "pointer" }}
      >
        <span style={{ fontSize: FS.micro }}>{open ? "▾" : "▸"}</span> How we know
      </button>
      {open && (
        <div
          style={{
            marginTop: 8, border: "1px solid var(--border-card)", borderRadius: R.md,
            background: "var(--bg-page)", padding: "12px 14px",
          }}
        >
          <p style={{ fontSize: FS.note, fontWeight: 700, color: "var(--font)" }}>{basis.headline}</p>
          {basis.coverage && (
            <p style={{ fontSize: FS.meta, color: "var(--font-muted)", marginTop: 2 }}>{basis.coverage}</p>
          )}
          {(basis.members?.length ?? 0) > 0 && (
            <div style={{ marginTop: 10, display: "flex", flexDirection: "column", gap: 5 }}>
              {basis.members!.map((m, i) => {
                const observed = observedDir(m.value);
                const shown = observed ?? m.direction;
                const d = DIR_GLYPH[String(shown)] ?? { glyph: "▬", color: "var(--font-muted)" };
                // Contributes one way, moves the other — worth saying, not worth hiding.
                const against = observed !== null && m.direction !== null && observed !== m.direction;
                return (
                  <div key={i} className="flex items-baseline gap-2 flex-wrap" style={{ fontSize: FS.note }}>
                    <span
                      style={{
                        fontSize: FS.micro, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.05em",
                        color: "var(--font-muted)", minWidth: 62, flexShrink: 0,
                      }}
                    >
                      {m.role}
                    </span>
                    <span style={{ color: "var(--font)", flex: "1 1 140px" }}>
                      {m.label}
                      {against && (
                        <span style={{ color: "var(--font-muted)", fontStyle: "italic" }}> · moving against the read</span>
                      )}
                    </span>
                    <span style={{ fontWeight: 700, color: d.color, flexShrink: 0 }}>
                      {d.glyph}{m.value ? ` ${m.value}` : ""}
                    </span>
                  </div>
                );
              })}
            </div>
          )}
          <div style={{ height: 1, background: "var(--border-card)", margin: "10px 0" }} />
          <ol style={{ paddingLeft: 0, listStyle: "none", margin: 0, display: "flex", flexDirection: "column", gap: 6 }}>
            {basis.chain.map((step, i) => (
              <li key={i} className="flex gap-2" style={{ lineHeight: 1.55 }}>
                <span className="flex-shrink-0 font-bold" style={{ color: "var(--font-muted)", minWidth: 14, fontSize: FS.label }}>
                  {i + 1}.
                </span>
                <span style={{ fontSize: FS.note, color: "var(--font)" }}>{step}</span>
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  );
}
