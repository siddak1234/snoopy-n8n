# snoopy-n8n

A self-hosted [n8n](https://n8n.io/) workflow automation platform for document processing. Ingests invoices and receipts via email or direct upload, runs them through Gemini-powered OCR and extraction, and outputs structured financial JSON.

---

## Table of Contents

- [What This Is](#what-this-is)
- [Architecture Overview](#architecture-overview)
- [Tech Stack](#tech-stack)
- [Repository Structure](#repository-structure)
- [Docker Architecture](#docker-architecture)
- [Pipelines](#pipelines)
- [Authentication Modes](#authentication-modes)
- [Environment Files](#environment-files)
- [Environment Variables Reference](#environment-variables-reference)
- [CI/CD Pipeline](#cicd-pipeline)
- [Local Development](#local-development)
- [Production Deployment](#production-deployment)
- [Operations & Scripts](#operations--scripts)
- [Backup Strategy](#backup-strategy)
- [Security Model](#security-model)

---

## What This Is

snoopy-n8n is a single Docker container running a customized n8n instance. It handles end-to-end document processing:

1. PDFs arrive via Gmail or direct webhook
2. They are stored in Google Cloud Storage (GCS)
3. Gemini AI extracts structured data (line items, totals, GL codes)
4. Output is validated JSON conforming to a strict schema

The only runtime dependency added on top of stock n8n is `pdf-lib` — a Node.js library for PDF manipulation used inside n8n Code nodes.

---

## Architecture Overview

```
                        ┌──────────────────────┐
                        │   Gmail Inbox / API   │
                        └──────────┬───────────┘
                                   │  PDF attachments / webhook triggers
                                   ▼
                        ┌──────────────────────┐
                        │    n8n  (Docker)      │
                        │    Self-Hosted        │
                        │    Port 5678          │
                        └───┬──────┬────────┬──┘
                            │      │        │
             ┌──────────────┘      │        └──────────────┐
             │                     │                        │
             ▼                     ▼                        ▼
  ┌──────────────────┐   ┌─────────────────┐   ┌───────────────────┐
  │  Google Cloud    │   │   Gemini AI      │   │   SQLite DB       │
  │  Storage (GCS)   │   │  (AI Studio)     │   │  (local volume)   │
  │  PDF storage     │   │  OCR + extract   │   │  workflows,       │
  └──────────────────┘   └─────────────────┘   │  credentials,     │
             │                     │            │  executions       │
             └──────────┬──────────┘            └───────────────────┘
                        ▼
          ┌─────────────────────────────┐
          │   Structured JSON Output    │
          │  vendor · line items ·      │
          │  totals · GL codes ·        │
          │  tax breakdown · metadata   │
          └─────────────────────────────┘
```

**Data flow summary:**

```
Email / Upload
    → Gmail Trigger or Webhook
    → PDF extracted from attachment
    → Uploaded to GCS (client-namespaced path)
    → Gemini OCR call (gs:// multimodal or base64)
    → Line-item extraction + GL code assignment
    → JSON schema validation
    → Structured output (downstream / webhook response)
```

---

## Tech Stack

| Component | Technology | Version | Purpose |
|-----------|-----------|---------|---------|
| Workflow engine | n8n (self-hosted, Docker) | 2.8.3 | Orchestration, triggers, credentials, UI |
| LLM / OCR | Gemini via Google AI Studio | — | Document OCR, extraction, inference |
| Object storage | Google Cloud Storage | — | PDF and document file storage |
| Database | SQLite | — | Workflows, credentials, execution history |
| PDF processing | pdf-lib | 1.17.1 | PDF manipulation in Code nodes |
| Containerization | Docker + Docker Compose | — | Runtime and environment isolation |
| GCP auth | Google ADC | — | Service account authentication (3 modes) |
| CI | GitHub Actions | — | PR validation, Docker build, smoke tests |
| CD | GitHub Actions + SSH | — | Push to GHCR, deploy to DigitalOcean droplet |
| Image registry | GitHub Container Registry (GHCR) | — | Built image hosting |

---

## Repository Structure

```
snoopy-n8n/
│
├── Dockerfile                   # Custom n8n image: extends n8nio/n8n, adds pdf-lib
│
├── docker-compose.yml           # Base compose: ports, volumes, shared env vars
├── docker-compose.local.yml     # Local dev overlay: debug logs, mounts ./secrets
├── docker-compose.prod.yml      # Production overlay: info logs, healthcheck
│
├── .env.local.example           # Local dev env template — copy to .env.local
├── .env.prod.example            # Production env template — copy to .env.prod
│                                # (.env.local and .env.prod are gitignored)
│
├── scripts/
│   ├── up.sh                    # Start local stack (wraps docker compose)
│   ├── down.sh                  # Stop local stack
│   ├── logs.sh                  # Tail container logs
│   └── smoke-cleanup.sh         # 5-step local smoke validation
│
├── .github/
│   └── workflows/
│       ├── ci.yml               # PR checks: compose validate, build, healthcheck
│       └── deploy.yml           # Push to main: build image → GHCR → SSH deploy
│
├── workflows/
│   └── exports/                 # Versioned n8n workflow exports (JSON)
│                                # Naming: <domain>-<action>-<version>.json
│
├── secrets/                     # GCP service account JSON keys (gitignored)
│   └── .gitkeep                 # Keeps the directory tracked without exposing keys
│
├── data/                        # n8n persistent state (gitignored)
│   ├── database.sqlite          # All workflows, credentials, execution history
│   ├── nodes/                   # Installed community nodes
│   └── storage/                 # n8n internal file storage
│
├── docs/
│   ├── README.md                # Extended architecture docs
│   ├── CONTRIBUTING.md          # Commit conventions, PR checklist, secrets policy
│   ├── CHANGELOG.md             # Version history
│   └── REFACTOR.md              # Planned and completed refactors
│
└── CLAUDE.md                    # Instructions for Claude Code (AI assistant)
```

---

## Docker Architecture

The image and runtime are split across three compose files that are always stacked with `--env-file` passed explicitly.

### Dockerfile

```
n8nio/n8n:2.8.3 (digest-pinned)
    └── npm install -g pdf-lib@1.17.1
    └── symlink pdf-lib into n8n's node_modules
```

The base image is pinned by SHA256 digest (not just tag) to prevent silent upstream changes. `pdf-lib` is installed globally and symlinked so n8n's Code nodes can `require('pdf-lib')` when `NODE_FUNCTION_ALLOW_EXTERNAL=pdf-lib` is set.

### Compose Layer Stack

```
docker-compose.yml          (always included — base)
    +
docker-compose.local.yml    (local dev)
    OR
docker-compose.prod.yml     (production)
```

| File | What it adds |
|------|-------------|
| `docker-compose.yml` | Port binding (`127.0.0.1:5678`), `./data` volume, all env vars via `${VAR}` references, `restart: unless-stopped` |
| `docker-compose.local.yml` | `N8N_LOG_LEVEL=debug`, mounts `./secrets:/secrets:ro`, passes `GOOGLE_APPLICATION_CREDENTIALS` |
| `docker-compose.prod.yml` | `N8N_LOG_LEVEL=info`, healthcheck (`/healthz` every 30s) |

Port is bound to `127.0.0.1` only — n8n is never directly internet-accessible. In production it sits behind an HTTPS reverse proxy (Nginx, Caddy, etc.).

### Why `--env-file` is Always Explicit

Docker Compose silently loads `.env` if it exists. This repo avoids that implicit behavior entirely — every compose command passes `--env-file .env.local` or `--env-file .env.prod` explicitly, making the active configuration unambiguous.

---

## Pipelines

### Invoice / Receipt Processing

```
Webhook or manual trigger
    → Receive PDF (binary or URL)
    → Upload PDF to GCS
        path: /<client>/<doc-type>/<year>/<month>/<filename>
    → Call Gemini (multimodal, gs:// URI or base64)
        prompt: extract vendor, line items, totals, tax, dates
    → Assign GL codes per line item
    → Validate output against JSON schema
        (malformed responses → error handler with diagnostics)
    → Return structured JSON
```

### Email Ingestion

```
Gmail Trigger (monitors inbox)
    → New email arrives
    → Extract PDF attachments
    → Upload each PDF to GCS (client-namespaced path)
    → Trigger invoice processing pipeline for each document
```

### Output Schema (simplified)

```json
{
  "vendor": { "name": "...", "address": "..." },
  "invoice_date": "YYYY-MM-DD",
  "line_items": [
    {
      "description": "...",
      "quantity": 1,
      "unit_price": 0.00,
      "total": 0.00,
      "gl_code": "..."
    }
  ],
  "subtotal": 0.00,
  "tax": 0.00,
  "total": 0.00
}
```

---

## Authentication Modes

GCP authentication is handled differently depending on the environment.

### Mode 1 — Local dev with JSON key (default for local)

A GCP service account JSON key is placed in `./secrets/`. The local compose overlay mounts this directory read-only into the container at `/secrets` and sets `GOOGLE_APPLICATION_CREDENTIALS=/secrets/gcs-service-account.json`.

```
./secrets/gcs-service-account.json   (gitignored, never committed)
    → mounted at /secrets inside container
    → GOOGLE_APPLICATION_CREDENTIALS points to it
    → GCS and Gemini calls authenticate via this key
```

### Mode 2 — GCP VM metadata ADC (for GCP Compute Engine)

When deployed on a GCP VM with a service account attached, the container inherits Application Default Credentials automatically via the metadata server. No JSON key or env var needed.

### Mode 3 — n8n Credentials per workflow (recommended for production)

API keys (Gemini, GCS) are stored encrypted in n8n's Credentials DB (`./data/database.sqlite`), encrypted with `N8N_ENCRYPTION_KEY`. Each workflow node references a named credential. No API keys are passed via environment variables.

---

## Environment Files

| File | Committed | Purpose |
|------|-----------|---------|
| `.env.local.example` | Yes | Local dev template — copy to `.env.local` |
| `.env.prod.example` | Yes | Production template — copy to `.env.prod` |
| `.env.local` | No (gitignored) | Active local config with real values |
| `.env.prod` | No (gitignored) | Active production config with real values |
| `secrets/*.json` | No (gitignored) | GCP service account keys |

**Never commit `.env.local`, `.env.prod`, or anything in `secrets/`.**

The `.env.local.example` and `.env.prod.example` files contain only placeholder values (`CHANGE_ME`, `<replace_me>`) — they are safe to commit and serve as the source of truth for what variables are required.

---

## Environment Variables Reference

| Variable | Required | Description |
|----------|----------|-------------|
| `N8N_ENCRYPTION_KEY` | Yes | Encrypts all credentials stored in SQLite. Never change after initial setup — existing credentials become unreadable. |
| `N8N_BASIC_AUTH_ACTIVE` | Yes | Enables basic auth on the n8n UI (`true`) |
| `N8N_BASIC_AUTH_USER` | Yes | n8n UI login username |
| `N8N_BASIC_AUTH_PASSWORD` | Yes | n8n UI login password |
| `N8N_PORT` | Yes | Internal container port (default: `5678`) |
| `N8N_PROTOCOL` | Yes | `http` (local) or `https` (behind reverse proxy) |
| `N8N_HOST` | Yes | Hostname n8n is reachable at (e.g. `n8n.example.com`) |
| `WEBHOOK_URL` | Yes | Full public URL for webhook triggers (must match how clients reach n8n) |
| `N8N_PROXY_HOPS` | Prod only | Number of reverse proxy hops (`1` for single proxy) |
| `NODE_FUNCTION_ALLOW_EXTERNAL` | Yes | Allowlist for `require()` in Code nodes — must include `pdf-lib` |
| `GENERIC_TIMEZONE` | Yes | Timezone for cron triggers (e.g. `America/Chicago`) |
| `TZ` | Yes | System timezone (should match `GENERIC_TIMEZONE`) |
| `GOOGLE_APPLICATION_CREDENTIALS` | Local dev only | Path to GCP service account JSON inside container |
| `GOOGLE_CLOUD_PROJECT` | Local dev | GCP project ID (for ADC-based calls) |
| `GOOGLE_CLOUD_LOCATION` | Local dev | GCP region (e.g. `us-central1`) |
| `EXECUTIONS_DATA_PRUNE` | Yes | Enable automatic execution log pruning (`true`) |
| `EXECUTIONS_DATA_MAX_AGE` | Yes | Hours to retain execution data (e.g. `168` = 7 days) |

---

## CI/CD Pipeline

### CI — Pull Request Validation (`.github/workflows/ci.yml`)

Runs on every PR targeting `main`. Uses a minimal `.env.ci` file with placeholder values (no real secrets).

```
1. Validate compose config (docker compose config --quiet)
2. Assert no /secrets mount in prod overlay
3. Build Docker image
4. Start container, wait for /healthz HTTP 200
5. Verify pdf-lib loads inside the container
6. Assert GEMINI_API_KEY is not set in container env
7. Assert EXECUTIONS_DATA_PRUNE=true
8. Teardown
```

### CD — Deploy on Push to Main (`.github/workflows/deploy.yml`)

Runs on every push to `main`.

```
1. Build Docker image
2. Push to GHCR (ghcr.io/siddak1234/snoopy-n8n)
   Tags: <version-tag> + sha-<commit>
3. SSH into DigitalOcean droplet
4. Pull latest image
5. docker compose up -d --pull always (uses .env.prod on the droplet)
6. Wait for /healthz HTTP 200
7. If health check fails:
   → Roll back to previous image digest
   → Exit 1
8. Prune old images
```

**GitHub Actions secrets required:**

| Secret | Used in |
|--------|---------|
| `DO_HOST` | SSH host (droplet IP) |
| `DO_USER` | SSH username |
| `DO_SSH_KEY` | SSH private key |
| `GHCR_TOKEN` | GHCR login on the droplet |
| `GITHUB_TOKEN` | Auto-provided — GHCR push from Actions |

---

## Local Development

### Prerequisites

- Docker Desktop
- A GCP service account JSON key with Storage and Gemini permissions

### Setup

```bash
# 1. Clone
git clone <repo-url> && cd snoopy-n8n

# 2. Copy env template and fill in values
cp .env.local.example .env.local
# Edit .env.local: set N8N_ENCRYPTION_KEY, N8N_BASIC_AUTH_PASSWORD, GOOGLE_CLOUD_PROJECT

# 3. Place GCP service account key
cp ~/Downloads/your-sa-key.json secrets/gcs-service-account.json

# 4. Start
./scripts/up.sh

# 5. Validate
./scripts/smoke-cleanup.sh

# 6. Open n8n
open http://localhost:5678
```

The local stack runs with `N8N_LOG_LEVEL=debug` and mounts `./secrets` read-only into the container.

### Rebuild after Dockerfile changes

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml build --no-cache
```

---

## Production Deployment

### Prerequisites on the VM

- Docker + Docker Compose installed
- `.env.prod` file created from `.env.prod.example` with real values
- `./data` directory created and owned by UID 1000 (n8n runs as this user)

### First-time setup

```bash
# On the VM
cp .env.prod.example .env.prod
# Fill in: N8N_ENCRYPTION_KEY, N8N_BASIC_AUTH_PASSWORD, N8N_HOST, WEBHOOK_URL

mkdir -p data && sudo chown -R 1000:1000 data

# Validate config before starting
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml config --quiet

# Start
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Reverse proxy

n8n binds to `127.0.0.1:5678` only. Put Nginx, Caddy, or Traefik in front with HTTPS termination. Forward headers:

```
Host
X-Forwarded-For
X-Forwarded-Proto
```

Set `N8N_PROTOCOL=https` and `N8N_PROXY_HOPS=1` in `.env.prod`.

### Ongoing deploys

Handled automatically by the CD pipeline on every push to `main`. To deploy manually:

```bash
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml pull
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d
```

---

## Operations & Scripts

All scripts target local dev only. On production, use the `docker compose --env-file .env.prod ...` commands directly.

| Command | What it does |
|---------|-------------|
| `./scripts/up.sh` | Start local stack |
| `./scripts/down.sh` | Stop local stack |
| `./scripts/logs.sh` | Tail container logs (follows) |
| `./scripts/smoke-cleanup.sh` | 5-step validation: service check, startup, container status, ADC env, pdf-lib load |

### Useful one-liners

```bash
# Check container health
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml ps

# Verify pdf-lib loads
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml \
  exec n8n sh -lc 'node -e "require(\"pdf-lib\"); console.log(\"ok\")"'

# Check ADC path in container (local)
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml \
  exec n8n sh -lc 'echo $GOOGLE_APPLICATION_CREDENTIALS; ls -la /secrets'

# Live logs (prod)
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml logs -f n8n
```

---

## Backup Strategy

**What to back up:** `./data/` — contains the SQLite database, all workflows, all encrypted credentials, and execution history.

**Schedule:** Nightly. Recommended retention: 7 daily + 4 weekly. Test restores periodically.

**Critical:** `N8N_ENCRYPTION_KEY` is required to decrypt stored credentials. If the key is lost, all encrypted credential data is permanently unrecoverable. Store it separately from the `./data` backup.

Backup automation is currently manual (planned in REF-009).

---

## Security Model

| Concern | How it's handled |
|---------|-----------------|
| Secrets in git | `.env.local`, `.env.prod`, `secrets/` are gitignored. Only `*.example` templates (with placeholders) are committed. |
| Secrets in Docker build | `.dockerignore` excludes all `.env*` files and `secrets/` from build context. |
| API keys in container env | API keys live in n8n's encrypted Credentials DB, not in env vars. Only infrastructure vars (`N8N_*`, `WEBHOOK_URL`, etc.) are passed via env. |
| Secrets mount in prod | CI asserts that `/secrets` is not present in the prod compose config. The `./secrets` mount only exists in `docker-compose.local.yml`. |
| Port exposure | n8n binds to `127.0.0.1:5678` only — not accessible directly from the internet. |
| Image integrity | Base image is pinned by SHA256 digest in the Dockerfile, preventing silent upstream tag changes. |
| Credential encryption | All n8n credentials are encrypted at rest using `N8N_ENCRYPTION_KEY` (AES-256). |
| CI secrets | All deploy credentials (SSH key, host, GHCR token) are stored as GitHub Actions secrets, never in the repository. |
