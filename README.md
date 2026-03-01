# snoopy-n8n

## Code Node Built-in Module Whitelist

To allow n8n Code nodes to use only required Node built-ins for local PDF processing, the `n8n` service sets:

- `NODE_FUNCTION_ALLOW_BUILTIN=child_process,fs,path,os`
- `NODE_FUNCTION_ALLOW_EXTERNAL=`

Use non-prefixed requires in Code nodes:

- `require('child_process')`
- `require('fs')`
- `require('path')`
- `require('os')`

Do not use `require('node:child_process')` because it can fail whitelist matching.

### Restart

```bash
docker compose down
docker compose up -d --build
```

### Verify env vars are active

```bash
docker exec snoopy-n8n /bin/sh -lc "env | grep NODE_FUNCTION"
```

### Rollback

Remove the two `NODE_FUNCTION_*` lines from `docker-compose.yml`, then:

```bash
docker compose down
docker compose up -d --build
```

## Poppler In Image

Poppler is baked into the custom image via `Dockerfile` so PDF rendering works inside the container runtime (no host installs, no runtime package install).

### Quick validation

```bash
./scripts/verify-poppler.sh
docker exec -it snoopy-n8n sh -lc "pdftoppm -h | head -n 5"
docker exec -it snoopy-n8n sh -lc "pdfinfo -v | head -n 3"
```

### Rebuild and restart safely (preserves workflows)

```bash
docker compose down
docker compose up -d --build
```

The bind mount `./data:/home/node/.n8n` keeps workflows/credentials between restarts.
