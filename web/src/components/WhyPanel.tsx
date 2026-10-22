import type { ExplanationClaimDecision, ExplanationPackage, MatchEvent, Moment } from "../types";
import type { NarrationState } from "./MomentDetail";

const CONTEXT_KEYS = new Set(["zone", "player", "metric", "milestone"]);

export type ExplanationState =
  | { status: "idle" }
  | { status: "loading" }
  | { status: "ready"; explanation: ExplanationPackage }
  | { status: "error"; message: string };

interface Props {
  moment: Moment | null;
  events: MatchEvent[];
  narration: NarrationState;
  explanation: ExplanationState;
  onRetryExplanation?: () => void;
}

type ClaimRow = {
  metric: string;
  claimed: unknown;
  status: "approved" | "corrected" | "blocked" | "pending";
  detail?: string;
  sentence?: string;
};

function rowsFromExplanation(explanation: ExplanationPackage | undefined): ClaimRow[] | null {
  if (!explanation) return null;
  const { claims, verifications } = explanation;
  const byMetric = new Map(verifications.map((v) => [v.metric, v]));
  return claims.map((c) => {
    const v: ExplanationClaimDecision | undefined = byMetric.get(c.metric);
    if (!v) {
      return { metric: c.metric, claimed: c.value, status: "pending", sentence: c.sentence };
    }
    const detail =
      v.status === "corrected"
        ? `${String(v.claimed)} → ${String(v.corrected_value ?? v.recomputed)}`
        : v.reason;
    return {
      metric: c.metric,
      claimed: c.value,
      status: v.status,
      detail,
      sentence: c.sentence ?? v.sentence,
    };
  });
}

function rowsFromStats(moment: Moment, narration: NarrationState): ClaimRow[] {
  const stats = moment.stats;
  const rows: ClaimRow[] = [];
  const verification = narration.status === "ready" ? narration.narration.verification : undefined;
  const correctedByMetric = new Map(
    (verification?.corrected ?? []).map((c) => [c.metric, c] as const),
  );
  const blocked = new Set(verification?.blocked ?? []);

  for (const [key, value] of Object.entries(stats)) {
    if (CONTEXT_KEYS.has(key)) continue;
    const metric = key === "value" && typeof stats.metric === "string" ? stats.metric : key;
    if (blocked.has(metric)) {
      rows.push({ metric, claimed: value, status: "blocked", detail: "blocked by verifier" });
      continue;
    }
    const corrected = correctedByMetric.get(metric);
    if (corrected) {
      rows.push({
        metric,
        claimed: value,
        status: "corrected",
        detail: `${String(corrected.claimed)} → ${String(corrected.corrected_value)}`,
      });
      continue;
    }
    if (verification) {
      rows.push({ metric, claimed: value, status: "approved", detail: "matches events" });
    } else {
      rows.push({ metric, claimed: value, status: "pending", detail: "awaiting narration / verify" });
    }
  }
  return rows;
}

function resolveEvents(moment: Moment, events: MatchEvent[]): MatchEvent[] {
  const index = new Map(events.map((e) => [e.id, e]));
  return moment.event_ids.map((id) => index.get(id)).filter((e): e is MatchEvent => Boolean(e));
}

