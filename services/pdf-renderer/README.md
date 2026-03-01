# PDF Renderer Service

## Endpoint

`POST /render`

Request JSON:

```json
{
  "job_id": "...",
  "bucket": "invoice-ai-poc-storage-claros",
  "object": "incoming/<filename>.pdf"
}
```

Success response JSON:

```json
{
  "job_id": "...",
  "bucket": "...",
  "source_object": "incoming/<filename>.pdf",
  "pages_prefix": "pages/<job_id>/",
  "page_count": 3,
  "pages": [
    {"page": 1, "gcs_object": "pages/<job_id>/page-0001.jpg"}
  ]
}
```

The service also writes `results/<job_id>/pages_manifest.json` to GCS.

## Auth

POC shared-secret auth is required via header:

- `X-Internal-Token: <token>`

Set token with env var:

- `INTERNAL_TOKEN`

## Environment Variables

- `GOOGLE_APPLICATION_CREDENTIALS=/run/secrets/gcp-sa.json`
- `INTERNAL_TOKEN=change-me`

## IAM (least privilege)

Grant the service account minimal object-level permissions on the target bucket:

- `storage.objects.get` (read source PDF)
- `storage.objects.create` (write rendered pages + manifest)
- `storage.objects.delete` (optional, only if future cleanup requires deletes)

Avoid bucket-admin roles.

## Run (docker compose)

From repo root:

```bash
docker compose up -d --build pdf-renderer
```

## Test

```bash
curl -X POST http://localhost:8081/render \
  -H "Content-Type: application/json" \
  -H "X-Internal-Token: change-me" \
  -d '{"job_id":"test123","bucket":"invoice-ai-poc-storage-claros","object":"incoming/somefile.pdf"}'
```

Verify outputs:

```bash
gsutil ls gs://invoice-ai-poc-storage-claros/pages/test123/ | head
gsutil cat gs://invoice-ai-poc-storage-claros/results/test123/pages_manifest.json | head
```
