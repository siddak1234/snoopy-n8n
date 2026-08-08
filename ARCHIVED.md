# Archived

This repository is **read-only history**. It has no runtime, no deployment, and
no dependents.

## What it was

An n8n instance on a DigitalOcean droplet, running invoice-extraction and
GL-coding workflows for one client.

## Why it stopped

`ADR-0006` in `snoopy-backend` — *Exclude n8n from the target runtime* — is
**Accepted**, and `test/architecture.test.ts` there fails the build on any n8n
reference in runtime code or configuration. Automations are now typed code in
their own repositories, invoked through a versioned contract.

## What happened to everything

| Thing | Where it went |
| --- | --- |
| The droplet | Deleted. `https://n8n.autom8x.ai/healthz` → HTTP 000 |
| 24 workflows + 25 history versions | `snoopy-backend/docs/platform/legacy/n8n/` — redacted, version-controlled |
| Prompts and code-node bodies | `snoopy-backend/docs/platform/legacy/prompts/` |
| `data/` — 1.6 GB runtime volume | Deleted 2026-08-07 after extraction and verification |
| 237 client invoice PDFs it held | Deleted by decision. From an earlier pipeline generation; matched no database row |
| `deploy.yml` | Deleted. It still targeted the deleted droplet and referenced `DO_HOST`, `DO_USER`, and `DO_SSH_KEY` |

## Before you archive on GitHub

Revoke the repository secrets — they outlive the workflow that used them:
`DO_HOST`, `DO_USER`, `DO_SSH_KEY`, `GHCR_TOKEN`.

Nothing here should be restarted. If n8n is ever wanted again it would be a new
decision superseding ADR-0006, not a revival of this.
