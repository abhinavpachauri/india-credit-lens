"use client";

import { useEffect, useState } from "react";
import { loadAtmPosData }    from "@/lib/atm_pos_data";
import { loadAtmPosInsights } from "@/lib/atm_pos_insights";
import { loadPlanes, type PlanesMap } from "@/lib/planes";
import { useAppShell }       from "@/components/AppShell";
import AtmPosGroupSection    from "@/components/AtmPosGroupSection";
import AtmReadMode           from "@/components/read/AtmReadMode";
import ModeToggle            from "@/components/read/ModeToggle";
import { usePersistent }     from "@/hooks/usePersistent";
import NewsletterCTA         from "@/components/NewsletterCTA";
import type { AtmPosSeries }   from "@/lib/atm_pos_data";
import type { AtmPosInsight }  from "@/lib/atm_pos_insights";

const GROUPS = ["cc", "dc", "infra"] as const;

// "2026-05-31" → "May 2026" — the data's own latest period, never a hardcoded label.
function latestMonthLabel(s: AtmPosSeries): string {
  const iso = s._meta.periods[s._meta.periods.length - 1];
  if (!iso) return "";
  const d = new Date(`${iso}T00:00:00Z`);
  return d.toLocaleString("en-US", { month: "short", year: "numeric", timeZone: "UTC" });
}

export default function PaymentsPage() {
  const { setHeaderMetric } = useAppShell();
  const [series, setSeries]     = useState<AtmPosSeries | null>(null);
  const [insights, setInsights] = useState<AtmPosInsight[]>([]);
  const [planes, setPlanes]     = useState<PlanesMap>({});
  const [mode, setMode] = usePersistent<"read" | "explore">("icl-mode", "read");

  useEffect(() => {
    loadAtmPosData().then((s) => {
      setSeries(s);
      setHeaderMetric(null, latestMonthLabel(s));
    });
    loadAtmPosInsights().then(setInsights);
    loadPlanes("atm_pos").then(setPlanes);
  }, [setHeaderMetric]);

  if (!series) {
    return (
      <div className="flex items-center justify-center min-h-[60vh] text-sm" style={{ color: "var(--font-muted)" }}>
        Loading data…
      </div>
    );
  }

  // Read mode uses a wider shell (two panes need the room, §14.1); Explore stays a single column.
  const shell = mode === "read" ? "max-w-[1440px] px-6" : "max-w-6xl px-3 sm:px-4";

  return (
    <main className={`${shell} mx-auto py-6`}>
      <ModeToggle mode={mode} setMode={setMode} />

      {mode === "read" && insights.length > 0 ? (
        <AtmReadMode series={series} insights={insights} planes={planes} />
      ) : (
        GROUPS.map((group) => <AtmPosGroupSection key={group} group={group} series={series} />)
      )}

      <div className="mt-10 mb-2">
        <NewsletterCTA variant="banner" />
      </div>

      <footer className="mt-6 pb-8 text-center text-xs" style={{ color: "var(--font-muted)" }}>
        Source: Reserve Bank of India · ATM / POS Card Statistics · Latest: {latestMonthLabel(series)}
      </footer>
    </main>
  );
}
