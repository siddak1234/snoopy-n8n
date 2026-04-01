# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this repo is

A self-hosted **n8n workflow automation platform** for document processing (invoices, receipts). Single Docker container running n8n with `pdf-lib` baked in, backed by SQLite, with Google Cloud integration for storage and Gemini AI inference.

## Commands

```bash
# Local dev
./scripts/up.sh          # start (uses .env.local + docker-compose.local.yml)
./scripts/down.sh        # stop
./scripts/logs.sh        # tail logs
./scripts/smoke-cleanup.sh  # 5-step smoke check

# Manual compose (always pass --env-file explicitly)
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d
docker compose --env-file .env.prod  -f docker-compose.yml -f docker-compose.prod.yml  up -d

# Rebuild after Dockerfile changes
docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml build --no-cache
```

## Environment

| File | Purpose |
|------|---------|
| `.env.local.example` | Local dev template -> copy to `.env.local` |
| `.env.prod.example` | Production template -> copy to `.env.prod` |

Never commit `.env`, `.env.local`, `.env.prod`, or `secrets/*.json`.

## Architecture

- **Base:** `docker-compose.yml` (ports, volumes, shared env, restart policy)
- **Dev overlay:** `docker-compose.local.yml` (debug logs, `./secrets` mount for JSON ADC)
- **Prod overlay:** `docker-compose.prod.yml` (info logs, healthcheck)
- **Image:** [Dockerfile](Dockerfile) extends `n8nio/n8n:2.8.3`, installs `pdf-lib@1.17.1`. Requires `NODE_FUNCTION_ALLOW_EXTERNAL=pdf-lib` at runtime.
- **State:** `./data/` (gitignored) — SQLite DB, credentials, community nodes. Back up nightly.

## Conventions

- Workflow exports go to `workflows/exports/`; naming: `<domain>-<action>-<version>` (e.g., `inbox-router-v1`)
- See [docs/CONTRIBUTING.md](docs/CONTRIBUTING.md) for commit conventions, PR checklist, and secrets policy
- n8n runs behind HTTPS reverse proxy; set `N8N_PROTOCOL=https`, `WEBHOOK_URL`, and `N8N_PROXY_HOPS=1`
