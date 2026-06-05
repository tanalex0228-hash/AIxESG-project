#!/usr/bin/env bash
set -euo pipefail

APP_NAME="aixesg"
IMAGE_NAME="${APP_NAME}-web:latest"
NETWORK_NAME="${APP_NAME}_net"
ENV_FILE="${ENV_FILE:-.env.production}"
WEB_PORT="${WEB_PORT:-8000}"

if [ ! -f "${ENV_FILE}" ]; then
  echo "Missing ${ENV_FILE}. Create it before running this deploy script." >&2
  exit 1
fi

docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1 || docker network create "${NETWORK_NAME}"

docker volume create "${APP_NAME}_postgres_data" >/dev/null
docker volume create "${APP_NAME}_media" >/dev/null
docker volume create "${APP_NAME}_staticfiles" >/dev/null

docker rm -f "${APP_NAME}_postgres" "${APP_NAME}_redis" "${APP_NAME}_web" "${APP_NAME}_worker" >/dev/null 2>&1 || true

docker run -d \
  --name "${APP_NAME}_postgres" \
  --network "${NETWORK_NAME}" \
  --restart unless-stopped \
  -e POSTGRES_DB=esg_ai_platform \
  -e POSTGRES_USER=esg \
  -e POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-esg_dev_password_change_me}" \
  -v "${APP_NAME}_postgres_data:/var/lib/postgresql/data" \
  pgvector/pgvector:pg17

docker run -d \
  --name "${APP_NAME}_redis" \
  --network "${NETWORK_NAME}" \
  --restart unless-stopped \
  redis:8-alpine

docker build -t "${IMAGE_NAME}" -f deploy/Dockerfile .

echo "Waiting for PostgreSQL..."
for _ in $(seq 1 60); do
  if docker exec "${APP_NAME}_postgres" pg_isready -U esg -d esg_ai_platform >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec "${APP_NAME}_postgres" pg_isready -U esg -d esg_ai_platform
docker exec "${APP_NAME}_postgres" psql -U esg -d esg_ai_platform -c "CREATE EXTENSION IF NOT EXISTS vector;"

docker run --rm \
  --network "${NETWORK_NAME}" \
  --env-file "${ENV_FILE}" \
  -v "${APP_NAME}_media:/app/media" \
  -v "${APP_NAME}_staticfiles:/app/staticfiles" \
  "${IMAGE_NAME}" python manage.py migrate

docker run --rm --network "${NETWORK_NAME}" --env-file "${ENV_FILE}" "${IMAGE_NAME}" python scripts/seed_gri_305.py
docker run --rm --network "${NETWORK_NAME}" --env-file "${ENV_FILE}" "${IMAGE_NAME}" python scripts/seed_benchmarks.py
docker run --rm --network "${NETWORK_NAME}" --env-file "${ENV_FILE}" -v "${APP_NAME}_staticfiles:/app/staticfiles" "${IMAGE_NAME}" python manage.py collectstatic --noinput

docker run -d \
  --name "${APP_NAME}_web" \
  --network "${NETWORK_NAME}" \
  --restart unless-stopped \
  --env-file "${ENV_FILE}" \
  -p "${WEB_PORT}:8000" \
  -v "${APP_NAME}_media:/app/media" \
  -v "${APP_NAME}_staticfiles:/app/staticfiles" \
  "${IMAGE_NAME}"

docker run -d \
  --name "${APP_NAME}_worker" \
  --network "${NETWORK_NAME}" \
  --restart unless-stopped \
  --env-file "${ENV_FILE}" \
  -v "${APP_NAME}_media:/app/media" \
  "${IMAGE_NAME}" celery -A config worker -l info --pool=solo --concurrency=1

docker ps --filter "name=${APP_NAME}_"
echo "Deployment complete: http://127.0.0.1:${WEB_PORT} or http://<server-ip>:${WEB_PORT}"
