"""
Per-entity RDF subgraph builder for the public export endpoints.

For each Book, Person or City the caller can ask for "just the triples
about *this* record and the directly-linked rows" — a compact graph
suitable for "export this one record as RDF". The full bulk dump still
lives in build_data_graph() in export.py.
"""
from __future__ import annotations

from typing import Any

from rdflib import Graph, URIRef
from rdflib.namespace import OWL, FOAF, DCTERMS

from .export import (
    HS, HSK, JL, GND, GND_ID_BASE,
    BookAuthor,
    add_model_instance,
    init_graph,
    person_uri,
)


# RDFLIB serialization format key → outbound mime type.
SERIALIZATION = {
    "ttl":     ("turtle",   "text/turtle"),
    "turtle":  ("turtle",   "text/turtle"),
    "jsonld":  ("json-ld",  "application/ld+json"),
    "json-ld": ("json-ld",  "application/ld+json"),
    "rdf":     ("xml",      "application/rdf+xml"),
    "xml":     ("xml",      "application/rdf+xml"),
    "nt":      ("nt",       "application/n-triples"),
}

# Accept-header → format key. The keys here intentionally cover the
# common Linked-Data mime types so content negotiation just works.
ACCEPT_TO_FORMAT = {
    "text/turtle":            "ttl",
    "application/ld+json":    "jsonld",
    "application/rdf+xml":    "rdf",
    "application/n-triples":  "nt",
}


def _bind_extra(g: Graph) -> None:
    """Bind the shorter prefixes our exports rely on."""
    g.bind("foaf", FOAF)
    g.bind("dcterms", DCTERMS)
    g.bind("owl", OWL)


def _add_book(g: Graph, book) -> URIRef:
    s = add_model_instance(g, book, extra_types=[JL.Resource])

    # bundle → extra rdf:type
    if book.bundle:
        g.add((s, JL.Resource, HS[book.bundle.capitalize()]))

    # Authorships
    for ba in BookAuthor.objects.filter(book=book).select_related("person"):
        if ba.person:
            p = person_uri(ba.person)
            g.add((s, DCTERMS.creator, p))

    # Digital copy
    if book.digital_book_url:
        try:
            g.add((s, FOAF.page, URIRef(book.digital_book_url.strip())))
        except Exception:
            pass

    return s


def _add_person(g: Graph, person) -> URIRef:
    s = add_model_instance(g, person, extra_types=[FOAF.Person, JL.Resource])

    if person.viaf_id:
        g.add((s, OWL.sameAs, URIRef(f"https://viaf.org/viaf/{person.viaf_id}")))

    if person.gnd_id:
        g.add((s, GND["gndIdentifier"], URIRef(f"{GND_ID_BASE}{person.gnd_id}")))
        g.add((s, OWL.sameAs, URIRef(f"{GND_ID_BASE}{person.gnd_id}")))

    return s


def _add_city(g: Graph, city) -> URIRef:
    s = add_model_instance(g, city, extra_types=[JL.Place, JL.Resource])
    for geo in city.geolocation_set.all():
        add_model_instance(g, geo)
    return s


def build_entity_graph(obj: Any) -> Graph:
    """
    Build a small RDF graph carrying every triple our public exporter
    would emit about a single Book / Person / City instance.
    """
    g = init_graph()
    _bind_extra(g)

    # Use a duck-type dispatch on class name so we don't have to
    # import the home.models classes at module load time (which would
    # circulate back through this file).
    cls = obj.__class__.__name__
    if cls == "Book":
        _add_book(g, obj)
    elif cls == "Person":
        _add_person(g, obj)
    elif cls == "City":
        _add_city(g, obj)
    else:
        add_model_instance(g, obj)

    return g


def serialize_entity(obj: Any, fmt: str) -> tuple[bytes, str]:
    """
    Serialize an entity to RDF in the requested format.

    Returns (body, mime_type). Raises ValueError on unknown fmt.
    """
    if fmt not in SERIALIZATION:
        raise ValueError(f"Unsupported RDF format: {fmt!r}")
    rdflib_format, mime = SERIALIZATION[fmt]
    g = build_entity_graph(obj)
    body = g.serialize(format=rdflib_format)
    if isinstance(body, str):
        body = body.encode("utf-8")
    return body, mime


__all__ = [
    "SERIALIZATION",
    "ACCEPT_TO_FORMAT",
    "build_entity_graph",
    "serialize_entity",
    "HSK",
]
