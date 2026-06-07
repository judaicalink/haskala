import gzip
import shutil
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from haskala_rdf.beacon import build_beacon_lines
from haskala_rdf.export import build_data_graph, build_meta_graph
from haskala_rdf.frontmatter import build_frontmatter_md
from haskala_rdf.push import push_graph, target_from_settings


class Command(BaseCommand):
    help = (
        "Export Haskala data to RDF (TTL + GZ), metagraph, frontmatter and "
        "BEACON. Optionally push the data graph to a remote SPARQL endpoint."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--no-push",
            action="store_true",
            help="Skip the SPARQL push even if HASKALA_SPARQL_PUSH_URL is set.",
        )

    def handle(self, *args, **options):
        base = Path(settings.HASKALA_DUMPS_ROOT) / settings.HASKALA_SLUG
        current = base / "current"
        archive = base / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        current.mkdir(parents=True, exist_ok=True)

        # Move any previous run aside into an archive subdir so /current
        # only ever holds the freshly produced files.
        if any(current.iterdir()):
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            target_dir = archive / timestamp
            target_dir.mkdir(parents=True)
            for f in current.iterdir():
                shutil.move(str(f), target_dir / f.name)

        data_graph = build_data_graph()
        meta_graph = build_meta_graph(
            data_graph,
            identifier=settings.HASKALA_SLUG,
            base_dump_uri="http://data.judaicalink.org/data/haskala/",
            dump_filename="haskala.ttl.gz",
        )

        def write_gz(graph, filename):
            ttl_path = current / filename
            graph.serialize(destination=str(ttl_path), format="turtle")
            with open(ttl_path, "rb") as f_in, gzip.open(str(ttl_path) + ".gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            ttl_path.unlink()

        write_gz(data_graph, "haskala.ttl")
        write_gz(meta_graph, "haskala-meta.ttl")

        md = build_frontmatter_md(
            identifier=settings.HASKALA_SLUG,
            title="Haskala Bibliography",
            graph_uri="http://data.judaicalink.org/data/haskala",
            dump_filename="haskala.ttl.gz",
            meta_dump_filename="haskala-meta.ttl.gz",
            beacon_filename="haskala-beacon.txt",
        )
        (current / "haskala.md").write_text(md, encoding="utf-8")

        beacon_lines = list(build_beacon_lines())
        (current / "haskala-beacon.txt").write_text(
            "\n".join(beacon_lines) + "\n", encoding="utf-8"
        )

        self.stdout.write(self.style.SUCCESS(
            f"Haskala RDF export completed: {current}"
        ))

        if options.get("no_push"):
            return

        push_target = target_from_settings(settings)
        if push_target is None:
            self.stdout.write(
                "  (SPARQL push disabled — HASKALA_SPARQL_PUSH_URL is empty)"
            )
            return

        self.stdout.write(
            f"  Pushing {len(data_graph)} triples to {push_target.url} "
            f"(graph: {push_target.graph_iri}, protocol: {push_target.protocol})"
        )
        response = push_graph(data_graph, push_target)
        self.stdout.write(self.style.SUCCESS(
            f"  SPARQL push complete: HTTP {response.status_code}"
        ))
