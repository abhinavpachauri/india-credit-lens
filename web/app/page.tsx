"use client";

import { useEffect, useState, useMemo, useCallback } from "react";
import {
  loadData, CreditRow, childrenOf, latestValue,
  formatCr, formatDate, uniqueDates, rowsForCodes,
} from "@/lib/data";
import { SEC_COLORS } from "@/lib/theme";
import { SECTION_META } from "@/lib/insights";
import Header from "@/components/Header";
import TabBar, { TabId } from "@/components/TabBar";
import SectionCard from "@/components/SectionCard";
import TrendChart from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";
import IndustryFilter from "@/components/IndustryFilter";

// ── Static section definitions ────────────────────────────────────────────────
const SECTIONS_DEF = [
  {
    title: "Bank Credit",      icon: "🏦",
    codes: ["I", "II", "III"],
    labels: { I: "Bank Credit", II: "Food Credit", III: "Non-food Credit" },
    pctLabel: "% of Bank Credit",
    dataOpts: { psl: false },
  },
  {
    title: "Main Sectors",     icon: "📊",
    codes: ["1", "2", "3", "4"],
    labels: { "1": "Agriculture", "2": "Industry", "3": "Services", "4": "Personal Loans" },
    pctLabel: "% Share",
    dataOpts: { psl: false },
  },
];

