# snoopy-n8n

## Current Architecture

- Core runtime: self-hosted `n8n` container only.
- Document path: PDFs stored in GCS -> invoice combination/merge -> downstream logic.
- Storage: Google Cloud Storage (GCS) remains the system of record for input/output artifacts.
- Removed from repo runtime: local PDF rendering/OCR infrastructure and MCP helper services.
- Only extra runtime dependency: `pdf-lib` for an n8n Code node.

## Deployment Shape

- `n8n` service in `docker-compose.yml`
- `docker-compose.local.yml` for local overrides (`N8N_LOG_LEVEL=debug`)
- `docker-compose.prod.yml` for production overrides (`N8N_LOG_LEVEL=info`, `N8N_PROXY_HOPS`, healthcheck)
- `./data:/home/node/.n8n` persistent bind mount
- `./secrets/gcs-service-account.json:/run/secrets/gcp-sa.json:ro` credential mount

## Environment Files

Committed templates:
- `.env.example` (shared baseline)
- `.env.local.example` (local dev shape)
- `.env.prod.example` (production shape behind HTTPS reverse proxy)

Never commit:
- `.env`
- `.env.local`
- `.env.prod`
- `secrets/gcs-service-account.json`
- Any API keys (for example `GEMINI_API_KEY`)

## Local Development

```bash
cp .env.local.example .env.local

docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d --build
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml logs -f n8n
```

## Production Startup (Cloud VM)

1) Create and fill production env:
```bash
cp .env.prod.example .env.prod
```

2) Ensure reverse proxy forwards `Host`, `X-Forwarded-For`, and `X-Forwarded-Proto`.

3) Start production stack:
```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps
```

## Minimal Smoke Checks

```bash
# n8n is the only compose service
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --services

# container is healthy/running
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps

# pdf-lib is available inside n8n runtime
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml exec n8n sh -lc 'node -e "require(\"pdf-lib\"); console.log(\"pdf-lib ok\")"'
```

## Backup Expectation (Required for Production)

- Back up `./data` nightly (this contains n8n database, workflows, credentials, and runtime state).
- Keep at least 7 daily and 4 weekly backups.
- Run a periodic restore test to a staging VM to confirm recovery works.
