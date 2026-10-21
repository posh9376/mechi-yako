import type {
  DataSource,
  MatchData,
  MatchEvent,
  MatchMeta,
  Moment,
  NarrateRequest,
  Narration,
  PersonaId,
  Register,
} from "../types";

export interface DemoBundle {
  bundle_version: number;
  match_id: string;
  moment_source: "fixture" | "live";
  match: MatchMeta;
  events: MatchEvent[];
  moments: Moment[];
  persona_default_register: Record<PersonaId, Register>;
  narrations: Record<string, Record<PersonaId, Record<string, Record<Register, Narration>>>>;
}

let bundlePromise: Promise<DemoBundle> | null = null;

/** `web/public/demo-bundle.json`, built by `python -m api.build_cache`. Served as a static asset. */
export function loadBundle(): Promise<DemoBundle> {
  if (!bundlePromise) {
    bundlePromise = fetch(`${import.meta.env.BASE_URL}demo-bundle.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`demo bundle missing (${res.status})`);
        return res.json() as Promise<DemoBundle>;
      })
      .catch((err) => {
        bundlePromise = null;
        throw err;
      });
  }
  return bundlePromise;
}

export function lookupNarration(bundle: DemoBundle, req: NarrateRequest): Narration | null {
  const register = req.register ?? bundle.persona_default_register[req.persona];
  return bundle.narrations[req.momentId]?.[req.persona]?.[req.language]?.[register] ?? null;
}

/** Everything from the pre-rendered bundle; no API calls. */
export function createCachedSource(): DataSource {
  return {
    kind: "cached",
    label: "Cached demo",
    momentSource: "fixture",
    async loadMatch(): Promise<MatchData> {
      const bundle = await loadBundle();
      return {
        match: bundle.match,
        events: bundle.events,
        moments: bundle.moments,
        momentSource: bundle.moment_source,
      };
    },
    async narrate(req: NarrateRequest) {
      return lookupNarration(await loadBundle(), req);
    },
  };
}
