"use client";

import { useEffect, useState } from "react";
import {
  loadSectionChartMap, chartKey,
} from "@/lib/section-chart-data";
import type { SectionChartMap, SectionChartSlice } from "@/lib/section-chart-data";
import TrendChart        from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";

// ── Derived feed types (web/public/data/opportunities_feed.json) ─────────────

type Pipeline = "sibc" | "atm_pos";
type Status   = "active" | "watch" | "closed" | "retired";

interface FeedItem {
  id: string; pipeline: Pipeline; scope: "pipeline"; tier: "opportunity" | "risk";
  status: Status; authored_status?: string;
  section: { id: string | null; title: string; icon: string };
  title: string; body: string; implication?: string | null;
  chain: string[]; driver?: string | null; via?: string | null; evidence: string[];
  highlight?: string[];
}
interface CrossItem {
  id: string; status: Status; title: string; body: string;
  basis: string; link: string; badge: string;
}
interface Feed {
  cross_system: CrossItem[];
  pipelines: Record<Pipeline, FeedItem[]>;
  _meta: { periods: Record<string, string> };
}

// ── Styles ───────────────────────────────────────────────────────────────────

type PipelineFilter = "all" | Pipeline;
type StatusFilter   = "live" | "active" | "watch" | "all";

const PIPELINE_LABEL: Record<string, string> = { sibc: "Credit", atm_pos: "Payments" };
const PIPELINE_COLOR: Record<string, string> = { sibc: "#4e8ef7", atm_pos: "#2ca02c" };
const OPP_COLOR = "#16A34A";

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

// ── Per-card chart panel (unchanged) ───────────────────────────────────────────

type TabId = "trend" | "distribution";

