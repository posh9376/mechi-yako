import { formatClock, phaseLabel } from "../clock";
import type { MatchMeta } from "../types";

interface Props {
  match: MatchMeta;
  score: [number, number];
  clockS: number;
}

export function ScoreBar({ match, score, clockS }: Props) {
  return (
    <header className="scorebar" aria-label="Score">
      <div className="scorebar__team scorebar__team--home">
        <span className="scorebar__code">{match.home.code}</span>
        <span className="scorebar__name">{match.home.name}</span>
      </div>
      <div className="scorebar__center">
        <div className="scorebar__score" data-testid="score">
          {score[0]} <span className="scorebar__dash">–</span> {score[1]}
        </div>
        <div className="scorebar__clock">
          <span data-testid="clock">{formatClock(clockS)}</span>
          <span className="scorebar__phase">{phaseLabel(clockS)}</span>
        </div>
      </div>
      <div className="scorebar__team scorebar__team--away">
        <span className="scorebar__name">{match.away.name}</span>
        <span className="scorebar__code">{match.away.code}</span>
      </div>
    </header>
  );
}
