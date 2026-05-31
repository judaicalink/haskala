# Tiny image dedicated to scheduled pg_dump backups of the Haskala
# Postgres database. Reachable from the host via:
#   docker compose run --rm backups backup.sh
#   docker compose run --rm backups restore.sh <file>
FROM alpine:3.20

RUN apk add --no-cache \
        bash \
        coreutils \
        gzip \
        postgresql16-client \
        tzdata

COPY backup.sh restore.sh /usr/local/bin/
RUN chmod 0755 /usr/local/bin/backup.sh /usr/local/bin/restore.sh

COPY crontab /etc/crontabs/root

# Use BusyBox crond (shipped in the alpine base image). It plays
# nicely with Docker's default seccomp profile, unlike the dcron
# package which trips on setpgid. -f keeps it in the foreground;
# -L /dev/stderr forwards its own log to docker logs while each cron
# job's stdout/stderr is redirected inside /etc/crontabs/root.
CMD ["crond", "-f", "-L", "/dev/stderr"]
