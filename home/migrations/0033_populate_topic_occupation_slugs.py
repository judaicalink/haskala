"""
Populate the new Topic.slug and Occupation.slug columns added in
``0032_occupation_slug_topic_slug``. Mirrors the slug pipeline the
runtime helper :func:`home.models.generate_unique_slug` uses (strip
non-Latin scripts → anyascii → slugify → de-dup with a -N suffix).
"""
from __future__ import annotations

from django.db import migrations


_NON_LATIN_SCRIPT_RANGES = (
    (0x0370, 0x03FF), (0x0400, 0x04FF), (0x0500, 0x052F),
    (0x0530, 0x058F), (0x0590, 0x05FF), (0x0600, 0x06FF),
    (0x0700, 0x074F), (0x0750, 0x077F), (0x0780, 0x07BF),
    (0x0900, 0x097F), (0x4E00, 0x9FFF), (0x3040, 0x309F),
    (0x30A0, 0x30FF), (0xAC00, 0xD7AF),
)


def _strip_non_latin(value):
    if not value:
        return ""
    out = []
    for ch in value:
        cp = ord(ch)
        if any(lo <= cp <= hi for lo, hi in _NON_LATIN_SCRIPT_RANGES):
            continue
        out.append(ch)
    return "".join(out)


def _slug_for(instance, source, model_cls):
    from anyascii import anyascii
    from django.utils.text import slugify

    cleaned = _strip_non_latin(source or "")
    base = slugify(anyascii(cleaned))
    if not base:
        short_id = str(instance.pk or "")[:8]
        base = f"{model_cls.__name__.lower()}-{short_id}".strip("-")
    slug = base
    i = 2
    while model_cls.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def forwards(apps, schema_editor):
    for model_name in ("Topic", "Occupation"):
        Model = apps.get_model("home", model_name)
        Model.objects.update(slug=None)
        for obj in Model.objects.order_by("pk"):
            obj.slug = _slug_for(obj, obj.name, Model)
            obj.save(update_fields=["slug"])


def revert(apps, schema_editor):
    # Lossless reset — the column itself is dropped by the previous
    # migration's reverse if the operator goes that far back.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0032_occupation_slug_topic_slug"),
    ]

    operations = [
        migrations.RunPython(forwards, reverse_code=revert),
    ]
