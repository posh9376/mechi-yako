# Agents

| Module | Owner | Role |
|---|---|---|
| `explainer.py` | Daniel | Template claims from moments (numbers) |
| `foundry.py` | Daniel | Optional Foundry rewrite of Why? sentences (`gpt-5-mini`) |
| `verifier.py` | Daniel | Deterministic approve / correct / block + audit log |
| `run_explain_verify.py` | Daniel | CLI smoke + injected wrong-stat demo |
| persona / narrator / language_qa | Posh | Not started |

Schema: [`docs/claim-schema.md`](../docs/claim-schema.md)

Optional Foundry: copy `.env.example` to `.env`, set `MECHI_EXPLAINER=foundry` plus the Azure OpenAI endpoint, key, and `gpt-5-mini` deployment. The Why? panel then shows `foundry-gpt-5-mini`. Numbers still come from templates and the verifier. Missing credentials or a failed call fall back to `template-v1`. Keep `MECHI_EXPLAINER=template` when running `python -m api.build_cache`.

```bash
# From repo root
python -m agents.run_explain_verify

# Optional JSON dump for API/UI
python -m agents.run_explain_verify --json-out data/fixtures/m-demo-001.verified.json
```

Posh: only **approved** (or corrected) claims should reach personas / Kiswahili / the Why? panel. Surface `audit_log` entries when a claim is blocked.
