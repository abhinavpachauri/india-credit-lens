// ── System Model — typed data layer ───────────────────────────────────────────
// Source: analysis/rbi_sibc/2026-02-27/system_model.json
// Source: analysis/output/mermaid/rbi_sibc/2026-02-27/subsystems.json
//
// Update: re-copy JSON files to web/lib/data/ after each new report period,
// then update RBI_SIBC_PERIOD below.

import rawModel    from "@/lib/data/system_model_rbi_sibc.json";
import rawSubsystems from "@/lib/data/subsystems_rbi_sibc.json";

export const RBI_SIBC_PERIOD = "Jan 2026";

// ── Types ─────────────────────────────────────────────────────────────────────

export type NodeTier = "driver" | "sector" | "gap" | "opportunity" | "pressure";

export type EdgeType =
  | "causes"
  | "suppresses"
  | "reroutes_demand_to"
  | "reinforces"
  | "creates_risk"
  | "creates_opportunity"
  | "is_data_gap"
  | "creates_gap"
  | "signals"
  | "contrast";

export interface SystemNode {
  id:             string;
  tier:           NodeTier;
  label:          string;
  description?:   string;
  stat?:          string | null;
  value_lcr?:     number | null;
  annotation_ids: string[];
}

export interface SystemEdge {
  from:   string;
  to:     string;
  type:   EdgeType;
  label?: string;
}

export interface SystemMeta {
  report_id:        string;
  report_name:      string;
  period:           string;
  generated:        string;
  total_credit_lcr: number;
  yoy_growth_pct:   number;
  schema_version:   string;
}

export interface Subsystem {
  id:              string;
  label:           string;
  newsletter:      boolean;
  drivers:         string[];
  sectors:         string[];
  outcomes:        string[];
  node_ids:        string[];
}

// ── Clean accessors ───────────────────────────────────────────────────────────

// Filter out _comment sentinel objects injected by the JSON author
const isRealNode = (n: unknown): n is SystemNode =>
  typeof n === "object" && n !== null &&
  typeof (n as SystemNode).id === "string" &&
  typeof (n as SystemNode).tier === "string";

const isRealEdge = (e: unknown): e is SystemEdge =>
  typeof e === "object" && e !== null &&
  typeof (e as SystemEdge).from === "string" &&
  typeof (e as SystemEdge).to === "string";

export const MODEL_META: SystemMeta =
  rawModel._meta as unknown as SystemMeta;

export const MODEL_NODES: SystemNode[] =
  (rawModel.nodes as unknown[]).filter(isRealNode);

export const MODEL_EDGES: SystemEdge[] =
  (rawModel.edges as unknown[]).filter(isRealEdge);

export const SUBSYSTEMS: Subsystem[] =
  rawSubsystems as unknown as Subsystem[];

/** Map node id → node, for O(1) lookup in components */
export const NODE_MAP: Record<string, SystemNode> =
  Object.fromEntries(MODEL_NODES.map((n) => [n.id, n]));

/** Map node id → subsystem id */
export const NODE_TO_SUBSYSTEM: Record<string, string> = {};
SUBSYSTEMS.forEach((sub) => {
  sub.node_ids.forEach((nodeId) => {
    NODE_TO_SUBSYSTEM[nodeId] = sub.id;
  });
});

// Edge type priority — lower number wins when multiple edges exist between
// the same subsystem pair (we show the most semantically significant one).
const EDGE_TYPE_PRIORITY: Partial<Record<EdgeType, number>> = {
  causes:              1,
  reinforces:          2,
  suppresses:          3,
  reroutes_demand_to:  4,
  signals:             5,
  creates_risk:        6,
  creates_opportunity: 7,
  is_data_gap:         8,
  creates_gap:         9,
  contrast:            10,
};

/**
 * Derive cross-subsystem edges from individual node edges.
 * One edge per directed subsystem pair — the highest-priority edge type wins.
 */
