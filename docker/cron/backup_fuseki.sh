#!/usr/bin/env bash
#
# Monthly snapshot of the Haskala Fuseki dataset. We grab a Turtle
# dump through Fuseki's Graph Store Protocol (GSP) endpoint rather
# than tarballing the on-disk TDB2 files, because the GSP dump is
# both engine-agnostic (replayable into any triplestore) and safer
# under a running server.
#
# Output: $BACKUP_DIR/monthly/fuseki-YYYY-MM.ttl.gz

set -euo pipefail

: "${BACKUP_DIR:=/backups}"
: "${FUSEKI_URL:=http://fuseki:3030}"
: "${FUSEKI_USER:=admin}"
: "${FUSEKI_PASSWORD:=admin}"
: "${FUSEKI_DATASET:=haskala}"

month=$(date -u +%Y-%m)
out="${BACKUP_DIR}/monthly/fuseki-${month}.ttl.gz"
tmp="${out}.partial"

log() { echo "[$(date -u +%FT%TZ)] $*"; }

mkdir -p "${BACKUP_DIR}/monthly"
log "Fetching ${FUSEKI_URL}/${FUSEKI_DATASET}/data?default -> ${out}"

# GSP "GET ?default" returns the union of the default graph; passing
# &graph=<iri> would fetch a single named graph instead.
curl --silent --show-error --fail \
    --user "${FUSEKI_USER}:${FUSEKI_PASSWORD}" \
    --header "Accept: text/turtle" \
    "${FUSEKI_URL}/${FUSEKI_DATASET}/data?default" \
  | gzip -9 > "${tmp}"

mv "${tmp}" "${out}"
size=$(du -h "${out}" | cut -f1)
log "Fuseki snapshot complete (${size})"
