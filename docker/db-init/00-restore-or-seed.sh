#!/usr/bin/env bash
#
# Runs on the FIRST boot of the postgres container — i.e. when the
# data volume is empty. Postgres's official image executes every
# *.sh in /docker-entrypoint-initdb.d/ at that point with PGUSER /
# PGPASSWORD / PGDATABASE already set to the values from POSTGRES_*
# env, so we can talk to the local socket without re-authenticating.
#
# Logic:
#   1. Look in /backups/daily/ then /backups/monthly/ for a *.sql.gz.
#   2. If found: zcat into psql — the dump uses --clean --if-exists
#      so it replays cleanly into the freshly-created database.
#   3. Otherwise: replay /initial/haskala.sql if it exists.
#   4. Otherwise: log and exit 0 — Django migrations will create the
#      schema on first run.
#
# Idempotent by design: the script only fires when the data dir is
# empty, so a subsequent restart of an already-populated cluster
# never touches /backups or /initial again.

set -euo pipefail

log() { echo "[$(date -u +%FT%TZ)] restore-or-seed: $*"; }

candidate=""
if compgen -G "/backups/daily/haskala-*.sql.gz" > /dev/null; then
    candidate="$(ls -1t /backups/daily/haskala-*.sql.gz | head -n 1)"
fi
if [ -z "$candidate" ] && compgen -G "/backups/monthly/haskala-*.sql.gz" > /dev/null; then
    candidate="$(ls -1t /backups/monthly/haskala-*.sql.gz | head -n 1)"
fi

if [ -n "$candidate" ]; then
    log "restoring from $candidate"
    zcat "$candidate" | psql \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        --quiet \
        --set ON_ERROR_STOP=1
    log "restore complete"
elif [ -f /initial/haskala.sql ]; then
    log "no backups found; seeding from /initial/haskala.sql"
    psql \
        --username "$POSTGRES_USER" \
        --dbname "$POSTGRES_DB" \
        --quiet \
        --set ON_ERROR_STOP=1 \
        --file /initial/haskala.sql
    log "seed complete"
else
    log "no backups and no /initial/haskala.sql — leaving DB empty for migrations to populate"
fi
