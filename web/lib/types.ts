// ── India Credit Lens — Universal Type Contract ───────────────────────────────
// Every report's data layer must produce these types.
// Chart components consume only these types — no report-specific knowledge.

// ── Chart data ────────────────────────────────────────────────────────────────

/** One point on the time axis. Keys beyond "date" are series names → values. */
export interface ChartPoint {
  date: string;
  [seriesName: string]: string | number | null;
}

// ── Annotations ───────────────────────────────────────────────────────────────

/**
 * What a card is a claim about — DASHBOARD_SPEC §15. Emitted by the generator from the
 * signal's own compute spec, so the chart can render the thing the card actually says
 * rather than the nearest series that happens to already be drawn.
 *
 *   level          one entity's own series, or a named set of them
 *   decomposition  the children of `parent_code`
 *   share_of       those children as a share of `denominator`
 *   pair           two named sides, and the gap between them
 */
export interface CardCut {
  shape:        "level" | "decomposition" | "share_of" | "pair";
  codes?:       string[];   // SIBC entity codes a level/pair cut names
  parent_code?: string;
  child_level?: number;
  statement?:   string;
  denominator?: string;
  metrics?:     string[];   // payments: the metrics the claim is made of
  /** A pair's two sides, each named as the card's own prose names it. A side can be a
   *  bundle: "value transacted at POS" is credit-card POS value plus debit-card POS value. */
  sides?:       { label: string; metrics: string[] }[];
}

/** Visual effect applied to the chart when this annotation is active. */
export interface AnnotationEffect {
  cut?:       CardCut;      // §15: what this card is a claim about
  highlight?: string[];     // series names — bold, full opacity
  dim?:       string[];     // series names — faded to 20% opacity
  dash?:      string[];     // series names — dashed stroke
  referenceDot?: {
    x:      string;         // formatted date label matching ChartPoint.date
    series: string;         // series name
    label:  string;         // callout text
  };
  referenceLine?: {
    value: number;
    label: string;
  };
}

export interface AnnotationBasis {
  facts:       string[];   // exact data points from sections.json this rests on
  inferences:  string[];   // analytical steps beyond what the data directly shows
  hypothesis?: string[];   // forward-looking or unverifiable claims in this annotation
}

export interface Annotation {
  id:            string;
  layer?:        1 | 2 | 3;      // 1 = computed from CSV, 2 = causal/regulatory/cross-signal, 3 = strategic
  title:         string;          // 4–6 words
  body:          string;          // 2–3 sentences
  implication?:  string;          // "For lenders: ..."
  preferredMode?: "absolute" | "yoy" | "fy" | "share"; // active annotation switches the chart to this view ("share" → Distribution tab, % share)
  effect:        AnnotationEffect;
  hidden?:       boolean;         // true → suppressed from dashboard (methodology notes, low-signal gaps)
  // ── Explainability fields (optional — populate for any annotation making causal or forward claims) ──
  claim_type?:   "data" | "inference" | "hypothesis"; // highest claim_type in body+implication
  basis?:        AnnotationBasis;                       // structured reasoning chain
}

export interface SectionAnnotations {
  insights:      Annotation[];
  gaps:          Annotation[];
  opportunities: Annotation[];
}

// ── Section ───────────────────────────────────────────────────────────────────

export interface ReportSection {
  id:           string;
  title:        string;
  icon:         string;
  accentIndex:  number;           // index into SEC_COLORS[]
  absoluteData: ChartPoint[];     // ₹ Crore values over time
  growthData:   ChartPoint[];     // YoY % growth over time
  fyData:       ChartPoint[];     // FY-to-date % growth (vs previous March-end)
  seriesNames:             string[];  // ordered list — drives legend + colour assignment in trend view
  distributionSeriesNames?: string[]; // if set, distribution chart uses this list instead of seriesNames
                                      // use when seriesNames includes a "total" series that is the sum
                                      // of the other series (e.g. bankCredit: excludes "Bank Credit" so
                                      // Food Credit + Non-food Credit sum to 100% correctly)
  pctLabel:     string;           // label for the % radio button in distribution view
  filterable?:  boolean;          // true → render with IndustryFilter (large series sets)
  defaultHiddenSeries?: string[]; // trend series off by default in explore mode (e.g. the
                                  // aggregate "Total" — shown but unselected so sub-series keep scale)
  /**
   * One entry per code in this section that RBI breaks down further — DASHBOARD_SPEC §15.6.
   * Keyed by the parent's code, so a card declaring `cut.parent_code` can be charted at the
   * level it is actually about. Precomputed here rather than derived in the view: the section
   * is built once from the CSV and the read surface never sees rows.
   */
  subCuts?:     Record<string, ReportSection>;
  parentLabel?: string;           // set on a sub-cut: what its parent is called on the chart above
  annotations:  SectionAnnotations;
}

// ── Report ────────────────────────────────────────────────────────────────────

export interface Report {
  id:               string;
  title:            string;
  source:           string;
  dataDate:         string;       // raw YYYY-MM-DD
  latestDate:       string;       // formatted for display e.g. "Jan 2026"
  totalBankCredit:  number | null; // headline metric for the header (null if not applicable)
  sections:         ReportSection[];
}
