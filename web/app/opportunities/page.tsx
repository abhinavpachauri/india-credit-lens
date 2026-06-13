"use client";

import { useEffect, useState } from "react";
import { loadSectionChartMap, chartKey } from "@/lib/section-chart-data";
import type { SectionChartMap, SectionChartSlice } from "@/lib/section-chart-data";
import TrendChart        from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";

// ── Derived feed types (web/public/data/opportunities_feed.json) ─────────────

type Pipeline = "sibc" | "atm_pos";
type Status   = "active" | "watch" | "closed" | "retired";

interface ChartRef { pipeline: Pipeline; section: string; highlight: string[]; caption?: string }

interface Item {
  id: string; pipeline?: Pipeline; scope: "pipeline" | "cross_source"; tier: "opportunity" | "risk";
  status: Status; section?: { id: string | null; title: string; icon: string };
  title: string; body: string; implication?: string | null; chain: string[];
  charts: ChartRef[]; badge?: string;
}
interface Feed {
  cross_system: Item[];
  pipelines: Record<Pipeline, Item[]>;
  _meta: { periods: Record<string, string> };
}
interface ResolvedChart { slice: SectionChartSlice; highlight: string[]; caption?: string; key: string }

// ── Styles ───────────────────────────────────────────────────────────────────

type PipelineFilter = "all" | Pipeline;
type StatusFilter   = "live" | "active" | "watch" | "all";

const PIPELINE_LABEL: Record<string, string> = { sibc: "Credit", atm_pos: "Payments" };
const PIPELINE_COLOR: Record<string, string> = { sibc: "#4e8ef7", atm_pos: "#2ca02c" };
const OPP_COLOR  = "#16A34A";
const RISK_COLOR = "#DC2626";

const STATUS_META: Record<Status, { label: string; color: string; dot: string }> = {
  active:  { label: "Active",  color: "#16A34A", dot: "●" },
  watch:   { label: "Watch",   color: "#D97706", dot: "◐" },
  closed:  { label: "Closed",  color: "#6B7280", dot: "○" },
  retired: { label: "Retired", color: "#9CA3AF", dot: "⊘" },
};

const BTN_FILTER = (active: boolean): React.CSSProperties => ({
  background: active ? OPP_COLOR : "var(--bg-page)", color: active ? "#fff" : "var(--font-muted)",
  border: `1px solid ${active ? OPP_COLOR : "var(--border-card)"}`, borderRadius: 20,
  padding: "6px 16px", fontSize: 13, fontWeight: 500, cursor: "pointer", transition: "all 0.15s",
});
const BTN_CTRL = (active: boolean): React.CSSProperties => ({
  background: active ? "#4e8ef7" : "var(--bg-page)", color: active ? "#fff" : "var(--font-muted)",
  border: `1px solid ${active ? "#4e8ef7" : "var(--border-card)"}`, borderRadius: 20,
  padding: "5px 12px", fontSize: 12, fontWeight: 500, cursor: "pointer", transition: "all 0.15s",
});
const CONTROLS_CARD: React.CSSProperties = {
  background: "var(--bg-card)", border: "1px solid var(--border-card)",
  borderRadius: 8, padding: "10px 14px", marginBottom: 12,
};
const DIVIDER: React.CSSProperties = { width: 1, height: 18, background: "var(--border-card)", flexShrink: 0 };

// ── Status pill ───────────────────────────────────────────────────────────────

function StatusPill({ status }: { status: Status }) {
  const m = STATUS_META[status];
  return (
    <span style={{
      display: "inline-flex", alignItems: "center", gap: 5, fontSize: 11, fontWeight: 700,
      textTransform: "uppercase", letterSpacing: "0.05em", color: m.color,
      background: `${m.color}14`, border: `1px solid ${m.color}40`, borderRadius: 20, padding: "2px 9px",
    }}>
      <span style={{ fontSize: 9 }}>{m.dot}</span>{m.label}
    </span>
  );
}

