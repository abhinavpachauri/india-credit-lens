"use client";

import { useState, useMemo } from "react"; // useState kept for hidden series toggle
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer,
} from "recharts";
import { formatCr, formatGrowth } from "@/lib/data";
import { pickColor } from "@/lib/theme";
import ChartLegend from "./ChartLegend";
import type { ChartPoint, AnnotationEffect } from "@/lib/types";

interface TrendChartProps {
  absoluteData:    ChartPoint[];
  growthData:      ChartPoint[];
  fyData:          ChartPoint[];
  seriesNames:     string[];
  pctLabel?:       string;
  mode:            "absolute" | "yoy" | "fy";  // owned by parent controls card
  visibleSeries?:  string[];                   // optional subset — used by IndustryFilter
  initialHidden?:  string[];                   // series off by default in explore mode (e.g. "Total")
  highlightConfig?: AnnotationEffect | null;   // from active annotation
  preferredMode?:  "absolute" | "yoy" | "fy" | "share" | null; // annotation overrides parent mode ("share" is a distribution view → ignored here)
}

/** Compute per-series visual style based on active annotation. */
function seriesStyle(name: string, config: AnnotationEffect | null | undefined) {
  if (!config) return { opacity: 1, strokeWidth: 2, strokeDasharray: undefined };
  const highlighted = config.highlight?.includes(name) ?? false;
  const dimmed      = config.dim?.includes(name)       ?? false;
  const dashed      = config.dash?.includes(name)      ?? false;
  // Auto-fade anything not explicitly highlighted when a highlight set exists
  const autoFade    = (config.highlight?.length ?? 0) > 0 && !highlighted && !dimmed;
  return {
    opacity:          highlighted ? 1 : (dimmed || autoFade) ? 0.15 : 1,
    strokeWidth:      highlighted ? 3 : 2,
    strokeDasharray:  dashed ? "5 5" : undefined,
  };
}

type ViewMode = "absolute" | "yoy" | "fy";

