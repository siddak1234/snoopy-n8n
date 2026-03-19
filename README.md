# snoopy-n8n

## Current Architecture

- Core runtime: self-hosted `n8n` container only.
- Document path: PDFs stored in GCS -> invoice combination/merge -> downstream logic.
- Storage: Google Cloud Storage (GCS) remains the system of record for input/output artifacts.
- Removed from repo runtime: local PDF rendering/OCR infrastructure and MCP helper services.

## What Is Kept

- `n8n` service in `docker-compose.yml`
- Service account mount for ADC:
  - `./secrets/gcs-service-account.json:/run/secrets/gcp-sa.json:ro`
- GCS auth env on n8n:
  - `GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-sa.json`
- Persistent n8n data bind mount:
  - `./data:/home/node/.n8n`
- Extra runtime dependency for Code nodes:
  - `pdf-lib` installed in the n8n image and allowlisted via `NODE_FUNCTION_ALLOW_EXTERNAL=pdf-lib`

## Bring Up

```bash
docker compose build --no-cache
docker compose up -d
docker compose logs -f n8n
```

## Smoke Checks

```bash
# 1) n8n service is the only compose service
docker compose config --services

# 2) n8n is up
docker compose ps

# 3) GCS env wiring exists in container
docker compose exec n8n sh -lc 'echo $GOOGLE_APPLICATION_CREDENTIALS'

# 4) pdf-lib allowlist is present
rg -n "NODE_FUNCTION_ALLOW_EXTERNAL=pdf-lib" .env.example
```

Optional helper:

```bash
./scripts/smoke-cleanup.sh
```
