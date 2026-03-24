"use client";

import { useEffect, useState, useCallback } from "react";
import { loadReport }    from "@/lib/reports/rbi_sibc";
import { SEC_COLORS }    from "@/lib/theme";
import { formatDate }    from "@/lib/data";
import Header            from "@/components/Header";
import TabBar, { TabId } from "@/components/TabBar";
import SectionCard       from "@/components/SectionCard";
import TrendChart        from "@/components/TrendChart";
import DistributionChart from "@/components/DistributionChart";
import IndustryFilter    from "@/components/IndustryFilter";
import type { Report, ReportSection } from "@/lib/types";

export default function Dashboard() {
  const [report, setReport]               = useState<Report | null>(null);
  const [tab, setTab]                     = useState<TabId>("trend");
  const [dark, setDark]                   = useState(false);
  const [visibleIndustries, setVisible]   = useState<string[]>([]);

  // Dark mode persistence
  useEffect(() => {
    const saved = localStorage.getItem("icl-dark");
    if (saved === "true") setDark(true);
  }, []);

  const toggleDark = () =>
    setDark((d) => {
      localStorage.setItem("icl-dark", String(!d));
      return !d;
    });

  // Load report data
  useEffect(() => {
    loadReport().then(setReport);
  }, []);

  // Stable callback for IndustryFilter
  const onFilteredSeries = useCallback((names: string[]) => setVisible(names), []);

  if (!report) {
    return (
      <div
        className="flex items-center justify-center min-h-screen text-sm"
        style={{ color: "var(--font-muted)" }}
      >
        Loading data…
      </div>
    );
  }

  // ── Chart renderer ──────────────────────────────────────────────────────────
  function renderChart(section: ReportSection, visibleSeries?: string[]) {
    return tab === "trend" ? (
      <TrendChart
        absoluteData={section.absoluteData}
        growthData={section.growthData}
        seriesNames={section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visibleSeries}
      />
    ) : (
      <DistributionChart
        absoluteData={section.absoluteData}
        seriesNames={section.seriesNames}
        pctLabel={section.pctLabel}
        visibleSeries={visibleSeries}
      />
    );
  }

  return (
    <div data-dark={dark} style={{ background: "var(--bg-page)", minHeight: "100vh" }}>
      <Header
        totalBankCredit={report.totalBankCredit}
        latestDate={report.latestDate}
        darkMode={dark}
        onToggleDark={toggleDark}
      />

      <TabBar active={tab} onChange={setTab} />

      <main className="max-w-5xl mx-auto px-4 py-6">
        {report.sections.map((section) => (
          <SectionCard
            key={section.id}
            title={section.title}
            icon={section.icon}
            accentColor={SEC_COLORS[section.accentIndex]}
          >
            {section.filterable ? (
              <>
                <IndustryFilter
                  absoluteData={section.absoluteData}
                  seriesNames={section.seriesNames}
                  onFilteredSeries={onFilteredSeries}
                />
                {visibleIndustries.length > 0 &&
                  renderChart(section, visibleIndustries)}
              </>
            ) : (
              renderChart(section)
            )}
          </SectionCard>
        ))}

        <footer className="mt-8 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
          <p>
            Source: {report.source} · Values in ₹ Crore ·
            Latest data: <strong>{report.latestDate}</strong>
          </p>
          <p className="mt-1">
            <span className="font-semibold" style={{ color: "#4e8ef7" }}>
              India Credit Lens
            </span>
            {" "}— More reports coming soon
          </p>
        </footer>
      </main>
    </div>
  );
}
