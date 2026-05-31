"""
The accessibility-statement StaticPage ships in the haskala.sql seed
dump with the slug "a", which makes its public URL /a/. Rename it to
the descriptive "accessibility" so the page lives at /accessibility/
and footer/cookiebanner links can target a stable URL.

Idempotent: if the page already has the correct slug, the operation
is a no-op.
"""
from django.db import migrations


def fix_slug(apps, schema_editor):
    StaticPage = apps.get_model("home", "StaticPage")
    page = StaticPage.objects.filter(slug="a").first()
    if page is None:
        return
    # Avoid colliding with any sibling already using the descriptive
    # slug (e.g. set manually before this migration ran).
    siblings = StaticPage.objects.filter(slug="accessibility").exclude(pk=page.pk)
    if siblings.exists():
        return
    page.slug = "accessibility"
    page.url_path = page.url_path.replace("/a/", "/accessibility/")
    page.save(update_fields=["slug", "url_path"])


def revert(apps, schema_editor):
    StaticPage = apps.get_model("home", "StaticPage")
    page = StaticPage.objects.filter(slug="accessibility").first()
    if page is None:
        return
    if StaticPage.objects.filter(slug="a").exclude(pk=page.pk).exists():
        return
    page.slug = "a"
    page.url_path = page.url_path.replace("/accessibility/", "/a/")
    page.save(update_fields=["slug", "url_path"])


class Migration(migrations.Migration):

    dependencies = [
        ("home", "0023_book_latest_revision_city_latest_revision_and_more"),
    ]

    operations = [
        migrations.RunPython(fix_slug, reverse_code=revert),
    ]
