# haskala_rdf/export.py

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any, Dict, Optional

from django.conf import settings
from django.db import models as dj_models

from rdflib import Graph, Namespace, URIRef, Literal
from rdflib.namespace import RDF, RDFS, SKOS, FOAF, DCTERMS, XSD, OWL
import logging

from home.models import (  # noqa: F401
    FORMAT_CHOICES,
    Language,
    Alignment,
    Font,
    Publisher,
    Series,
    TargetAudience,
    Typography,
    DateFormat,
    TextualModel,
    LanguageCount,
    City,
    Geolocation,
    Gender,
    Occupation,
    Person,
    Edition,
    TranslationType,
    Translation,
    Mention,
    Preface,
    Production,
    Topic,
    BookAuthor,
    MentionDescription,
    ProductionRole,
    FootnoteLocation,
    OriginalType,
    Book,
)

logger = logging.getLogger("haskala.export")

# ---------------------------------------------------------
# Namespaces
# ---------------------------------------------------------

# JudaicaLink Ontology (anpassen, wenn bei dir anders)
JL = Namespace("http://data.judaicalink.org/ontology/")

# Haskala-Ontologie (aus ontology.ttl)
HS = Namespace("http://data.judaicalink.org/ontology/haskala#")

# Datenbasis für Haskala-Instanzen
HSK = Namespace("http://data.judaicalink.org/data/haskala/")

# GND-Elemente + Identifier-URIs
GND = Namespace("http://d-nb.info/standards/elementset/gnd#")
GND_ID_BASE = "https://d-nb.info/gnd/"

# WGS84 Geo
WGS84 = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")

VOID = Namespace("http://rdfs.org/ns/void#")
DCAT = Namespace("http://www.w3.org/ns/dcat#")
PROV = Namespace("http://www.w3.org/ns/prov#")
# ---------------------------------------------------------
# URI-Helfer für Instanzen
# ---------------------------------------------------------

def person_uri(person: Person) -> URIRef:
    """Stabile URI für Personen (uuid-basiert)."""
    return HSK[f"person/{person.uuid}"]


def book_uri(book: Book) -> URIRef:
    """Stabile URI für Bücher (uuid-basiert)."""
    return HSK[f"book/{book.uuid}"]


def place_uri(city: City) -> URIRef:
    """Stabile URI für Orte (Cities)."""
    return HSK[f"place/{city.uuid}"]


def resource_uri(obj: Any) -> URIRef:
    """
    Generischer URI-Bauer für alle Modelle.
    - Für Person/Book/City spezielle URIs
    - Sonst: <modellname>/<uuid|pk>
    """
    if isinstance(obj, Person):
        return person_uri(obj)
    if isinstance(obj, Book):
        return book_uri(obj)
    if isinstance(obj, City):
        return place_uri(obj)

    model_name = obj.__class__.__name__.lower()
    if hasattr(obj, "uuid"):
        return HSK[f"{model_name}/{obj.uuid}"]
    return HSK[f"{model_name}/{obj.pk}"]


# ---------------------------------------------------------
# GND-Mapping (optional)
# ---------------------------------------------------------

def load_gnd_mapping() -> Dict[str, str]:
    """
    Lädt optional ein Mapping Person-UUID -> GND-ID aus CSV.

    Erwartete Spalten (eine Kombination reicht):
      - uuid / person_uuid / id
      - gnd / gnd_id

    Pfad kommt aus settings.HASKALA_GND_MAPPING_CSV.
    """
    path_str = getattr(settings, "HASKALA_GND_MAPPING_CSV", None)
    if not path_str:
        return {}

    path = Path(path_str)
    if not path.exists():
        return {}

    mapping: Dict[str, str] = {}
    with path.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            uuid_val = (
                row.get("uuid")
                or row.get("person_uuid")
                or row.get("id")
            )
            gnd_val = (
                row.get("gnd")
                or row.get("gnd_id")
            )
            if not uuid_val or not gnd_val:
                continue
            mapping[str(uuid_val).strip()] = str(gnd_val).strip()
    return mapping


# ---------------------------------------------------------
# RDF-Graph initialisieren
# ---------------------------------------------------------

def init_graph() -> Graph:
    g = Graph()
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("skos", SKOS)
    g.bind("foaf", FOAF)
    g.bind("dcterms", DCTERMS)
    g.bind("owl", OWL)
    g.bind("jl", JL)
    g.bind("hs", HS)
    g.bind("hsk", HSK)
    g.bind("gndo", GND)
    g.bind("wgs84", WGS84)
    return g


