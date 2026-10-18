export type PersonaId = "analyst" | "casual" | "newcomer";
export type Language = "en" | "sw";
export type Register = "formal" | "casual" | "simple";
export type MomentSource = "fixture" | "live";

export interface Player {
  id: string;
  name: string;
  number: number;
  position: string;
}

export interface Team {
  code: string;
  name: string;
  players: Player[];
}

export interface MatchMeta {
  id: string;
  competition?: string;
  venue?: string;
  home: Team;
  away: Team;
  score_ht: [number, number];
  score_ft: [number, number];
}

export interface MatchEvent {
  id: string;
  t: string;
  period: number;
  type: string;
  team: string;
  player: string | null;
  location: [number, number] | null;
  outcome: string | null;
}

export interface Moment {
  id: string;
  match_id: string;
  type: string;
  t_start: string;
  t_end: string;
  t_peak: string;
  team: string;
  headline: { en: string };
  significance: number;
  event_ids: string[];
  stats: Record<string, unknown>;
  entities?: Record<string, unknown>;
}

export interface Narrative {
  moment_id: string;
  text: string;
  language: Language;
  persona: PersonaId;
  register: Register;
  event_ids: string[];
  stats_used: Record<string, unknown>;
  lexicon_terms: string[];
}

export interface QaResult {
  status: "pass" | "flag";
  reasons: string[];
}

export interface VerificationSummary {
  approved: number;
  corrected: { metric: string; claimed: unknown; corrected_value: unknown }[];
  blocked: string[];
}

/** Daniel's TemplateExplainer output, verified for the Why? panel. */
export interface ExplanationClaimDecision {
  moment_id: string;
  metric: string;
  claimed: unknown;
  event_ids: string[];
  recomputed: unknown;
  status: "approved" | "corrected" | "blocked";
  reason: string;
  sentence?: string;
  claim_id?: string;
  corrected_value?: unknown;
  checker?: string;
}

export interface ExplanationPackage {
  schema_version: string;
  match_id: string;
  moment_id: string;
  summary_en: string;
  claims: {
    id: string;
    metric: string;
    value: unknown;
    sentence: string;
    event_ids: string[];
  }[];
  verifications: ExplanationClaimDecision[];
  summary: { approved: number; corrected: number; blocked: number };
  explainer: string;
}

export interface Narration {
  narrative: Narrative;
  qa: QaResult;
  verification?: VerificationSummary;
  /** Present when API/cached bundle includes Daniel's explainer. */
  explanation?: ExplanationPackage;
}

export interface NarrateRequest {
  momentId: string;
  persona: PersonaId;
  language: Language;
  register: Register | null;
}

export interface MatchData {
  match: MatchMeta;
  events: MatchEvent[];
  moments: Moment[];
  momentSource: MomentSource;
}

export type SourceKind = "fixtures" | "api" | "cached";

export interface DataSource {
  kind: SourceKind;
  label: string;
  loadMatch(): Promise<MatchData>;
  /** Returns null when narration is not available for this source. */
  narrate(req: NarrateRequest): Promise<Narration | null>;
}
