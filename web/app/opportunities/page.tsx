"use client";

import { useEffect, useState } from "react";
import { loadAllOpportunities }  from "@/lib/opportunities";
import type { Opportunity }       from "@/lib/opportunities";
import {
  loadSectionChartMap, chartKey,
} from "@/lib/section-chart-data";
import type { SectionChartMap, SectionChartSlice } from "@/lib/section-chart-data";
import TrendChart        from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";

// ── Styles shared across all cards ───────────────────────────────────────────

type PipelineFilter = "all" | "sibc" | "atm_pos";

const PIPELINE_LABEL: Record<string, string> = {
  sibc:    "Credit",
  atm_pos: "Payments",
};

const PIPELINE_COLOR: Record<string, string> = {
  sibc:    "#4e8ef7",
  atm_pos: "#2ca02c",
};

const OPP_COLOR = "#16A34A";

const BTN_FILTER = (active: boolean): React.CSSProperties => ({
  background:   active ? OPP_COLOR : "var(--bg-page)",
  color:        active ? "#fff"    : "var(--font-muted)",
  border:       `1px solid ${active ? OPP_COLOR : "var(--border-card)"}`,
  borderRadius: 20,
  padding:      "6px 16px",
  fontSize:     13,
  fontWeight:   500,
  cursor:       "pointer",
  transition:   "all 0.15s",
});

const BTN_CTRL = (active: boolean): React.CSSProperties => ({
  background:   active ? "#4e8ef7"       : "var(--bg-page)",
  color:        active ? "#fff"          : "var(--font-muted)",
  border:       `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`,
  borderRadius: 20,
  padding:      "5px 12px",
  fontSize:     12,
  fontWeight:   500,
  cursor:       "pointer",
  transition:   "all 0.15s",
});

const CONTROLS_CARD: React.CSSProperties = {
  background:   "var(--bg-card)",
  border:       "1px solid var(--border-card)",
  borderRadius: 8,
  padding:      "10px 14px",
  marginBottom: 12,
};

const DIVIDER: React.CSSProperties = {
  width: 1, height: 18, background: "var(--border-card)", flexShrink: 0,
};

// ── Per-card chart controls ───────────────────────────────────────────────────

type TabId     = "trend" | "distribution";
type TrendMode = "absolute" | "yoy" | "fy";
type DistMode  = "absolute" | "pct";

function ChartPanel({ slice, sectionId }: { slice: SectionChartSlice; sectionId: string }) {
  const [tab,       setTab]       = useState<TabId>("trend");
  const [trendMode, setTrendMode] = useState<TrendMode>("absolute");
  const [distMode,  setDistMode]  = useState<DistMode>("absolute");

  return (
    <div>
      {/* Controls */}
      <div style={CONTROLS_CARD}>
        <div className="flex flex-wrap items-center gap-2">
          {/* Tab */}
          <div className="flex gap-1">
            {(["trend", "distribution"] as const).map((t) => (
              <button key={t} style={BTN_CTRL(tab === t)} onClick={() => setTab(t)}>
                {t === "trend" ? "📈 Trend" : "📊 Distribution"}
              </button>
            ))}
          </div>

          <div className="hidden sm:block" style={DIVIDER} />

          {/* Mode radios */}
          <div className="flex items-center gap-3 text-xs" style={{ color: "var(--font)" }}>
            {tab === "trend"
              ? (["absolute", "yoy", "fy"] as const).map((m) => (
                  <label key={m} className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="radio"
                      name={`trend-${sectionId}`}
                      value={m}
                      checked={trendMode === m}
                      onChange={() => setTrendMode(m)}
                      className="accent-blue-500"
                    />
                    {m === "absolute" ? "Absolute" : m === "yoy" ? "YoY %" : "FY Cumul."}
                  </label>
                ))
              : (["absolute", "pct"] as const).map((m) => (
                  <label key={m} className="flex items-center gap-1 cursor-pointer">
                    <input
                      type="radio"
                      name={`dist-${sectionId}`}
                      value={m}
                      checked={distMode === m}
                      onChange={() => setDistMode(m)}
                      className="accent-blue-500"
                    />
                    {m === "absolute" ? "₹ Crore" : "% Share"}
                  </label>
                ))}
          </div>
        </div>
      </div>

      {/* Chart */}
      <div
        style={{
          background:   "var(--bg-card)",
          border:       "1px solid var(--border-card)",
          borderRadius: 8,
          padding:      "12px 8px 8px",
        }}
      >
        {tab === "trend" ? (
          <TrendChart
            absoluteData={slice.absoluteData}
            growthData={slice.growthData}
            fyData={slice.fyData}
            seriesNames={slice.seriesNames}
            pctLabel={slice.pctLabel}
            mode={trendMode}
            highlightConfig={null}
            preferredMode={null}
          />
        ) : (
          <DistributionChart
            absoluteData={slice.absoluteData}
            seriesNames={slice.distributionSeriesNames ?? slice.seriesNames}
            pctLabel={slice.pctLabel}
            mode={distMode}
            highlightConfig={null}
            preferredMode={null}
          />
        )}
      </div>
    </div>
  );
}

// ── Opportunity card ──────────────────────────────────────────────────────────

