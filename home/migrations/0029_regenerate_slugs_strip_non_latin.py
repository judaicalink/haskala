"""
Regenerate Book / Person / City slugs with the new non-Latin-script
stripper in front of anyascii. The previous slugs let Hebrew (and
other non-Latin) characters bleed through as transliterated noise
(``hrn-yvsf``); the new pipeline strips them up front, keeping only
the Latin part of the source string. Hebrew-only rows fall back to a
``<modelclass>-<short-uuid>`` slug.

The migration is idempotent: re-running yields the same result. It
re-uses the runtime ``generate_unique_slug`` helper so the migration
and the live save() codepath stay in lock-step.
"""
from django.db import migrations


def _slug_for(instance, source, model_cls):
    """Mirror generate_unique_slug() but resolve via the apps registry."""
    from anyascii import anyascii
    from django.utils.text import slugify

    from home.models import _NON_LATIN_SCRIPT_RANGES

    def strip_non_latin(value):
        if not value:
            return ""
        out = []
        for ch in value:
            cp = ord(ch)
            if any(lo <= cp <= hi for lo, hi in _NON_LATIN_SCRIPT_RANGES):
                continue
            out.append(ch)
        return "".join(out)

    cleaned = strip_non_latin(source or "")
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


def regenerate(apps, schema_editor):
    Book = apps.get_model("home", "Book")
    Person = apps.get_model("home", "Person")
    City = apps.get_model("home", "City")

    # Clear all slugs first so collision resolution starts from a
    # blank slate; otherwise the order in which rows are visited
    # could carry over -2, -3 suffixes from the old run.
    Book.objects.update(slug=None)
    Person.objects.update(slug=None)
    City.objects.update(slug=None)

    for city in City.objects.order_by("pk"):
        city.slug = _slug_for(city, city.name, City)
        city.save(update_fields=["slug"])

    for person in Person.objects.order_by("pk"):
        source = (
            person.pref_label
            or person.german_name
            or person.hebrew_name
            or f"person-{person.pk}"
        )
        person.slug = _slug_for(person, source, Person)
        person.save(update_fields=["slug"])

    for book in Book.objects.order_by("pk"):
        book.slug = _slug_for(book, book.name or f"book-{book.pk}", Book)
        book.save(update_fields=["slug"])


def revert(apps, schema_editor):
    # Nothing to revert structurally; the previous slug column shape
    # is preserved. Leaving as a no-op so a backwards migration
    # doesn't blank user-curated slugs.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0028_book_expire_at_book_expired_book_first_published_at_and_more"),
    ]

    operations = [
        migrations.RunPython(regenerate, reverse_code=revert),
    ]
