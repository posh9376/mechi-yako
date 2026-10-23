# Agents

Specialized roles on one claim-then-verify chain. Numbers never come from a model.

| Module | Role |
|---|---|
| `explainer.py` | Template claims from moments (numbers) |
| `foundry.py` | Optional Foundry rewrite of Why? sentences (`gpt-5-mini`) |
| `verifier.py` | Deterministic approve / correct / block + audit log |
| `run_explain_verify.py` | CLI smoke + injected wrong-stat demo |
| `persona/` | Analyst, casual fan, and newcomer writers |
| `narrator/` | Native Kiswahili templates and registers |
| `language_qa/` | Number, name, event-ID and lexicon checks |

Schema: [`docs/claim-schema.md`](../docs/claim-schema.md)

Optional Foundry: copy `.env.example` to `.env`, set `MECHI_EXPLAINER=foundry` plus the Azure OpenAI endpoint, key, and `gpt-5-mini` deployment. The Why? panel then shows `foundry-gpt-5-mini`. Numbers still come from templates and the verifier. Missing credentials or a failed call fall back to `template-v1`. Keep `MECHI_EXPLAINER=template` when running `python -m api.build_cache`.

Only **approved** (or corrected) claims reach personas, Kiswahili, and the Why? panel. Blocked claims are written to the audit log.

```bash
# From repo root
python -m agents.run_explain_verify

# Optional JSON dump for API/UI
python -m agents.run_explain_verify --json-out data/fixtures/m-demo-001.verified.json
```
