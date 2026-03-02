# receipt-assembler

Internal MCP-style service that computes invoice `start_page` (after Gideon summary pages) and groups subsequent pages into invoice chunks using page-pair Gemini checks over GCS `gs://` image URIs.

## Endpoints

- `GET /healthz` -> `{ "ok": true }`
- `POST /assemble_invoices`
- `POST /assemble_from_manifest`

## Auth

Both POST endpoints require header:

- `X-Internal-Token: <INTERNAL_TOKEN>`

## `POST /assemble_invoices` request

```json
{
  "job_id": "string",
  "bucket": "string",
  "page_count": 182,
  "pages_prefix": "pages/{job_id}/",
  "debug": false
}
```

## `POST /assemble_from_manifest` request

```json
{
  "bucket": "invoice-ai-poc-storage-claros",
  "manifest_object": "manifests/2026-03-02T03-45-34-314Z_incoming_Invoice 10194 FLL.pdf.json",
  "max_pages": 50,
  "debug": true
}
```

Behavior:
- Derives `job_id` from `manifests/<JOB_ID>.json`
- Derives `pages_prefix` as `pages/<JOB_ID>/`
- Reads manifest from GCS and uses `page_count` if present
- Uses `max_pages` as test cap
- Returns `debug_traces` when `debug=true` (capped to 200)

## Response shape

```json
{
  "job_id": "string",
  "bucket": "string",
  "start_page": 8,
  "groups": [
    {
      "group_id": "g0001",
      "pages": [8, 9],
      "kind": "invoice",
      "multi_invoices_on_page": false,
      "notes": ""
    }
  ],
  "stats": {
    "gemini_calls": 0,
    "pair_checks": 0,
    "jpg_jpeg_fallbacks": 0
  },
  "debug_traces": []
}
```

## Env vars

- `GEMINI_API_KEY` (required)
- `GEMINI_MODEL` (optional, default `gemini-1.5-flash`)
- `INTERNAL_TOKEN` (required)
- `GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-sa.json`

## Run

```bash
docker compose up -d --build receipt-assembler
```

## Host curl test (real manifest example)

```bash
curl -X POST http://localhost:8090/assemble_from_manifest \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: change-me" \
  -d '{"bucket":"invoice-ai-poc-storage-claros","manifest_object":"manifests/2026-03-02T03-45-34-314Z_incoming_Invoice 10194 FLL.pdf.json","max_pages":50,"debug":true}'
```

## n8n internal URL

`http://receipt-assembler:8090/assemble_from_manifest`
