import type { Language, PersonaId, Register } from "./types";

export const MOMENT_TYPE_LABELS: Record<string, Record<Language, string>> = {
  pressure_spell: { en: "Pressure spell", sw: "Presha ya juu" },
  shot_after_turnovers: { en: "Shot after turnovers", sw: "Shuti baada ya kunyang'anya mpira" },
  momentum_swing: { en: "Momentum swing", sw: "Mwelekeo wa mchezo" },
  goal: { en: "Goal", sw: "Bao" },
  player_milestone: { en: "Player milestone", sw: "Hatua muhimu" },
};

export function momentTypeLabel(type: string, language: Language): string {
  return MOMENT_TYPE_LABELS[type]?.[language] ?? type;
}

export const PERSONA_OPTIONS: { id: PersonaId; label: string; hint: string }[] = [
  { id: "analyst", label: "Analyst", hint: "Counts, windows and zones" },
  { id: "casual", label: "Casual fan", hint: "The story, not the stats sheet" },
  { id: "newcomer", label: "Newcomer", hint: "Plain words plus the key term explained" },
];

export const LANGUAGE_OPTIONS: { id: Language; label: string }[] = [
  { id: "en", label: "English" },
  { id: "sw", label: "Kiswahili" },
];

export const REGISTER_OPTIONS: { id: Register | "auto"; label: string }[] = [
  { id: "auto", label: "Persona default" },
  { id: "formal", label: "Formal broadcast" },
  { id: "casual", label: "Casual banter" },
  { id: "simple", label: "Simple explainer" },
];
