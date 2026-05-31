#!/usr/bin/env bash
#
# Take a timestamped, gzipped pg_dump of the Haskala database and
# prune dumps older than BACKUP_RETENTION_DAYS.
#
# Connection is configured via environment variables (see the
# `backups` service in docker-compose.yml).

set -euo pipefail

: "${POSTGRES_HOST:=db}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=haskala}"
: "${POSTGRES_USER:=haskala}"
: "${BACKUP_DIR:=/backups}"
: "${BACKUP_RETENTION_DAYS:=14}"

mkdir -p "$BACKUP_DIR"

ts=$(date -u +%Y%m%d-%H%M%S)
out="$BACKUP_DIR/haskala-${ts}.sql.gz"
tmp="${out}.partial"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "Dumping ${POSTGRES_DB} on ${POSTGRES_HOST}:${POSTGRES_PORT} -> ${out}"

# Stream pg_dump straight into gzip so the uncompressed plain SQL
# never lands on disk. --format=plain so the file is human-readable
# and can be piped into psql for restore. --clean --if-exists adds
# DROP IF EXISTS statements ahead of every CREATE so the dump can be
# replayed into an already-populated database.
PGPASSWORD="${POSTGRES_PASSWORD:-}" pg_dump \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --format=plain \
    --no-owner \
    --no-privileges \
    --clean \
    --if-exists \
  | gzip -9 > "${tmp}"

mv "${tmp}" "${out}"

# Retention: drop dumps older than BACKUP_RETENTION_DAYS. -mtime is in
# 24-hour multiples relative to "now"; +N matches "older than N days".
removed=$(find "${BACKUP_DIR}" -maxdepth 1 -name 'haskala-*.sql.gz' \
    -type f -mtime "+${BACKUP_RETENTION_DAYS}" -print -delete | wc -l)

size=$(du -h "${out}" | cut -f1)
log "Backup complete (${size}); pruned ${removed} dump(s) older than ${BACKUP_RETENTION_DAYS}d"
