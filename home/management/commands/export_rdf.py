import gzip
import shutil
from datetime import datetime
from pathlib import Path
from django.conf import settings
from django.core.management.base import BaseCommand

from haskala_rdf.export import build_data_graph, build_meta_graph
from haskala_rdf.beacon import build_beacon_lines
from haskala_rdf.frontmatter import build_frontmatter_md

class Command(BaseCommand):
    help = "Export Haskala data to RDF (TTL + GZ), metagraph, frontmatter and BEACON."

    def handle(self, *args, **options):
        base = Path(settings.HASKALA_DUMPS_ROOT) / settings.HASKALA_SLUG
        current = base / "current"
        archive = base / "archive"
        archive.mkdir(parents=True, exist_ok=True)
        current.mkdir(parents=True, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        if any(current.iterdir()):
            target = archive / timestamp
            target.mkdir(parents=True)
            for f in current.iterdir():
                shutil.move(str(f), target / f.name)

        data_graph = build_data_graph()
        meta_graph = build_meta_graph(
            data_graph,
            identifier="haskala",
            base_dump_uri="http://data.judaicalink.org/data/haskala/",
            dump_filename="haskala.ttl.gz",
        )

        # Frontmatter-Markdown
        md_content = build_frontmatter_md(
            identifier="haskala",
            title="Haskala Bibliography",
            graph_uri="http://data.judaicalink.org/data/haskala",
            dump_filename="haskala.ttl.gz",
            meta_dump_filename="haskala-meta.ttl.gz",
            beacon_filename="haskala-beacon.txt",
        )
        (current / "haskala.md").write_text(md_content, encoding="utf-8")

        def write_gz(graph, filename):
            ttl_path = current / filename
            graph.serialize(destination=str(ttl_path), format="turtle")
            with open(ttl_path, "rb") as f_in, gzip.open(str(ttl_path) + ".gz", "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)
            ttl_path.unlink()  # nur .ttl.gz behalten

        write_gz(data_graph, "haskala.ttl")
        write_gz(meta_graph, "haskala-meta.ttl")

        # Frontmatter-Markdown
        md_path = current / "haskala.md"
        md_path.write_text(build_frontmatter_md(), encoding="utf-8")

        # BEACON-Datei
        beacon_path = current / "haskala-beacon.txt"
        beacon_path.write_text("\n".join(build_beacon_lines()), encoding="utf-8")

        self.stdout.write(self.style.SUCCESS("Haskala RDF export completed."))
