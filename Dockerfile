# One image: Vite UI + FastAPI, same origin. Used locally and later on Azure Container Apps.
# syntax=docker/dockerfile:1

FROM node:20-alpine AS web
WORKDIR /src/web
COPY web/package.json web/package-lock.json ./
RUN npm ci
COPY web/ ./
COPY data /src/data
# Same-origin API: the browser calls /matches, /health, /feed on this host.
ENV VITE_API_BASE_URL=/
RUN npm run build

FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8080
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY api ./api
COPY agents ./agents
COPY pipeline ./pipeline
COPY data ./data
COPY lexicon ./lexicon
COPY --from=web /src/web/dist ./web/dist
EXPOSE 8080
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8080"]
