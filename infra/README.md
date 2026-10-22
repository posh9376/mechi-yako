# Infra

One Docker image serves the Vite build and the FastAPI API on the same origin. That is the shape we put on Azure Container Apps.

Public demo: https://mechi-yako.icyriver-d1adadda.southafricanorth.azurecontainerapps.io/

## Local smoke

Docker Desktop must be running. From the repo root:

```bash
docker compose up --build
```

Then open http://127.0.0.1:8080

Secrets stay in local `.env` (`env_file` in Compose). They are not copied into the image.

`MECHI_EXPLAINER_PREWARM` is `0` in Compose so the first boot does not wait on Foundry. The Azure app is set to `1`.

Azure Container Apps needs **linux/amd64**. On an Apple Silicon Mac, build with `--platform linux/amd64` before `docker push` to ACR.

## CI

[`.github/workflows/ci.yml`](../.github/workflows/ci.yml) runs on every pull request and on `main`:

- pytest + `python -m api.build_cache --check`
- `web` TypeScript check
- Docker image build (no push)

No secrets required.

## CD

[`.github/workflows/cd.yml`](../.github/workflows/cd.yml) runs on push to `main` (and manually).

1. Sign in to Azure with `AZURE_CREDENTIALS`.
2. Build `linux/amd64` and push to `mechiyakoacr.azurecr.io/mechi-yako` (`latest` and `sha-<short>`).
3. Update Container App `mechi-yako` in `inside_the_game_hackathon` to that image.

Foundry keys stay on the Container App as secrets. They never go in the image or in git.

### GitHub secret

One secret, `AZURE_CREDENTIALS`. Create the principal on your machine (do not commit the JSON):

```bash
az ad sp create-for-rbac \
  --name github-mechi-yako-cd \
  --role contributor \
  --scopes "$(az group show -n inside_the_game_hackathon --query id -o tsv)" \
  --sdk-auth
```

Paste the JSON into GitHub → Settings → Secrets and variables → Actions → `AZURE_CREDENTIALS`. Then Actions → CD → Run workflow. Foundry keys stay on the Container App; this principal only pushes images and updates the app.