# ---------------------------------------------------------
# FORMAT_CHOICES → RDF-Datatypes
# ---------------------------------------------------------

# FORMAT_CHOICES:
# ('', 'None'),
# ('NULL', 'Unknown'),
# ('text', 'Text'),
# ('filtered_html', 'Filtered HTML'),
# ('full_html', 'Full HTML'),
# ('markdown', 'Markdown'),
# ('xml', 'XML'),
# ('json', 'JSON'),

FORMAT_CODE_TO_DATATYPE: Dict[str, URIRef] = {
    "": HS.FormatNone,
    "NULL": HS.FormatUnknown,
    "text": HS.FormatText,
    "filtered_html": HS.FormatFilteredHTML,
    "full_html": HS.FormatFullHTML,
    "markdown": HS.FormatMarkdown,
    "xml": HS.FormatXML,
    "json": HS.FormatJSON,
}


def literal_with_format(value: Any, fmt_code: Optional[str]) -> Literal:
    """
    Erzeugt ein Literal, dessen Datentyp von *_format abhängt.
    Format-Felder selbst werden NICHT als eigene Properties exportiert,
    sondern nur hier berücksichtigt.
    """
    if value is None:
        # sollte vorher gefiltert sein
        return Literal("")
    dt = FORMAT_CODE_TO_DATATYPE.get((fmt_code or "").strip(), HS.FormatUnknown)
    return Literal(value, datatype=dt)


# ---------------------------------------------------------
# Generischer Exporter für ein Modell
# ---------------------------------------------------------

def add_model_instance(g: Graph, obj: Any, extra_types: Optional[list[URIRef]] = None) -> URIRef:
    """
    Exportiert ALLE Felder eines Django-Objekts generisch:
    - keine legacy_* Felder
    - *_format-Felder werden als Datentyp für das passende Feld genutzt
    - ForeignKeys und ManyToMany werden auf Ressourcen-URIs gemappt
    - Alles landet unter hs:<feldname>

    extra_types: zusätzliche rdf:type-Einträge (z.B. FOAF.Person)
    """
    s = resource_uri(obj)
    cls_name = obj.__class__.__name__
    g.add((s, RDF.type, HS[cls_name]))
    if extra_types:
        for t in extra_types:
            g.add((s, RDF.type, t))

    # Feld-Namen → Field-Objekte
    field_map: Dict[str, dj_models.Field] = {f.name: f for f in obj._meta.fields}

    # Normale Felder (inkl. ForeignKeys)
    for field in obj._meta.fields:
        name = field.name

        # Primärschlüssel und intern generierte Felder überspringen
        if name in ("id", "pk"):
            continue
        # Alle legacy_* Felder komplett AUSKLAMMERN
        if name.startswith("legacy_"):
            continue

        # *_format Felder: werden NICHT als eigene Predicate verwendet
        if name.endswith("_format") and isinstance(field, dj_models.CharField):
            continue

        value = getattr(obj, name, None)
        if value in (None, ""):
            continue

        pred = HS[name]

        # Text/Char: Optionales *_format-Feld als Datentyp
        if isinstance(field, (dj_models.TextField, dj_models.CharField)):
            fmt_name = f"{name}_format"
            fmt_code = getattr(obj, fmt_name, None) if fmt_name in field_map else None
            lit = literal_with_format(value, fmt_code)
            g.add((s, pred, lit))

        # Bool
        elif isinstance(field, dj_models.BooleanField):
            g.add((s, pred, Literal(bool(value), datatype=XSD.boolean)))

        # Integer
        elif isinstance(field, dj_models.IntegerField):
            g.add((s, pred, Literal(int(value), datatype=XSD.integer)))

        # Float
        elif isinstance(field, dj_models.FloatField):
            g.add((s, pred, Literal(float(value), datatype=XSD.double)))

        # DateTime
        elif isinstance(field, dj_models.DateTimeField):
            g.add((s, pred, Literal(value.isoformat(), datatype=XSD.dateTime)))

        # ForeignKey
        elif isinstance(field, dj_models.ForeignKey):
            target = value
            g.add((s, pred, resource_uri(target)))

        # Fallback: String
        else:
            g.add((s, pred, Literal(str(value))))

    # ManyToMany
    for m2m in obj._meta.many_to_many:
        name = m2m.name
        if name.startswith("legacy_"):
            continue
        pred = HS[name]
        manager = getattr(obj, name)
        for target in manager.all():
            g.add((s, pred, resource_uri(target)))

    return s


# ---------------------------------------------------------
# Spezielle Exporte mit zusätzlicher Semantik
# ---------------------------------------------------------

