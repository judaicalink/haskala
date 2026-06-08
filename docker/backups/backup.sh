#!/usr/bin/env bash
#
# Take a timestamped, gzipped pg_dump of the Haskala database into
# $BACKUP_DIR/daily/. On the first day of the month also copy the
# fresh dump into $BACKUP_DIR/monthly/ as a long-term snapshot.
# Prune both directories on their own retention windows.
#
# Connection is configured via environment variables (see the
# `backups` service in docker-compose.yml).

set -euo pipefail

: "${POSTGRES_HOST:=db}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=haskala}"
: "${POSTGRES_USER:=haskala}"
: "${BACKUP_DIR:=/backups}"
: "${BACKUP_RETENTION_DAYS_DAILY:=14}"
: "${BACKUP_RETENTION_DAYS_MONTHLY:=365}"

daily_dir="${BACKUP_DIR}/daily"
monthly_dir="${BACKUP_DIR}/monthly"
mkdir -p "${daily_dir}" "${monthly_dir}"

ts=$(date -u +%Y%m%d-%H%M%S)
out="${daily_dir}/haskala-${ts}.sql.gz"
tmp="${out}.partial"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "Dumping ${POSTGRES_DB} on ${POSTGRES_HOST}:${POSTGRES_PORT} -> ${out}"

# Stream pg_dump straight into gzip so the uncompressed plain SQL
# never lands on disk. --clean --if-exists adds DROP IF EXISTS
# statements ahead of every CREATE so the dump can be replayed into
# an already-populated database or pulled in by 00-restore-or-seed.sh
# on a fresh data volume.
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

# Monthly rollover: on the 1st of the month, make a long-lived copy
# of today's daily dump under monthly/. Naming uses YYYY-MM so the
# file is overwriteable in case the cron fires twice (rare; harmless).
day_of_month=$(date -u +%d)
if [ "${day_of_month}" = "01" ]; then
    yyyymm=$(date -u +%Y-%m)
    monthly="${monthly_dir}/haskala-${yyyymm}.sql.gz"
    cp -f "${out}" "${monthly}"
    log "Monthly rollover: copied -> ${monthly}"
fi

# Retention. -mtime is in 24-hour multiples relative to "now"; +N
# matches "older than N days". Daily and monthly have separate
# windows so a month-old monthly stays even when daily is pruned.
removed_daily=$(find "${daily_dir}" -maxdepth 1 -name 'haskala-*.sql.gz' \
    -type f -mtime "+${BACKUP_RETENTION_DAYS_DAILY}" -print -delete | wc -l)
removed_monthly=$(find "${monthly_dir}" -maxdepth 1 -name 'haskala-*.sql.gz' \
    -type f -mtime "+${BACKUP_RETENTION_DAYS_MONTHLY}" -print -delete | wc -l)

size=$(du -h "${out}" | cut -f1)
log "Backup complete (${size}); pruned ${removed_daily} daily older than ${BACKUP_RETENTION_DAYS_DAILY}d, ${removed_monthly} monthly older than ${BACKUP_RETENTION_DAYS_MONTHLY}d"
