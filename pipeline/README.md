# Pipeline (Daniel)

Importable libraries for ingest/interpret. **HTTP API is Posh’s** (`api/`).  
These modules are **deterministic** (no Foundry / no agents yet).

## Quick smoke

```bash
# Replay
python -m pipeline.replay --instant
python -m pipeline.replay --start 55:00 --end 65:00 --speed 30

# State + moment detection on the demo match
python -m pipeline.detect
```

## Modules

| Module | Role |
|---|---|
| `queue.py` | `EventSink` + `InProcessEventQueue` |
| `replay.py` | `MatchReplay` timed/instant stream |
| `state.py` | `MatchStateAggregator` — score, possession, shots, turnovers, rolling window |
| `moments.py` | `MomentDetector` — five moment types with `event_ids` + `stats` |
| `detect.py` | CLI wiring aggregator + detector |
| `clock.py` | Shared clock parse/format |

## Library usage (for API)

```python
from pipeline.replay import MatchReplay, load_match
from pipeline.state import MatchStateAggregator
from pipeline.moments import MomentDetector
from pipeline.queue import InProcessEventQueue

doc = load_match("data/matches/m-demo-001.json")
detector = MomentDetector(doc["match"])
moments = detector.detect_all(doc["events"])

# Or online with replay:
agg = MatchStateAggregator(doc["match"])
replay = MatchReplay(doc, instant=True)
for event in replay.iter_events():
    agg.ingest(event)
    new_moments = detector.ingest(event)  # if using a fresh detector in lockstep
```

## Moment types

`pressure_spell` · `shot_after_turnovers` · `momentum_swing` · `goal` · `player_milestone`

Output shape matches `docs/event-schema.md` fact-layer fixtures (Posh can compare to `data/fixtures/`).

## Next (agentic — see team plan)

Explainer + verifier libraries (**Wed–Thu Oct 21–22**), then Foundry models.
