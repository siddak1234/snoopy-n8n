# Autom8x (A8X) — n8n Automation Backend

Autom8x is a self-hosted n8n workflow automation platform for document processing. It ingests invoices, receipts, and emails, runs them through Gemini-powered OCR and extraction, and outputs structured financial data.

## Architecture

```
                          +-----------------+
                          |   Gmail / API   |
                          +--------+--------+
                                   |
                                   v
                          +--------+--------+
                          |   n8n (Docker)  |
                          |   Self-Hosted   |
                          +---+----+----+---+
                              |    |    |
               +--------------+    |    +--------------+
               |                   |                   |
               v                   v                   v
      +--------+------+   +-------+-------+   +-------+-------+
      | Google Cloud   |   |   Gemini AI   |   |   SQLite DB   |
      | Storage (GCS)  |   |  (AI Studio)  |   |  (Local Vol)  |
      +---------------+   +---------------+   +---------------+
               |                   |
               v                   v
      +--------+------------------+--------+
      |        Structured JSON Output      |
      |  (Line Items, GL Codes, Metadata)  |
      +------------------------------------+
```

## Tech Stack

| Component         | Technology                        | Purpose                              |
|-------------------|-----------------------------------|--------------------------------------|
| Workflow Engine   | n8n 2.8.3 (self-hosted, Docker)   | Orchestration and automation         |
| LLM / OCR        | Gemini via Google AI Studio       | Document OCR, extraction, inference  |
| Object Storage    | Google Cloud Storage (GCS)        | PDF and document file storage        |
| Database          | SQLite (local volume)             | Workflows, credentials, executions   |
| PDF Processing    | pdf-lib 1.17.1                    | PDF manipulation in Code nodes       |
| Containerization  | Docker + Docker Compose           | Deployment and environment isolation |
| Auth              | Google ADC (2 modes)              | GCP service authentication           |

## Repository Structure

```
snoopy-n8n/
├── docs/                    # Project documentation (this folder)
├── data/                    # Persistent n8n state (gitignored)
│   ├── database.sqlite
│   ├── nodes/node_modules/
│   └── storage/
├── scripts/                 # Operational scripts (up, down, logs, smoke)
├── secrets/                 # Local dev credentials (gitignored)
├── workflows/
│   └── exports/             # Named exports: <domain>-<action>-<version>
├── docker-compose.yml       # Base compose (ports, volumes, shared env)
├── docker-compose.local.yml # Local dev overlay (debug, secrets mount)
├── docker-compose.prod.yml  # Production overlay (healthcheck, info logs)
├── Dockerfile               # Custom n8n image with pdf-lib
├── CLAUDE.md                # Claude Code instructions
└── README.md                # Top-level readme
```

## Environment Variables

| Variable                        | Required | Description                                |
|---------------------------------|----------|--------------------------------------------|
| `N8N_ENCRYPTION_KEY`            | Yes      | Encrypts stored credentials                |
| `N8N_BASIC_AUTH_USER`           | Yes      | n8n UI login username                      |
| `N8N_BASIC_AUTH_PASSWORD`       | Yes      | n8n UI login password                      |
| `WEBHOOK_URL`                   | Yes      | Public URL for webhook triggers            |
| `N8N_PROTOCOL`                  | Yes      | `https` (behind reverse proxy)             |
| `N8N_PROXY_HOPS`               | Yes      | `1` (single reverse proxy)                 |
| `NODE_FUNCTION_ALLOW_EXTERNAL`  | Yes      | `pdf-lib` (allowlist for Code nodes)       |
| `GOOGLE_APPLICATION_CREDENTIALS`| Conditional | Path to ADC JSON key (local dev only)   |
| `GEMINI_API_KEY`                | Yes      | Google AI Studio API key for Gemini        |

Env files: `.env.local.example` (dev template) / `.env.prod.example` (prod template). Copy to `.env.local` / `.env.prod`. Never commit real env files.

## Getting Started

```bash
# 1. Clone the repo
git clone <repo-url> && cd snoopy-n8n

# 2. Copy env template
cp .env.local.example .env.local
# Edit .env.local with your credentials

# 3. (Local dev) Place GCP service account key
cp your-key.json secrets/gcp-sa.json

# 4. Start the local stack
./scripts/up.sh

# 5. Run smoke tests
./scripts/smoke-cleanup.sh

# 6. Open n8n UI
open http://localhost:5678
```

## Core Pipelines

### Invoice / Receipt Processing

```
PDF Upload → GCS Storage → Gemini OCR → Line-Item Extraction
→ GL Code Assignment → Strict JSON Schema Output
```

- Accepts PDF invoices and receipts
- Stores originals in GCS with structured paths
- Gemini extracts vendor, line items, totals, and tax
- Assigns general ledger (GL) codes per line item
- Outputs validated JSON conforming to a strict schema

### Email Ingestion

```
Gmail Trigger → PDF Attachment Extraction → GCS Storage
→ Downstream Workflow Trigger
```

- Monitors configured Gmail inbox for new messages
- Extracts PDF attachments from incoming emails
- Stores PDFs in GCS under client-namespaced paths
- Triggers the invoice processing pipeline for each document

## Operations

| Command                    | Purpose                         |
|----------------------------|----------------------------------|
| `./scripts/up.sh`         | Start local dev stack            |
| `./scripts/down.sh`       | Stop local dev stack             |
| `./scripts/logs.sh`       | Tail container logs (debug)      |
| `./scripts/smoke-cleanup.sh` | 5-step smoke test + cleanup   |