export default function TrendChart({
  absoluteData, growthData, fyData = [], seriesNames,
  pctLabel = "% of Total", mode, visibleSeries, initialHidden, highlightConfig, preferredMode,
}: TrendChartProps) {
  // When an annotation specifies a trend preferredMode, use it — otherwise use the
  // parent-controlled mode. "share" is a distribution view (handled by the parent
  // routing to DistributionChart), so it's ignored here.
  const effectiveMode: ViewMode =
    preferredMode && preferredMode !== "share" ? (preferredMode as ViewMode) : mode;
  const [hidden, setHidden] = useState<Set<string>>(() => new Set(initialHidden ?? []));

  // Which series to actually render
  const activeNames = useMemo(
    () => (visibleSeries ? seriesNames.filter((n) => visibleSeries.includes(n)) : seriesNames),
    [seriesNames, visibleSeries]
  );

  // Switch between absolute, YoY, and FY data based on effectiveMode
  const seriesData = useMemo(
    () => effectiveMode === "absolute" ? absoluteData
        : effectiveMode === "fy"       ? fyData
        :                                growthData,
    [effectiveMode, absoluteData, growthData, fyData]
  );

  // Proportional time axis: collect timestamps from current dataset
  const tsTicks = useMemo(
    () => (seriesData ?? []).map((p) => p._ts as number).filter((t) => typeof t === "number" && t > 0),
    [seriesData]
  );
  const tsDomain = useMemo(
    (): [number, number] =>
      tsTicks.length >= 2
        ? [tsTicks[0], tsTicks[tsTicks.length - 1]]
        : [0, 1],
    [tsTicks]
  );

  // Map _ts → original publication date note (for delayed-publication markers)
  const dateNotes = useMemo(() => {
    const notes: Record<number, string> = {};
    (seriesData ?? []).forEach((p) => {
      if (p._sourceDate && typeof p._ts === "number" && p._ts > 0) {
        notes[p._ts as number] = `Published: ${p._sourceDate}`;
      }
    });
    return notes;
  }, [seriesData]);

  // When an annotation highlights specific series, only those series render as lines.
  // Others are shown in the legend as inactive (so users know they exist) but not drawn —
  // this lets recharts auto-scale the Y-axis to the relevant data naturally.
  const hasHighlight = (highlightConfig?.highlight?.length ?? 0) > 0;
  const highlightSet = new Set(highlightConfig?.highlight ?? []);

  // In intelligence mode the annotation governs which series show; manual
  // legend toggles (`hidden`) only apply in explore mode. This prevents a
  // highlighted series from being suppressed by a stale prior deselection.
  const legendItems = activeNames.map((name, i) => ({
    label:  name,
    color:  pickColor(name, i),
    active: hasHighlight ? highlightSet.has(name) : !hidden.has(name),
  }));

  const toggleSeries = (name: string) =>
    setHidden((prev) => {
      const next = new Set(prev);
      next.has(name) ? next.delete(name) : next.add(name);
      return next;
    });

  const formatY = (v: number) =>
    effectiveMode === "absolute" ? formatCr(v, 1) : `${v > 0 ? "+" : ""}${v.toFixed(1)}%`;

  // Custom tooltip — filters to highlighted series only when an annotation is active
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (!active || !payload?.length) return null;
    const highlighted = highlightConfig?.highlight;
    const visible = highlighted?.length
      ? payload.filter((p: any) => highlighted.includes(p.dataKey))
      : payload;
    if (!visible.length) return null;
    const ts   = Number(label);
    const note = dateNotes[ts];
    return (
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: 8, fontSize: 13, color: "var(--font)", padding: "10px 14px" }}>
        <p style={{ marginBottom: 4, fontWeight: 600 }}>
          {new Date(ts).toLocaleDateString("en-IN", { month: "short", year: "numeric" })}
          {note ? "*" : ""}
        </p>
        {visible.map((p: any) => (
          <p key={p.dataKey} style={{ color: p.color, margin: "2px 0" }}>
            {p.name}: {effectiveMode === "absolute" ? formatCr(Number(p.value) || 0) : formatGrowth(Number(p.value) || 0)}
          </p>
        ))}
        {note && (
          <p style={{ color: "var(--font-muted)", fontSize: 11, marginTop: 6, fontStyle: "italic", borderTop: "1px solid var(--border-card)", paddingTop: 4 }}>
            {note}
          </p>
        )}
      </div>
    );
  };

  return (
    <div>
      {/* Legend — not toggleable in intelligence mode */}
      <ChartLegend items={legendItems} onToggle={highlightConfig ? undefined : toggleSeries} />

      <ResponsiveContainer width="100%" height={320}>
        <LineChart data={seriesData} margin={{ top: 4, right: 16, bottom: 4, left: 0 }}>
          <CartesianGrid strokeDasharray="3 3" stroke="var(--grid)" />
          <XAxis
            dataKey="_ts"
            type="number"
            domain={tsDomain}
            ticks={tsTicks}
            tickFormatter={(ts: number) =>
              new Date(ts).toLocaleDateString("en-IN", { month: "short", year: "numeric" })
            }
            tick={{ fontSize: 12, fill: "var(--font-muted)" }}
            tickLine={false}
          />
          <YAxis
            tickFormatter={formatY}
            tick={{ fontSize: 12, fill: "var(--font-muted)" }}
            tickLine={false}
            axisLine={false}
            width={96}
          />
          <Tooltip content={<CustomTooltip />} />
          {activeNames.map((name, i) => {
            // Explore mode honours manual legend toggles; intelligence mode does
            // not — the annotation highlight decides visibility (below).
            if (!hasHighlight && hidden.has(name)) return null;
            // When annotation highlights specific series, completely hide all others —
            // this lets the Y-axis auto-scale to only the relevant data
            if (hasHighlight && !highlightSet.has(name)) return null;
            const style = seriesStyle(name, highlightConfig);
            return (
              <Line
                key={name}
                type="monotone"
                dataKey={name}
                stroke={pickColor(name, i)}
                strokeWidth={style.strokeWidth}
                strokeDasharray={style.strokeDasharray}
                style={{ opacity: style.opacity }}
                dot={{ r: 4, strokeWidth: 1, opacity: style.opacity }}
                activeDot={{ r: 6 }}
                connectNulls={effectiveMode === "absolute"}
              />
            );
          })}
        </LineChart>
      </ResponsiveContainer>
    </div>
  );
}
