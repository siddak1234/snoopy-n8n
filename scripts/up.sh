#!/usr/bin/env bash
set -e
# LOCAL ONLY — mounts ./secrets. Do not use on production VMs.
# Production (any provider): README → docker compose --env-file .env.prod -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml up -d
docker ps
