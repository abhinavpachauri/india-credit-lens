"use client";

// NBFC adapter — the thinnest one, because this pipeline has no cards.
//
// SIBC and payments build their RMModel from insight cards and rank them; NBFC deliberately
// generates none (PLAN_2026-09-16_NBFC.md D2 — cards are the NEWS layer, and eleven dates is
// a thin basis for "fastest in N periods"). So the model here is a DECLARATION of five
// dimensions with no subjects and no reads, and everything a reader sees comes from the two
// derived sidecars: the standing state band (§16) and the Layer 1 cut tables (§17).
//
// That is the shape the §20 refactor was arguing for — the table is the generic L1 surface
// and needs no generator — so this adapter is what that claim looks like when it is true.

import { useMemo } from "react";
import type { StateMap } from "@/lib/state";
import type { CutTables } from "@/lib/table";
import ReadModeShell, { type CutRef } from "./ReadModeShell";
import { type RMModel, type RMDimension } from "./parts";

/** The five dimensions, in the order a reader meets them: the whole book, then its parts.
 *
 *  Declared rather than derived from the table sidecar, for the same reason the Python side
 *  declares its cut table: which pane a cut appears under, what it is CALLED and what icon it
 *  carries are presentation decisions. Everything else — the parts, the columns, the coverage
 *  line, the band — is discovered. */
const DIMS: { id: string; title: string; icon: string; color: string; stem: string;
              bookLabel?: string }[] = [
  { id: "mainSectors",    title: "Main sectors",   icon: "🏦", color: "#2ca02c",
    stem: "nbfc-main" },
  { id: "industry",       title: "Industry",       icon: "🏭", color: "#e05c5c",
    stem: "nbfc-industry",  bookLabel: "of NBFC credit" },
  { id: "infrastructure", title: "Infrastructure", icon: "🛣️", color: "#2ec4b6",
    stem: "nbfc-infra",     bookLabel: "of NBFC credit" },
  { id: "services",       title: "Services",       icon: "🛎️", color: "#a87fdb",
    stem: "nbfc-services",  bookLabel: "of NBFC credit" },
  { id: "retail",         title: "Retail",         icon: "🛍️", color: "#f0912a",
    stem: "nbfc-retail",    bookLabel: "of NBFC credit" },
];

const CUTS: Record<string, CutRef[]> = Object.fromEntries(
  DIMS.map((d) => [d.id, [{ stem: d.stem, title: d.title, bookLabel: d.bookLabel }]]));

export default function NbfcReadMode(
  { state, tables, period = "" }: { state: StateMap; tables: CutTables; period?: string },
) {
  const model: RMModel = useMemo(() => ({
    // No reads and no subjects — not an empty result, an absent LAYER. The tiles carry the
    // band and the table count, and the shell renders no "What's notable" block at all.
    reads: [],
    dimensions: DIMS.map<RMDimension>((d) => ({
      id: d.id, title: d.title, icon: d.icon, color: d.color,
      cardCount: 0, moved: 0, subjects: [], compositionTitles: [],
    })),
  }), []);

  return (
    <ReadModeShell
      model={model}
      homeLabel="NBFC deployment"
      period={period}
      state={state}
      tables={tables}
      cutsFor={(dimId) => CUTS[dimId] ?? []}
      // Every NBFC dimension owns a table, so the shell never needs the card-chart fallback.
      renderChart={() => null}
      hasDeep={() => false}
      renderDeep={() => null}
    />
  );
}
