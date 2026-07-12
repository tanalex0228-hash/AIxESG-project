#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env.db ]; then
  echo "Missing .env.db. Copy .env.db.example to .env.db and set POSTGRES_PASSWORD." >&2
  exit 1
fi

docker volume create aixesg_postgres_data >/dev/null
docker rm -f aixesg_postgres >/dev/null 2>&1 || true

docker run -d \
  --name aixesg_postgres \
  --restart unless-stopped \
  --env-file .env.db \
  -p 100.92.162.59:5432:5432 \
  -v aixesg_postgres_data:/var/lib/postgresql/data \
  -v "$(pwd)/init:/docker-entrypoint-initdb.d:ro" \
  pgvector/pgvector:pg17

echo "Waiting for PostgreSQL..."
for _ in $(seq 1 60); do
  if docker exec aixesg_postgres pg_isready -U esg -d esg_ai_platform >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec aixesg_postgres pg_isready -U esg -d esg_ai_platform
docker exec aixesg_postgres psql -U esg -d esg_ai_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"
docker ps --filter "name=aixesg_postgres"
