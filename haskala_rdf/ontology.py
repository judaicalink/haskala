"""
Builds the Haskala RDF ontology (research/ontology.ttl) from the Django
models. Every class the exporter emits gets an owl:Class declaration;
every field gets an owl:DatatypeProperty or owl:ObjectProperty with a
matching rdfs:domain and rdfs:range. Hand-curated alignment statements
at the bottom link a small set of central predicates to JudaicaLink
(jl:), FOAF, SKOS, Dublin Core and the GND elementset, so consumers
that speak those vocabularies can interpret the Haskala data without
needing a custom mapper.

Regenerate via `python manage.py dump_ontology`; the output is
deterministic so the diff is reviewable.
"""
from __future__ import annotations

from datetime import date
from typing import Iterable

from django.apps import apps
from django.db import models as dj_models

from rdflib import Graph, Namespace, Literal, URIRef
from rdflib.namespace import RDF, RDFS, OWL, XSD, SKOS, FOAF, DCTERMS

HS = Namespace("http://data.judaicalink.org/ontology/haskala#")
JL = Namespace("http://data.judaicalink.org/ontology/")
GND = Namespace("http://d-nb.info/standards/elementset/gnd#")
WGS84 = Namespace("http://www.w3.org/2003/01/geo/wgs84_pos#")

# Bundle values on Book that the exporter turns into extra rdf:types,
# e.g. bundle="translation" → `hs:Translation`. Declare them so the
# ontology covers the actual produced types.
BUNDLE_SUBCLASSES = [
    "Translation", "Edition", "Mention", "Preface", "Production",
]

# Hand-curated mapping: Haskala predicate → JudaicaLink/standard predicate.
# Adds `hs:<key> rdfs:subPropertyOf <value>` so consumers can fold the
# Haskala-local property into the wider vocabulary.
PROPERTY_ALIGNMENTS = {
    "pref_label": SKOS.prefLabel,
    "german_name": SKOS.altLabel,
    "hebrew_name": SKOS.altLabel,
    "pseudonym": SKOS.altLabel,
    "viaf_id": DCTERMS.identifier,
    "gnd_id": GND.gndIdentifier,
    "date_of_birth": JL.birthDate,
    "date_of_death": JL.deathDate,
    "place_of_birth": JL.birthLocationURI,
    "place_of_death": JL.deathLocationURI,
    "occupations": JL.occupation,
    "name": RDFS.label,
    "full_title": DCTERMS.title,
    "title_in_latin_characters": DCTERMS.title,
    "publisher": DCTERMS.publisher,
    "topic": DCTERMS.subject,
    "languages": DCTERMS.language,
}

# Hand-curated class alignments.
CLASS_ALIGNMENTS = {
    "Person": [FOAF.Person, JL.Resource],
    "Book": [JL.Resource],
    "City": [JL.Resource],
    # The exporter labels places jl:Place (which JudaicaLink does not
    # define as a class itself — declared here as an alias for clarity).
}

# Format companion values that *_format fields can hold. Declared as
# rdfs:Datatype so consumers know what the literal datatypes mean.
FORMAT_DATATYPES = [
    ("FormatNone", "none"),
    ("FormatUnknown", "unknown"),
    ("FormatText", "text"),
    ("FormatFilteredHTML", "filtered HTML"),
    ("FormatFullHTML", "full HTML"),
    ("FormatMarkdown", "Markdown"),
    ("FormatXML", "XML"),
    ("FormatJSON", "JSON"),
]


def _ontology_model_classes() -> list[type]:
    """Return the Django model classes the exporter writes types for."""
    from home.models import (
        Language, Alignment, Font, Publisher, Series, TargetAudience,
        Typography, DateFormat, TextualModel, LanguageCount, Gender,
        Occupation, Edition, TranslationType, Translation, Mention, Preface,
        Production, Topic, MentionDescription, ProductionRole,
        FootnoteLocation, OriginalType, Person, City, Geolocation, Book,
        BookAuthor,
    )
    return [
        Language, Alignment, Font, Publisher, Series, TargetAudience,
        Typography, DateFormat, TextualModel, LanguageCount, Gender,
        Occupation, Edition, TranslationType, Translation, Mention, Preface,
        Production, Topic, MentionDescription, ProductionRole,
        FootnoteLocation, OriginalType, Person, City, Geolocation, Book,
        BookAuthor,
    ]


def _xsd_range_for(field: dj_models.Field) -> URIRef:
    if isinstance(field, dj_models.BooleanField):
        return XSD.boolean
    if isinstance(field, dj_models.IntegerField):
        return XSD.integer
    if isinstance(field, dj_models.FloatField):
        return XSD.double
    if isinstance(field, dj_models.DateTimeField):
        return XSD.dateTime
    if isinstance(field, dj_models.DateField):
        return XSD.date
    if isinstance(field, dj_models.UUIDField):
        return XSD.string
    return XSD.string


def _label_for_field(field: dj_models.Field) -> str:
    verbose = getattr(field, "verbose_name", None)
    if verbose and str(verbose) != field.name:
        return str(verbose)
    return field.name.replace("_", " ")


