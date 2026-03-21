# snoopy-n8n

## Current Architecture

- Core runtime: self-hosted `n8n` container only.
- Document path: PDFs stored in GCS -> invoice combination/merge -> downstream logic.
- Storage: Google Cloud Storage (GCS) remains the system of record for input/output artifacts.
- Removed from repo runtime: local PDF rendering/OCR infrastructure and MCP helper services.
- Only extra runtime dependency: `pdf-lib` for an n8n Code node.

## Deployment Shape

- `docker-compose.yml` — base `n8n` (persistent `./data` only; **no** `./secrets` mounts)
- `docker-compose.prod.yml` — production (`N8N_LOG_LEVEL=info`, `N8N_PROXY_HOPS`, healthcheck)
- `docker-compose.local.yml` — **local only**: debug logs + `./secrets` mounts for JSON-based ADC
- `docker-compose.gcp.yml` — **optional** GCP-only override (metadata ADC); see [docs/deploy-gcp.md](docs/deploy-gcp.md)

## Default: production on any VM (DigitalOcean, AWS, Azure, GCP, Hetzner, …)

1) Create env from example:

```bash
cp .env.prod.example .env.prod
# Edit .env.prod: set N8N_ENCRYPTION_KEY, N8N_BASIC_AUTH_*, N8N_HOST, WEBHOOK_URL, N8N_PROTOCOL, N8N_PROXY_HOPS
```
Operator safety: always pass `--env-file` (`.env.prod` for production or `.env.local` for local dev). Do not rely on Docker Compose’s implicit `.env`, since it may contain stale local secrets.

2) If you use a reverse proxy with HTTPS, ensure it forwards `Host`, `X-Forwarded-For`, and `X-Forwarded-Proto`, and set `N8N_PROTOCOL=https` plus the correct `N8N_PROXY_HOPS`.

3) Start:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps
```

**Operator safety:** `scripts/up.sh` / `scripts/down.sh` / `scripts/logs.sh` target **local** dev (`--env-file .env.local` + `docker-compose.local.yml`). On a production VM, use the command above, not those scripts.

## Auth and integration modes

1. **Generic VM (default)**  
   No provider metadata assumed. Set standard `N8N_*` / `WEBHOOK_URL` in `.env.prod`. Add optional `GOOGLE_*` or `GEMINI_*` in `.env.prod` only if your workflows need them.

2. **Local dev with Google JSON key**  
   `docker-compose.yml` + `docker-compose.local.yml`. Place key under `./secrets`, set `GOOGLE_APPLICATION_CREDENTIALS=/secrets/<file>.json` in `.env.local`. Secrets stay gitignored.

3. **Optional: GCP VM metadata ADC**  
   Add `-f docker-compose.gcp.yml` and follow [docs/deploy-gcp.md](docs/deploy-gcp.md). **Do not** use this file on non-GCP hosts expecting metadata ADC.

4. **POC API keys (e.g. Gemini)**  
   Prefer **n8n Credentials** per workflow. Optional container env: `GEMINI_API_KEY` / `GEMINI_MODEL` (see [Gemini env vars](#gemini-env-vars-optional)).

When you add a frontend, route by project/workflow and n8n auth; do not expose provider secrets in the browser.

## Gemini env vars (optional)

- **In this repo:** `GEMINI_API_KEY` and `GEMINI_MODEL` are passed only via `docker-compose.yml` from the host environment (`${GEMINI_API_KEY:-}`, `${GEMINI_MODEL:-}`). There are **no** hardcoded API keys in compose or committed env templates.
- **Local:** set in `.env.local` if a Code node or integration reads `process.env.GEMINI_API_KEY`.
- **Production:** leave unset and use n8n Credentials, or set in `.env.prod` only for deliberate POC injection.
- **Risk:** workflows stored in `./data` may still reference keys or endpoints; export and review workflows before migration.

## Environment Files

Committed templates:

- `.env.example` (shared baseline)
- `.env.local.example` (local dev + optional JSON ADC path)
- `.env.prod.example` (provider-agnostic production baseline)

Operator rule (important):
- Operators should **only edit** `.env.local` (for local dev) and `.env.prod` (for production).
- The `*.example` files are templates; they are meant to be copied once, then edited in `.env.local` / `.env.prod`.
- `.env.example` is informational/legacy and is not required for the compose commands in this repo (those commands always use `--env-file` explicitly).

Never commit:

- `.env`, `.env.local`, `.env.prod`
- `secrets/*.json`
- Any API keys

## Local Development

```bash
cp .env.local.example .env.local

docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d --build
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml logs -f n8n
```

## Minimal Smoke Checks (generic production)

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --services
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml exec n8n sh -lc 'node -e "require(\"pdf-lib\"); console.log(\"pdf-lib ok\")"'
```

## Pre-Deployment Validation (generic VM)

Run before first production deploy:

```bash
# 1) .env.prod exists and has no placeholders
test -f .env.prod
! rg -n "<replace_me>|<SET_AFTER_VM_CREATION>|n8n.example.com" .env.prod

# 2) Generic production config renders
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --quiet

# 3) Optional GCP overlay config renders (only if you plan to use it)
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml config --quiet

# 4) Generic production config should NOT include local secrets mounts
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config | grep -q "/secrets" && echo "Unexpected /secrets mount in prod config" && exit 1 || true
```

If you are intentionally using key-file auth on a non-GCP VM, treat that as an explicit override and document it in your deployment notes.

## Verify Google / ADC (non-destructive)

Does **not** print key material.

**Local (JSON under `./secrets`):**

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml exec n8n sh -lc 'echo "GOOGLE_APPLICATION_CREDENTIALS=$GOOGLE_APPLICATION_CREDENTIALS"; echo "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"; ls -la /secrets'
```

**Optional GCP stack (metadata ADC):**

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml -f docker-compose.gcp.yml exec n8n sh -lc 'echo "GOOGLE_APPLICATION_CREDENTIALS=${GOOGLE_APPLICATION_CREDENTIALS-<unset>}"; echo "GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"'
```

## Backup Expectation (Required for Production)

- Back up `./data` nightly (n8n database, workflows, credentials, runtime state).
- Keep at least 7 daily and 4 weekly backups.
- Run periodic restore tests.

## First Deployment Checklist (generic VM)

1. Copy template and edit only `.env.prod`:
   - set `N8N_ENCRYPTION_KEY`, `N8N_BASIC_AUTH_*`, `N8N_HOST`, `WEBHOOK_URL`, `N8N_PROTOCOL`, `N8N_PROXY_HOPS`.
2. Run the **Pre-Deployment Validation** block above.
3. Start stack:
   - `docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build`
4. Check health and logs:
   - `docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps`
   - `docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml logs -f n8n`
5. Confirm auth/login and webhook/public URL behavior from an external browser/caller.
6. Run representative workflows (Google integrations, Gemini/LLM paths, file-heavy flows).
7. Confirm persistence expectations:
   - `./data` is on durable disk and included in backups.
8. Rollback basic:
   - if deployment is bad, run `docker compose ... down`, restore previous `.env.prod`/image/tag, and re-run `up -d`.
