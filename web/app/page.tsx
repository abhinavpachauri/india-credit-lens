"use client";

import { useEffect, useState } from "react";
import { loadReport }           from "@/lib/reports/rbi_sibc";
import { useAppShell }          from "@/components/AppShell";
import SectionWithAnnotations   from "@/components/SectionWithAnnotations";
import NewsletterCTA             from "@/components/NewsletterCTA";
import type { Report }          from "@/lib/types";

export default function Dashboard() {
  const { setHeaderMetric } = useAppShell();
  const [report, setReport] = useState<Report | null>(null);

  useEffect(() => {
    loadReport().then((r) => {
      setReport(r);
      setHeaderMetric(r.totalBankCredit, r.latestDate);
    });
  }, [setHeaderMetric]);

  if (!report) {
    return (
      <div
        className="flex items-center justify-center min-h-[60vh] text-sm"
        style={{ color: "var(--font-muted)" }}
      >
        Loading data…
      </div>
    );
  }

  return (
    <main className="max-w-5xl mx-auto px-4 py-6">
      {report.sections.map((section) => (
        <SectionWithAnnotations key={section.id} section={section} />
      ))}

      <div className="mt-10 mb-2">
        <NewsletterCTA variant="banner" />
      </div>

      <footer className="mt-6 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
        <p>
          Source: {report.source} · Values in ₹ Crore ·
          Latest data: <strong>{report.latestDate}</strong>
        </p>
      </footer>
    </main>
  );
}
