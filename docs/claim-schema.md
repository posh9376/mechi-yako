# Claim schema v1

Structured claims sit between **moments** (fact layer) and **persona / Kiswahili** rendering.  
The explainer emits claims; the **verifier** recomputes each claim from raw events and approves, corrects, or blocks it.

Related: [`event-schema.md`](event-schema.md) · fixtures in `data/fixtures/`.

## Explanation package

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | `"1.0"` |
| `match_id` | string | yes | |
| `moment_id` | string | yes | Moment being explained |
| `claims` | Claim[] | yes | One or more grounded claims |
| `summary_en` | string | no | Short English summary (pre-persona) |

## Claim object

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | e.g. `c-0001` |
| `match_id` | string | yes | |
| `moment_id` | string | yes | |
| `sentence` | string | yes | Human-readable claim (English for v1 stub) |
| `metric` | string | yes | See [Metrics](#metrics) |
| `value` | number \| string \| boolean \| array | yes | Asserted value |
| `entities` | object | yes | e.g. `{ "team": "RK", "player": "RK-4" }` |
| `event_ids` | string[] | yes | Supporting raw event ids (must exist on the match) |

## Metrics

Verifier knows how to recompute these from events (and optional moment window):

| `metric` | `value` type | How it is checked |
|---|---|---|
| `event_count` | int | `len(event_ids)` after resolving ids on the match |
| `high_turnovers` | int | Count of `tackle`/`interception` with `won_possession` in `event_ids` |
| `pressure_events` | int | Count of `type == pressure` in `event_ids` |
| `turnovers_before_shot` | int | Count of won turnovers in `event_ids` excluding the shot itself |
| `shot_outcome` | string | `outcome` of the shot event referenced by `entities.shot_event_id` or sole shot in `event_ids` |
| `goals` | int | Count of `shot` + `outcome == goal` in `event_ids` |
| `tackles_won` | int | Count of won tackles for `entities.player` in `event_ids` (or whole match if `attrs.scope == "match"`) |
| `score_after` | `[int, int]` | Home/away goals from all `goal` shots with `t <= claim` peak, or from moment stats cross-check when events suffice |
| `literal` | any | Pass-through; verifier **blocks** unless `attrs.trusted` is true (used only for demos) |

Unknown metrics → **block** with reason `unknown_metric`.

## Verification decision

| Field | Type | Description |
|---|---|---|
| `claim_id` | string | |
| `decision` | string | `approved` \| `corrected` \| `blocked` |
| `reason` | string | Short audit reason |
| `expected_value` | any \| null | Recomputed value when available |
| `corrected_claim` | Claim \| null | Claim with fixed `value` / `sentence` when `corrected` |
| `event_ids_resolved` | string[] | Ids that existed on the match |
| `event_ids_missing` | string[] | Ids cited but not found → usually **blocked** |

## Audit log entry

| Field | Type | Description |
|---|---|---|
| `id` | string | e.g. `audit-0001` |
| `ts` | string | ISO-8601 (synthetic ok) |
| `match_id` | string | |
| `moment_id` | string | |
| `claim_id` | string | |
| `decision` | string | |
| `reason` | string | |
| `claim` | Claim | Input claim |
| `expected_value` | any \| null | |

## Explainer note (v1)

v1 ships a **template explainer** that turns moment `stats` into claims.  
Optional Foundry (`gpt-5-mini`) rewrites claim *sentences* only. Metric, value, and `event_ids` stay on the template layer so the verifier never checks LLM output. Set `MECHI_EXPLAINER=foundry` in `.env` (see `.env.example`). On missing credentials or a failed call, the API falls back to templates.
