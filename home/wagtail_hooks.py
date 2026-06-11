"""
Wagtail admin hooks: snippet ViewSets with search + filter + list_display.

Each `register_snippet` invocation in `home/models.py` exposed the model
to the admin but with no list-display columns, no filters and no
search. Catalogue work on >1k Person / Book / City rows was painful.
This module replaces every raw `@register_snippet`-style registration
with a `SnippetViewSet` that wires the three pieces explicitly.

The simple "lookup table" snippets (Language, Gender, …) only need to
search on `name`; they share a base class. The entity-flavoured
snippets (Person, City, BookAuthor, Edition, Translation, Mention,
Preface, Production, plus the catalog dimensions like Publisher,
Series, Topic, Occupation) get bespoke ViewSets with cross-relation
filters and multi-field search.

The decorator-style `@register_snippet` on the model definitions still
fires when models load, but the explicit `register_snippet(ViewSet)`
calls below take precedence — Wagtail uses the most recent registration
per model.
"""
from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import (
    Alignment, Book, BookAuthor, City, DateFormat, Edition, FootnoteLocation,
    Font, Gender, Language, LanguageCount, Mention, MentionDescription,
    Occupation, OriginalType, Person, Preface, Production, ProductionRole,
    Publisher, Series, TargetAudience, TextualModel, Topic, Translation,
    TranslationType, Typography,
)


@hooks.register('register_admin_menu_item')
def register_front_page_menu_item():
    return MenuItem('Home Page', '/', icon_name='home', order=10000)


# ---------------------------------------------------------------------
# Entity-flavoured snippets
# ---------------------------------------------------------------------

class BookViewSet(SnippetViewSet):
    model = Book
    menu_label = "Books"
    menu_icon = "book"
    menu_order = 200

    list_display = ("name", "author_names", "bundle", "gregorian_year")
    list_filter = ("bundle", "gregorian_year", "live")
    search_fields = (
        "name",
        "full_title",
        "title_in_latin_characters",
        "authors__pref_label",
        "authors__german_name",
        "authors__hebrew_name",
    )


class PersonViewSet(SnippetViewSet):
    model = Person
    menu_label = "Persons"
    menu_icon = "user"
    menu_order = 210

    list_display = ("pref_label", "german_name", "hebrew_name", "gender", "live")
    list_filter = ("gender", "occupations", "place_of_birth", "live")
    search_fields = (
        "pref_label", "german_name", "hebrew_name", "pseudonym",
        "viaf_id", "gnd_id",
    )


class CityViewSet(SnippetViewSet):
    model = City
    menu_label = "Places"
    menu_icon = "site"
    menu_order = 220

    list_display = (
        "name", "slug", "wikidata_id",
        "parent_place", "merged_into",
        "legacy_language", "live",
    )
    list_filter = ("legacy_language", "live")
    search_fields = ("name", "slug", "wikidata_id")


class BookAuthorViewSet(SnippetViewSet):
    model = BookAuthor
    menu_label = "Book authors"
    menu_icon = "group"
    menu_order = 230

    list_display = ("book", "person", "role")
    list_filter = ("role",)
    search_fields = (
        "book__name", "person__pref_label",
        "person__german_name", "person__hebrew_name",
    )


class EditionViewSet(SnippetViewSet):
    model = Edition
    menu_label = "Editions"
    menu_icon = "doc-full"
    menu_order = 240

    list_display = ("name", "book", "city", "year")
    list_filter = ("year",)
    search_fields = ("name", "book__name", "city__name")


class TranslationViewSet(SnippetViewSet):
    model = Translation
    menu_label = "Translations"
    menu_icon = "globe"
    menu_order = 250

    list_display = ("title", "book", "language", "city", "year")
    list_filter = ("language", "year")
    search_fields = ("title", "book__name", "language__name", "city__name")


class MentionViewSet(SnippetViewSet):
    model = Mention
    menu_label = "Mentions"
    menu_icon = "comment"
    menu_order = 260

    list_display = ("book", "mentionee", "mentionee_city")
    list_filter = ("mentionee_city",)
    search_fields = (
        "book__name", "mentionee__pref_label",
        "mentionee__german_name", "mentionee__hebrew_name",
    )


class PrefaceViewSet(SnippetViewSet):
    model = Preface
    menu_label = "Prefaces"
    menu_icon = "openquote"
    menu_order = 270

    list_display = ("title", "book", "writer", "number")
    list_filter = ("number",)
    search_fields = (
        "title", "book__name",
        "writer__pref_label", "writer__german_name", "writer__hebrew_name",
    )


class ProductionViewSet(SnippetViewSet):
    model = Production
    menu_label = "Productions"
    menu_icon = "cogs"
    menu_order = 280

    list_display = ("title", "book", "producer", "role")
    list_filter = ("role",)
    search_fields = (
        "title", "book__name",
        "producer__pref_label", "producer__german_name", "producer__hebrew_name",
    )


# ---------------------------------------------------------------------
# Catalog dimensions (single-name snippets that anchor many books /
# persons; search on `name`)
# ---------------------------------------------------------------------

class PublisherViewSet(SnippetViewSet):
    model = Publisher
    menu_label = "Publishers"
    menu_icon = "form"
    menu_order = 290
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


class SeriesViewSet(SnippetViewSet):
    model = Series
    menu_label = "Series"
    menu_icon = "list-ul"
    menu_order = 300
    list_display = ("name", "slug")
    search_fields = ("name", "slug")


class TopicViewSet(SnippetViewSet):
    model = Topic
    menu_label = "Topics"
    menu_icon = "tag"
    menu_order = 310
    list_display = ("name",)
    search_fields = ("name",)


class OccupationViewSet(SnippetViewSet):
    model = Occupation
    menu_label = "Occupations"
    menu_icon = "pick"
    menu_order = 320
    list_display = ("name",)
    search_fields = ("name",)


# ---------------------------------------------------------------------
# Simple lookup tables. All carry just a `name` field; bulk-register
# with a uniform ViewSet so the admin gains search + list-display
# without 14 copy-pasted class bodies.
# ---------------------------------------------------------------------

_LOOKUP_MODELS = [
    (Language, "Languages"),
    (Alignment, "Alignments"),
    (Font, "Fonts"),
    (TargetAudience, "Target audiences"),
    (Typography, "Typography"),
    (DateFormat, "Date formats"),
    (TextualModel, "Textual models"),
    (LanguageCount, "Language counts"),
    (Gender, "Genders"),
    (TranslationType, "Translation types"),
    (MentionDescription, "Mention descriptions"),
    (ProductionRole, "Production roles"),
    (FootnoteLocation, "Footnote locations"),
    (OriginalType, "Original types"),
]


def _make_lookup_viewset(model, label, order):
    return type(
        f"{model.__name__}ViewSet",
        (SnippetViewSet,),
        {
            "model": model,
            "menu_label": label,
            "menu_icon": "snippet",
            "menu_order": order,
            "list_display": ("name",),
            "search_fields": ("name",),
        },
    )


# ---------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------

for viewset in [
    BookViewSet, PersonViewSet, CityViewSet, BookAuthorViewSet,
    EditionViewSet, TranslationViewSet, MentionViewSet, PrefaceViewSet,
    ProductionViewSet, PublisherViewSet, SeriesViewSet, TopicViewSet,
    OccupationViewSet,
]:
    register_snippet(viewset)

for i, (model, label) in enumerate(_LOOKUP_MODELS):
    register_snippet(_make_lookup_viewset(model, label, 400 + i * 10))
