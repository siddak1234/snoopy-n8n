# receipt-assembler

Small internal MCP-style service that classifies rendered page images in GCS and groups consecutive receipt pages.

## Endpoint

`POST /assemble_receipts`

Request JSON:

```json
{
  "job_id": "string",
  "bucket": "string",
  "start_page": 1,
  "page_count": 182,
  "pages_prefix": "pages/{job_id}/"
}
```

Response JSON:

```json
{
  "job_id": "...",
  "receipt_start_page": 13,
  "receipts": [
    {
      "receipt_id": "r0001",
      "pages": [13, 14],
      "multi_receipts_on_page": false,
      "notes": "POC grouping of consecutive receipt pages"
    }
  ],
  "stats": {
    "gemini_calls": 182
  }
}
```

## Env vars

- `GEMINI_API_KEY` (required)
- `GEMINI_MODEL` (optional, default `gemini-1.5-flash`)

## Health

`GET /healthz` => `{ "ok": true }`

## Internal test (from n8n network)

```bash
curl -X POST http://receipt-assembler:8090/assemble_receipts \
  -H "Content-Type: application/json" \
  -d '{"job_id":"test123","bucket":"invoice-ai-poc-storage-claros","start_page":1,"page_count":10,"pages_prefix":"pages/test123/"}'
```
