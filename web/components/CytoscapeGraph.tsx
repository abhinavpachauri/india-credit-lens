"use client";

// ── CytoscapeGraph ────────────────────────────────────────────────────────────
// Two-mode interactive graph via Cytoscape.js + dagre.
//
// OVERVIEW mode  — 7 subsystem bubbles + cross-subsystem edges.
//                  Always fits the viewport. Click a bubble → detail mode.
//
// DETAIL mode    — nodes + internal edges of the selected subsystem only.
//                  Clean layout at readable size. Click a node → annotation.
//
// Mode switch swaps elements and re-runs layout — no full remount.

import { useEffect, useRef } from "react";
import type cytoscape from "cytoscape";
import {
  MODEL_NODES,
  MODEL_EDGES,
  NODE_STYLE,
  EDGE_COLOR,
  EDGE_STYLE,
  NODE_MAP,
  SUBSYSTEMS,
  deriveSubsystemEdges,
  type SystemNode,
  type EdgeType,
  type NodeTier,
} from "@/lib/system_model_data";

export type GraphMode = "overview" | "detail";

interface Props {
  mode:               GraphMode;
  selectedSubsystem:  string | null;   // required when mode === "detail"
  onSubsystemClick:   (id: string) => void;
  onNodeClick:        (node: SystemNode) => void;
}

// ── Edge label map ────────────────────────────────────────────────────────────

const EDGE_LABEL: Record<string, string> = {
  causes:              "causes",
  suppresses:          "suppresses",
  reroutes_demand_to:  "reroutes demand",
  reinforces:          "reinforces",
  creates_risk:        "creates risk",
  creates_opportunity: "creates opportunity",
  is_data_gap:         "data gap",
  creates_gap:         "data gap",
  signals:             "signals",
  contrast:            "contrast",
};

// ── Element builders ──────────────────────────────────────────────────────────

function buildOverviewElements(): cytoscape.ElementDefinition[] {
  const nodes: cytoscape.ElementDefinition[] = SUBSYSTEMS.map((sub) => {
    // Pull a representative stat from the subsystem's sector nodes
    const statNode = MODEL_NODES.find(
      (n) => sub.node_ids.includes(n.id) && n.tier === "sector" && n.stat,
    );
    const label = statNode?.stat
      ? `${sub.label}\n${statNode.stat}`
      : sub.label;

    return {
      data: {
        id:          sub.id,
        label,
        tier:        "subsystem",
        bgColor:     "#1E3A5F",
        fgColor:     "#e2e8f0",
        borderColor: "#2d5986",
        opacity:     1,
      },
    };
  });

  const crossEdges = deriveSubsystemEdges();
  const edges: cytoscape.ElementDefinition[] = crossEdges.map((e, i) => ({
    data: {
      id:        `ov-edge-${i}`,
      source:    e.from,
      target:    e.to,
      label:     EDGE_LABEL[e.type] ?? e.type,
      color:     EDGE_COLOR[e.type as EdgeType] ?? "#9ca3af",
      lineStyle: EDGE_STYLE[e.type as EdgeType] ?? "solid",
      opacity:   0.85,
    },
  }));

  return [...nodes, ...edges];
}

function buildDetailElements(subsystemId: string): cytoscape.ElementDefinition[] {
  const sub = SUBSYSTEMS.find((s) => s.id === subsystemId);
  if (!sub) return [];

  const activeIds = new Set(sub.node_ids);

  const nodes: cytoscape.ElementDefinition[] = MODEL_NODES
    .filter((n) => activeIds.has(n.id))
    .map((n) => {
      const style = NODE_STYLE[n.tier as NodeTier] ?? NODE_STYLE.gap;
      return {
        data: {
          id:          n.id,
          label:       n.stat ? `${n.label}\n${n.stat}` : n.label,
          tier:        n.tier,
          bgColor:     style.bg,
          fgColor:     style.fg,
          borderColor: style.border,
          opacity:     1,
        },
      };
    });

  const edges: cytoscape.ElementDefinition[] = MODEL_EDGES
    .filter((e) => activeIds.has(e.from) && activeIds.has(e.to))
    .map((e, i) => ({
      data: {
        id:        `dt-edge-${i}`,
        source:    e.from,
        target:    e.to,
        label:     EDGE_LABEL[e.type] ?? e.type,
        color:     EDGE_COLOR[e.type as EdgeType] ?? "#9ca3af",
        lineStyle: EDGE_STYLE[e.type as EdgeType] ?? "solid",
        opacity:   0.85,
      },
    }));

  return [...nodes, ...edges];
}