// ── Per-chart panel ────────────────────────────────────────────────────────────

type TabId = "trend" | "distribution";

function ChartPanel({ slice, sectionId, highlightConfig }: {
  slice: SectionChartSlice; sectionId: string;
  highlightConfig?: { highlight: string[] } | null;
}) {
  const [tab, setTab]             = useState<TabId>("trend");
  const [trendMode, setTrendMode] = useState<"absolute" | "yoy" | "fy">("absolute");
  const [distMode, setDistMode]   = useState<"absolute" | "pct">("absolute");
  const isAtm = slice.variant === "atm_pos";
  const trendModes = (isAtm ? ["absolute", "yoy"] : ["absolute", "yoy", "fy"]) as ("absolute" | "yoy" | "fy")[];
  const trendLabel = (m: string) =>
    m === "absolute" ? (isAtm ? "Count" : "Absolute") : m === "yoy" ? (isAtm ? "MoM %" : "YoY %") : "FY Cumul.";
  const mode = trendMode === "fy" && isAtm ? "absolute" : trendMode;
  return (
    <div>
      <div style={CONTROLS_CARD}>
        <div className="flex flex-wrap items-center gap-2">
          <div className="flex gap-1">
            {(["trend", "distribution"] as const).map((t) => (
              <button key={t} style={BTN_CTRL(tab === t)} onClick={() => setTab(t)}>
                {t === "trend" ? "📈 Trend" : "📊 Distribution"}
              </button>
            ))}
          </div>
          <div className="hidden sm:block" style={DIVIDER} />
          <div className="flex items-center gap-3 text-xs" style={{ color: "var(--font)" }}>
            {tab === "trend"
              ? trendModes.map((m) => (
                  <label key={m} className="flex items-center gap-1 cursor-pointer">
                    <input type="radio" name={`trend-${sectionId}`} value={m}
                      checked={trendMode === m} onChange={() => setTrendMode(m)} className="accent-blue-500" />
                    {trendLabel(m)}
                  </label>))
              : (["absolute", "pct"] as const).map((m) => (
                  <label key={m} className="flex items-center gap-1 cursor-pointer">
                    <input type="radio" name={`dist-${sectionId}`} value={m}
                      checked={distMode === m} onChange={() => setDistMode(m)} className="accent-blue-500" />
                    {m === "absolute" ? (isAtm ? "Count" : "₹ Crore") : "% Share"}
                  </label>))}
          </div>
        </div>
      </div>
      <div style={{ background: "var(--bg-card)", border: "1px solid var(--border-card)", borderRadius: 8, padding: "12px 8px 8px" }}>
        {tab === "trend" ? (
          <TrendChart absoluteData={slice.absoluteData} growthData={slice.growthData} fyData={slice.fyData}
            seriesNames={slice.seriesNames} pctLabel={slice.pctLabel} mode={mode}
            highlightConfig={highlightConfig ?? null} preferredMode={null} />
        ) : (
          <DistributionChart absoluteData={slice.absoluteData}
            seriesNames={slice.distributionSeriesNames ?? slice.seriesNames} pctLabel={slice.pctLabel}
            mode={distMode} highlightConfig={highlightConfig ?? null} preferredMode={null} />
        )}
      </div>
    </div>
  );
}

// ── Flip zone: For lenders ↔ Causal chain ───────────────────────────────────

