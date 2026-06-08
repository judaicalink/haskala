# Cron container for the production stack. Owns the scheduled work
# the standalone `backups` service doesn't:
#   - monthly Fuseki dump
#   - AWStats refresh every 30 minutes
#   - weekly logrotate of /var/local/log/*.log
#
# The Postgres backup itself stays on the dedicated `backups` service
# (docker-compose.yml) — duplicating the schedule would risk two
# concurrent pg_dumps racing on retention pruning.
FROM alpine:3.20

RUN apk add --no-cache \
        bash \
        coreutils \
        gzip \
        tar \
        curl \
        ca-certificates \
        logrotate \
        postgresql16-client \
        tzdata

COPY backup_fuseki.sh /usr/local/bin/backup_fuseki.sh
COPY update_awstats.sh /usr/local/bin/update_awstats.sh
COPY logrotate.conf /etc/logrotate.d/haskala
COPY crontab /etc/crontabs/root
RUN chmod 0755 /usr/local/bin/*.sh && chmod 0644 /etc/crontabs/root

CMD ["crond", "-f", "-L", "/dev/stderr"]
