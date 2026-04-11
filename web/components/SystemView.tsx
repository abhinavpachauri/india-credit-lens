"use client";

// ── SystemView ─────────────────────────────────────────────────────────────────
// Two-level interactive knowledge graph.
//
// LEVEL 1 — Overview (default)
//   7 subsystem bubbles + cross-subsystem edges. Fits any viewport.
//   Free access. Click a bubble → Level 2.
//
// LEVEL 2 — Subsystem detail
//   Selected subsystem's nodes + internal edges. Readable at viewport size.
//   Graph structure free. Click a node → annotation panel (email-gated).
//
// SEO: annotation content rendered server-side in a visually hidden block.
//      The graph itself is client-only (Cytoscape, ssr:false).

import { useState, useEffect, useCallback } from "react";
import dynamic from "next/dynamic";
import { ANNOTATIONS } from "@/lib/reports/rbi_sibc";
import {
  SUBSYSTEMS,
  MODEL_META,
  validateSubsystemCoverage,
  type SystemNode,
} from "@/lib/system_model_data";
import SubstackCTA from "@/components/SubstackCTA";
import type { GraphMode } from "@/components/CytoscapeGraph";

// CytoscapeGraph is DOM-only
const CytoscapeGraph = dynamic(
  () => import("@/components/CytoscapeGraph"),
  { ssr: false, loading: () => <GraphPlaceholder /> }
);

function GraphPlaceholder() {
  return (
    <div className="w-full h-full flex items-center justify-center text-sm"
      style={{ color: "var(--font-muted)" }}>
      Loading graph…
    </div>
  );
}

// ── Annotation panel — floats over canvas right side ─────────────────────────

function AnnotationPanel({
  node,
  unlocked,
  onUnlock,
  onClose,
}: {
  node:      SystemNode;
  unlocked:  boolean;
  onUnlock:  () => void;
  onClose:   () => void;
}) {
  const allAnnotations = Object.values(ANNOTATIONS).flatMap((sec) => [
    ...sec.insights,
    ...sec.gaps,
    ...sec.opportunities,
  ]);

  const nodeAnnotations = (node.annotation_ids ?? [])
    .map((id) => allAnnotations.find((a) => a.id === id))
    .filter(Boolean) as typeof allAnnotations;

  return (
    <div
      className="text-sm"
      style={{
        position:     "absolute",
        top:          12,
        right:        12,
        bottom:       12,
        width:        "clamp(260px, 26vw, 340px)",
        background:   "var(--bg-card)",
        border:       "1px solid var(--border-card)",
        borderRadius: 8,
        overflowY:    "auto",
        padding:      "16px",
        zIndex:       20,
        boxShadow:    "0 4px 24px rgba(0,0,0,0.22)",
      }}
    >
      <button onClick={onClose}
        className="absolute top-3 right-3 text-xs"
        style={{ color: "var(--font-muted)" }}
        aria-label="Close">
        ✕
      </button>

      {/* Node header — always visible */}
      <div className="flex items-center gap-2 mb-2 pr-6 flex-wrap">
        <span className="text-xs px-2 py-0.5 rounded shrink-0"
          style={{ background: "#1E3A5F", color: "#a0b8d4" }}>
          {node.tier}
        </span>
        <span className="font-semibold" style={{ color: "var(--font)" }}>
          {node.label}
        </span>
        {node.stat && (
          <span className="font-bold text-sm shrink-0" style={{ color: "#0F766E" }}>
            {node.stat}
          </span>
        )}
      </div>

      {node.description && (
        <p className="mb-3 leading-relaxed" style={{ color: "var(--font-muted)" }}>
          {node.description}
        </p>
      )}

      {/* Annotation body — gated */}
      {nodeAnnotations.length > 0 && (
        unlocked ? (
          <div className="flex flex-col gap-3 mt-2">
            {nodeAnnotations.map((ann) => (
              <div key={ann.id} className="pl-3 py-2"
                style={{ borderLeft: "2px solid var(--border-card)" }}>
                <div className="text-xs font-semibold mb-1" style={{ color: "var(--font)" }}>
                  {ann.title}
                </div>
                <p className="text-xs leading-relaxed" style={{ color: "var(--font-muted)" }}>
                  {ann.body}
                </p>
                {ann.implication && (
                  <p className="text-xs italic mt-1" style={{ color: "var(--font-muted)" }}>
                    {ann.implication}
                  </p>
                )}
              </div>
            ))}
          </div>
        ) : (
          /* Email gate — inline card, not a canvas overlay */
          <div
            className="mt-3 rounded p-4 text-center"
            style={{ background: "var(--bg-page)", border: "1px solid var(--border-card)" }}
          >
            <p className="text-xs mb-3" style={{ color: "var(--font-muted)" }}>
              {nodeAnnotations.length} insight{nodeAnnotations.length > 1 ? "s" : ""} attached
              to this node — enter your email to read them.
            </p>
            <form
              onSubmit={(e) => {
                e.preventDefault();
                const email = (e.currentTarget.elements.namedItem("email") as HTMLInputElement).value;
                window.open(
                  `https://indiacreditlens.substack.com?email=${encodeURIComponent(email)}`,
                  "_blank",
                );
                if (typeof window !== "undefined") {
                  localStorage.setItem("icl-graph-unlocked", "true");
                }
                onUnlock();
              }}
              className="flex flex-col gap-2"
            >
              <input
                name="email"
                type="email"
                required
                placeholder="you@company.com"
                className="w-full px-3 py-2 text-xs rounded"
                style={{
                  background:  "var(--bg-card)",
                  border:      "1px solid var(--border-card)",
                  color:       "var(--font)",
                  outline:     "none",
                }}
              />
              <button
                type="submit"
                className="w-full py-2 text-xs font-semibold rounded"
                style={{ background: "#0F766E", color: "#ffffff" }}
              >
                Read insights →
              </button>
            </form>
          </div>
        )
      )}

      {nodeAnnotations.length === 0 && (
        <p className="text-xs" style={{ color: "var(--font-muted)" }}>
          No annotations for this node yet.
        </p>
      )}
    </div>
  );
}

