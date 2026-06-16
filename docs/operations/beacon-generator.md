# BEACON link-dump generator

Periodic emission of [BEACON](https://gbv.github.io/beaconspec/beacon.html)
link-dump files so external services (GND, VIAF, Wikidata,
Judaicalink aggregator) can advertise the back-links from their
authority records into the Haskala-Bibliothek catalog.

Five files emitted today (one per (entity, authority) pair):

| File | Source field | Public link |
|---|---|---|
| `beacon-gnd-persons.txt` | `Person.gnd_id` | `/persons/<slug>/` |
| `beacon-viaf-persons.txt` | `Person.viaf_id` | `/persons/<slug>/` |
| `beacon-wikidata-persons.txt` | `Person.wikidata_id` | `/persons/<slug>/` |
| `beacon-wikidata-places.txt` | `City.wikidata_id` | `/places/<slug>/` |
| `beacon-wikidata-topics.txt` | `Topic.wikidata_id` | `/topics/<slug>/` |

The Topics file is empty today (no `Topic.wikidata_id` field yet);
the command guards on `hasattr` so the file appears automatically
once the field lands.

## Manual run

    docker compose exec web \
        python manage.py generate_beacons

Output goes to
`<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/beacon/`. The same command
overwrites the existing files on every run, so the cron schedule
(below) makes the files self-refreshing.

## Cron — once a month

Add to the operator host's crontab (NOT inside the container):

    # 02:30 on the 1st of every month, refresh BEACON dumps
    30 2 1 * * cd /srv/haskala && docker compose exec -T web \
        python manage.py generate_beacons \
        >> /var/log/haskala/beacon.log 2>&1

Drop the resulting files into nginx's served path so they're
reachable via the `#FEED` URL embedded in each file's header
(default: `https://www.haskala-library.net/data/beacon-<id>.txt`).

## Publishing

For each authority that wants to consume the file:

- **GND** ships an OAI-PMH-based aggregator that picks up BEACON
  files from registered hosts. Register the catalog at
  https://format.gbv.de/beacon/ once the URL is reachable.
- **Wikidata** doesn't aggregate BEACON natively, but
  Judaicalink (and similar Linked-Open-Data hubs) does. The
  Judaicalink generator pattern (see
  https://github.com/judaicalink/judaicalink-generators) reads
  BEACON files into its catalog graph.

The corresponding records also need the back-link statement in
the OTHER direction. That's the `export_wikidata_quickstatements`
command for the Wikidata side (PR #131).

## File format reminder

Each file opens with a small header block, then one link per line:

    #FORMAT: BEACON
    #PREFIX: https://d-nb.info/gnd/
    #TARGET: https://www.haskala-library.net/persons/{ID}/
    #NAME: Haskala-Bibliothek
    #INSTITUTION: École Pratique des Hautes Études
    #DESCRIPTION: GND identifiers of persons in the Haskala catalog
    #CONTACT: benjamin.schnabel@ephe.psl.eu
    #TIMESTAMP: 2026-06-16T12:00:00Z
    #FEED: https://www.haskala-library.net/data/beacon-gnd-persons.txt

    118582143|moses-mendelssohn
    118585770|saul-ascher

Aggregators read the header to know:
- `#PREFIX` — what to concat with each source ID
- `#TARGET` — where the local catalog page is, with `{ID}` replaced by the slug after the pipe

So a line `118582143|moses-mendelssohn` advertises that
`https://d-nb.info/gnd/118582143` is described at
`https://www.haskala-library.net/persons/moses-mendelssohn/`.
