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

        {/* Substack embed */}
        <div className="mt-10 mb-2 flex flex-col items-center gap-2">
          <p className="text-sm font-medium" style={{ color: "var(--font-muted)" }}>
            Enjoyed the data? Get the analysis behind it in your inbox
          </p>
          <iframe
            src="https://indiacreditlens.substack.com/embed"
            width="100%"
            height="320"
            style={{
              maxWidth:     "480px",
              border:       "1px solid #EEE",
              background:   "white",
              borderRadius: "0.5rem",
            }}
            frameBorder={0}
            scrolling="no"
          />
        </div>

        <footer className="mt-6 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
          <p>
            Source: {report.source} · Values in ₹ Crore ·
            Latest data: <strong>{report.latestDate}</strong>
          </p>
        </footer>
      </main>
    </div>
  );
}
