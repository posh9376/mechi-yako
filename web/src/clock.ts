import type { MatchEvent, MatchMeta } from "./types";

export const HALF_TIME_S = 45 * 60;
export const FULL_TIME_S = 90 * 60;

export function parseClock(t: string): number {
  const [m, s] = t.split(":").map(Number);
  return m * 60 + s;
}

export function formatClock(seconds: number): string {
  const total = Math.max(0, Math.floor(seconds));
  const m = Math.floor(total / 60);
  const s = total % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}

export function minuteMark(t: string): string {
  return `${Math.floor(parseClock(t) / 60)}'`;
}

export function scoreAt(meta: MatchMeta, events: MatchEvent[], clockS: number): [number, number] {
  const score: [number, number] = [0, 0];
  for (const e of events) {
    if (e.type !== "shot" || e.outcome !== "goal") continue;
    if (parseClock(e.t) > clockS) continue;
    if (e.team === meta.home.code) score[0] += 1;
    else if (e.team === meta.away.code) score[1] += 1;
  }
  return score;
}

export function phaseLabel(clockS: number): string {
  if (clockS <= 0) return "Kick-off";
  if (clockS >= FULL_TIME_S) return "Full time";
  if (clockS === HALF_TIME_S) return "Half time";
  return clockS < HALF_TIME_S ? "1st half" : "2nd half";
}
