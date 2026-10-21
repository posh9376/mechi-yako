# Cached demo bundle

The cached bundle is one static JSON file that lets the web app run the whole demo with the API down. Daniel's deploy (Sat 24 Oct) ships it as a static asset next to the built web app.

| | |
|---|---|
| File | [`web/public/demo-bundle.json`](../web/public/demo-bundle.json) (~135 KB) |
| Builder | [`api/build_cache.py`](../api/build_cache.py) |
| Consumer | [`web/src/data/cached.ts`](../web/src/data/cached.ts) |
| Served at | `${BASE_URL}demo-bundle.json` (Vite copies `web/public/` to the build root) |
| Bundle version | `1` |

## When the web app uses it

- **`?demo=cached`** in the URL forces cached mode and makes no network calls to the API.
- **API unreachable.** When `VITE_API_BASE_URL` is set and the first load fails, the error panel offers **Use cached demo**. That switches to cached mode and adds `?demo=cached` to the URL, so a refresh stays offline.
- **Fixture mode** (no `VITE_API_BASE_URL`) reads narrations from the same bundle, so persona, language and register switching works with no backend.

The header label reads `Cached demo · fixture moments` in cached mode.

## Regenerating

The bundle is deterministic. Rebuild it whenever the lexicon, writers, narrator, QA, verifier, fixture, or demo match changes.

```bash
python -m api.build_cache            # writes web/public/demo-bundle.json
python -m api.build_cache --check    # exit 1 if the committed file is stale
python -m api.build_cache --out /tmp/bundle.json
```

`tests/api/test_cache_bundle.py` runs the `--check` comparison, so `pytest` fails on a stale bundle.

## Shape

```jsonc
{
  "bundle_version": 1,
  "schema_version": "1.0",               // from the match document
  "match_id": "m-demo-001",
  "moment_source": "fixture",            // moments come from data/fixtures/m-demo-001.moments.json
  "match": { ... },                      // match block from data/matches/m-demo-001.json, unchanged
  "events": [ ... ],                     // all 123 events, unchanged
  "final_state": { ... },                // MatchStateAggregator.snapshot() after full time
  "moments": [ ... ],                    // the 5 fixture moments, unchanged
  "persona_default_register": {
    "analyst": "formal",
    "casual": "casual",
    "newcomer": "simple"
  },
  "narrations": {
    "<moment_id>": {
      "<persona>": {                     // analyst | casual | newcomer
        "<language>": {                  // en | sw
          "<register>": NarrateResponse  // formal | casual | simple
        }
      }
    }
  },
  "claims": {
    "checker": "deterministic-v1",
    "summary": { "approved": 12, "corrected": 1, "blocked": 0 },
    "claims": [ ClaimDecision, ... ]
  },
  "lexicon": { "version": 1, "review": "approved" }
}
```

`narrations` holds every combination: 5 moments × 3 personas × 2 languages × 3 registers = 90 entries. The UI resolves `register: "auto"` through `persona_default_register`.

### `NarrateResponse`

Each entry is byte-for-byte what `POST /matches/m-demo-001/narrate` returns for the same request with `"source": "fixture"`.

```json
{
  "narrative": {
    "moment_id": "mom-goal-equaliser-01",
    "match_id": "m-demo-001",
    "moment_type": "goal",
    "text": "Omar Diallo amefunga bao kwa Red Kites katika dakika ya 63. Sasa matokeo ni Blue Herons 1, Red Kites 1. Sasa ni sare. Bao linapatikana pale mpira wote unapovuka mstari kati ya milingoti ya lango.",
    "language": "sw",
    "persona": "newcomer",
    "register": "simple",
    "register_requested": "simple",
    "event_ids": ["e-0100"],
    "stats_used": { "scorer": "RK-9", "minute": 63, "score_after": [1, 1] },
    "entities_used": { "scorer": "RK-9" },
    "lexicon_terms": ["goal"],
    "writer": "deterministic-sw-v1"
  },
  "qa": { "status": "pass", "reasons": [] },
  "verification": { "approved": 3, "corrected": [], "blocked": [] }
}
```

- `register` is the register actually used. It differs from `register_requested` only when a moment type has no template for the requested register and falls back to `formal`.
- `qa.status` is `pass` or `flag`. On `flag`, `reasons` lists human-readable strings, and the UI shows them under the text.
- `verification.corrected` holds full `ClaimDecision` objects (below) with `status: "corrected"`. The writer used each `recomputed` value. `verification.blocked` lists metric names the writer was not allowed to use.

### `ClaimDecision`

Same shape as the entries `GET /matches/{id}/claims` returns.

```json
{
  "moment_id": "mom-pressure-01",
  "metric": "high_turnovers",
  "claimed": 5,
  "event_ids": ["e-0085", "e-0087", "e-0091", "e-0093", "e-0098", "e-0086", "e-0088", "e-0090", "e-0092", "e-0097"],
  "recomputed": 5,
  "status": "approved",
  "reason": "matches raw events",
  "checker": "deterministic-v1"
}
```

`status` is `approved`, `corrected` (float within 0.5 of the recomputed value) or `blocked`.

## Known data note for Daniel

The fixture moment `mom-pressure-01` has `stats.window_minutes: 7`. Its cited events span 55:05–61:45, which is 6 min 40 s (6.7 minutes). The verifier marks this claim `corrected` (7 → 6.7), which accounts for the single `corrected` in the summary. Narrations use 6.7, and the UI shows "verifier corrected window_minutes 7 → 6.7". If the fixture is changed to 6.7, rebuild the bundle and the summary becomes 13 approved.

## Contract for the deploy

- Serve `demo-bundle.json` from the same origin and base path as the web build. No CORS setup is needed.
- The file is static. Caching it with a long max-age is fine as long as the build is versioned.
- A swap to Foundry-generated narration keeps this shape. `narrative.writer` changes, and every other field stays.
