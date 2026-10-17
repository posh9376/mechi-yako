# Pipeline (Daniel)

Importable libraries for ingest/interpret. **HTTP API is Posh’s** (`api/`).

## Replay

Stream a stored match at real time or sped up, behind an `EventSink` interface
(`InProcessEventQueue` now; Service Bus can replace later).

```bash
# Full demo match as fast as possible (smoke)
python -m pipeline.replay --instant

# Key storyline window (~55'–65') at 30× match speed
python -m pipeline.replay --start 55:00 --end 65:00 --speed 30

# Real-time (slow — 90 minutes wall clock)
python -m pipeline.replay --speed 1
```

### Library usage (for API)

```python
from pipeline import InProcessEventQueue, MatchReplay

replay = MatchReplay.from_path("data/matches/m-demo-001.json", speed=60, start_clock="55:00")
queue = InProcessEventQueue()

# In one thread / task:
# replay.play(queue)

# In consumer (SSE / websocket):
# for event in queue:
#     ...
```

| Module | Role |
|---|---|
| `queue.py` | `EventSink` protocol + `InProcessEventQueue` |
| `replay.py` | `MatchReplay`, `load_match`, `parse_clock`, CLI |

Next: match-state aggregator → moment detector.