def export_persons(g: Graph, gnd_mapping: Optional[Dict[str, str]] = None) -> None:
    """
    Exportiert alle Person-Objekte:
    - generische hs:* Properties für alle Felder
    - zusätzlicher Typ foaf:Person
    - VIAF als owl:sameAs
    - GND (falls im Modell oder Mapping vorhanden)
    """
    if gnd_mapping is None:
        gnd_mapping = {}

    persons = Person.objects.all().select_related(
        "gender", "place_of_birth", "place_of_death"
    ).prefetch_related("occupations")

    for person in persons:
        s = add_model_instance(g, person, extra_types=[FOAF.Person])

        # VIAF
        if person.viaf_id:
            viaf_uri = URIRef(f"https://viaf.org/viaf/{person.viaf_id}")
            g.add((s, OWL.sameAs, viaf_uri))

        # GND aus Modell-Feld (falls später hinzugefügt) oder Mapping
        gnd_id = None
        if hasattr(person, "gnd_id") and getattr(person, "gnd_id"):
            gnd_id = str(person.gnd_id).strip()
        else:
            gnd_id = gnd_mapping.get(str(person.uuid))

        if gnd_id:
            g.add((s, GND["gndIdentifier"], Literal(gnd_id)))
            g.add((s, OWL.sameAs, URIRef(f"{GND_ID_BASE}{gnd_id}")))


def export_places(g: Graph) -> None:
    """
    Exportiert City + Geolocation:
    - generische hs:* Properties für City und Geolocation
    - zusätzlicher Typ jl:Place + wgs84-Lat/Lon
    """
    cities = City.objects.all().prefetch_related("geolocation_set")

    for city in cities:
        s = add_model_instance(g, city, extra_types=[JL.Place])

        # Ergänze Geolocation-Infos (auch generisch)
        geos = list(city.geolocation_set.all())
        for geo in geos:
            geo_s = add_model_instance(g, geo)
            # optional: wgs84 lat/long ergänzen
            if geo.lat is not None:
                g.add((geo_s, WGS84.lat, Literal(geo.lat, datatype=XSD.double)))
            if geo.lng is not None:
                g.add((geo_s, WGS84.long, Literal(geo.lng, datatype=XSD.double)))


def export_books(g: Graph) -> None:
    """
    Exportiert alle Book-Objekte:
    - generischer Export aller Felder nach hs:*
    - zusätzlicher Typ jl:Resource
    - Autorenrollen (BookAuthor) mit spezifischen Properties
    - Sprachen zusätzlich als dcterms:language
    - digitale Links zusätzlich als foaf:page
    - bundle-Feld als zusätzlicher rdf:type
    """
    books = Book.objects.all().prefetch_related(
        "authors",
        "languages",
        "footnote_languages",
        "occasional_words_languages",
        "main_textual_models",
        "secondary_textual_models",
        "fonts",
        "target_audience",
        "typography",
    ).select_related(
        "alignment",
        "languages_number",
        "original_type",
        "publication_place",
        "publication_place_other",
        "original_publication_place",
        "original_language",
        "translation_type",
        "topic",
        "format_of_publication_date",
        "series",
        "publisher",
        "original_publisher",
    )

    # Rollen für BookAuthor.role → spezifische Properties
    ROLE_TO_PREDICATE = {
        "old_text_author": HS.old_text_author,       # oder HS.oldTextAuthor
        "original_text_author": HS.original_text_author,
        "producer": HS.producer,
    }

    for book in books:
        extra_types = [JL.Resource]

        # bundle als zusätzlicher Typ (z.B. hs:Translation, hs:Edition usw.)
        if book.bundle:
            class_name = book.bundle.capitalize()  # "translation" -> "Translation"
            extra_types.append(HS[class_name])

        s = add_model_instance(g, book, extra_types=extra_types)

        # BookAuthor-Rollen
        for ba in BookAuthor.objects.filter(book=book).select_related("person"):
            if not ba.person:
                continue
            p = person_uri(ba.person)
            pred = ROLE_TO_PREDICATE.get(ba.role, DCTERMS.creator)
            g.add((s, pred, p))
            # Optional inverse Relation: Person -> Buch
            g.add((p, HS.has_book, s))

        # Sprachen zusätzlich als dcterms:language
        for lang in book.languages.all():
            g.add((s, DCTERMS.language, resource_uri(lang)))

        # Fußnotensprachen zusätzlich explizit
        for lang in book.footnote_languages.all():
            g.add((s, HS.footnote_language, resource_uri(lang)))

        # „Gelegenheitswörter“-Sprachen
        for lang in book.occasional_words_languages.all():
            g.add((s, HS.occasional_words_language, resource_uri(lang)))

        # Digital Book URL zusätzlich als foaf:page
        if book.digital_book_url:
            try:
                url = book.digital_book_url.strip()
                if url:
                    page = URIRef(url)
                    g.add((s, FOAF.page, page))
                    g.add((s, HS.has_digital_copy, page))
            except Exception:
                # Falls mal eine kaputte URL drin ist, Export nicht abbrechen
                pass


