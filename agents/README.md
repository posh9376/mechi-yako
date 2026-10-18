# Agents

| Module | Owner | Role |
|---|---|---|
| `explainer.py` | Daniel | Template claims from moments (Foundry later) |
| `verifier.py` | Daniel | Deterministic approve / correct / block + audit log |
| `run_explain_verify.py` | Daniel | CLI smoke + injected wrong-stat demo |
| persona / narrator / language_qa | Posh | Not started |

Schema: [`docs/claim-schema.md`](../docs/claim-schema.md)

```bash
# From repo root
python -m agents.run_explain_verify

# Optional JSON dump for API/UI
python -m agents.run_explain_verify --json-out data/fixtures/m-demo-001.verified.json
```

Posh: only **approved** (or corrected) claims should reach personas / Kiswahili / the Why? panel. Surface `audit_log` entries when a claim is blocked.