// ── Cytoscape style builders ──────────────────────────────────────────────────

// eslint-disable-next-line @typescript-eslint/no-explicit-any
function buildStyle(mode: GraphMode, isMobile: boolean): any[] {
  const isOverview  = mode === "overview";
  const fontSize    = isOverview ? (isMobile ? 13 : 16) : (isMobile ? 14 : 18);
  const edgeFontSz  = isOverview ? (isMobile ? 10 : 12) : (isMobile ? 10 : 12);
  const textWidth   = isOverview ? (isMobile ? "130px" : "180px") : (isMobile ? "160px" : "220px");
  const nodePad     = isOverview ? (isMobile ? "20px 16px" : "28px 22px") : (isMobile ? "20px 16px" : "26px 20px");
  const edgeWidth   = isMobile ? 1.5 : 2;

  return [
    {
      selector: "node",
      style: {
        "label":               "data(label)",
        "background-color":    "data(bgColor)",
        "color":               "data(fgColor)",
        "border-color":        "data(borderColor)",
        "border-width":        2,
        "font-size":           fontSize,
        "font-family":         "system-ui, sans-serif",
        "font-weight":         500,
        "text-valign":         "center",
        "text-halign":         "center",
        "text-wrap":           "wrap",
        "text-max-width":      textWidth,
        "width":               "label",
        "height":              "label",
        "padding":             nodePad,
        "shape":               isOverview ? "ellipse" : "roundrectangle",
        "opacity":             "data(opacity)" as unknown as number,
        "transition-property": "opacity",
        "transition-duration": 250,
        "cursor":              "pointer",
      } as unknown as cytoscape.Css.Node,
    },
    // Detail mode: driver nodes keep ellipse shape
    {
      selector: "node[tier = 'driver']",
      style: { "shape": "ellipse" } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "node:selected",
      style: { "border-width": 3, "border-color": "#4e8ef7" } as unknown as cytoscape.Css.Node,
    },
    {
      selector: "edge",
      style: {
        "label":                   "data(label)",
        "font-size":               edgeFontSz,
        "font-family":             "system-ui, sans-serif",
        "color":                   "data(color)",
        "text-rotation":           "autorotate",
        "text-margin-y":           -10,
        "text-background-opacity": 0.8,
        "text-background-color":   "var(--bg-page, #0f172a)",
        "text-background-padding": "3px",
        "line-color":              "data(color)",
        "target-arrow-color":      "data(color)",
        "target-arrow-shape":      "triangle",
        "arrow-scale":             1.1,
        "curve-style":             "bezier",
        "line-style":              "data(lineStyle)" as unknown as "solid",
        "opacity":                 "data(opacity)" as unknown as number,
        "width":                   edgeWidth,
        "transition-property":     "opacity",
        "transition-duration":     250,
      } as unknown as cytoscape.Css.Edge,
    },
  ];
}

// ── Layout options ────────────────────────────────────────────────────────────

function buildLayout(mode: GraphMode, isMobile: boolean): cytoscape.LayoutOptions {
  const isOverview = mode === "overview";
  return {
    name:    "dagre",
    rankDir: "TB",
    nodeSep: isOverview ? (isMobile ? 40  : 80)  : (isMobile ? 36  : 70),
    rankSep: isOverview ? (isMobile ? 120 : 200) : (isMobile ? 120 : 220),
    padding: 60,
    animate: false,
    fit:     true,
  } as cytoscape.LayoutOptions;
}

