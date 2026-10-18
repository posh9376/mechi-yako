import type {
  DataSource,
  MatchData,
  MatchEvent,
  MatchMeta,
  Moment,
  MomentSource,
  NarrateRequest,
  Narration,
} from "../types";

const MATCH_ID = "m-demo-001";

async function getJson<T>(url: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch {
    throw new Error(`API unreachable at ${new URL(url).origin}`);
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body?.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      /* non-JSON error body */
    }
    throw new Error(`${res.status} ${detail}`);
  }
  return (await res.json()) as T;
}

/** Live fact-layer API (`uvicorn api.main:app`). */
export function createApiSource(baseUrl: string, momentSource: MomentSource = "live"): DataSource {
  const base = baseUrl.replace(/\/+$/, "");
  const matchUrl = `${base}/matches/${MATCH_ID}`;

  return {
    kind: "api",
    label: `API ${base}`,
    async loadMatch(): Promise<MatchData> {
      const [meta, events, moments] = await Promise.all([
        getJson<{ match: MatchMeta }>(matchUrl),
        getJson<{ events: MatchEvent[] }>(`${matchUrl}/events`),
        getJson<{ moments: Moment[]; source: MomentSource }>(`${matchUrl}/moments?source=${momentSource}`),
      ]);
      return { match: meta.match, events: events.events, moments: moments.moments, momentSource: moments.source };
    },
    async narrate(req: NarrateRequest): Promise<Narration | null> {
      return getJson<Narration>(`${matchUrl}/narrate`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          moment_id: req.momentId,
          persona: req.persona,
          language: req.language,
          register: req.register,
          source: momentSource,
        }),
      });
    },
  };
}
