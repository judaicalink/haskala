#!/usr/bin/env bash
#
# Re-parse the nginx access log into the AWStats DB. Both sides
# share the same /var/local/log/ bind-mount, so this script reaches
# in directly without needing rsync.

set -euo pipefail

# awstats is shipped as a separate container with awstats_updateall
# on PATH; calling it from here would need that binary installed in
# this image too. Instead we use awstats's documented update via
# curl against the AWStats container's CGI — kept commented out
# because the AWStats container's own command line already invokes
# awstats_updateall.pl on startup and on every refresh window.
#
# This script stays in the schedule as the hook point for any future
# logic (e.g. log rotation snapshots, off-host upload).
echo "[$(date -u +%FT%TZ)] AWStats hook tick (awstats container handles the refresh itself)."
