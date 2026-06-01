/**
 * Opportunities data layer.
 *
 * Pulls opportunities from both pipelines without loading CSV data.
 * SIBC: imported directly from ANNOTATIONS (static, no fetch needed)
 * ATM/POS: from atm_pos_insights.json (forward-compatible, currently none)
 */

import { ANNOTATIONS } from "@/lib/reports/rbi_sibc";
import { loadAtmPosInsights } from "@/lib/atm_pos_insights";
import type { Annotation } from "@/lib/types";

export interface Opportunity {
  id:           string;
  pipeline:     "sibc" | "atm_pos";
  sectionId:    string;
  sectionTitle: string;
  sectionIcon:  string;
  title:        string;
  body:         string;
  implication?: string;
  basis?:       Annotation["basis"];
}

// Static section metadata — mirrors makeSection calls in rbi_sibc.ts
const SIBC_SECTIONS: { id: string; title: string; icon: string }[] = [
  { id: "bankCredit",    title: "Bank Credit",       icon: "🏦" },
  { id: "mainSectors",   title: "Main Sectors",      icon: "📊" },
  { id: "industryBySize", title: "Industry by Size",  icon: "🏭" },
  { id: "services",      title: "Services",           icon: "🛎️" },
  { id: "personalLoans", title: "Personal Loans",     icon: "💳" },
  { id: "prioritySector", title: "Priority Sector",   icon: "⭐" },
  { id: "industryByType", title: "Industry by Type",  icon: "🔩" },
];

const ATM_GROUP_META: Record<string, { title: string; icon: string }> = {
  cc:    { title: "Credit Cards",   icon: "💳" },
  dc:    { title: "Debit Cards",    icon: "🏧" },
  infra: { title: "Infrastructure", icon: "🏗️" },
};

// ── Loaders ───────────────────────────────────────────────────────────────────

function loadSibcOpportunities(): Opportunity[] {
  const opps: Opportunity[] = [];
  for (const section of SIBC_SECTIONS) {
    const ann = ANNOTATIONS[section.id];
    if (!ann) continue;
    for (const opp of ann.opportunities.filter((a) => !a.hidden)) {
      opps.push({
        id:           opp.id,
        pipeline:     "sibc",
        sectionId:    section.id,
        sectionTitle: section.title,
        sectionIcon:  section.icon,
        title:        opp.title,
        body:         opp.body,
        implication:  opp.implication,
        basis:        opp.basis,
      });
    }
  }
  return opps;
}

async function loadAtmPosOpportunities(): Promise<Opportunity[]> {
  const insights = await loadAtmPosInsights();
  return insights
    .filter((i) => (i.type as string) === "opportunity")
    .map((i) => {
      const meta = ATM_GROUP_META[i.group] ?? { title: i.group, icon: "📊" };
      return {
        id:           i.id,
        pipeline:     "atm_pos" as const,
        sectionId:    i.group,
        sectionTitle: meta.title,
        sectionIcon:  meta.icon,
        title:        i.title,
        body:         i.body,
        implication:  i.implication,
      };
    });
}

export async function loadAllOpportunities(): Promise<Opportunity[]> {
  const [sibc, atmPos] = await Promise.all([
    Promise.resolve(loadSibcOpportunities()),
    loadAtmPosOpportunities(),
  ]);
  return [...sibc, ...atmPos];
}