function FlipZone({ implication, chain, accent = OPP_COLOR, frontLabel = "For lenders" }: {
  implication?: string | null; chain?: string[]; accent?: string; frontLabel?: string;
}) {
  const [showBack, setShowBack] = useState(false);
  const [midFlip, setMidFlip]   = useState(false);
  const hasChain = (chain?.length ?? 0) > 0;
  const flip = () => { setMidFlip(true); setTimeout(() => { setShowBack((s) => !s); setMidFlip(false); }, 160); };
  if (!implication && !hasChain) return null;
  return (
    <div>
      <div style={{ height: 1, background: `${accent}25`, margin: "14px 0" }} />
      <div style={{ transition: "transform 0.16s ease-in, opacity 0.16s", transform: midFlip ? "scaleX(0)" : "scaleX(1)", opacity: midFlip ? 0 : 1, transformOrigin: "center" }}>
        {!showBack ? (
          <div style={{ background: `${accent}0D`, border: `1px solid ${accent}30`, borderRadius: 8, padding: "12px 14px" }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: accent, marginBottom: 6 }}>{frontLabel}</p>
            <p style={{ fontSize: 14, color: "var(--font)", lineHeight: 1.65 }}>{implication}</p>
            {hasChain && (
              <button onClick={flip} className="flex items-center gap-1.5 text-xs font-semibold mt-3"
                style={{ color: "var(--font-muted)", background: "none", border: "none", padding: 0, cursor: "pointer" }}>
                <span style={{ fontSize: 11 }}>↺</span> Why — the chain
              </button>)}
          </div>
        ) : (
          <div>
            <p style={{ fontSize: 12, fontWeight: 700, color: accent, marginBottom: 8 }}>Why — the chain</p>
            <ol className="flex flex-col gap-2" style={{ paddingLeft: 0, listStyle: "none", margin: 0 }}>
              {chain!.map((step, i) => (
                <li key={i} className="flex gap-2" style={{ lineHeight: 1.6 }}>
                  <span className="flex-shrink-0 font-bold" style={{ color: accent, minWidth: 16, fontSize: 14 }}>{i + 1}.</span>
                  <span style={{ fontSize: 14, color: "var(--font)" }}>{step}</span>
                </li>))}
            </ol>
            <button onClick={flip} className="flex items-center gap-1.5 text-xs font-semibold mt-3"
              style={{ color: "var(--font-muted)", background: "none", border: "none", padding: 0, cursor: "pointer" }}>
              <span style={{ fontSize: 11 }}>↺</span> Back
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

// ── Card (opportunity + cross-system, unified) ──────────────────────────────

function OppCard({ item, charts }: { item: Item; charts: ResolvedChart[] }) {
  const isCross = item.scope === "cross_source";
  const isRisk  = item.tier === "risk";
  const accent  = isCross ? OPP_COLOR : isRisk ? RISK_COLOR : STATUS_META[item.status].color;
  return (
    <div style={{
      background: "var(--bg-card)", border: `1px solid ${isCross ? OPP_COLOR : isRisk ? `${RISK_COLOR}55` : "var(--border-card)"}`,
      borderLeft: `4px solid ${accent}`, borderRadius: 10, marginBottom: 20, overflow: "hidden",
      ...(isCross ? { background: `linear-gradient(135deg, ${OPP_COLOR}0A, transparent 55%)` } : {}),
    }}>
      <div className="grid grid-cols-1 sm:grid-cols-[45fr_55fr]" style={{ alignItems: "start" }}>
        {/* Text */}
        <div style={{ padding: "20px 24px", borderRight: charts.length ? "1px solid var(--border-card)" : undefined }}>
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <StatusPill status={item.status} />
            {isRisk && (
              <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em",
                color: "#fff", background: RISK_COLOR, borderRadius: 4, padding: "2px 8px" }}>
                ⚠ Risk
              </span>
            )}
            {isCross ? (
              <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.06em",
                color: "#fff", background: "linear-gradient(90deg,#4e8ef7,#2ca02c)", borderRadius: 4, padding: "2px 8px" }}>
                ✦ {item.badge ?? "Cross-system"}
              </span>
            ) : (
              <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em",
                color: "#fff", background: PIPELINE_COLOR[item.pipeline ?? "sibc"] ?? OPP_COLOR, borderRadius: 4, padding: "2px 8px" }}>
                {PIPELINE_LABEL[item.pipeline ?? ""] ?? item.pipeline}
              </span>
            )}
            {item.section?.title && (
              <span style={{ fontSize: 13, color: "var(--font-muted)" }}>{item.section.icon} {item.section.title}</span>
            )}
          </div>
          <h3 className="text-base font-bold leading-snug mb-3" style={{ color: "var(--font)" }}>{item.title}</h3>
          <p style={{ fontSize: 14, color: "var(--font)", lineHeight: 1.65 }}>{item.body}</p>
          <FlipZone implication={item.implication} chain={item.chain}
            accent={isRisk ? RISK_COLOR : OPP_COLOR} frontLabel={isRisk ? "Why it matters" : "For lenders"} />
        </div>

        {/* Charts (1 for opportunities, 2 for cross-system) */}
        {charts.length > 0 && (
          <div style={{ padding: "20px 20px 16px", display: "flex", flexDirection: "column", gap: 18 }}>
            {charts.map((c) => (
              <div key={c.key}>
                {c.caption && (
                  <p style={{ fontSize: 12, fontWeight: 700, color: "var(--font-muted)", marginBottom: 6 }}>{c.caption}</p>
                )}
                <ChartPanel slice={c.slice} sectionId={c.key}
                  highlightConfig={c.highlight.length ? { highlight: c.highlight } : null} />
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function OpportunitiesPage() {
  const [feed, setFeed]     = useState<Feed | null>(null);
  const [charts, setCharts] = useState<SectionChartMap | null>(null);
  const [pf, setPf]         = useState<PipelineFilter>("all");
  const [sf, setSf]         = useState<StatusFilter>("live");

  useEffect(() => {
    Promise.all([
      fetch("/data/opportunities_feed.json").then((r) => r.json() as Promise<Feed>),
      loadSectionChartMap(),
    ]).then(([f, c]) => { setFeed(f); setCharts(c); });
  }, []);

  if (!feed) {
    return <div className="flex items-center justify-center min-h-[60vh] text-sm" style={{ color: "var(--font-muted)" }}>Loading opportunities…</div>;
  }

  const resolve = (item: Item): ResolvedChart[] => {
    const out: ResolvedChart[] = [];
    (item.charts ?? []).forEach((c, i) => {
      const slice = charts?.get(chartKey(c.pipeline, c.section));
      if (slice) out.push({ slice, highlight: c.highlight, caption: c.caption, key: `${item.id}-${i}` });
    });
    return out;
  };

  const statusOk = (s: Status) =>
    sf === "all" ? true : sf === "live" ? (s === "active" || s === "watch") : s === sf;

  const allOpps = (["sibc", "atm_pos"] as Pipeline[])
    .flatMap((p) => feed.pipelines[p] ?? [])
    .filter((o) => o.tier === "opportunity" && o.status !== "retired");
  const sibcN = allOpps.filter((o) => o.pipeline === "sibc").length;
  const atmN  = allOpps.filter((o) => o.pipeline === "atm_pos").length;
  const period = feed._meta.periods.sibc ?? "";

  const allRisks = (["sibc", "atm_pos"] as Pipeline[])
    .flatMap((p) => feed.pipelines[p] ?? [])
    .filter((o) => o.tier === "risk" && o.status !== "retired");

  const crossVisible = feed.cross_system.filter((c) => statusOk(c.status));
  const visible = (pf === "all" ? allOpps : allOpps.filter((o) => o.pipeline === pf)).filter((o) => statusOk(o.status));
  const visibleRisks = (pf === "all" ? allRisks : allRisks.filter((o) => o.pipeline === pf)).filter((o) => statusOk(o.status));

  const renderPipeline = (p: Pipeline) => {
    const opps  = visible.filter((o) => o.pipeline === p);
    const risks = visibleRisks.filter((o) => o.pipeline === p);
    if (opps.length === 0 && risks.length === 0) return null;
    return (
      <div key={p} style={{ marginBottom: 12 }}>
        <div className="flex items-center gap-2" style={{ margin: "8px 0 14px" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: PIPELINE_COLOR[p] }}>
            {PIPELINE_LABEL[p]} ({p === "sibc" ? "SIBC" : "ATM/POS"})
          </span>
          <div style={{ flex: 1, height: 1, background: "var(--border-card)" }} />
          <span style={{ fontSize: 12, color: "var(--font-muted)" }}>
            {opps.filter((o) => o.status === "active").length} active
            {risks.length > 0 && ` · ${risks.length} risk${risks.length === 1 ? "" : "s"}`}
          </span>
        </div>
        {opps.map((o) => <OppCard key={o.id} item={o} charts={resolve(o)} />)}
        {risks.length > 0 && (
          <div style={{ margin: "4px 0 10px" }}>
            <div className="flex items-center gap-2" style={{ marginBottom: 10 }}>
              <span style={{ fontSize: 12, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em", color: RISK_COLOR }}>
                ⚠ Risks &amp; watch-outs
              </span>
              <div style={{ flex: 1, height: 1, background: `${RISK_COLOR}25` }} />
            </div>
            {risks.map((o) => <OppCard key={o.id} item={o} charts={resolve(o)} />)}
          </div>
        )}
      </div>
    );
  };

  return (
    <main className="max-w-7xl mx-auto px-4 py-8">
      <div className="mb-6">
        <div className="flex items-baseline gap-3 flex-wrap">
          <h1 className="text-2xl font-bold" style={{ color: "var(--font)" }}>Opportunities</h1>
          {period && <span style={{ fontSize: 13, color: "var(--font-muted)" }}>⟳ {period}</span>}
        </div>
        <p className="text-sm mt-1" style={{ color: "var(--font-muted)" }}>
          Live openings &amp; risks derived from the causal model · re-evaluated each ingestion.
        </p>
      </div>

      {/* Filters */}
      <div className="flex gap-4 mb-7 flex-wrap items-center">
        <div className="flex gap-2 flex-wrap">
          <button style={BTN_FILTER(pf === "all")} onClick={() => setPf("all")}>All {allOpps.length}</button>
          <button style={BTN_FILTER(pf === "sibc")} onClick={() => setPf("sibc")}>📊 Credit {sibcN}</button>
          {atmN > 0 && <button style={BTN_FILTER(pf === "atm_pos")} onClick={() => setPf("atm_pos")}>💳 Payments {atmN}</button>}
        </div>
        <div className="hidden sm:block" style={DIVIDER} />
        <div className="flex gap-2 flex-wrap text-xs items-center">
          <span style={{ color: "var(--font-muted)" }}>Status:</span>
          {(["live", "active", "watch", "all"] as StatusFilter[]).map((s) => (
            <button key={s} style={BTN_CTRL(sf === s)} onClick={() => setSf(s)}>
              {s === "live" ? "Live" : s[0].toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {/* Cross-system signals (premium) */}
      {pf === "all" && crossVisible.length > 0 && (
        <div style={{ marginBottom: 22 }}>
          <div className="flex items-center gap-2" style={{ marginBottom: 12, flexWrap: "wrap" }}>
            <span style={{ fontSize: 12, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.07em", color: OPP_COLOR }}>
              ✦ Cross-system signals
            </span>
            <span style={{ fontSize: 12, color: "var(--font-muted)" }}>only by composing pipelines</span>
          </div>
          {crossVisible.map((c) => <OppCard key={c.id} item={c} charts={resolve(c)} />)}
        </div>
      )}

      {/* Per-pipeline cards */}
      {visible.length === 0 && visibleRisks.length === 0 && crossVisible.length === 0 ? (
        <p style={{ color: "var(--font-muted)", fontSize: 14 }}>No opportunities for this filter.</p>
      ) : (
        (pf === "all" ? (["sibc", "atm_pos"] as Pipeline[]) : [pf as Pipeline]).map(renderPipeline)
      )}

      <footer className="mt-10 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
        Derived from the India Credit Lens causal model (S3) · status updates each ingestion
      </footer>
    </main>
  );
}
