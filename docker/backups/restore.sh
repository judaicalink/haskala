#!/usr/bin/env bash
#
# Restore a previously-taken pg_dump into the Haskala database.
#
# Usage:
#   restore.sh haskala-20260530-120000.sql.gz
#   restore.sh /backups/haskala-20260530-120000.sql.gz
#   restore.sh latest
#
# The script never drops the database itself; it pipes the SQL into
# psql, which expects the target database to already exist. The dump
# is taken with --no-owner / --no-privileges so it replays cleanly
# under whatever role you happen to be connected as.

set -euo pipefail

: "${POSTGRES_HOST:=db}"
: "${POSTGRES_PORT:=5432}"
: "${POSTGRES_DB:=haskala}"
: "${POSTGRES_USER:=haskala}"
: "${BACKUP_DIR:=/backups}"

if [ $# -ne 1 ]; then
    echo "Usage: $(basename "$0") <backup file | 'latest'>" >&2
    exit 64
fi

target="$1"

if [ "${target}" = "latest" ]; then
    # Newest across daily/ and monthly/ wins.
    target=$(ls -1t \
        "${BACKUP_DIR}"/daily/haskala-*.sql.gz \
        "${BACKUP_DIR}"/monthly/haskala-*.sql.gz \
        2>/dev/null | head -n 1 || true)
    if [ -z "${target}" ]; then
        echo "No backups found under ${BACKUP_DIR}/{daily,monthly}/" >&2
        exit 1
    fi
fi

# Allow the caller to pass a bare filename or a fully-qualified path.
# Bare names get resolved against daily/ first, then monthly/.
if [[ "${target}" != /* ]]; then
    for candidate in "${BACKUP_DIR}/daily/${target}" "${BACKUP_DIR}/monthly/${target}" "${BACKUP_DIR}/${target}"; do
        if [ -f "${candidate}" ]; then
            target="${candidate}"
            break
        fi
    done
fi

if [ ! -f "${target}" ]; then
    echo "Backup not found: ${target}" >&2
    exit 1
fi

case "${target}" in
    *.gz)  cat_cmd=(zcat "${target}") ;;
    *)     cat_cmd=(cat  "${target}") ;;
esac

log() { echo "[$(date -u +%FT%TZ)] $*"; }

log "Restoring ${target} into ${POSTGRES_DB} on ${POSTGRES_HOST}:${POSTGRES_PORT}"

"${cat_cmd[@]}" | PGPASSWORD="${POSTGRES_PASSWORD:-}" psql \
    --host="${POSTGRES_HOST}" \
    --port="${POSTGRES_PORT}" \
    --username="${POSTGRES_USER}" \
    --dbname="${POSTGRES_DB}" \
    --quiet \
    --set ON_ERROR_STOP=1

log "Restore complete"
