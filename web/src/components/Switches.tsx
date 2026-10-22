import { LANGUAGE_OPTIONS, PERSONA_OPTIONS, REGISTER_OPTIONS } from "../labels";
import type { Language, PersonaId, Register } from "../types";

interface Props {
  persona: PersonaId;
  language: Language;
  register: Register | "auto";
  onPersona: (p: PersonaId) => void;
  onLanguage: (l: Language) => void;
  onRegister: (r: Register | "auto") => void;
}

export function Switches({ persona, language, register, onPersona, onLanguage, onRegister }: Props) {
  return (
    <section className="switches" aria-label="Viewer settings">
      <p className="switches__kicker">Watch as</p>
      <div className="switches__group">
        <span className="switches__label" id="persona-label">
          Persona
        </span>
        <div className="segmented" role="radiogroup" aria-labelledby="persona-label">
          {PERSONA_OPTIONS.map((p) => (
            <button
              key={p.id}
              type="button"
              role="radio"
              aria-checked={persona === p.id}
              title={p.hint}
              className={persona === p.id ? "segmented__item is-active" : "segmented__item"}
              onClick={() => onPersona(p.id)}
            >
              {p.label}
            </button>
          ))}
        </div>
      </div>
      <div className="switches__group">
        <span className="switches__label" id="language-label">
          Language
        </span>
        <div className="segmented" role="radiogroup" aria-labelledby="language-label">
          {LANGUAGE_OPTIONS.map((l) => (
            <button
              key={l.id}
              type="button"
              role="radio"
              aria-checked={language === l.id}
              className={language === l.id ? "segmented__item is-active" : "segmented__item"}
              onClick={() => onLanguage(l.id)}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>
      <label className="switches__register">
        <span className="switches__label">Register</span>
        <select value={register} onChange={(e) => onRegister(e.target.value as Register | "auto")}>
          {REGISTER_OPTIONS.map((r) => (
            <option key={r.id} value={r.id}>
              {r.label}
            </option>
          ))}
        </select>
      </label>
    </section>
  );
}