def _exported_fields(model: type) -> Iterable[dj_models.Field]:
    """Yield the fields the exporter actually writes for this model."""
    for field in model._meta.fields:
        if field.name in ("id", "pk"):
            continue
        if field.name.startswith("legacy_"):
            continue
        if field.name.endswith("_format") and isinstance(field, dj_models.CharField):
            continue
        yield field
    for m2m in model._meta.many_to_many:
        if m2m.name.startswith("legacy_"):
            continue
        yield m2m


def _bind_prefixes(g: Graph) -> None:
    g.bind("rdf", RDF)
    g.bind("rdfs", RDFS)
    g.bind("owl", OWL)
    g.bind("xsd", XSD)
    g.bind("skos", SKOS)
    g.bind("foaf", FOAF)
    g.bind("dcterms", DCTERMS)
    g.bind("gndo", GND)
    g.bind("wgs84", WGS84)
    g.bind("jl", JL)
    g.bind("hs", HS)


def _add_ontology_header(g: Graph) -> None:
    ont = URIRef(str(HS).rstrip("#"))
    g.add((ont, RDF.type, OWL.Ontology))
    g.add((ont, DCTERMS.title, Literal("Haskala Bibliography Ontology", lang="en")))
    g.add((ont, DCTERMS.description, Literal(
        "Schema vocabulary for the Haskala bibliography dataset. "
        "Generated from the Django models that drive the public site; "
        "regenerated by the dump_ontology management command.",
        lang="en",
    )))
    g.add((ont, DCTERMS.created, Literal(date.today().isoformat(), datatype=XSD.date)))
    g.add((ont, DCTERMS.publisher, Literal("JudaicaLink / Haskala Project")))
    g.add((ont, DCTERMS.license, URIRef("https://creativecommons.org/licenses/by/4.0/")))


def _add_format_datatypes(g: Graph) -> None:
    for local, human in FORMAT_DATATYPES:
        node = HS[local]
        g.add((node, RDF.type, RDFS.Datatype))
        g.add((node, RDFS.label, Literal(f"format: {human}", lang="en")))
        g.add((node, RDFS.subClassOf, XSD.string))


def _add_class(g: Graph, model: type) -> URIRef:
    cls_uri = HS[model.__name__]
    g.add((cls_uri, RDF.type, OWL.Class))
    verbose = getattr(model._meta, "verbose_name", None)
    label = str(verbose) if verbose else model.__name__
    g.add((cls_uri, RDFS.label, Literal(label, lang="en")))
    doc = _meaningful_docstring(model)
    if doc:
        g.add((cls_uri, RDFS.comment, Literal(doc, lang="en")))
    for jl_class in CLASS_ALIGNMENTS.get(model.__name__, []):
        g.add((cls_uri, RDFS.subClassOf, jl_class))
    return cls_uri


def _meaningful_docstring(model: type) -> str:
    """
    Return the hand-written docstring of `model`, or "" if Django has
    synthesised the default one of the form `Book(field1, field2, ...)`.
    """
    doc = (model.__doc__ or "").strip()
    if not doc:
        return ""
    auto_prefix = f"{model.__name__}("
    if doc.startswith(auto_prefix) and doc.endswith(")"):
        return ""
    return doc


def _add_property(g: Graph, model: type, field: dj_models.Field) -> None:
    pred = HS[field.name]
    domain = HS[model.__name__]

    is_object = isinstance(field, (dj_models.ForeignKey, dj_models.ManyToManyField))
    g.add((pred, RDF.type, OWL.ObjectProperty if is_object else OWL.DatatypeProperty))
    g.add((pred, RDFS.label, Literal(_label_for_field(field), lang="en")))
    g.add((pred, RDFS.domain, domain))

    if is_object:
        target = field.related_model
        if target is not None:
            g.add((pred, RDFS.range, HS[target.__name__]))
    else:
        g.add((pred, RDFS.range, _xsd_range_for(field)))

    aligned = PROPERTY_ALIGNMENTS.get(field.name)
    if aligned is not None:
        g.add((pred, RDFS.subPropertyOf, aligned))


def _add_bundle_subclasses(g: Graph) -> None:
    book_uri = HS["Book"]
    for sub in BUNDLE_SUBCLASSES:
        sub_uri = HS[sub]
        # Some of these (Edition, Mention, Preface, Production) are also
        # their own model classes — that's fine, owl:Class can be asserted
        # twice. Add an explicit subClassOf hint to the Book class for
        # the bundle-tag semantics the exporter uses.
        g.add((sub_uri, RDF.type, OWL.Class))
        g.add((sub_uri, RDFS.subClassOf, book_uri))
        g.add((sub_uri, RDFS.label, Literal(f"Book (bundle: {sub.lower()})", lang="en")))


def build_ontology_graph() -> Graph:
    # Make sure the Django app registry is populated before introspecting.
    apps.check_apps_ready()

    g = Graph()
    _bind_prefixes(g)
    _add_ontology_header(g)
    _add_format_datatypes(g)

    for model in _ontology_model_classes():
        _add_class(g, model)
        for field in _exported_fields(model):
            _add_property(g, model, field)

    _add_bundle_subclasses(g)
    return g
