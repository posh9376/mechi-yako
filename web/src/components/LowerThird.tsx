import { formatClock, minuteMark } from "../clock";
import { momentTypeLabel } from "../labels";
import { overlayFor } from "../overlay";
import type { Language, MatchMeta, Moment } from "../types";
import type { NarrationState } from "./MomentDetail";

interface Props {
  match: MatchMeta;
  score: [number, number];
  clockS: number;
  moment: Moment | null;
  language: Language;
  narration: NarrationState;
}

/** Broadcast-style lower third driven by the selected moment (overlay JSON shape in spirit). */
export function LowerThird({ match, score, clockS, moment, language, narration }: Props) {
  if (!moment) return null;

  const line =
    narration.status === "ready"
      ? narration.narration.narrative.text
      : moment.headline.en;

  const overlay = overlayFor({ moment, score, clockS, text: line });

  return (
    <aside
      className="lower-third"
      aria-label="Broadcast lower third"
      data-testid="lower-third"
      data-overlay={JSON.stringify(overlay)}
    >
      <div className="lower-third__bar">
        <div className="lower-third__score">
          <span className="lower-third__club lower-third__club--home">{match.home.code}</span>
          <span className="lower-third__nums">
            {score[0]}–{score[1]}
          </span>
          <span className="lower-third__club lower-third__club--away">{match.away.code}</span>
          <span className="lower-third__clock">{minuteMark(formatClock(clockS))}</span>
        </div>
        <div className="lower-third__copy">
          <span className="lower-third__eyebrow">
            Overlay · {momentTypeLabel(moment.type, language)} · {moment.team}
          </span>
          <p className="lower-third__text" lang={narration.status === "ready" ? language : "en"}>
            {line}
          </p>
        </div>
        <div className="lower-third__cite" title={moment.event_ids.join(", ")}>
          {moment.event_ids.length} events
        </div>
      </div>
    </aside>
  );
}
