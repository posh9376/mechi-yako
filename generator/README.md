# Generator

v1 ships a **hand-scripted** demo match and a **realism report**. A full possession simulator can come later.

```bash
# From repo root
python -m generator.build_demo_data
```

| Module | Role |
|---|---|
| `scripted_demo.py` | Builds `m-demo-001` storyline |
| `realism.py` | Pass/fail checks |
| `build_demo_data.py` | Writes `data/matches/` + `data/fixtures/` |
