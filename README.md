# snoopy-n8n

Self-hosted n8n container for document processing. PDFs stored in GCS, processed via Gemini OCR, output as structured JSON. Only runtime dependency beyond n8n: `pdf-lib` for Code nodes.

## Deployment

Two compose overlays. Always pass `--env-file` explicitly — never rely on implicit `.env`.

| File | Role |
|------|------|
| `docker-compose.yml` | Base: ports, volumes, shared env, `restart: unless-stopped` |
| `docker-compose.local.yml` | Dev: debug logs, mounts `./secrets` for JSON ADC |
| `docker-compose.prod.yml` | Prod: info logs, healthcheck, proxy hops |

### Local development

```bash
cp .env.local.example .env.local
# Place GCP service account key in secrets/

./scripts/up.sh              # start local stack
./scripts/down.sh            # stop
./scripts/logs.sh            # tail logs
./scripts/smoke-cleanup.sh   # 5-step validation
```

### Production (any VM)

```bash
# 1. Create env and persistent storage
cp .env.prod.example .env.prod
# Set: N8N_ENCRYPTION_KEY, N8N_BASIC_AUTH_*, N8N_HOST, WEBHOOK_URL, N8N_PROTOCOL, N8N_PROXY_HOPS
mkdir -p data && sudo chown -R 1000:1000 data

# 2. Validate config
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --quiet
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config | grep -q "/secrets" && echo "ERROR: /secrets mount in prod" && exit 1 || true

# 3. Start and verify
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps
```

If behind a reverse proxy: forward `Host`, `X-Forwarded-For`, `X-Forwarded-Proto`. Set `N8N_PROTOCOL=https` and `N8N_PROXY_HOPS=1`.

**Scripts note:** `scripts/up.sh`, `down.sh`, `logs.sh`, `smoke-cleanup.sh` target local dev only. On production VMs, use the commands above.

### Smoke checks (production)

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml exec n8n sh -lc 'node -e "require(\"pdf-lib\"); console.log(\"pdf-lib ok\")"'
```

## Auth modes

| Mode | Config |
|------|--------|
| **Generic VM** (default) | Set `N8N_*` / `WEBHOOK_URL` in `.env.prod`. Use n8n Credentials per workflow for GCP/Gemini |
| **Local dev with JSON key** | `docker-compose.local.yml` mounts `./secrets`. Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env.local` |
| **GCP VM metadata ADC** | Configure VM-level service account. Container inherits ADC via metadata server |

`GEMINI_API_KEY` / `GEMINI_MODEL` can be injected via env for POC, but prefer n8n Credentials per workflow in production.

## Environment files

| File | Purpose | Committed |
|------|---------|-----------|
| `.env.local.example` | Local dev template | Yes |
| `.env.prod.example` | Production template | Yes |
| `.env.local` | Active local config | **No** |
| `.env.prod` | Active prod config | **No** |
| `secrets/*` | GCP service account keys | **No** |

### Verify ADC (non-destructive)

```bash
# Local (JSON under ./secrets)
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml exec n8n sh -lc \
  'echo "GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"; echo "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"; ls -la /secrets'
```

## Backup

Back up `./data` nightly — it contains the n8n database, workflows, credentials, and runtime state. Keep 7 daily + 4 weekly backups. Test restores periodically.

`N8N_ENCRYPTION_KEY` is required to decrypt stored credentials. If lost, all encrypted data is unrecoverable.
