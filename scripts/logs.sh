#!/usr/bin/env bash
set -e
# LOCAL ONLY — for prod, add same -f files as your production up command.
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml logs -f n8n
