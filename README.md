# snoopy-n8n

## Current Architecture

- Core runtime: self-hosted `n8n` container only.
- Document path: Google Drive PDF -> Mistral Document OCR (`mistral-ocr-latest`) -> downstream logic.
- Storage: Google Cloud Storage (GCS) remains the system of record for input/output artifacts.
- Removed from repo runtime: local PDF/image rendering pipeline and MCP helper services.

## What Is Kept

- `n8n` service in `docker-compose.yml`
- Service account mount for ADC:
  - `./secrets/gcs-service-account.json:/run/secrets/gcp-sa.json:ro`
- GCS auth env on n8n:
  - `GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-sa.json`
- Persistent n8n data bind mount:
  - `./data:/home/node/.n8n`

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
docker compose exec snoopy-n8n sh -lc 'echo $GOOGLE_APPLICATION_CREDENTIALS'

# 4) Mistral OCR path is documented/configured in repo docs
rg -n "Mistral Document OCR|mistral-ocr-latest" README.md

# 5) MCP/local-render references are removed
rg -n "receipt-assembler|assemble_from_manifest|pdf-renderer|X-Internal-Token|pdftoppm|pdfinfo|ghostscript|imagemagick|mutool|gotenberg" -S . --glob '!README.md' --glob '!scripts/smoke-cleanup.sh'
```

Optional helper:

```bash
./scripts/smoke-cleanup.sh
```
