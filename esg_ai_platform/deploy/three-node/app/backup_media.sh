#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/home/alex/aixesg/backups/media}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${BACKUP_DIR}"
docker run --rm \
  -v aixesg_media:/media:ro \
  -v "${BACKUP_DIR}:/backup" \
  alpine:3.20 \
  sh -c "tar -czf /backup/aixesg_media_${STAMP}.tar.gz -C /media ."
find "${BACKUP_DIR}" -type f -name 'aixesg_media_*.tar.gz' -mtime +"${RETENTION_DAYS}" -delete
ls -lh "${BACKUP_DIR}/aixesg_media_${STAMP}.tar.gz"
