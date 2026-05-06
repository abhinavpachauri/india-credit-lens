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

/** Visual effect applied to the chart when this annotation is active. */
export interface AnnotationEffect {
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
  title:         string;          // 4–6 words
  body:          string;          // 2–3 sentences
  implication?:  string;          // "For lenders: ..."
  preferredMode?: "absolute" | "yoy" | "fy"; // chart switches to this mode when annotation is active
  effect:        AnnotationEffect;
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