// ── Component ─────────────────────────────────────────────────────────────────

export default function CytoscapeGraph({
  mode,
  selectedSubsystem,
  onSubsystemClick,
  onNodeClick,
}: Props) {
  const containerRef  = useRef<HTMLDivElement>(null);
  const cyRef         = useRef<cytoscape.Core | null>(null);
  const modeRef       = useRef<GraphMode>(mode);
  const isMobileRef   = useRef(false);

  // ── Initial mount ───────────────────────────────────────────────────────────
  useEffect(() => {
    if (!containerRef.current) return;

    Promise.all([
      import("cytoscape"),
      import("cytoscape-dagre"),
    ]).then(([cytoscapeModule, dagreModule]) => {
      const cy    = cytoscapeModule.default;
      const dagre = dagreModule.default;

      try { cy.use(dagre as Parameters<typeof cy.use>[0]); } catch { /* already registered */ }

      cyRef.current?.destroy();
      cyRef.current = null;

      isMobileRef.current = window.innerWidth < 768;
      modeRef.current     = mode;

      const elements = mode === "overview"
        ? buildOverviewElements()
        : buildDetailElements(selectedSubsystem ?? "");

      const instance = cy({
        container:           containerRef.current!,
        elements,
        userZoomingEnabled:  true,
        userPanningEnabled:  true,
        wheelSensitivity:    0.15,
        boxSelectionEnabled: false,
        minZoom:             0.08,
        maxZoom:             3,
        style:               buildStyle(mode, isMobileRef.current),
        layout:              buildLayout(mode, isMobileRef.current),
      });

      // Overview: click bubble → drill in
      instance.on("tap", "node", (evt) => {
        const nodeId = evt.target.id() as string;
        if (modeRef.current === "overview") {
          onSubsystemClick(nodeId);
        } else {
          const n = NODE_MAP[nodeId];
          if (n) onNodeClick(n);
        }
      });

      instance.on("mouseover", "node", () => {
        if (containerRef.current) containerRef.current.style.cursor = "pointer";
      });
      instance.on("mouseout", "node", () => {
        if (containerRef.current) containerRef.current.style.cursor = "default";
      });

      cyRef.current = instance;
    });

    return () => {
      cyRef.current?.destroy();
      cyRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // mount only

  // ── Mode / subsystem change — swap elements + re-layout ────────────────────
  useEffect(() => {
    const instance = cyRef.current;
    if (!instance) return;

    modeRef.current = mode;

    const newElements = mode === "overview"
      ? buildOverviewElements()
      : buildDetailElements(selectedSubsystem ?? "");

    instance.elements().remove();
    instance.add(newElements);
    instance.style(buildStyle(mode, isMobileRef.current));
    instance.layout(buildLayout(mode, isMobileRef.current)).run();
  }, [mode, selectedSubsystem]);

  // ── Fit button handler (exposed via data attribute for SystemView) ───────────
  const handleFit = () => cyRef.current?.fit(undefined, 60);

  return (
    <div style={{ position: "relative", width: "100%", height: "100%" }}>
      <div
        ref={containerRef}
        style={{ width: "100%", height: "100%", background: "var(--bg-card)" }}
      />
      <button
        onClick={handleFit}
        title="Fit all in view"
        style={{
          position:     "absolute",
          bottom:       14,
          left:         14,
          zIndex:       10,
          background:   "var(--bg-card)",
          border:       "1px solid var(--border-card)",
          borderRadius: 6,
          padding:      "6px 12px",
          fontSize:     12,
          cursor:       "pointer",
          color:        "var(--font-muted)",
          fontFamily:   "system-ui, sans-serif",
        }}
      >
        ⊙ Fit all
      </button>
    </div>
  );
}
