#!/usr/bin/env sh
set -eu

echo "[1/5] Checking compose services"
services="$(docker compose config --services)"
echo "$services"

echo "[2/5] Starting n8n"
docker compose up -d

echo "[3/5] Checking container status"
docker compose ps

echo "[4/5] Checking GCS env in n8n"
docker compose exec n8n sh -lc 'echo $GOOGLE_APPLICATION_CREDENTIALS'

echo "[5/5] Verifying pdf-lib allowlist and runtime availability"
rg -n "NODE_FUNCTION_ALLOW_EXTERNAL=pdf-lib" .env.example
docker compose exec n8n sh -lc 'node -e "require(\"pdf-lib\"); console.log(\"pdf-lib ok\")"'

echo "Smoke cleanup checks passed"