export function deriveSubsystemEdges(): Array<{ from: string; to: string; type: EdgeType }> {
  // Best edge per (fromSub, toSub) pair
  const best: Record<string, { from: string; to: string; type: EdgeType; priority: number }> = {};

  MODEL_EDGES.forEach((edge) => {
    const fromSub = NODE_TO_SUBSYSTEM[edge.from];
    const toSub   = NODE_TO_SUBSYSTEM[edge.to];
    if (!fromSub || !toSub || fromSub === toSub) return;

    const key      = `${fromSub}→${toSub}`;
    const priority = EDGE_TYPE_PRIORITY[edge.type] ?? 99;

    if (!best[key] || priority < best[key].priority) {
      best[key] = { from: fromSub, to: toSub, type: edge.type, priority };
    }
  });

  return Object.values(best).map(({ from, to, type }) => ({ from, to, type }));
}

/**
 * Dev-only validation — logs warnings when nodes or edges fall outside
 * the subsystem coverage. Call once on mount in development.
 */
export function validateSubsystemCoverage(): void {
  if (process.env.NODE_ENV !== "development") return;

  const allSubsystemNodeIds = new Set(SUBSYSTEMS.flatMap((s) => s.node_ids));

  // Orphan nodes — in the model but not in any subsystem
  const orphanNodes = MODEL_NODES.filter((n) => !allSubsystemNodeIds.has(n.id));
  if (orphanNodes.length > 0) {
    console.warn(
      "[ICL] ⚠ Nodes not in any subsystem (will be invisible in overview):",
      orphanNodes.map((n) => n.id),
    );
  }

  // Edges with at least one unmapped endpoint — lost from cross-subsystem view
  const lostEdges = MODEL_EDGES.filter(
    (e) => !NODE_TO_SUBSYSTEM[e.from] || !NODE_TO_SUBSYSTEM[e.to],
  );
  if (lostEdges.length > 0) {
    console.warn(
      "[ICL] ⚠ Edges with unmapped node(s) — not represented in overview:",
      lostEdges.map((e) => `${e.from} →[${e.type}]→ ${e.to}`),
    );
  }

  if (orphanNodes.length === 0 && lostEdges.length === 0) {
    console.log("[ICL] ✓ All nodes and edges are subsystem-mapped.");
  }
}

/** Edge colour by type — matches newsletter + Mermaid palette */
export const EDGE_COLOR: Record<EdgeType, string> = {
  causes:               "#3b82f6",  // blue
  suppresses:           "#ef4444",  // red
  reroutes_demand_to:   "#f97316",  // orange
  reinforces:           "#22c55e",  // green
  creates_risk:         "#f59e0b",  // amber
  creates_opportunity:  "#0d9488",  // teal
  is_data_gap:          "#9ca3af",  // grey
  creates_gap:          "#9ca3af",  // grey
  signals:              "#8b5cf6",  // purple
  contrast:             "#6b7280",  // grey
};

export const EDGE_STYLE: Record<EdgeType, "solid" | "dashed" | "dotted"> = {
  causes:               "solid",
  suppresses:           "solid",
  reroutes_demand_to:   "solid",
  reinforces:           "solid",
  creates_risk:         "dashed",
  creates_opportunity:  "dashed",
  is_data_gap:          "dotted",
  creates_gap:          "dotted",
  signals:              "solid",
  contrast:             "dashed",
};

/** Node background + text colour by tier */
export const NODE_STYLE: Record<NodeTier, { bg: string; fg: string; border: string }> = {
  driver:      { bg: "#1E3A5F", fg: "#ffffff", border: "#1E3A5F" },
  sector:      { bg: "#F0FDF4", fg: "#166534", border: "#166534" },
  opportunity: { bg: "#0F766E", fg: "#ffffff", border: "#0F766E" },
  pressure:    { bg: "#FEF3C7", fg: "#92400E", border: "#B45309" },
  gap:         { bg: "#F9FAFB", fg: "#374151", border: "#6B7280" },
};
