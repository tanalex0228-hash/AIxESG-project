#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

docker rm -f aixesg_nginx >/dev/null 2>&1 || true
docker run -d \
  --name aixesg_nginx \
  --restart unless-stopped \
  -p 80:80 \
  -v "$(pwd)/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  nginx:1.27-alpine

docker ps --filter "name=aixesg_nginx"
