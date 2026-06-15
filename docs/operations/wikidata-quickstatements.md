# Wikidata Sync via QuickStatements

Periodic back-link sync from the Haskala catalog into the matching
Wikidata items. Every Person / Book / City whose `wikidata_id` is
populated gets enriched with a "described at URL" (P973) statement
pointing at its catalog detail page, plus VIAF (P214) / GND (P227)
ID statements when those are available.

All edits run **under your personal Wikidata account**. There is no
bot account involved — the QuickStatements API token is bound to
your QS profile, which is in turn bound to your Wikidata OAuth
identity.

## One-off: generate the TSV

    docker compose exec web \
        python manage.py export_wikidata_quickstatements

Writes the batch to
`dumps/haskala/wikidata/quickstatements_<YYYY-MM-DD>.tsv`. The
command is read-only and does not contact Wikidata.

## Manual upload (no setup needed)

1. Open the TSV from the dumps directory.
2. Visit <https://quickstatements.toolforge.org/> while logged in
   with your personal Wikidata account.
3. Paste the TSV under **Import V1 commands** and run the batch.
   Every edit shows up in your Wikidata contribution history.

## Automated upload (one-time OAuth setup)

1. While logged in, open
   <https://quickstatements.toolforge.org/#/user>. Copy the
   "Token" field — it's bound to your account.
2. Add these env vars to the host that runs the cron job (NOT to
   the repo's `.env` — keep them out of git):

       HASKALA_QS_USER=YourWikidataUsername
       HASKALA_QS_TOKEN=<token from step 1>

3. Run with `--upload`:

       docker compose exec web \
           python manage.py export_wikidata_quickstatements --upload

   The command writes the TSV, then POSTs the batch to
   QuickStatements. The new batch appears in your QS history
   under the label `haskala-sync-<YYYY-MM-DD>` (override with
   `--batchname`).

## Cron — once a month

Add to the operator host's crontab (NOT inside the container):

    # 02:30 on the 1st of every month, push new statements
    30 2 1 * * cd /srv/haskala && docker compose exec -T web \
        python manage.py export_wikidata_quickstatements --upload \
        >> /var/log/haskala/wikidata-sync.log 2>&1

## Cron — twice a year

    # 02:30 on Jan 15 and Jul 15
    30 2 15 1,7 * cd /srv/haskala && docker compose exec -T web \
        python manage.py export_wikidata_quickstatements --upload \
        >> /var/log/haskala/wikidata-sync.log 2>&1

## Idempotency

QuickStatements rejects statements that already exist with matching
references, so re-running the command does not double-publish. The
catalog URL + retrieval date are stored as references on every
statement, which means QS treats each month's batch as a refresh of
the reference timestamp rather than a duplicate value.

## What gets synced today

| Model | Property emitted | Source field |
|---|---|---|
| Person | P973 (described at URL) | catalog `/persons/<slug>/` |
| Person | P214 (VIAF ID) | `Person.viaf_id` if non-empty |
| Person | P227 (GND ID) | `Person.gnd_id` if non-empty |
| Book | P973 (described at URL) | catalog `/books/<slug>/` |
| City | P973 (described at URL) | catalog `/places/<slug>/` |

Books and Persons require `wikidata_id` to be set on the row first
— that field still lives only on `City` until Phase 1 is extended to
the other models. Until then this command only emits statements for
anchored cities; the body count will grow once Books / Persons get
their own anchor fields.

## Troubleshooting

- **`QuickStatements rejected the batch: {...}`** — most often a
  missing or expired token. Re-fetch from the QS user page.
- **`Cannot upload: HASKALA_QS_USER and HASKALA_QS_TOKEN must be set`**
  — env vars not exported to the cron environment. Cron runs with a
  bare shell; export them in the crontab or via
  `EnvironmentFile=` if you migrate to a systemd timer.
- **Output TSV is empty** — no Wikidata anchors yet. Run
  `python manage.py enrich_cities_from_wikidata --apply` first.