// ── Top bar ───────────────────────────────────────────────────────────────────

function TopBar({
  mode,
  selectedSubsystem,
  onBack,
}: {
  mode:              GraphMode;
  selectedSubsystem: string | null;
  onBack:            () => void;
}) {
  const sub = SUBSYSTEMS.find((s) => s.id === selectedSubsystem);

  return (
    <div
      style={{
        position:     "absolute",
        top:          12,
        left:         12,
        zIndex:       10,
        display:      "flex",
        alignItems:   "center",
        gap:          10,
        maxWidth:     "calc(100% - 380px)",
        flexWrap:     "wrap",
      }}
    >
      {mode === "detail" && (
        <button
          onClick={onBack}
          style={{
            background:   "var(--bg-card)",
            border:       "1px solid var(--border-card)",
            borderRadius: 6,
            padding:      "6px 12px",
            fontSize:     12,
            cursor:       "pointer",
            color:        "var(--font-muted)",
            fontFamily:   "system-ui, sans-serif",
            whiteSpace:   "nowrap",
          }}
        >
          ← All subsystems
        </button>
      )}

      {mode === "overview" && (
        <p className="text-xs" style={{ color: "var(--font-muted)", fontFamily: "system-ui" }}>
          {MODEL_META.period} · Click a subsystem to explore
        </p>
      )}

      {mode === "detail" && sub && (
        <span
          className="text-xs font-semibold px-3 py-1.5 rounded"
          style={{ background: "#1E3A5F", color: "#e2e8f0", fontFamily: "system-ui" }}
        >
          {sub.label}
        </span>
      )}
    </div>
  );
}

// ── SEO text block — always in SSR HTML, never visible to users ───────────────

function SeoTextBlock() {
  const allAnnotations = Object.values(ANNOTATIONS).flatMap((sec) => [
    ...sec.insights,
    ...sec.gaps,
    ...sec.opportunities,
  ]);

  return (
    <div
      aria-hidden="true"
      style={{
        position: "absolute",
        width:    1,
        height:   1,
        overflow: "hidden",
        opacity:  0,
        pointerEvents: "none",
      }}
    >
      <h2>India Credit Lens — Causal System Model · {MODEL_META.period}</h2>
      <p>{MODEL_META.report_name} · ₹{MODEL_META.total_credit_lcr}L Cr total bank credit · +{MODEL_META.yoy_growth_pct}% YoY</p>
      {SUBSYSTEMS.map((sub) => (
        <section key={sub.id}>
          <h3>{sub.label}</h3>
        </section>
      ))}
      {allAnnotations.map((ann) => (
        <div key={ann.id}>
          <h4>{ann.title}</h4>
          <p>{ann.body}</p>
          {"implication" in ann && ann.implication && <p>{ann.implication}</p>}
        </div>
      ))}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function SystemView() {
  const [mode,              setMode]              = useState<GraphMode>("overview");
  const [selectedSubsystem, setSelectedSubsystem] = useState<string | null>(null);
  const [activeNode,        setActiveNode]        = useState<SystemNode | null>(null);
  const [unlocked,          setUnlocked]          = useState(false);

  // Restore unlock state; run validation in dev
  useEffect(() => {
    if (typeof window !== "undefined") {
      setUnlocked(localStorage.getItem("icl-graph-unlocked") === "true");
    }
    validateSubsystemCoverage();
  }, []);

  const handleSubsystemClick = useCallback((id: string) => {
    setSelectedSubsystem(id);
    setMode("detail");
    setActiveNode(null);
  }, []);

  const handleNodeClick = useCallback((node: SystemNode) => {
    setActiveNode((prev) => (prev?.id === node.id ? null : node));
  }, []);

  const handleBack = useCallback(() => {
    setMode("overview");
    setSelectedSubsystem(null);
    setActiveNode(null);
  }, []);

  const handleUnlock = useCallback(() => setUnlocked(true), []);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>

      {/* SEO text — rendered server-side, visually hidden */}
      <SeoTextBlock />

      {/* Top bar — back button in detail mode, period hint in overview */}
      <TopBar
        mode={mode}
        selectedSubsystem={selectedSubsystem}
        onBack={handleBack}
      />

      {/* Graph canvas — fills the full slot */}
      <CytoscapeGraph
        mode={mode}
        selectedSubsystem={selectedSubsystem}
        onSubsystemClick={handleSubsystemClick}
        onNodeClick={handleNodeClick}
      />

      {/* Annotation panel — right overlay, only in detail mode */}
      {mode === "detail" && activeNode && (
        <AnnotationPanel
          node={activeNode}
          unlocked={unlocked}
          onUnlock={handleUnlock}
          onClose={() => setActiveNode(null)}
        />
      )}

      {/* Substack CTA — bottom-right pill */}
      <div style={{
        position:   "absolute",
        bottom:     16,
        right:      (mode === "detail" && activeNode)
                      ? "calc(clamp(260px, 26vw, 340px) + 20px)"
                      : 16,
        zIndex:     10,
        transition: "right 0.2s ease",
      }}>
        <SubstackCTA
          activeSubsystemId={mode === "detail" ? selectedSubsystem : null}
          compact
        />
      </div>
    </div>
  );
}
