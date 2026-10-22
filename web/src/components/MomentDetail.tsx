import { minuteMark } from "../clock";
import { momentTypeLabel } from "../labels";
import type { Language, Moment, Narration } from "../types";

export type NarrationState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "error"; message: string }
  | { status: "unavailable" }
  | { status: "ready"; narration: Narration };

interface Props {
  moment: Moment | null;
  language: Language;
  narration: NarrationState;
  onRetry: () => void;
}

const UNAVAILABLE: Record<Language, string> = {
  en: "Persona narration needs the API or the cached demo. Showing the fact headline.",
  sw: "Simulizi ya Kiswahili inahitaji API au onyesho lililohifadhiwa.",
};

export function MomentDetail({ moment, language, narration, onRetry }: Props) {
  if (!moment) {
    return (
      <section className="detail detail--empty" aria-label="Moment detail">
        <p className="detail__empty-title">Your match, your language</p>
        <p>Select a moment from the timeline. Or join at 55′ and watch the press arrive live.</p>
      </section>
    );
  }

  return (
    <section className="detail" aria-label="Moment detail" aria-live="polite">
      <div className="detail__meta">
        <span className="detail__minute">{minuteMark(moment.t_peak)}</span>
        <span className={`moment__type moment__type--${moment.type}`}>
          {momentTypeLabel(moment.type, language)}
        </span>
        {narration.status === "ready" && <QaBadge narration={narration.narration} />}
      </div>

      {narration.status === "loading" && (
        <p className="detail__text detail__text--muted detail__text--writing">Writing…</p>
      )}

      {narration.status === "error" && (
        <div className="detail__error" role="alert">
          <p>Could not load the narration: {narration.message}</p>
          <button type="button" className="btn" onClick={onRetry}>
            Try again
          </button>
        </div>
      )}

      {(narration.status === "unavailable" || narration.status === "idle") && (
        <>
          <p className="detail__text" lang="en">
            {moment.headline.en}
          </p>
          <p className="detail__note">{UNAVAILABLE[language]}</p>
        </>
      )}

      {narration.status === "ready" && <ReadyNarration narration={narration.narration} />}
    </section>
  );
}

function ReadyNarration({ narration }: { narration: Narration }) {
  const { narrative, qa, verification } = narration;
  const corrected = verification?.corrected ?? [];
  return (
    <>
      <p className="detail__text" lang={narrative.language} data-testid="narration">
        {narrative.text}
      </p>
      {qa.status === "flag" && (
        <ul className="detail__flags" data-testid="qa-reasons">
          {qa.reasons.map((r) => (
            <li key={r}>{r}</li>
          ))}
        </ul>
      )}
      <p className="detail__note">
        {narrative.persona} · {narrative.register} register · cites {narrative.event_ids.length}{" "}
        {narrative.event_ids.length === 1 ? "event" : "events"}
        {corrected.length > 0 &&
          ` · verifier corrected ${corrected
            .map((c) => `${c.metric} ${String(c.claimed)} → ${String(c.corrected_value)}`)
            .join(", ")}`}
      </p>
    </>
  );
}

function QaBadge({ narration }: { narration: Narration }) {
  const { qa } = narration;
  const pass = qa.status === "pass";
  return (
    <span
      className={pass ? "qa-badge qa-badge--pass" : "qa-badge qa-badge--flag"}
      title={pass ? "Every number and event matches the fact layer" : qa.reasons.join("\n")}
      data-testid="qa-badge"
    >
      {pass ? "QA pass" : `QA flag (${qa.reasons.length})`}
    </span>
  );
}
