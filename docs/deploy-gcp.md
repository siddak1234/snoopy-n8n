# Optional: Deploy on Google Compute Engine (metadata ADC)

Use this **only** when the VM has a **attached service account** and you want **Application Default Credentials** without a JSON key file on disk.

## When to use

- Vertex AI / Google client libraries inside n8n should authenticate via **VM metadata**, not `GOOGLE_APPLICATION_CREDENTIALS`.
- You are **not** mounting `./secrets` on the VM.

## Compose

Add the optional override **after** `docker-compose.prod.yml`:

```bash
docker compose --env-file .env.prod \
  -f docker-compose.yml \
  -f docker-compose.prod.yml \
  -f docker-compose.gcp.yml \
  up -d --build
```

`docker-compose.gcp.yml` is a marker/optional overlay for GCP mode. The base/prod compose path no longer injects `GOOGLE_APPLICATION_CREDENTIALS`, so metadata ADC can be used without a key-file path.

## Environment

Only edit `.env.prod` for this mode (it is copied from `.env.prod.example`):

Set (uncomment in `.env.prod.example` if you copied the optional block):

- `GOOGLE_CLOUD_PROJECT` — your GCP project ID  
- `GOOGLE_CLOUD_LOCATION` — e.g. `us-central1`  

Do **not** set `GOOGLE_APPLICATION_CREDENTIALS` for this mode.

## Operational checks

- Confirm the VM service account has the IAM roles your workflows need (e.g. Vertex AI User).
- If ADC fails from inside the container, verify Docker networking can reach the metadata server for your VPC/firewall setup.

## Reverse proxy

If you terminate TLS in front of n8n, use `N8N_PROTOCOL=https`, correct `WEBHOOK_URL`, and set `N8N_PROXY_HOPS` per your proxy hop count (see main `README.md`).
