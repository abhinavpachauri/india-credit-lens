"use client";

import { useEffect, useState } from "react";
import { loadReport }           from "@/lib/reports/rbi_sibc";
import { loadPlanes, type PlanesMap } from "@/lib/planes";
import { useAppShell }          from "@/components/AppShell";
import SectionWithAnnotations   from "@/components/SectionWithAnnotations";
import SibcReadMode             from "@/components/read/SibcReadMode";
import ModeToggle               from "@/components/read/ModeToggle";
import { usePersistent }        from "@/hooks/usePersistent";
import type { Report }          from "@/lib/types";

export default function Dashboard() {
  const { setHeaderMetric } = useAppShell();
  const [report, setReport] = useState<Report | null>(null);
  const [planes, setPlanes] = useState<PlanesMap>({});
  const [mode, setMode] = usePersistent<"read" | "explore">("icl-mode", "read");

  useEffect(() => {
    loadReport().then((r) => {
      setReport(r);
      setHeaderMetric(r.totalBankCredit, r.latestDate);
    });
    loadPlanes("sibc").then(setPlanes);
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

  // Read mode uses a wider shell (two panes need the room, §14.1); Explore stays a single column.
  const shell = mode === "read" ? "max-w-[1440px] px-6" : "max-w-5xl px-4";

  return (
    <main className={`${shell} mx-auto py-6`}>
      <ModeToggle mode={mode} setMode={setMode} />

      {mode === "read" ? (
        <SibcReadMode report={report} planes={planes} />
      ) : (
        report.sections.map((section) => (
          <SectionWithAnnotations key={section.id} section={section} />
        ))
      )}

      <footer className="mt-10 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
        <p>
          Source: {report.source} · Values in ₹ Crore ·
          Latest data: <strong>{report.latestDate}</strong>
        </p>
      </footer>
    </main>
  );
}
