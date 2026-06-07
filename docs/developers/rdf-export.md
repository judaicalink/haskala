# RDF export

The catalogue is also published as RDF (Turtle). The `haskala_rdf`
package and two management commands do the work; this page explains
what comes out and how to regenerate it.

## The `export_rdf` command

```bash
docker compose exec web python manage.py export_rdf
```

Writes four files under `settings.HASKALA_DUMPS_ROOT/<slug>/current/`
(default `dumps/haskala/current/` in the repo):

| File                  | Format        | Contents                                           |
| --------------------- | ------------- | -------------------------------------------------- |
| `haskala.ttl.gz`      | gzip Turtle   | The data graph: every Book, Person, City, Edition, … |
| `haskala-meta.ttl.gz` | gzip Turtle   | VoID + DCAT + PROV metadata about the data graph    |
| `haskala.md`          | Markdown      | YAML-frontmatter file consumed by judaicalink-loader |
| `haskala-beacon.txt`  | BEACON text   | Person-to-GND-ID mapping                            |

Any previous run is moved to
`dumps/haskala/archive/<timestamp>/` first, so `current/` always
holds exactly the freshest set.

A daily cron entry in the Docker image
(`/etc/cron.d/export_rdf`) runs the command at midnight.

## The `dump_ontology` command

```bash
docker compose exec web python manage.py dump_ontology
```

Regenerates `research/ontology.ttl` from the Django models. Output is
deterministic — diff before committing. The ontology declares an
`owl:Class` per exported model, an `owl:DatatypeProperty` /
`owl:ObjectProperty` per field, and a hand-curated set of
`rdfs:subPropertyOf` and `rdfs:subClassOf` alignments to JudaicaLink,
FOAF, SKOS and Dublin Core terms.

The generator lives in `haskala_rdf/ontology.py`. The
`PROPERTY_ALIGNMENTS` and `CLASS_ALIGNMENTS` dicts at the top are the
place to extend the alignment when a new predicate maps to an
established vocabulary term.

## Module layout

```
haskala_rdf/
├── export.py       # build_data_graph(), build_meta_graph(),
│                   # build_frontmatter_md(); the generic field-by-field
│                   # exporter is add_model_instance()
├── beacon.py       # build_beacon_lines() — BEACON header + GND IDs
├── frontmatter.py  # thin re-export of build_frontmatter_md
└── ontology.py     # build_ontology_graph() and the alignment tables
```

## Settings

| Setting                     | Default               | Purpose                                                  |
| --------------------------- | --------------------- | -------------------------------------------------------- |
| `HASKALA_DUMPS_ROOT`        | `<repo>/dumps`        | Parent directory for `<slug>/current` and `<slug>/archive` |
| `HASKALA_SLUG`              | `haskala`             | Sub-directory and graph identifier                       |
| `HASKALA_GND_MAPPING_CSV`   | `""`                  | Optional path to a CSV mapping Person UUID → GND ID      |

Override via environment variables of the same name.

## Loading into a SPARQL endpoint

The `export_rdf` command can push the freshly-built data graph to a
remote SPARQL endpoint as the last step of every run, using the HTTP
Graph Store Protocol (PUT) by default, or SPARQL 1.1 Update over POST.
Set `HASKALA_SPARQL_PUSH_URL` to enable it; leave it empty to keep the
push disabled.

| Setting                            | Default                                       | Purpose                                                                  |
| ---------------------------------- | --------------------------------------------- | ------------------------------------------------------------------------ |
| `HASKALA_SPARQL_PUSH_URL`          | `""` (disabled)                               | GSP endpoint, e.g. `http://fuseki:3030/haskala/data`                     |
| `HASKALA_SPARQL_PUSH_GRAPH`        | `http://data.judaicalink.org/data/haskala`    | Named graph IRI                                                          |
| `HASKALA_SPARQL_PUSH_PROTOCOL`     | `gsp`                                         | `gsp` (PUT) or `update` (POST `application/sparql-update`)               |
| `HASKALA_SPARQL_PUSH_USER`         | `""`                                          | Optional HTTP Basic Auth username                                        |
| `HASKALA_SPARQL_PUSH_PASSWORD`     | `""`                                          | Matching password                                                        |
| `HASKALA_SPARQL_PUSH_TIMEOUT`      | `60`                                          | Seconds                                                                  |

The push replaces the named graph wholesale — successive runs converge
on the same end state without accumulating stale triples.

`python manage.py export_rdf` runs both the local file export and the
push (in that order). To skip the push for a single run pass
`--no-push`.

`python manage.py push_rdf` skips the export and re-uploads the most
recent dump from `<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/current/`. Use
this after fixing a transient endpoint failure, or pass `--source` to
upload a hand-edited Turtle file.

For Fuseki specifically: the GSP endpoint is
`http(s)://<host>:3030/<dataset>/data`; the SPARQL Update endpoint is
`http(s)://<host>:3030/<dataset>/update`. The bundled dev `fuseki`
service ships with admin/admin credentials.

## Namespaces

| Prefix  | URI                                                                   |
| ------- | --------------------------------------------------------------------- |
| `hs:`   | `http://data.judaicalink.org/ontology/haskala#`                       |
| `hsk:`  | `http://data.judaicalink.org/data/haskala/`                           |
| `jl:`   | `http://data.judaicalink.org/ontology/` (JudaicaLink shared ontology) |
| `gndo:` | `http://d-nb.info/standards/elementset/gnd#`                          |

`hs:` predicates carry one-to-one mappings of every Django field on
every exported model. The alignment statements in `ontology.ttl`
declare which of those `hs:` predicates are subproperties of a
shared term (`hs:pref_label rdfs:subPropertyOf skos:prefLabel`,
`hs:date_of_birth rdfs:subPropertyOf jl:birthDate`, …) so a SPARQL
consumer can query either side.
