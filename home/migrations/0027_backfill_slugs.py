"""
Backfill the new Book / Person / City slug fields for every row that
already exists in the database. Calls into the same slug helper the
runtime uses so the formatting is identical.

Idempotent: rows that already carry a slug (from an earlier partial
run, or set manually in the admin) are left alone.
"""
from django.db import migrations


def _slug_for(instance, source, model_cls):
    """Mirror generate_unique_slug() but resolve via apps registry."""
    from anyascii import anyascii
    from django.utils.text import slugify

    base = slugify(anyascii(source or ""))
    if not base:
        base = f"{model_cls.__name__.lower()}-{instance.pk}".strip("-")
    slug = base
    i = 2
    while model_cls.objects.filter(slug=slug).exclude(pk=instance.pk).exists():
        slug = f"{base}-{i}"
        i += 1
    return slug


def backfill(apps, schema_editor):
    Book = apps.get_model("home", "Book")
    Person = apps.get_model("home", "Person")
    City = apps.get_model("home", "City")

    for city in City.objects.filter(slug__isnull=True):
        city.slug = _slug_for(city, city.name, City)
        city.save(update_fields=["slug"])

    for city in City.objects.filter(slug=""):
        city.slug = _slug_for(city, city.name, City)
        city.save(update_fields=["slug"])

    for person in Person.objects.filter(slug__isnull=True):
        source = person.pref_label or person.german_name or person.hebrew_name or f"person-{person.pk}"
        person.slug = _slug_for(person, source, Person)
        person.save(update_fields=["slug"])

    for person in Person.objects.filter(slug=""):
        source = person.pref_label or person.german_name or person.hebrew_name or f"person-{person.pk}"
        person.slug = _slug_for(person, source, Person)
        person.save(update_fields=["slug"])

    for book in Book.objects.filter(slug__isnull=True):
        book.slug = _slug_for(book, book.name or f"book-{book.pk}", Book)
        book.save(update_fields=["slug"])

    for book in Book.objects.filter(slug=""):
        book.slug = _slug_for(book, book.name or f"book-{book.pk}", Book)
        book.save(update_fields=["slug"])


def revert(apps, schema_editor):
    # Re-running the forward migration is harmless; reverting just
    # blanks the slugs. No-op chosen so accidental backwards migration
    # doesn't lose user-curated slugs.
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0026_book_slug_city_slug_person_slug"),
    ]

    operations = [
        migrations.RunPython(backfill, reverse_code=revert),
    ]
