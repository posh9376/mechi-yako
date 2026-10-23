# Data

Synthetic match events and fact-layer fixtures. No real clubs, players, or footage.

| Path | Purpose | Consumer |
|---|---|---|
| `matches/*.json` | Full match documents (schema v1) | Pipeline libraries, realism report |
| `fixtures/*.moments.json` | Ranked moments with `event_ids` + `stats` | API, UI, and the cached demo bundle |

## Demo match

- **Id:** `m-demo-001`
- **Storyline:** Blue Herons 1–0 HT → Red Kites press from 55' → equalise 63' → RK-4 tackle milestone 78'

Regenerate match + fixtures + realism report:

```bash
python -m generator.build_demo_data
```

Schema: [`docs/event-schema.md`](../docs/event-schema.md)