# ---------------------------------------------------------
# Export der restlichen „Vokabel“- und Strukturmodelle
# ---------------------------------------------------------

def export_simple_vocab_models(g: Graph) -> None:
    """
    Exportiert alle übrigen Modelle, ohne spezielle Extra-Logik,
    aber mit vollständigem Feldexport:
    Language, Alignment, Font, Publisher, Series, TargetAudience,
    Typography, DateFormat, TextualModel, LanguageCount, Gender,
    Occupation, Edition, TranslationType, Translation, Mention,
    Preface, Production, Topic, MentionDescription, ProductionRole,
    FootnoteLocation, OriginalType.
    """
    vocab_models = [
        Language,
        Alignment,
        Font,
        Publisher,
        Series,
        TargetAudience,
        Typography,
        DateFormat,
        TextualModel,
        LanguageCount,
        Gender,
        Occupation,
        Edition,
        TranslationType,
        Translation,
        Mention,
        Preface,
        Production,
        Topic,
        MentionDescription,
        ProductionRole,
        FootnoteLocation,
        OriginalType,
    ]

    for model_cls in vocab_models:
        for obj in model_cls.objects.all():
            add_model_instance(g, obj)


# ---------------------------------------------------------
# Gesamten Datengraphen bauen
# ---------------------------------------------------------

def build_data_graph() -> Graph:
    """
    Baut den kompletten Datengraphen aus allen relevanten Modellen:

    - Language, Alignment, Font, Publisher, Series, TargetAudience,
      Typography, DateFormat, TextualModel, LanguageCount
    - City, Geolocation
    - Gender, Occupation
    - Person (+ GND/VIAF-Semantik)
    - Edition, TranslationType, Translation, Mention, Preface, Production
    - Topic, MentionDescription, ProductionRole, FootnoteLocation, OriginalType
    - Book (+ Autorenrollen, Sprachen, Digital-Infos)
    """
    g = init_graph()
    gnd_map = load_gnd_mapping()

    export_simple_vocab_models(g)
    export_places(g)
    export_persons(g, gnd_mapping=gnd_map)
    export_books(g)

    return g

def init_meta_graph() -> Graph:
    """
    Initialisiert einen RDF-Graphen für den Metagraph (VoID/DCAT/PROV).
    """
    g = Graph()
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("dcterms", DCTERMS)
    g.bind("void", VOID)
    g.bind("dcat", DCAT)
    g.bind("prov", PROV)
    g.bind("jl", JL)
    g.bind("hs", HS)
    g.bind("hsk", HSK)
    return g


