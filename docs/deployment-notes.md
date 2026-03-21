# Deployment notes (ARCHIVED / WIP)

This document is an archived scratchpad.
For active deployment steps, use the runbook in `README.md`:
- `Production Preflight Checklist (generic VM)`
- `Pre-Deployment Validation (generic VM)`
- `First Deployment Checklist (generic VM)`

Historical notes:
- n8n will run as a container service in cloud later
- Need: WEBHOOK_URL, N8N_HOST, N8N_PROTOCOL=https in production
- Secrets should move to a secrets manager (AWS/GCP/Azure)
- OCR path: Google Drive PDF -> Mistral Document OCR (`mistral-ocr-latest`) -> store JSON/text outputs to GCS
