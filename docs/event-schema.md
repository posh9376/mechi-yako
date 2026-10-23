# Event schema v1

All clubs and players are **fictional**. Times use `MM:SS` from kick-off of that half’s clock as wall-clock match time (`0:00`–`45:00` first half, `45:00`–`90:00` second half; stoppage may exceed).

## Match document

A match file under `data/matches/` is one JSON object:

| Field | Type | Required | Description |
|---|---|---|---|
| `schema_version` | string | yes | `"1.0"` |
| `match` | object | yes | Match metadata (below) |
| `events` | array | yes | Ordered list of events |

### `match` metadata

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Stable id, e.g. `m-demo-001` |
| `competition` | string | no | Fictional competition name |
| `kickoff` | string | no | ISO-8601 datetime (synthetic) |
| `venue` | string | no | Fictional venue |
| `home` | team | yes | Home team |
| `away` | team | yes | Away team |
| `score_ht` | `[int, int]` | yes | `[home, away]` at half time |
| `score_ft` | `[int, int]` | yes | `[home, away]` at full time |
| `seed` | int \| null | no | Generator seed if produced by sim; `null` if hand-scripted |
| `notes` | string | no | Human notes (storyline) |

### `team`

| Field | Type | Required | Description |
|---|---|---|---|
| `code` | string | yes | Short code, e.g. `BH`, `RK` |
| `name` | string | yes | Display name |
| `players` | array | yes | List of `player` objects |

### `player`

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | e.g. `BH-9` |
| `name` | string | yes | Fictional display name |
| `number` | int | yes | Shirt number |
| `position` | string | yes | `GK` \| `DEF` \| `MID` \| `FWD` |

## Event object

Every event in `events[]`:

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | Unique within match, e.g. `e-0001` |
| `t` | string | yes | Match clock `M:SS` or `MM:SS` |
| `period` | int | yes | `1` or `2` |
| `type` | string | yes | See [Event types](#event-types) |
| `team` | string | yes | Team `code` |
| `player` | string \| null | yes | Player `id`, or `null` if N/A |
| `location` | `[number, number]` \| null | yes | Pitch coords; see [Pitch](#pitch-coordinates) |
| `outcome` | string \| null | yes | Type-specific outcome |
| `match_id` | string | yes | Same as `match.id` |
| `related_event_ids` | string[] | no | Links (e.g. shot that follows a tackle) |
| `attrs` | object | no | Extra typed fields (speed, pass length, …) |

### Event types

| `type` | Typical `outcome` values | Notes |
|---|---|---|
| `kickoff` | `started` | Period start |
| `pass` | `complete` \| `incomplete` \| `intercepted` | |
| `carry` | `continued` \| `lost` | Dribble / progressive carry |
| `tackle` | `won_possession` \| `fouled` \| `missed` | |
| `interception` | `won_possession` | |
| `block` | `blocked` | |
| `clearance` | `cleared` \| `incomplete` | |
| `pressure` | `applied` | Defensive pressure event (no possession change required) |
| `shot` | `goal` \| `saved` \| `blocked` \| `off_target` \| `woodwork` | |
| `save` | `held` \| `parried` \| `conceded` | Keeper |
| `foul` | `committed` | |
| `card` | `yellow` \| `red` | |
| `substitution` | `on` \| `off` | Use `attrs.player_on` / `player_off` |
| `period_end` | `ended` | Half or full time whistle |

### Pitch coordinates

- Origin `(0, 0)` = **home** team’s left corner (own goal line, touchline).
- `x` ∈ `[0, 100]` along length; home attacks toward `x = 100` in both halves for simplicity in v1 (coordinates are absolute, not flipped by half).
- `y` ∈ `[0, 100]` along width.
- Own half for home ≈ `x < 50`; attacking third ≈ `x ≥ 66`.

## Fact-layer fixture (for API / UI)

Files under `data/fixtures/` pin ranked moments (`event_ids` + `stats`) for the API, UI, and cached demo.

### Moment object

| Field | Type | Required | Description |
|---|---|---|---|
| `id` | string | yes | e.g. `mom-pressure-01` |
| `match_id` | string | yes | |
| `type` | string | yes | `pressure_spell` \| `shot_after_turnovers` \| `momentum_swing` \| `goal` \| `player_milestone` |
| `t_start` | string | yes | Clock at window start |
| `t_end` | string | yes | Clock at window end |
| `t_peak` | string | yes | Clock for on-screen cue |
| `team` | string | yes | Primary team for the moment |
| `headline` | object | yes | `{ "en": "..." }` short fact headline (not persona copy) |
| `significance` | number | yes | `0`–`1` rank hint |
| `event_ids` | string[] | yes | Supporting raw events |
| `stats` | object | yes | Deterministic metrics the verifier can recompute |
| `entities` | object | no | Players/teams referenced |

### Fixture file shape

```json
{
  "schema_version": "1.0",
  "match_id": "m-demo-001",
  "moments": [ /* Moment objects */ ]
}
```

## Demo match storyline (locked)

`m-demo-001` — Blue Herons vs Red Kites:

1. Blue Herons lead **1–0** at half time.
2. Red Kites start a **press** around **55'** and force turnovers in the Blue Herons half.
3. Red Kites **equalise** around **63'**.
4. A Red Kites player hits a **personal milestone** late (e.g. 5th completed tackle or 50th pass).

That single match must contain all five moment types.

## Versioning

- Bump `schema_version` only on breaking changes.
- Additive optional fields may land without a version bump if fixtures remain valid.