export function WhyPanel({ moment, events, narration, explanation: explanationState, onRetryExplanation }: Props) {
  if (!moment) {
    return (
      <section className="why why--empty" aria-label="Why panel">
        <h2 className="why__title">Why?</h2>
        <p className="muted">Select a moment to see the cited events and verifier status.</p>
      </section>
    );
  }

  const cited = resolveEvents(moment, events);
  const missing = moment.event_ids.length - cited.length;
  const explanation = explanationState.status === "ready" ? explanationState.explanation : undefined;
  const fromExplainer = rowsFromExplanation(explanation);
  const claims = fromExplainer ?? rowsFromStats(moment, narration);
  const verification = narration.status === "ready" ? narration.narration.verification : undefined;
  const summary = explanation?.summary;

  return (
    <section className="why" aria-label="Why panel" data-testid="why-panel">
      <div className="why__header">
        <h2 className="why__title">Why?</h2>
        <p className="why__lede">
          {fromExplainer
            ? "Explainer claims (Daniel) verified against raw events, then shown to fans."
            : "Every on-screen claim cites raw events and a verifier decision."}
        </p>
        {explanation && (
          <p className="why__source muted" data-testid="why-explainer-source">
            {explanation.explainer} · {explanation.summary_en}
          </p>
        )}
        {explanation?.foundry_error && (
          <p className="why__source muted" data-testid="why-explainer-fallback" title={explanation.foundry_error}>
            Foundry unavailable, showing template sentences.
          </p>
        )}
        {explanationState.status === "loading" && (
          <p className="why__source muted" data-testid="why-explaining">
            Explaining why this matters…
          </p>
        )}
        {explanationState.status === "error" && (
          <p className="why__source why__error" role="alert">
            Could not load the explanation: {explanationState.message}
            {onRetryExplanation && (
              <button type="button" className="btn why__retry" onClick={onRetryExplanation}>
                Retry
              </button>
            )}
          </p>
        )}
      </div>

      {(summary || verification) && (
        <div className="why__summary" data-testid="why-summary">
          {summary ? (
            <>
              <VerifierBadge status="approved" label={`${summary.approved} approved`} />
              {summary.corrected > 0 && (
                <VerifierBadge status="corrected" label={`${summary.corrected} corrected`} />
              )}
              {summary.blocked > 0 && (
                <VerifierBadge status="blocked" label={`${summary.blocked} blocked`} />
              )}
            </>
          ) : (
            verification && (
              <>
                <VerifierBadge status="approved" label={`${verification.approved} approved`} />
                {verification.corrected.length > 0 && (
                  <VerifierBadge
                    status="corrected"
                    label={`${verification.corrected.length} corrected`}
                  />
                )}
                {verification.blocked.length > 0 && (
                  <VerifierBadge
                    status="blocked"
                    label={`${verification.blocked.length} blocked`}
                  />
                )}
              </>
            )
          )}
        </div>
      )}

      <div className="why__grid">
        <div>
          <h3 className="why__section">Claims</h3>
          {claims.length === 0 ? (
            <p className="muted">No structured stats on this moment.</p>
          ) : (
            <ul className="why__claims">
              {claims.map((c) => (
                <li key={c.metric} className="why__claim" data-testid={`claim-${c.metric}`}>
                  <VerifierBadge status={c.status} label={c.status} />
                  <span className="why__claim-metric">{c.metric}</span>
                  <span className="why__claim-value">{formatValue(c.claimed)}</span>
                  {c.sentence && <span className="why__claim-sentence">{c.sentence}</span>}
                  {c.detail && <span className="why__claim-detail">{c.detail}</span>}
                </li>
              ))}
            </ul>
          )}
        </div>

        <div>
          <h3 className="why__section">
            Cited events ({cited.length}
            {missing > 0 ? `, ${missing} missing` : ""})
          </h3>
          <ul className="why__events" data-testid="why-events">
            {cited.map((e) => (
              <li key={e.id} className="why__event">
                <code className="why__eid">{e.id}</code>
                <span className="why__etime">{e.t}</span>
                <span>
                  {e.type}
                  {e.outcome ? ` · ${e.outcome}` : ""}
                </span>
                <span className="muted">
                  {e.team}
                  {e.player ? ` / ${e.player}` : ""}
                </span>
              </li>
            ))}
          </ul>
        </div>
      </div>
    </section>
  );
}

function VerifierBadge({
  status,
  label,
}: {
  status: ClaimRow["status"];
  label: string;
}) {
  return (
    <span className={`v-badge v-badge--${status}`} data-testid={`v-badge-${status}`}>
      {label}
    </span>
  );
}

function formatValue(value: unknown): string {
  if (Array.isArray(value)) return value.join("–");
  if (typeof value === "object" && value !== null) return JSON.stringify(value);
  return String(value);
}