function OpportunityCard({
  opp,
  chartSlice,
}: {
  opp:        Opportunity;
  chartSlice: SectionChartSlice | null;
}) {
  const [expanded, setExpanded] = useState(false);

  return (
    <div
      id={opp.sectionId}
      style={{
        background:   "var(--bg-card)",
        border:       "1px solid var(--border-card)",
        borderLeft:   `4px solid ${OPP_COLOR}`,
        borderRadius: 10,
        marginBottom: 20,
        overflow:     "hidden",
      }}
    >
      {/* Two-col grid: text left, chart right */}
      <div
        className="grid grid-cols-1 sm:grid-cols-[45fr_55fr]"
        style={{ alignItems: "start" }}
      >
        {/* ── Left: opportunity content ── */}
        <div
          style={{
            padding:     "20px 24px",
            borderRight: chartSlice ? "1px solid var(--border-card)" : undefined,
          }}
        >
          {/* Badges */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <span
              style={{
                fontSize:      11,
                fontWeight:    700,
                textTransform: "uppercase",
                letterSpacing: "0.06em",
                color:         "#fff",
                background:    PIPELINE_COLOR[opp.pipeline] ?? OPP_COLOR,
                borderRadius:  4,
                padding:       "2px 8px",
              }}
            >
              {PIPELINE_LABEL[opp.pipeline] ?? opp.pipeline}
            </span>
            <span style={{ fontSize: 13, color: "var(--font-muted)" }}>
              {opp.sectionIcon} {opp.sectionTitle}
            </span>
          </div>

          {/* Title */}
          <h3
            className="text-base font-bold leading-snug mb-3"
            style={{ color: "var(--font)" }}
          >
            {opp.title}
          </h3>

          {/* Body */}
          <p style={{ fontSize: 14, color: "var(--font)", lineHeight: 1.65, marginBottom: 12 }}>
            {opp.body}
          </p>

          {/* Implication */}
          {opp.implication && (
            <div
              style={{
                background:   `${OPP_COLOR}0D`,
                border:       `1px solid ${OPP_COLOR}30`,
                borderRadius: 6,
                padding:      "10px 14px",
                marginBottom: 12,
              }}
            >
              <p style={{ fontSize: 12, fontWeight: 600, color: OPP_COLOR, marginBottom: 4 }}>
                For lenders
              </p>
              <p style={{ fontSize: 13, color: "var(--font)", lineHeight: 1.6 }}>
                {opp.implication}
              </p>
            </div>
          )}

          {/* Reasoning toggle */}
          {opp.basis?.inferences && opp.basis.inferences.length > 0 && (
            <div>
              <button
                onClick={() => setExpanded((x) => !x)}
                style={{
                  fontSize:   12,
                  color:      "var(--font-muted)",
                  background: "transparent",
                  border:     "none",
                  cursor:     "pointer",
                  padding:    0,
                }}
              >
                {expanded ? "▾ Hide reasoning" : "▸ Show reasoning"}
              </button>
              {expanded && (
                <ol style={{ marginTop: 8, paddingLeft: 20 }}>
                  {opp.basis.inferences.map((step, i) => (
                    <li
                      key={i}
                      style={{
                        fontSize:     13,
                        color:        "var(--font-muted)",
                        lineHeight:   1.6,
                        marginBottom: 4,
                      }}
                    >
                      {step}
                    </li>
                  ))}
                </ol>
              )}
            </div>
          )}
        </div>

        {/* ── Right: chart panel ── */}
        {chartSlice && (
          <div style={{ padding: "20px 20px 16px" }}>
            <ChartPanel slice={chartSlice} sectionId={opp.sectionId} />
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function OpportunitiesPage() {
  const [opps,   setOpps]   = useState<Opportunity[] | null>(null);
  const [charts, setCharts] = useState<SectionChartMap | null>(null);
  const [filter, setFilter] = useState<PipelineFilter>("all");

  useEffect(() => {
    Promise.all([
      loadAllOpportunities(),
      loadSectionChartMap(),
    ]).then(([o, c]) => {
      setOpps(o);
      setCharts(c);
    });
  }, []);

  if (!opps) {
    return (
      <div
        className="flex items-center justify-center min-h-[60vh] text-sm"
        style={{ color: "var(--font-muted)" }}
      >
        Loading opportunities…
      </div>
    );
  }

  const sibcCount = opps.filter((o) => o.pipeline === "sibc").length;
  const atmCount  = opps.filter((o) => o.pipeline === "atm_pos").length;
  const filtered  = filter === "all" ? opps : opps.filter((o) => o.pipeline === filter);

  return (
    // Full width — wider than the 3xl content pages
    <main className="max-w-7xl mx-auto px-4 py-8">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-2xl font-bold mb-2" style={{ color: "var(--font)" }}>
          Opportunities
        </h1>
        <p className="text-sm" style={{ color: "var(--font-muted)" }}>
          {opps.length} actionable opportunities identified from India&apos;s credit and payments data.
          Updated each period.
        </p>
      </div>

      {/* Pipeline filter */}
      <div className="flex gap-2 mb-8 flex-wrap">
        <button style={BTN_FILTER(filter === "all")}  onClick={() => setFilter("all")}>
          All {opps.length}
        </button>
        <button style={BTN_FILTER(filter === "sibc")} onClick={() => setFilter("sibc")}>
          📊 Credit {sibcCount}
        </button>
        {atmCount > 0 && (
          <button style={BTN_FILTER(filter === "atm_pos")} onClick={() => setFilter("atm_pos")}>
            💳 Payments {atmCount}
          </button>
        )}
      </div>

      {/* Cards */}
      {filtered.length === 0 ? (
        <p style={{ color: "var(--font-muted)", fontSize: 14 }}>
          No opportunities for this filter yet.
        </p>
      ) : (
        filtered.map((opp) => (
          <OpportunityCard
            key={opp.id}
            opp={opp}
            chartSlice={charts?.get(chartKey(opp.pipeline, opp.sectionId)) ?? null}
          />
        ))
      )}

      <footer className="mt-10 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
        Source: RBI SIBC + ATM/POS data · India Credit Lens analysis
      </footer>
    </main>
  );
}
