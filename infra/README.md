# Infra

One Docker image serves the Vite build and the FastAPI API on the same origin. That is the shape we put on Azure Container Apps.

## Local smoke

Docker Desktop must be running. From the repo root:

```bash
docker compose up --build
```

Then open http://127.0.0.1:8080

Secrets stay in local `.env` (`env_file` in Compose). They are not copied into the image.

`MECHI_EXPLAINER_PREWARM` is `0` in Compose so the first boot does not wait on Foundry. The Azure app can set it back to `1`.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every pull request and on `main`:

- pytest + `python -m api.build_cache --check`
- `web` TypeScript check
- Docker image build (no push)

No secrets required.

## CD

[`.github/workflows/cd.yml`](../.github/workflows/cd.yml) runs on push to `main` (and manually).

1. **Publish** the image to `ghcr.io/<owner>/mechi-yako` as `latest` and `sha-<short>`. Uses `GITHUB_TOKEN`; first successful run creates the package. Make the package **public** so Azure can pull it without extra registry credentials.
2. **Deploy** to Azure Container Apps only if GitHub **variables** `AZURE_RESOURCE_GROUP` and `AZURE_CONTAINER_APP` are set. Until then this job is skipped.

### GitHub variables (repo → Settings → Variables)

| Name | Example |
|---|---|
| `AZURE_RESOURCE_GROUP` | `inside_the_game_hackathon` |
| `AZURE_CONTAINER_APP` | `mechi-yako` |

### GitHub secrets (repo → Settings → Secrets)

OIDC login for the deploy job (no password in git):

| Name | From |
|---|---|
| `AZURE_CLIENT_ID` | App registration / federated credential |
| `AZURE_TENANT_ID` | Azure AD tenant |
| `AZURE_SUBSCRIPTION_ID` | Subscription |

Foundry keys stay on the Container App as secrets (`AZURE_OPENAI_*`, `MECHI_EXPLAINER=foundry`). They never go in the image or in git.
