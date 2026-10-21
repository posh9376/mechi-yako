import matchDoc from "../../../data/matches/m-demo-001.json";
import fixtureDoc from "../../../data/fixtures/m-demo-001.moments.json";
import type { DataSource, MatchData, MatchEvent, MatchMeta, Moment } from "../types";
import { loadBundle, lookupNarration } from "./cached";

/** Repo fixtures bundled at build time; narrations come from the static demo bundle. */
export function createFixtureSource(): DataSource {
  return {
    kind: "fixtures",
    label: "Repo fixtures",
    momentSource: "fixture",
    async loadMatch(): Promise<MatchData> {
      return {
        match: matchDoc.match as unknown as MatchMeta,
        events: matchDoc.events as unknown as MatchEvent[],
        moments: fixtureDoc.moments as unknown as Moment[],
        momentSource: "fixture",
      };
    },
    async narrate(req) {
      try {
        return lookupNarration(await loadBundle(), req);
      } catch {
        return null;
      }
    },
  };
}
