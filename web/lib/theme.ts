// ── India Credit Lens — Theme & Colour System ─────────────────────────────────
// Mirrors the Streamlit dashboard palette exactly

export const LIGHT_THEME = {
  bgPage:   "#faf6ef",
  bgCard:   "#fffcf5",
  border:   "#e4d9c8",
  shadow:   "rgba(120,90,40,0.08)",
  grid:     "#e8ddd0",
  font:     "#2c1e0f",
  fontMuted:"#7a6a55",
};

export const DARK_THEME = {
  bgPage:   "#0e1117",
  bgCard:   "#141728",
  border:   "#2a2f4a",
  shadow:   "rgba(0,0,0,0.4)",
  grid:     "#1e2240",
  font:     "#c8cfe8",
  fontMuted:"#7a85aa",
};

// Named colours for the 7 core sector labels
export const NAMED_COLORS: Record<string, string> = {
  "Bank Credit":          "#1f77b4",
  "Food Credit":          "#aec7e8",
  "Non-food Credit":      "#17becf",
  "Agriculture":          "#2ca02c",
  "Industry":             "#d62728",
  "Services":             "#9467bd",
  "Personal Loans":       "#ff7f0e",
};

// Accent colour per section card (left border + header tint)
export const SEC_COLORS = [
  "#4e8ef7",   // 0 Bank Credit
  "#2ca02c",   // 1 Main Sectors
  "#e05c5c",   // 2 Industry by Size
  "#a87fdb",   // 3 Services
  "#f0912a",   // 4 Personal Loans
  "#e8b94f",   // 5 Priority Sector
  "#2ec4b6",   // 6 Industry by Type
];

// Plotly D3 fallback palette — used for dynamic sub-sector lists
export const D3_PALETTE = [
  "#1f77b4","#ff7f0e","#2ca02c","#d62728","#9467bd",
  "#8c564b","#e377c2","#7f7f7f","#bcbd22","#17becf",
  "#aec7e8","#ffbb78","#98df8a","#ff9896","#c5b0d5",
  "#c49c94","#f7b6d2","#c7c7c7","#dbdb8d","#9edae5",
];

export function pickColor(label: string, index: number): string {
  return NAMED_COLORS[label] ?? D3_PALETTE[index % D3_PALETTE.length];
}
