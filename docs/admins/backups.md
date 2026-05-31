# Backups and restore

The Haskala stack ships a dedicated `backups` container that takes a
daily, gzipped `pg_dump` of the Postgres database and prunes old
copies. This page covers the schedule, the manual triggers, and how
to restore.

## What gets backed up

The full `haskala` database, including:

- Catalogue data (Book, Person, City, …)
- Wagtail page tree and revisions
- Admin users, groups, sessions

Backups are taken with `--clean --if-exists`, so each dump can be
replayed straight into an already-populated database without
manual schema cleanup.

## Where the dumps live

Inside the `backups_data` named volume, mounted at `/backups`
within the container. The host can reach them via:

```bash
docker compose run --rm backups ls -lh /backups
```

Filename pattern: `haskala-YYYYMMDD-HHMMSS.sql.gz` (timestamp in UTC).

## Schedule

The container runs BusyBox `crond`. The active crontab (in
`docker/backups/crontab`) fires `backup.sh` once a day at
**02:30 local time** (Europe/Berlin per the `TZ` env on the
service).

Change the schedule by editing `docker/backups/crontab` and
rebuilding the image:

```bash
docker compose build backups
docker compose up -d backups
```

## Retention

Dumps older than **14 days** are removed at the end of every
backup run. Override via the `BACKUP_RETENTION_DAYS` environment
variable on the `backups` service in `docker-compose.yml`.

## Manual backup

Trigger an ad-hoc dump (e.g. before a risky import):

```bash
docker compose run --rm backups backup.sh
```

The script writes its progress to stdout and leaves the new dump
in the same `/backups` location as the scheduled runs.

## Restore

To restore over the live database (it does NOT need to be
empty — the dump carries DROP IF EXISTS statements):

```bash
# By filename, expressed relative to /backups:
docker compose run --rm backups restore.sh haskala-20260530-023000.sql.gz

# Or by absolute path:
docker compose run --rm backups restore.sh /backups/haskala-20260530-023000.sql.gz

# Or "latest", which picks the most recent dump by mtime:
docker compose run --rm backups restore.sh latest
```

After a restore, flush the cache so the public site reflects the
restored state:

```bash
docker compose exec redis redis-cli FLUSHALL
docker compose restart web
```

## Copying a dump off-host

For an off-host backup copy:

```bash
# Pick the freshest dump.
docker compose run --rm backups sh -c 'ls -t /backups/haskala-*.sql.gz | head -1' \
  | tr -d '\r' \
  | xargs -I{} docker compose run --rm -T backups cat {} > haskala-latest.sql.gz
```

The resulting file can be rsynced or uploaded to remote storage
on the same schedule as the host's normal off-site backups.

## Disaster recovery

If the `postgres_data` volume is lost, the Compose stack will
re-initialise the database from `haskala.sql` (the bundled seed)
on next `docker compose up`. To recover the *current* state from
the most recent backup instead:

1. Bring up the stack with the seeded database as usual.
2. Copy the most recent backup into the new `backups_data` volume.
3. Run `docker compose run --rm backups restore.sh latest`.

The seed dump (`haskala.sql`) is intentionally not refreshed by the
backup container — it's the fallback bootstrap, not a live snapshot.
