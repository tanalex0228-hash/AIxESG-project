#!/usr/bin/env bash
set -euo pipefail

BACKUP_DIR="${BACKUP_DIR:-/home/alex/aixesg/backups/postgres}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "${BACKUP_DIR}"
docker exec aixesg_postgres pg_dump -U esg -d esg_ai_platform -Fc > "${BACKUP_DIR}/aixesg_${STAMP}.dump"
find "${BACKUP_DIR}" -type f -name 'aixesg_*.dump' -mtime +"${RETENTION_DAYS}" -delete
ls -lh "${BACKUP_DIR}/aixesg_${STAMP}.dump"
