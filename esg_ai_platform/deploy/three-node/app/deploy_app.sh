#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ ! -f .env.app ]; then
  echo "Missing .env.app. Copy .env.app.example to .env.app and set secrets." >&2
  exit 1
fi

APP_NAME="aixesg"
IMAGE_NAME="${APP_NAME}-web:latest"
NETWORK_NAME="${APP_NAME}_app_net"

docker network inspect "${NETWORK_NAME}" >/dev/null 2>&1 || docker network create "${NETWORK_NAME}"
docker volume create "${APP_NAME}_media" >/dev/null
docker volume create "${APP_NAME}_staticfiles" >/dev/null
docker volume create "${APP_NAME}_redis_data" >/dev/null

docker build -t "${IMAGE_NAME}" -f ../../Dockerfile ../../..

docker rm -f "${APP_NAME}_redis" "${APP_NAME}_web" "${APP_NAME}_worker" >/dev/null 2>&1 || true

docker run -d \
  --name "${APP_NAME}_redis" \
  --network "${NETWORK_NAME}" \
  --restart unless-stopped \
  -v "${APP_NAME}_redis_data:/data" \
  redis:8-alpine

echo "Waiting for Redis..."
for _ in $(seq 1 30); do
  if docker exec "${APP_NAME}_redis" redis-cli ping >/dev/null 2>&1; then
    break
  fi
  sleep 1
done

docker exec "${APP_NAME}_redis" redis-cli ping

docker run --rm \
  --network "${NETWORK_NAME}" \
  --env-file .env.app \
  -v "${APP_NAME}_media:/app/media" \
  -v "${APP_NAME}_staticfiles:/app/staticfiles" \
  "${IMAGE_NAME}" python manage.py migrate

docker run --rm --network "${NETWORK_NAME}" --env-file .env.app "${IMAGE_NAME}" python scripts/seed_gri_305.py
docker run --rm --network "${NETWORK_NAME}" --env-file .env.app "${IMAGE_NAME}" python scripts/seed_benchmarks.py
docker run --rm --network "${NETWORK_NAME}" --env-file .env.app -v "${APP_NAME}_staticfiles:/app/staticfiles" "${IMAGE_NAME}" python manage.py collectstatic --noinput

docker run -d \
  --name "${APP_NAME}_web" \
  --network "${NETWORK_NAME}" \
  --restart unless-stopped \
  --env-file .env.app \
  -p 100.72.157.21:8020:8000 \
  -v "${APP_NAME}_media:/app/media" \
  -v "${APP_NAME}_staticfiles:/app/staticfiles" \
  "${IMAGE_NAME}"

docker run -d \
  --name "${APP_NAME}_worker" \
  --network "${NETWORK_NAME}" \
  --restart unless-stopped \
  --env-file .env.app \
  -v "${APP_NAME}_media:/app/media" \
  "${IMAGE_NAME}" celery -A config worker -l info --pool=solo --concurrency=1

docker ps --filter "name=aixesg_"
