# The Library of the Haskala

The Library of the [Haskala](https://www.haskala-library.net/) is a research
database of Hebrew and German books from the Jewish Enlightenment (Haskala)
period, together with the people, places, publishers, series, topics and
occupations that surround them.

The site is built on Django 6 and Wagtail 7.4, runs in Docker, and ships its
catalogue as RDF (Turtle) alongside the human-readable site.

## Quick start

```bash
git clone git@github.com:judaicalink/haskala.git
cd haskala
docker compose up -d
```

The site comes up on <http://localhost:8080/>. The Postgres dump in
`haskala.sql` is loaded on the very first boot of the `db` container.

The Wagtail admin lives at <http://localhost:8080/admin/>. Create a
superuser:

```bash
docker compose exec web python manage.py createsuperuser
```

## Documentation

Three audiences, three sub-trees under [`docs/`](docs/):

- [docs/users/](docs/users/) — researchers and lay readers: how to navigate
  the site, search, read the detail pages, export citations.
- [docs/admins/](docs/admins/) — content editors: pushing data through the
  Wagtail admin, working with snippets and revisions, when to reach for a
  management command.
- [docs/developers/](docs/developers/) — contributors: local setup,
  architecture, data model, importer workflow, tests, contribution
  conventions, RDF export pipeline.

## Stack

| Service     | Port (host) | Purpose                                       |
| ----------- | ----------- | --------------------------------------------- |
| `web`       | (via nginx) | Django + Wagtail under gunicorn               |
| `nginx`     | 8080        | reverse proxy + `/static/` served from volume |
| `db`        | —           | PostgreSQL 16 (seeded from `haskala.sql`)     |
| `redis`     | —           | django-redis cache                            |
| `solr`      | 8983        | search index                                  |
| `fuseki`    | 3030        | RDF triple store (Apache Jena)                |
| `mailserver`| 1025 / 8025 | MailHog (dev SMTP + UI)                       |

## License

The platform code is published under the MIT license; the dataset is
published under CC-BY 4.0.
