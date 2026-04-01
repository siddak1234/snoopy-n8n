# Refactor Tracker — Autom8x (A8X)

Tracks planned, in-progress, and completed refactoring efforts.

## Status Legend

| Status        | Meaning                                           |
|---------------|---------------------------------------------------|
| **Planned**   | Identified and scoped, not yet started             |
| **In Progress** | Actively being worked on                        |
| **Complete**  | Merged to main, verified in production             |
| **Deferred**  | Deprioritized, revisit later                       |

---

## Refactor Items

### REF-001: Gemini Migration
- **Status:** Complete
- **Description:** Migrate all LLM inference from Mistral to Gemini (Google AI Studio). Replace prompt templates, credential configuration, and API call nodes.
- **Outcome:** All workflows now use Gemini. Mistral nodes, credentials, and prompt templates fully removed. API key auth via env var.

### REF-002: JSON Schema Validation Layer
- **Status:** Complete
- **Description:** Add strict JSON schema validation to Gemini extraction output. Ensures line items, GL codes, totals, and metadata conform to defined structure before downstream consumption.
- **Outcome:** Validation Code node added after Gemini extraction. Malformed responses trigger error handler with meaningful diagnostics.

### REF-003: GCS Folder Restructure
- **Status:** Complete
- **Description:** Reorganize GCS bucket paths from flat structure to client-namespaced hierarchy (`/<client>/<doc-type>/<year>/<month>/`).
- **Outcome:** All upload and retrieval nodes updated. Existing files migrated. Path generation is now dynamic based on client metadata.

### REF-004: Sub-Workflow Modularization
- **Status:** Planned
- **Description:** Extract shared pipeline stages (PDF upload to GCS, Gemini OCR call, schema validation) into reusable sub-workflows. Main workflows call these as sub-workflow nodes.
- **Rationale:** Reduces duplication across invoice and email ingestion pipelines. Enables single-point updates for shared logic.
- **Scope:** Identify 3-5 shared stages. Create sub-workflows. Update parent workflows to reference them.

### REF-005: CI/CD Pipeline
- **Status:** Planned
- **Description:** Implement automated CI/CD for testing and deployment. Run smoke tests on PR, build Docker image on merge to main, deploy to target VM.
- **Rationale:** Currently deployment is manual (`docker compose up`). Automation reduces risk and speeds up releases.
- **Scope:** GitHub Actions workflow with smoke test, Docker build, and SSH deploy steps.

### REF-006: Multi-Client Namespacing
- **Status:** Planned
- **Description:** Introduce client-level namespacing across workflows, GCS paths, and n8n variables. Support onboarding new clients without duplicating workflows.
- **Rationale:** Currently pipeline is configured for one live client. Scaling requires parameterized workflows that resolve client context dynamically.
- **Scope:** Client config table (n8n variables or external), parameterized workflow inputs, GCS path templating per client.

### REF-007: Repo Cleanup
- **Status:** Complete
- **Description:** Remove dead code, empty directories, redundant files, and duplicate documentation. Consolidate overlapping deployment sections in README.
- **Outcome:** Deleted `custom-nodes/mistral/` (dead after Gemini migration), empty `services/` and `workflows/templates/` dirs, redundant `.env.example`, no-op `docker-compose.gcp.yml`, `scripts/export-workflows.md` (content in CONTRIBUTING.md), `claude/conventions.md` (content in CONTRIBUTING.md). Removed duplicate `restart: unless-stopped` from prod overlay. Deduplicated `.gitignore` from 179 to 48 lines. Consolidated root README from 179 to 83 lines (5 overlapping deployment sections merged into 1). Trimmed CLAUDE.md from 102 to 42 lines.

### REF-008: Secret Remediation
- **Status:** Complete (verified 2026-03-30)
- **Description:** Audit git history for committed secrets and remediate if found.
- **Outcome:** Verified via `git log --all --diff-filter=A` — `.env`, `.env.local`, `.env.prod`, and `secrets/` were **never committed** to git history. No BFG purge needed. Active keys in local `.env` are on-disk only and not exposed via git. Remaining action: clean up `.env` to remove stale/duplicate vars (`RENDER_AUTH_TOKEN`, duplicate `GOOGLE_CLOUD_PROJECT`) and strip any keys that are redundant with n8n Credentials DB (see REF-010).

### REF-009: Backup Automation
- **Status:** Planned
- **Description:** Implement automated nightly backup of `./data` directory to GCS or remote storage.
- **Rationale:** Backup strategy is documented but has zero implementation. `N8N_ENCRYPTION_KEY` is non-rotatable — if the SQLite DB is lost without backup, all encrypted credentials are unrecoverable.
- **Scope:** Cron-based backup script, GCS upload, retention policy (7 daily + 4 weekly), restore runbook, periodic restore testing.

### REF-010: Env Cleanup — Strip Redundant Keys
- **Status:** Planned
- **Description:** Remove API keys from `.env` that are already stored in the n8n Credentials DB.
- **Rationale:** `GEMINI_API_KEY`, `GEMINI_MODEL`, `GOOGLE_CLOUD_PROJECT`, `GOOGLE_CLOUD_LOCATION`, and `RENDER_AUTH_TOKEN` are either redundant (credentials live in n8n) or stale. Keeping them creates confusion and an unnecessary attack surface if the file is ever leaked.
- **Scope:** Export workflows, grep for `process.env` usage in Code nodes. Remove any key not read via `process.env`. Update `docker-compose.yml` to drop corresponding env passthrough lines. Update `.env.local.example` and `.env.prod.example` to match.

### REF-011: CI/CD Pipeline — GitHub Actions
- **Status:** Planned
- **Description:** Implement GitHub Actions workflows for PR validation, Docker image build, and production deployment.
- **Rationale:** All deployments are currently manual `docker compose up` commands. No automated guardrails on PRs. Risk of shipping broken image to prod.
- **Scope:**
  - `ci.yml` — on PR: lint compose config, run smoke checks (docker build + healthcheck)
  - `deploy.yml` — on push to `main`: build image, push to registry (GHCR or GCR), SSH deploy to VM, verify health
  - Secrets stored in GitHub Actions secrets (not repo files)
  - See deployment roadmap in docs for implementation order.
