"""
Scan every Book / Person / Edition / Translation / Mention / Preface
/ Production free-text column for the names of orphan cities and
report potential reconnect targets. Read-only — no FK is set.

The output CSV (``orphan_place_mentions.csv``) lists, for each
orphan city whose name appears verbatim somewhere in the catalog,
the entity that mentions it, the field that carries the mention,
and a short snippet of surrounding text. Use it as a worklist for
the manual reconnect pass.
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand
from django.db.models import Q

from home.models import (
    Book, City, Edition, Mention, Person, Preface, Production, Translation,
)


TARGET_MODELS = [
    ("Book", Book),
    ("Person", Person),
    ("Edition", Edition),
    ("Translation", Translation),
    ("Mention", Mention),
    ("Preface", Preface),
    ("Production", Production),
]

SKIP_FIELDS = {"slug", "uuid", "id", "legacy_language"}

# Person name columns store toponymic surnames ("Dubno, Salomon",
# "Hirschberg (Dr.)") that match City names without being place
# references. Skipping them keeps the reconnect worklist signal-
# dense.
SKIP_FIELDS_PER_MODEL = {
    "Person": {"pref_label", "german_name", "hebrew_name", "pseudonym"},
}


def _text_fields(model_cls, model_label):
    """Yield the model's TextField/CharField names worth scanning.

    Drupal left paired ``foo`` + ``foo_format`` columns where only
    the value column is interesting. Slug and uuid columns are
    skipped because a place name landing there is by definition not
    a free-text mention. Per-model skip lists drop name-shaped
    columns whose hits are toponymic surnames, not place refs."""
    per_model_skip = SKIP_FIELDS_PER_MODEL.get(model_label, set())
    out = []
    for f in model_cls._meta.fields:
        if f.get_internal_type() not in ("TextField", "CharField"):
            continue
        if f.name in SKIP_FIELDS or f.name.endswith("_format"):
            continue
        if f.name in per_model_skip:
            continue
        out.append(f.name)
    return out


def is_orphan(c: City) -> bool:
    """Same predicate as ``mark_orphan_places_draft``."""
    if Book.objects.filter(
        Q(publication_place=c)
        | Q(publication_place_other=c)
        | Q(original_publication_place=c)
    ).exists():
        return False
    if Person.objects.filter(
        Q(place_of_birth=c) | Q(place_of_death=c)
    ).exists():
        return False
    if Edition.objects.filter(city=c).exists():
        return False
    if Translation.objects.filter(city=c).exists():
        return False
    if Mention.objects.filter(mentionee_city=c).exists():
        return False
    return True


def _make_pattern(name: str) -> re.Pattern:
    """Whole-word, case-insensitive match. Python's ``\\b`` doesn't
    cover Hebrew letters, so we fall back to a non-word-char /
    string-edge boundary that does the right thing for Latin,
    Hebrew and extended scripts alike."""
    escaped = re.escape(name)
    return re.compile(
        rf"(?:^|(?<=[^\w]))({escaped})(?=[^\w]|$)",
        re.IGNORECASE,
    )


def _snippet(text: str, pattern: re.Pattern) -> str:
    m = pattern.search(text)
    if m is None:
        return ""
    start = max(0, m.start() - 50)
    end = min(len(text), m.end() + 50)
    return " ".join(text[start:end].split())


class Command(BaseCommand):
    help = (
        "Scan every text column for mentions of orphan cities. "
        "Output a CSV with one row per match for the manual reconnect pass."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="docs/audits/orphan_place_mentions.csv",
            help=(
                "Output path. Default: "
                "docs/audits/orphan_place_mentions.csv."
            ),
        )
        parser.add_argument(
            "--min-name-length",
            type=int,
            default=4,
            help="Skip orphan names shorter than this. Default 4. Avoids "
                 "false positives from 2-3 letter tokens like 'Or', 'Rom'.",
        )

    def handle(self, *args, **options):
        out_path = Path(options["out"])
        out_path.parent.mkdir(parents=True, exist_ok=True)
        min_len = options["min_name_length"]

        orphans = []
        for c in City.objects.all():
            name = (c.name or "").strip()
            if len(name) < min_len:
                continue
            if not is_orphan(c):
                continue
            orphans.append((c, name))

        target_total = sum(m.objects.count() for _, m in TARGET_MODELS)
        self.stdout.write(
            f"Scanning {len(orphans)} orphan cities "
            f"across {target_total} rows"
        )

        patterns = {
            (c.pk, name): _make_pattern(name) for c, name in orphans
        }

        rows = []
        for model_label, model_cls in TARGET_MODELS:
            fields = _text_fields(model_cls, model_label)
            for obj in model_cls.objects.all().iterator(chunk_size=200):
                for fname in fields:
                    value = getattr(obj, fname, "") or ""
                    if not value:
                        continue
                    text = str(value)
                    for (orphan_pk, orphan_name), pattern in patterns.items():
                        if pattern.search(text):
                            rows.append({
                                "orphan_uuid": orphan_pk,
                                "orphan_name": orphan_name,
                                "model": model_label,
                                "entity_pk": str(obj.pk),
                                "entity_slug": getattr(obj, "slug", "") or "",
                                "field": fname,
                                "snippet": _snippet(text, pattern),
                            })

        with out_path.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "orphan_uuid", "orphan_name",
                    "model", "entity_pk", "entity_slug",
                    "field", "snippet",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)

        unique_orphans = len({r["orphan_uuid"] for r in rows})
        self.stdout.write(self.style.SUCCESS(
            f"Wrote {len(rows)} mention(s) for "
            f"{unique_orphans} / {len(orphans)} orphan cities -> {out_path}"
        ))
