import { formatClock } from "./clock";
import type { Moment } from "./types";

export const OVERLAY_SCHEMA = "mechi-yako-overlay-v1";

export function overlayFor(args: {
  moment: Moment;
  score: [number, number];
  clockS: number;
  text: string;
}) {
  const { moment, score, clockS, text } = args;
  return {
    schema: OVERLAY_SCHEMA,
    t: formatClock(clockS),
    score: { home: score[0], away: score[1] },
    team: moment.team,
    moment_type: moment.type,
    moment_id: moment.id,
    event_ids: moment.event_ids,
    headline: moment.headline,
    text,
    stats: moment.stats,
  };
}
