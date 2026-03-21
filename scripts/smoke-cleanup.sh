#!/usr/bin/env sh
set -eu
# LOCAL stack only (includes ./secrets mounts). Not for generic production.

COMPOSE_FILES="-f docker-compose.yml -f docker-compose.local.yml"

echo "[1/5] Checking compose services"
services="$(docker compose $COMPOSE_FILES config --services)"
echo "$services"

echo "[2/5] Starting n8n (local stack with ./secrets mounts)"
docker compose $COMPOSE_FILES up -d

echo "[3/5] Checking container status"
docker compose $COMPOSE_FILES ps

echo "[4/5] Checking GCS/ADC env in n8n (path only)"
docker compose $COMPOSE_FILES exec n8n sh -lc 'echo "$GOOGLE_APPLICATION_CREDENTIALS"'

echo "[5/5] Verifying pdf-lib allowlist and runtime availability"
rg -n "NODE_FUNCTION_ALLOW_EXTERNAL=pdf-lib" .env.local.example
docker compose $COMPOSE_FILES exec n8n sh -lc 'node -e "require(\"pdf-lib\"); console.log(\"pdf-lib ok\")"'

echo "Smoke cleanup checks passed"