function ChartPanel({ slice, sectionId, highlightConfig }: {
  slice: SectionChartSlice; sectionId: string;
  highlightConfig?: { highlight: string[] } | null;
}) {
  const [tab, setTab]             = useState<TabId>("trend");
  const [trendMode, setTrendMode] = useState<"absolute" | "yoy" | "fy">("absolute");
  const [distMode, setDistMode]   = useState<"absolute" | "pct">("absolute");
  const isAtm = slice.variant === "atm_pos";
  // payments slice has no YoY/FY — offer Absolute + MoM only
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

function FlipZone({ implication, chain }: { implication?: string | null; chain?: string[] }) {
  const [showBack, setShowBack] = useState(false);
  const [midFlip, setMidFlip]   = useState(false);
  const hasChain = (chain?.length ?? 0) > 0;
  const flip = () => { setMidFlip(true); setTimeout(() => { setShowBack((s) => !s); setMidFlip(false); }, 160); };
  if (!implication && !hasChain) return null;
  return (
    <div>
      <div style={{ height: 1, background: `${OPP_COLOR}25`, margin: "14px 0" }} />
      <div style={{ transition: "transform 0.16s ease-in, opacity 0.16s", transform: midFlip ? "scaleX(0)" : "scaleX(1)", opacity: midFlip ? 0 : 1, transformOrigin: "center" }}>
        {!showBack ? (
          <div style={{ background: `${OPP_COLOR}0D`, border: `1px solid ${OPP_COLOR}30`, borderRadius: 8, padding: "12px 14px" }}>
            <p style={{ fontSize: 14, fontWeight: 700, color: OPP_COLOR, marginBottom: 6 }}>For lenders</p>
            <p style={{ fontSize: 14, color: "var(--font)", lineHeight: 1.65 }}>{implication}</p>
            {hasChain && (
              <button onClick={flip} className="flex items-center gap-1.5 text-xs font-semibold mt-3"
                style={{ color: "var(--font-muted)", background: "none", border: "none", padding: 0, cursor: "pointer" }}>
                <span style={{ fontSize: 11 }}>↺</span> Causal chain
              </button>)}
          </div>
        ) : (
          <div>
            <p style={{ fontSize: 12, fontWeight: 700, color: OPP_COLOR, marginBottom: 8 }}>Causal chain</p>
            <ol className="flex flex-col gap-2" style={{ paddingLeft: 0, listStyle: "none", margin: 0 }}>
              {chain!.map((step, i) => (
                <li key={i} className="flex gap-2" style={{ lineHeight: 1.6 }}>
                  <span className="flex-shrink-0 font-bold" style={{ color: OPP_COLOR, minWidth: 16, fontSize: 14 }}>{i + 1}.</span>
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

// ── Cross-system premium band ───────────────────────────────────────────────

function CrossBand({ items }: { items: CrossItem[] }) {
  if (items.length === 0) return null;
  return (
    <div style={{
      border: `1.5px solid ${OPP_COLOR}`, borderRadius: 12, padding: "16px 20px", marginBottom: 28,
      background: `linear-gradient(135deg, ${OPP_COLOR}0D, transparent 60%)`,
    }}>
      <div className="flex items-center gap-2 mb-3 flex-wrap">
        <span style={{ fontSize: 11, fontWeight: 800, textTransform: "uppercase", letterSpacing: "0.08em", color: OPP_COLOR }}>
          ✦ Cross-system signals
        </span>
        <span style={{ fontSize: 12, color: "var(--font-muted)" }}>premium · only by composing pipelines</span>
      </div>
      {items.map((c) => (
        <div key={c.id} style={{ marginTop: 4 }}>
          <div className="flex items-center gap-2 mb-1 flex-wrap">
            <StatusPill status={c.status} />
            <h3 className="text-base font-bold leading-snug" style={{ color: "var(--font)" }}>{c.title}</h3>
          </div>
          <p style={{ fontSize: 14, color: "var(--font)", lineHeight: 1.65, marginBottom: 6 }}>{c.body}</p>
          <p style={{ fontSize: 12, color: "var(--font-muted)", fontFamily: "var(--font-mono, monospace)" }}>
            basis: {c.basis}
          </p>
          <span style={{ display: "inline-block", marginTop: 6, fontSize: 11, fontWeight: 700, color: "#fff",
            background: "linear-gradient(90deg,#4e8ef7,#2ca02c)", borderRadius: 4, padding: "2px 8px" }}>
            {c.badge}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Opportunity card ────────────────────────────────────────────────────────

function MetaRow({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex gap-2" style={{ fontSize: 13, lineHeight: 1.55, marginTop: 4 }}>
      <span style={{ color: "var(--font-muted)", minWidth: 48, fontWeight: 600 }}>{k}</span>
      <span style={{ color: "var(--font)" }}>{v}</span>
    </div>
  );
}

function OpportunityCard({ item, chartSlice }: { item: FeedItem; chartSlice: SectionChartSlice | null }) {
  return (
    <div style={{
      background: "var(--bg-card)", border: "1px solid var(--border-card)",
      borderLeft: `4px solid ${STATUS_META[item.status].color}`, borderRadius: 10, marginBottom: 20, overflow: "hidden",
    }}>
      <div className="grid grid-cols-1 sm:grid-cols-[45fr_55fr]" style={{ alignItems: "start" }}>
        <div style={{ padding: "20px 24px", borderRight: chartSlice ? "1px solid var(--border-card)" : undefined }}>
          {/* Badges + status */}
          <div className="flex items-center gap-2 mb-3 flex-wrap">
            <StatusPill status={item.status} />
            <span style={{ fontSize: 11, fontWeight: 700, textTransform: "uppercase", letterSpacing: "0.06em",
              color: "#fff", background: PIPELINE_COLOR[item.pipeline] ?? OPP_COLOR, borderRadius: 4, padding: "2px 8px" }}>
              {PIPELINE_LABEL[item.pipeline] ?? item.pipeline}
            </span>
            {item.section.title && (
              <span style={{ fontSize: 13, color: "var(--font-muted)" }}>{item.section.icon} {item.section.title}</span>
            )}
          </div>
          <h3 className="text-base font-bold leading-snug mb-3" style={{ color: "var(--font)" }}>{item.title}</h3>
          <p style={{ fontSize: 14, color: "var(--font)", lineHeight: 1.65, marginBottom: 10 }}>{item.body}</p>

          {/* Driver / via / evidence */}
          {item.driver && <MetaRow k="driver" v={item.driver} />}
          {item.via && <MetaRow k="via" v={item.via} />}
          {item.evidence.length > 0 && (
            <div className="flex gap-2 flex-wrap" style={{ marginTop: 8, alignItems: "center" }}>
              <span style={{ fontSize: 13, color: "var(--font-muted)", fontWeight: 600 }}>▸ evidence</span>
              {item.evidence.map((e) => (
                <span key={e} style={{ fontSize: 11, color: STATUS_META[item.status].color,
                  background: `${STATUS_META[item.status].color}12`, border: `1px solid ${STATUS_META[item.status].color}30`,
                  borderRadius: 4, padding: "1px 7px", fontFamily: "var(--font-mono, monospace)" }}>{e}</span>
              ))}
            </div>
          )}

          <FlipZone implication={item.implication} chain={item.chain} />
        </div>

        {chartSlice && (
          <div style={{ padding: "20px 20px 16px" }}>
            <ChartPanel slice={chartSlice} sectionId={item.section.id!}
              highlightConfig={item.highlight?.length ? { highlight: item.highlight } : null} />
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

  const allOpps: FeedItem[] = (["sibc", "atm_pos"] as Pipeline[])
    .flatMap((p) => feed.pipelines[p] ?? [])
    .filter((o) => o.tier === "opportunity" && o.status !== "retired");

  const byPipeline = pf === "all" ? allOpps : allOpps.filter((o) => o.pipeline === pf);
  const statusOk = (s: Status) =>
    sf === "all" ? true : sf === "live" ? (s === "active" || s === "watch") : s === sf;
  const visible = byPipeline.filter((o) => statusOk(o.status));

  const sibcN = allOpps.filter((o) => o.pipeline === "sibc").length;
  const atmN  = allOpps.filter((o) => o.pipeline === "atm_pos").length;
  const period = feed._meta.periods.sibc ?? "";

  const renderPipeline = (p: Pipeline) => {
    const items = visible.filter((o) => o.pipeline === p);
    if (items.length === 0) return null;
    const activeN = items.filter((o) => o.status === "active").length;
    return (
      <div key={p} style={{ marginBottom: 12 }}>
        <div className="flex items-center gap-2" style={{ margin: "8px 0 14px" }}>
          <span style={{ fontSize: 13, fontWeight: 700, color: PIPELINE_COLOR[p] }}>
            {PIPELINE_LABEL[p]} ({p === "sibc" ? "SIBC" : "ATM/POS"})
          </span>
          <div style={{ flex: 1, height: 1, background: "var(--border-card)" }} />
          <span style={{ fontSize: 12, color: "var(--font-muted)" }}>{activeN} active</span>
        </div>
        {items.map((o) => (
          <OpportunityCard key={o.id} item={o}
            chartSlice={(o.section.id && charts?.get(chartKey(o.pipeline, o.section.id))) || null} />
        ))}
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
          Live openings derived from the causal model · re-evaluated each ingestion.
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

      {/* Cross-system premium band */}
      {(pf === "all") && <CrossBand items={feed.cross_system} />}

      {/* Per-pipeline cards */}
      {visible.length === 0 ? (
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