def build_meta_graph(
    data_graph: Optional[Graph] = None,
    *,
    identifier: str = "haskala",
    title_de: str = "Haskala-Bibliographie",
    title_en: str = "Haskala Bibliography",
    description_de: str = "Bibliographische Daten zur jüdischen Aufklärung (Haskala).",
    description_en: str = "Bibliographical dataset on the Jewish Enlightenment (Haskala).",
    homepage_uri: str = "http://data.judaicalink.org/datasets/haskala",
    base_dump_uri: str = "http://data.judaicalink.org/data/haskala/",
    dump_filename: str = "haskala.ttl.gz",
    publisher_name: str = "JudaicaLink / Haskala Project",
    creator_name: str = "JudaicaLink / Haskala Project",
    license_uri: str = "https://creativecommons.org/licenses/by/4.0/",
) -> Graph:
    """
    Erzeugt den Metagraphen (VoID/DCAT) für das Haskala-Dataset.

    - identifier: interner Name des Datasets (z.B. 'haskala')
    - data_graph: optionaler Datengraph; wenn gesetzt, wird void:triples daraus berechnet
    - base_dump_uri: Basis-URL, unter der die Dump-Dateien erreichbar sind
    - dump_filename: Name der Dump-Datei (z.B. 'haskala.ttl.gz')

    Rückgabe: Graph mit den Metadaten.
    """
    g = init_meta_graph()

    today = date.today().isoformat()

    # Dataset-URI (kannst du bei Bedarf anpassen)
    dataset_uri = HSK[f"dataset/{identifier}"]
    g.add((dataset_uri, RDF.type, VOID.Dataset))
    g.add((dataset_uri, RDF.type, DCAT.Dataset))

    # Titel (de/en)
    g.add((dataset_uri, DCTERMS.title, Literal(title_de, lang="de")))
    g.add((dataset_uri, DCTERMS.title, Literal(title_en, lang="en")))

    # Beschreibung (de/en)
    g.add((dataset_uri, DCTERMS.description, Literal(description_de, lang="de")))
    g.add((dataset_uri, DCTERMS.description, Literal(description_en, lang="en")))

    # Identifier
    g.add((dataset_uri, DCTERMS.identifier, Literal(identifier)))

    # Homepage / Landing Page
    g.add((dataset_uri, FOAF.homepage, URIRef(homepage_uri)))

    # Creator / Publisher
    g.add((dataset_uri, DCTERMS.creator, Literal(creator_name)))
    g.add((dataset_uri, DCTERMS.publisher, Literal(publisher_name)))

    # Lizenz
    g.add((dataset_uri, DCTERMS.license, URIRef(license_uri)))
    g.add((dataset_uri, DCTERMS.rights, Literal("CC-BY 4.0")))

    # Erstelldatum / Änderungsdatum
    g.add((dataset_uri, DCTERMS.issued, Literal(today, datatype=XSD.date)))
    g.add((dataset_uri, DCTERMS.modified, Literal(today, datatype=XSD.date)))

    # Anzahl Tripel, falls Datengraph übergeben
    if data_graph is not None:
        triple_count = len(data_graph)
        g.add((dataset_uri, VOID.triples, Literal(triple_count, datatype=XSD.integer)))

    # Dump-Distribution
    dump_uri = URIRef(base_dump_uri.rstrip("/") + "/" + dump_filename)

    # VoID: Datendump
    g.add((dataset_uri, VOID.dataDump, dump_uri))

    # DCAT:Distribution
    dist_uri = HSK[f"distribution/{identifier}"]
    g.add((dist_uri, RDF.type, DCAT.Distribution))
    g.add((dist_uri, DCAT.downloadURL, dump_uri))
    g.add((dist_uri, DCTERMS.format, Literal("text/turtle+gz")))
    g.add((dataset_uri, DCAT.distribution, dist_uri))

    # PROV: einfache Provenance (Dataset wurde am today generiert)
    activity_uri = HSK[f"activity/{identifier}/{today}"]
    g.add((activity_uri, RDF.type, PROV.Activity))
    g.add((activity_uri, PROV.generated, dataset_uri))
    g.add((activity_uri, PROV.endedAtTime, Literal(today, datatype=XSD.date)))

    return g

def build_frontmatter_md(
    *,
    identifier: str = "haskala",
    title: str = "Haskala Bibliography",
    graph_uri: str = "http://data.judaicalink.org/data/haskala",
    dump_filename: str = "haskala.ttl.gz",
    meta_dump_filename: str = "haskala-meta.ttl.gz",
    beacon_filename: str = "haskala-beacon.txt",
    load_to_fuseki: bool = True,
    load_to_solr: bool = True,
    description: str = (
        "Bibliographical dataset on the Jewish Enlightenment (Haskala). "
        "The dataset is part of JudaicaLink and provides structured "
        "information about persons, works, places and related metadata."
    ),
) -> str:
    """
    Erzeugt den Inhalt für das Markdown-File mit Frontmatter (z.B. haskala.md).

    Dieses File kann von Hugo / judaicalink-loader verwendet werden, um:
      - das Dataset zu beschreiben
      - die Dump-Dateien (TTL, Meta-TTL, BEACON) zu referenzieren
      - zu steuern, ob Fuseki und Solr aktualisiert werden sollen.
    """
    today = date.today().isoformat()

    # YAML-Frontmatter
    lines = [
        "---",
        f'title: "{title}"',
        f"identifier: \"{identifier}\"",
        f"graph: \"{graph_uri}\"",
        "data_dumps:",
        f"  - \"{dump_filename}\"",
        f"meta_dump: \"{meta_dump_filename}\"",
        f"beacon_file: \"{beacon_filename}\"",
        f"load_to_fuseki: {str(load_to_fuseki).lower()}",
        f"load_to_solr: {str(load_to_solr).lower()}",
        f"last_update: \"{today}\"",
        "---",
        "",
        description,
        "",
    ]

    return "\n".join(lines)
