"""
Push the most recent RDF dump to a SPARQL endpoint without re-running
the export. Reads the freshly-built data graph from HASKALA_DUMPS_ROOT
(or wherever --source points), parses it, and writes it back via the
Graph Store Protocol (or SPARQL Update).

Useful for:
    - retrying a failed push after the export already succeeded
    - pushing a dump made on a different host
    - hand-editing a Turtle file before sending it upstream
"""
from __future__ import annotations

import gzip
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rdflib import Graph

from haskala_rdf.push import push_graph, target_from_settings


class Command(BaseCommand):
    help = (
        "Push the latest data graph from HASKALA_DUMPS_ROOT to the SPARQL "
        "endpoint configured via HASKALA_SPARQL_PUSH_URL."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--source",
            default=None,
            help=(
                "Path to the Turtle (or gzipped Turtle) file to push. "
                "Defaults to "
                "<HASKALA_DUMPS_ROOT>/<HASKALA_SLUG>/current/haskala.ttl.gz."
            ),
        )

    def handle(self, *args, **options):
        push_target = target_from_settings(settings)
        if push_target is None:
            raise CommandError(
                "HASKALA_SPARQL_PUSH_URL is empty — set it (or pass the URL "
                "via env) before running push_rdf."
            )

        if options.get("source"):
            source = Path(options["source"])
        else:
            source = (
                Path(settings.HASKALA_DUMPS_ROOT)
                / settings.HASKALA_SLUG
                / "current"
                / "haskala.ttl.gz"
            )

        if not source.exists():
            raise CommandError(f"Dump not found: {source}")

        self.stdout.write(f"Loading {source} …")
        graph = Graph()
        opener = gzip.open if source.suffix == ".gz" else open
        with opener(source, "rb") as f:
            graph.parse(f, format="turtle")

        self.stdout.write(
            f"  parsed {len(graph)} triples"
            f"\n  → PUT {push_target.url} (graph: {push_target.graph_iri},"
            f" protocol: {push_target.protocol})"
        )
        response = push_graph(graph, push_target)
        self.stdout.write(self.style.SUCCESS(
            f"  push complete: HTTP {response.status_code}"
        ))
