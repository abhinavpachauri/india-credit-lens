"use client";

import { useEffect, useState } from "react";
import { loadReport }           from "@/lib/reports/rbi_sibc";
import Header                   from "@/components/Header";
import TabBar, { TabId }        from "@/components/TabBar";
import SectionWithAnnotations   from "@/components/SectionWithAnnotations";
import type { Report }          from "@/lib/types";

export default function Dashboard() {
  const [report, setReport] = useState<Report | null>(null);
  const [tab, setTab]       = useState<TabId>("trend");
  const [dark, setDark]     = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("icl-dark");
    if (saved === "true") setDark(true);
  }, []);

  const toggleDark = () =>
    setDark((d) => {
      localStorage.setItem("icl-dark", String(!d));
      return !d;
    });

  useEffect(() => {
    loadReport().then(setReport);
  }, []);

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
          <SectionWithAnnotations key={section.id} section={section} tab={tab} />
        ))}

        <footer className="mt-8 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
          <p>
            Source: {report.source} · Values in ₹ Crore ·
            Latest data: <strong>{report.latestDate}</strong>
          </p>
          <p className="mt-1">
            <span className="font-semibold" style={{ color: "#4e8ef7" }}>India Credit Lens</span>
            {" "}— More reports coming soon
          </p>
          <p className="mt-3">
            <button
              onClick={() => {
                // Export the processed data model (no annotations) for Claude analysis pipeline
                const exportData = {
                  report:   report.id,
                  source:   report.source,
                  dataDate: report.dataDate,
                  sections: report.sections.map((s) => ({
                    id:           s.id,
                    title:        s.title,
                    seriesNames:  s.seriesNames,
                    absoluteData: s.absoluteData,
                    growthData:   s.growthData,
                    fyData:       s.fyData,
                  })),
                };
                const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: "application/json" });
                const url  = URL.createObjectURL(blob);
                const a    = document.createElement("a");
                a.href     = url;
                a.download = `${report.id}_sections_${report.dataDate}.json`;
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="text-xs underline cursor-pointer"
              style={{ color: "var(--font-muted)" }}
            >
              Export data model
            </button>
          </p>
        </footer>
      </main>
    </div>
  );
}
