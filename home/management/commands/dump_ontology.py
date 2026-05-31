from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from haskala_rdf.ontology import build_ontology_graph


DEFAULT_OUTPUT = Path(settings.BASE_DIR) / "research" / "ontology.ttl"


class Command(BaseCommand):
    help = (
        "Regenerate research/ontology.ttl from the Django models. "
        "Output is deterministic — diff before committing."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--output", "-o",
            default=str(DEFAULT_OUTPUT),
            help=(
                "Target file (defaults to research/ontology.ttl in the "
                "project root)."
            ),
        )

    def handle(self, *args, **options):
        target = Path(options["output"])
        target.parent.mkdir(parents=True, exist_ok=True)

        g = build_ontology_graph()
        g.serialize(destination=str(target), format="turtle")

        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(g)} triples to {target}"
        ))
