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

## Loading into Fuseki

Manual upload for now (the project Fuseki was down during the
migration window):

```bash
curl --upload-file dumps/haskala/current/haskala.ttl.gz \
     -u admin:<password> \
     http://fuseki:3030/haskala/data
```

Auto-push is on the [open workstream list](../../docs/) as a future
task; for the time being the dumps are static files served from the
data portal.

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
