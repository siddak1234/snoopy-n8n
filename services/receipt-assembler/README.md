# receipt-assembler

Internal MCP-style service that computes invoice `start_page` (after Gideon summary pages) and groups subsequent pages into invoice chunks.

## Endpoints

- `GET /healthz` -> `{ "ok": true }`
- `POST /assemble_invoices`

## Auth

`POST /assemble_invoices` requires header:

- `X-Internal-Token: <INTERNAL_TOKEN>`

## Request JSON

```json
{
  "job_id": "string",
  "bucket": "string",
  "page_count": 182,
  "pages_prefix": "pages/{job_id}/"
}
```

## Response JSON

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
  }
}
```

## Env vars

- `GEMINI_API_KEY` (required)
- `GEMINI_MODEL` (optional, default `gemini-1.5-flash`)
- `INTERNAL_TOKEN` (required for request auth)

## Run

```bash
docker compose up -d --build receipt-assembler
```

## Local curl test (host)

```bash
curl -X POST http://localhost:8090/assemble_invoices \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: change-me" \
  -d '{"job_id":"<JOB_ID>","bucket":"invoice-ai-poc-storage-claros","page_count":182,"pages_prefix":"pages/<JOB_ID>/"}'
```

## Internal call from n8n network

`http://receipt-assembler:8090/assemble_invoices`
