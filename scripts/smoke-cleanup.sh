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

echo "[5/5] Verifying docs + removal references"
rg -n "Mistral Document OCR|mistral-ocr-latest" README.md
if rg -n "receipt-assembler|assemble_from_manifest|pdf-renderer|X-Internal-Token|pdftoppm|pdfinfo|ghostscript|imagemagick|mutool|gotenberg" -S . --glob '!README.md' --glob '!scripts/smoke-cleanup.sh'; then
  echo "Found legacy MCP/local-render references"
  exit 1
fi

echo "Smoke cleanup checks passed"
