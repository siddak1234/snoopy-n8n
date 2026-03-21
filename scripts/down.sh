#!/usr/bin/env bash
set -e
# LOCAL ONLY — see scripts/up.sh and README for production compose command.
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.local.yml down