export default function Dashboard() {
  const [rows, setRows]       = useState<CreditRow[]>([]);
  const [tab, setTab]         = useState<TabId>("trend");
  const [dark, setDark]       = useState(false);
  const [industry7, setIndustry7] = useState<string[]>([]);

  // Load dark mode preference
  useEffect(() => {
    const saved = localStorage.getItem("icl-dark");
    if (saved === "true") setDark(true);
  }, []);

  const toggleDark = () => {
    setDark((d) => {
      localStorage.setItem("icl-dark", String(!d));
      return !d;
    });
  };

  // Load CSV data
  useEffect(() => {
    loadData().then(setRows);
  }, []);

  // ── Derived section data (computed once from rows) ─────────────────────────
  const sec3 = useMemo(() => childrenOf(rows, "2"), [rows]);           // Industry by Size
  const sec4 = useMemo(() => childrenOf(rows, "3"), [rows]);           // Services
  const sec5 = useMemo(() => childrenOf(rows, "4"), [rows]);           // Personal Loans
  const sec7 = useMemo(() => childrenOf(rows, "2", { stmt: "Statement 2" }), [rows]); // Industry by Type

  // Priority sector
  const pslRows  = useMemo(() => rows.filter((r) => r.is_priority_sector_memo), [rows]);
  const pslCodes = useMemo(() => [...new Set(pslRows.map((r) => r.code))].sort(), [pslRows]);
  const pslLabels = useMemo(() => {
    const m: Record<string, string> = {};
    pslRows.forEach((r) => { m[r.code] = r.sector; });
    return m;
  }, [pslRows]);

  // Header metric
  const dates     = useMemo(() => uniqueDates(rows), [rows]);
  const latestDt  = dates[dates.length - 1] ?? "";
  const totalCredit = useMemo(() => latestValue(rows, "I"), [rows]);

  // Stable data opts objects — prevent new object refs on every render
  const sec7DataOpts = useMemo(() => ({ stmt: "Statement 2" as const }), []);
  const pslDataOpts  = useMemo(() => ({ psl: true  as const }), []);

  // Dynamic section 7 filter callback
  const onFilteredCodes = useCallback((codes: string[]) => setIndustry7(codes), []);

  if (!rows.length) {
    return (
      <div
        className="flex items-center justify-center min-h-screen text-sm"
        style={{ color: "var(--font-muted)" }}
      >
        Loading data…
      </div>
    );
  }

  // ── Chart renderer helper ──────────────────────────────────────────────────
  const renderChart = (
    codes: string[],
    labels: Record<string, string>,
    pctLabel: string,
    dataOpts: { psl?: boolean; stmt?: string } = {},
    sectionKey?: string,
  ) => {
    const meta = sectionKey ? SECTION_META[sectionKey] : undefined;
    return tab === "trend" ? (
      <TrendChart
        rows={rows} codes={codes} labels={labels} pctLabel={pctLabel} dataOpts={dataOpts}
        annotations={meta?.trendAnnotations}
      />
    ) : (
      <DistributionChart
        rows={rows} codes={codes} labels={labels} pctLabel={pctLabel} dataOpts={dataOpts}
        distAnnotations={meta?.distAnnotations}
      />
    );
  };

  return (
    <div data-dark={dark} style={{ background: "var(--bg-page)", minHeight: "100vh" }}>
      <Header
        totalBankCredit={totalCredit}
        latestDate={formatDate(latestDt)}
        darkMode={dark}
        onToggleDark={toggleDark}
      />

      <TabBar active={tab} onChange={setTab} />

      <main className="max-w-5xl mx-auto px-4 py-6">
        {/* Section 1 – Bank Credit */}
        <SectionCard title="Bank Credit" icon="🏦" accentColor={SEC_COLORS[0]} insights={SECTION_META.bankCredit.insights}>
          {renderChart(
            ["I", "II", "III"],
            { I: "Bank Credit", II: "Food Credit", III: "Non-food Credit" },
            "% of Bank Credit", {}, "bankCredit"
          )}
        </SectionCard>

        {/* Section 2 – Main Sectors */}
        <SectionCard title="Main Sectors" icon="📊" accentColor={SEC_COLORS[1]} insights={SECTION_META.mainSectors.insights}>
          {renderChart(
            ["1", "2", "3", "4"],
            { "1": "Agriculture", "2": "Industry", "3": "Services", "4": "Personal Loans" },
            "% Share", {}, "mainSectors"
          )}
        </SectionCard>

        {/* Section 3 – Industry by Size */}
        {sec3.codes.length > 0 && (
          <SectionCard title="Industry by Size" icon="🏭" accentColor={SEC_COLORS[2]} insights={SECTION_META.industryBySize.insights}>
            {renderChart(sec3.codes, sec3.labels, "% of Industry", {}, "industryBySize")}
          </SectionCard>
        )}

        {/* Section 4 – Services */}
        {sec4.codes.length > 0 && (
          <SectionCard title="Services" icon="🛎️" accentColor={SEC_COLORS[3]} insights={SECTION_META.services.insights}>
            {renderChart(sec4.codes, sec4.labels, "% of Services", {}, "services")}
          </SectionCard>
        )}

        {/* Section 5 – Personal Loans */}
        {sec5.codes.length > 0 && (
          <SectionCard title="Personal Loans" icon="💳" accentColor={SEC_COLORS[4]} insights={SECTION_META.personalLoans.insights}>
            {renderChart(sec5.codes, sec5.labels, "% of Personal Loans", {}, "personalLoans")}
          </SectionCard>
        )}

        {/* Section 6 – Priority Sector */}
        {pslCodes.length > 0 && (
          <SectionCard title="Priority Sector" icon="⭐" accentColor={SEC_COLORS[5]} insights={SECTION_META.prioritySector.insights}>
            {renderChart(pslCodes, pslLabels, "% of Priority Sector", pslDataOpts, "prioritySector")}
          </SectionCard>
        )}

        {/* Section 7 – Industry by Type (filterable) */}
        {sec7.codes.length > 0 && (
          <SectionCard title="Industry by Type" icon="🔩" accentColor={SEC_COLORS[6]} insights={SECTION_META.industryByType.insights}>
            <IndustryFilter
              rows={rows}
              allCodes={sec7.codes}
              labels={sec7.labels}
              dataOpts={sec7DataOpts}
              onFilteredCodes={onFilteredCodes}
            />
            {industry7.length > 0 &&
              renderChart(
                industry7,
                Object.fromEntries(industry7.map((c) => [c, sec7.labels[c] ?? c])),
                "% of Industry",
                sec7DataOpts, "industryByType"
              )}
          </SectionCard>
        )}

        {/* Footer */}
        <footer className="mt-8 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
          <p>
            Source: RBI Sector/Industry-wise Bank Credit (SIBC) Return · Values in ₹ Crore ·
            Latest data: <strong>{formatDate(latestDt)}</strong>
          </p>
          <p className="mt-1">
            <span className="font-semibold" style={{ color: "#4e8ef7" }}>India Credit Lens</span>
            {" "}— More reports coming soon
          </p>
        </footer>
      </main>
    </div>
  );
}
