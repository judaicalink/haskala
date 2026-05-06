import secrets
import uuid as uuid
from collections import defaultdict

from SPARQLWrapper import SPARQLWrapper, JSON
from django.contrib import messages
from django.db import models
from django.template.defaultfilters import slugify
from django.template.response import TemplateResponse
from django.utils.decorators import method_decorator
from django.utils.translation import gettext_lazy as _
from django.views.decorators.cache import cache_page
from modelcluster.fields import ParentalKey
from wagtail.admin.panels import FieldPanel, MultiFieldPanel, InlinePanel, FieldRowPanel
from wagtail.contrib.forms.models import AbstractFormField, AbstractEmailForm
from wagtail.contrib.forms.panels import FormSubmissionsPanel
from wagtail.fields import RichTextField
from wagtail.models import Page
from wagtail.search import index
from wagtail.snippets.models import register_snippet

# Create a bundle choice field for the options of translation, edition, mention and preface
BUNDLE_CHOICES = (
    ('translation', 'Translation'),
    ('edition', 'Edition'),
    ('mention', 'Mention'),
    ('preface', 'Preface'),
    ('person', 'Person'),
    ('book', 'Book'),
    ('production', 'Production'),
)

FORMAT_CHOICES = (
    ('', 'None'),
    ('NULL', 'Unknown'),
    ('text', 'Text'),
    ('filtered_html', 'Filtered HTML'),
    ('full_html', 'Full HTML'),
    ('markdown', 'Markdown'),
    ('xml', 'XML'),
    ('json', 'JSON'),
)


def sort_and_group_by_name(objects):
    # Step 1: Extract the 'name' attribute from each object
    names = [obj.name for obj in objects if hasattr(obj, 'name')]

    # Step 2: Sort the names alphabetically
    sorted_names = sorted(names)

    # Step 3: Group the names by their first letter
    grouped_names = {}
    for name in sorted_names:
        first_letter = name[0].upper()  # Group by uppercase first letter
        if first_letter not in grouped_names:
            grouped_names[first_letter] = []
        grouped_names[first_letter].append(name)

    return grouped_names


def get_people_names(self):
    """
    This function queries the rdf file for all instances of the class Person and returns their names
    :param self:
    :return: results
    """
    # make a request to the rdf file
    try:
        sparql = SPARQLWrapper("http://localhost:3030/haskala/sparql")
        # write the query which selects all instances of the class Person per name
        sparql.setQuery("""
            PREFIX foaf: <http://xmlns.com/foaf/0.1/>
            PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
            PREFIX xsd: <http://www.w3.org/2001/XMLSchema#>
            PREFIX owl: <http://www.w3.org/2002/07/owl#>
            PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
            PREFIX hs: <http://localhost/ontology#>
            
            SELECT ?person ?name ?gender ?occupation ?german_name ?hebrew_name ?VIAF_ID ?same_as
            WHERE { ?person foaf:name ?name .
            }
            ORDER BY asc(?name)
        """)
        sparql.setReturnFormat(JSON)
        results = sparql.query().convert()
        # print(results)
        return results
    except Exception as e:
        print(e)
        print("No people found")
        print("Check FUSEKI server")
        return None


def group_names_by_first_letter(names):
    grouped_names = defaultdict(list)

    for name in names:
        first_letter = name[0].upper()
        grouped_names[first_letter].append(name)

    return dict(grouped_names)


class LegacyImportedModel(models.Model):
    legacy_nid = models.IntegerField(null=True, blank=True, db_index=True)
    legacy_vid = models.IntegerField(null=True, blank=True)
    legacy_language = models.CharField(max_length=12, blank=True)
    legacy_status = models.BooleanField(default=True, blank=True)
    legacy_created = models.DateTimeField(null=True, blank=True)
    legacy_changed = models.DateTimeField(null=True, blank=True)

    class Meta:
        abstract = True


# Language model
@register_snippet
class Language(models.Model):
    """
    Model for the languages.
    Has no page view.
    For the languages of the books, not the pages.
    """
    id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(default=uuid.uuid4, editable=False, auto_created=True, unique=True)

    name = models.CharField(max_length=255, unique=True)
    language_code = models.CharField(max_length=50, blank=True, null=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Languages"

    def __str__(self):
        return self.name


# Alignment of text (vid = 7)
@register_snippet
class Alignment(models.Model):
    """
    Alignment of text (Drupal vocabulary: 'Alignment of text', vid = 7)
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Alignments"

    def __str__(self):
        return self.name


# Fonts (vid = 10)
@register_snippet
class Font(models.Model):
    """
    Fonts used in the publications (Drupal vocabulary: 'Fonts', vid = 10)
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Fonts"

    def __str__(self):
        return self.name


# Publishers (vid = 14)
@register_snippet
class Publisher(models.Model):
    """
    Publishers (Drupal vocabulary: 'Publishers', vid = 14)
    """
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    def save(self, *args, **kwargs):
        if self.name and not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("legacy_tid"),
    ]


    class Meta:
        verbose_name_plural = "Publishers"

    def __str__(self):
        return self.name


# Series (vid = 16)
@register_snippet
class Series(models.Model):
    """
    Series titles (Drupal vocabulary: 'Series', vid = 16)
    """
    name = models.CharField(max_length=255, unique=True)
    slug = models.SlugField(max_length=255, unique=True, blank=True, null=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("slug"),
        FieldPanel("legacy_tid"),
    ]

    def save(self, *args, **kwargs):
        if self.name and not self.slug:
            self.slug = generate_unique_slug(self, self.name)
        super().save(*args, **kwargs)


    class Meta:
        verbose_name_plural = "Series"

    def __str__(self):
        return self.name


# Target audience (vid = 17)
@register_snippet
class TargetAudience(models.Model):
    """
    Target audience (Drupal vocabulary: 'Target audience', vid = 17)
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Target audiences"

    def __str__(self):
        return self.name


# Typography (vid = 19)
@register_snippet
class Typography(models.Model):
    """
    Typography (Drupal vocabulary: 'Typography', vid = 19)
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Typographies"

    def __str__(self):
        return self.name


# Date format (vid = 8)
@register_snippet
class DateFormat(models.Model):
    """
    Format of dates (Drupal vocabulary: 'Date format', vid = 8)
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Date formats"

    def __str__(self):
        return self.name


# Textual models (vid = 3: 'Models')
@register_snippet
class TextualModel(models.Model):
    """
    Textual models (Drupal vocabulary: 'Models', vid = 3)
    Used e.g. for main/secondary textual models of a book.
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Textual models"

    def __str__(self):
        return self.name


# Language counts (vid = 2: 'Language counts')
@register_snippet
class LanguageCount(models.Model):
    """
    Language count categories (Drupal vocabulary: 'Language counts', vid = 2)
    E.g. 'monolingual', 'bilingual', 'multilingual'.
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Language counts"

    def __str__(self):
        return self.name


@register_snippet
class City(LegacyImportedModel):
    """
    Model for the cities
    """
    # id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, auto_created=True, unique=True)
    name = models.CharField(max_length=255)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    class Meta:
        verbose_name_plural = "Cities"

    def __str__(self):
        return self.name


@register_snippet
# Geolocations
class Geolocation(models.Model):
    """
    Model for the geolocation.
    Belongs to te city.
    """

    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, auto_created=True, unique=True)
    city = models.ForeignKey(City, on_delete=models.CASCADE)

    lat = models.FloatField(max_length=255, blank=True, null=True)
    lng = models.FloatField(max_length=255, blank=True, null=True)
    lat_sin = models.FloatField(max_length=255, blank=True, null=True)
    lat_cos = models.FloatField(max_length=255, blank=True, null=True)
    lng_rad = models.FloatField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.city.name


@register_snippet
class Gender(models.Model):
    name = models.CharField(max_length=255)
    legacy_tid = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


@register_snippet
class Occupation(models.Model):
    name = models.CharField(max_length=255)
    legacy_tid = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


@register_snippet
class Person(LegacyImportedModel):
    """
    Model for the person.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    pref_label = models.CharField(max_length=255, blank=True)
    german_name = models.CharField(max_length=255, blank=True)
    hebrew_name = models.CharField(max_length=255, blank=True)

    gender = models.ForeignKey(Gender, null=True, blank=True, on_delete=models.SET_NULL)
    occupations = models.ManyToManyField(Occupation, blank=True)

    viaf_id = models.CharField(max_length=255, blank=True)

    date_of_birth = models.CharField(max_length=255, blank=True)
    date_of_death = models.CharField(max_length=255, blank=True)

    place_of_birth = models.ForeignKey("City", null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name="born_here")
    place_of_death = models.ForeignKey("City", null=True, blank=True, on_delete=models.SET_NULL,
                                       related_name="died_here")

    pseudonym = models.CharField(max_length=255, blank=True)

    search_fields = [
        index.SearchField('pref_label', partial_match=True),
        index.SearchField('german_name', partial_match=True),
        index.SearchField('hebrew_name', partial_match=True),
    ]

    class Meta:
        verbose_name = "Person"
        verbose_name_plural = "Persons"
        ordering = ("pref_label",)

    def __str__(self):
        return self.pref_label or self.german_name or self.hebrew_name or str(self.pk)


@register_snippet
class Edition(LegacyImportedModel):
    """
    Model for the editions.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Belongs to book
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name="editions")

    # Edition changes, nut the usual created and updated at
    changes = models.CharField(max_length=255, blank=True, null=True)
    changes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Edition city
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)

    # Edition references
    references = models.CharField(max_length=255, blank=True, null=True)
    references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Edition year
    year = models.CharField(max_length=255, blank=True, null=True)
    year_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Editions"

    def __str__(self):
        return self.name


# Translation type
@register_snippet
class TranslationType(models.Model):
    """
    Model for the translation types
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = "Translation Types"

    def __str__(self):
        return self.name


@register_snippet
class Translation(LegacyImportedModel):
    """
    Model for the Translations
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    title = models.CharField(max_length=255, blank=True)

    # Belongs to book
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name="translations")

    # Translator
    translator = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)

    # Language
    language = models.ForeignKey(Language, null=True, blank=True, on_delete=models.SET_NULL)

    # City
    city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)

    # References
    references = models.TextField(blank=True, null=True)
    references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Year
    year = models.CharField(max_length=255, blank=True)
    year_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)


@register_snippet
class Mention(LegacyImportedModel):
    """
    Model for Mentions
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book, but not found in tables

    # Mentionee
    mentionee = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)

    # Mentionee city
    mentionee_city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)

    # Mentionee description
    mentionee_description = models.ForeignKey("MentionDescription", null=True, blank=True, on_delete=models.SET_NULL)


@register_snippet
class Preface(LegacyImportedModel):
    """
    Model for the Prefaces
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book
    book = models.ForeignKey('Book', on_delete=models.SET_NULL, null=True, blank=True, related_name="prefaces")

    # Notes
    notes = models.TextField(blank=True, null=True)
    notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Number
    number = models.IntegerField(default=1, blank=True, null=True)
    number_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Title
    title = models.TextField(blank=True, null=True)
    title_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Writer
    writer = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)
    writer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Prefaces"


@register_snippet
class Production(LegacyImportedModel):
    """
    Model for the Production
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    name_in_book = models.CharField(max_length=255, blank=True)
    person_name_appear = models.CharField(max_length=255, blank=True)
    # Belongs to book
    book = models.ForeignKey('Book', on_delete=models.CASCADE, related_name="productions", null=True, blank=True)

    # Producer
    producer = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)

    # Role
    role = models.ForeignKey("ProductionRole", null=True, blank=True, on_delete=models.SET_NULL)


@register_snippet
class Topic(models.Model):
    name = models.CharField(max_length=255)
    legacy_tid = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


class BookAuthor(models.Model):
    book = models.ForeignKey("Book", on_delete=models.CASCADE)
    person = models.ForeignKey("Person", on_delete=models.CASCADE)
    role = models.CharField(max_length=50, choices=[
        ("old_text_author", "Old text author"),
        ("original_text_author", "Original text author"),
        ("producer", "Producer"),
    ])


@register_snippet
class MentionDescription(models.Model):
    name = models.CharField(max_length=255)
    legacy_tid = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


@register_snippet
class ProductionRole(models.Model):
    name = models.CharField(max_length=255)
    legacy_tid = models.IntegerField(unique=True)

    def __str__(self):
        return self.name


@register_snippet
class FootnoteLocation(models.Model):
    """
    Location of footnotes (e.g. bottom of page, end of chapter, end of book).
    Drupal: dedicated vocabulary for 'location_of_footnotes' (tid).
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Footnote locations"

    def __str__(self):
        return self.name


@register_snippet
class OriginalType(models.Model):
    """
    Original type (Drupal vocabulary for 'original_type', e.g. original work,
    translation, adaptation etc.; cf. migrate_map_haskalaoriginaltypetermsmigrate).
    """
    name = models.CharField(max_length=255, unique=True)
    legacy_tid = models.IntegerField(unique=True, null=True, blank=True)

    panels = [
        FieldPanel("name"),
        FieldPanel("legacy_tid"),
    ]

    class Meta:
        verbose_name_plural = "Original types"

    def __str__(self):
        return self.name


class Book(LegacyImportedModel):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    bundle = models.CharField(max_length=255, choices=BUNDLE_CHOICES)

    # Authors
    authors = models.ManyToManyField(Person, through="BookAuthor", related_name="books")

    # Alignment
    alignment = models.ForeignKey(Alignment, null=True, blank=True, on_delete=models.SET_NULL)

    # Availability
    availability_notes = models.TextField(blank=True, null=True)
    availability_notes_format = models.TextField(blank=True, null=True)
    not_available = models.BooleanField(default=False, null=True, blank=True)

    # Notes
    structure_notes = models.TextField(blank=True, null=True)
    structure_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Studies
    studies = models.TextField(blank=True, null=True)
    studies_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Type general
    type_general_notes = models.TextField(blank=True, null=True)
    type_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Bans
    bans = models.TextField(blank=True, null=True)
    bans_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Bar Ilan Library ID
    bar_ilan_library_id = models.CharField(max_length=255, blank=True)
    bar_ilan_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Berlin Library ID
    berlin_library_id = models.CharField(max_length=255, blank=True)
    berlin_library_id_format = models.CharField(
        max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True
    )

    # Bibliographical citations
    bibliographical_citations = models.TextField(blank=True, null=True)
    bibliographical_citations_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # British Library ID
    british_library_id = models.CharField(max_length=255, blank=True)
    british_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Catalog numbers
    catalog_numbers_notes = models.TextField(blank=True, null=True)
    catalog_numbers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Censorship
    censorship = models.TextField(blank=True, null=True)
    censorship_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Contacts official agents
    contacts_official_agents = models.TextField(blank=True, null=True)
    contacts_official_agents_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Contacts other people
    contacts_other_people = models.TextField(blank=True, null=True)
    contacts_other_people_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Contemporary disputes
    contemporary_disputes = models.TextField(blank=True, null=True)
    contemporary_disputes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Contemporary references
    contemporary_references = models.TextField(blank=True, null=True)
    contemporary_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Contents table notes
    contents_table_notes = models.TextField(blank=True, null=True)
    contents_table_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                   null=True)

    # Contradict new edition
    contradict_new_edition = models.IntegerField(default=1, null=True, blank=True)

    # Contradict original
    contradict_original = models.IntegerField(default=1, null=True, blank=True)

    # Copy of book used
    copy_of_book_used = models.TextField(blank=True, null=True)
    copy_of_book_used_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Dedications
    dedications = models.TextField(blank=True, null=True)

    # Dedications notes
    dedications_notes = models.TextField(blank=True, null=True)
    dedications_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Diagrams book pages
    diagrams_book_pages = models.TextField(blank=True, null=True)
    diagrams_book_pages_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Diagrams notes
    diagrams_notes = models.TextField(blank=True, null=True)
    diagrams_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Editions notes
    editions_notes = models.TextField(blank=True, null=True)
    editions_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Epilogue
    epilogue = models.IntegerField(default=0, blank=True, null=True)

    # Epilogue notes
    epilogue_notes = models.TextField(blank=True, null=True)
    epilogue_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Examined volume number
    examined_volume_number = models.IntegerField(default=1, blank=True, null=True)

    # Expanded in edition
    expanded_in_edition = models.IntegerField(default=1, blank=True, null=True)

    # Expanded in translation
    expanded_in_translation = models.IntegerField(default=1, blank=True, null=True)

    # Fonts
    fonts = models.ManyToManyField(Font, blank=True)

    # Format of publication date
    format_of_publication_date = models.ForeignKey(
        DateFormat, null=True, blank=True, on_delete=models.SET_NULL
    )

    # Founders notes
    founders_notes = models.TextField(blank=True, null=True)
    founders_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Frankfurt Library ID
    frankfurt_library_id = models.CharField(max_length=255, blank=True)
    frankfurt_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                   null=True)

    # Full title
    full_title = models.TextField(blank=True, null=True)
    full_title_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Founders
    founders = models.IntegerField(default=0, blank=True, null=True)

    # Gregorian year
    gregorian_year = models.IntegerField(default=0, blank=True, null=True)

    # Gregorian year pub other
    gregorian_year_pub_other = models.CharField(max_length=255, blank=True)
    gregorian_year_pub_other_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Hebrew year publication other
    hebrew_year_pub_other = models.CharField(max_length=255, blank=True)
    hebrew_year_pub_other_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Hebrew year of publication
    hebrew_year_of_publication = models.CharField(max_length=255, blank=True)
    hebrew_year_of_publication_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Height
    height = models.CharField(max_length=255, blank=True)
    height_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # HUJI library ID
    huji_library_id = models.CharField(max_length=255, blank=True)
    huji_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                              null=True)

    # Illustrations diagrams
    illustrations_diagrams = models.IntegerField(default=0, blank=True, null=True)

    # Jewish sources quotes
    jewish_sources_quotes = models.TextField(blank=True, null=True)
    jewish_sources_quotes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Language
    languages = models.ManyToManyField(Language, blank=True, related_name="books")

    # Languages of footnotes
    footnote_languages = models.ManyToManyField(Language, blank=True, related_name="footnote_books")

    # Languages numbers (mono-, bi-, multi-)
    languages_number = models.ForeignKey(
        LanguageCount, null=True, blank=True, on_delete=models.SET_NULL
    )

    # Last known edition
    last_known_edition = models.TextField(blank=True, null=True)
    last_known_edition_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Later references
    later_references = models.TextField(blank=True, null=True)
    later_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Link to digital book
    digital_book_url = models.CharField(max_length=255, blank=True)
    digital_book_url_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Location of footnotes
    location_of_footnotes = models.ForeignKey(FootnoteLocation, null=True, blank=True, on_delete=models.SET_NULL,
                                              related_name="books")

    # Main textual models
    main_textual_models = models.ManyToManyField(TextualModel, blank=True, related_name="books_as_main_model")

    # Mention general notes
    mention_general_notes = models.TextField(blank=True, null=True)
    mention_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Mentions in reviews
    mentions_in_reviews = models.TextField(blank=True, null=True)
    mentions_in_reviews_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Motto
    motto = models.TextField(blank=True, null=True)
    motto_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Name in book
    name_in_book = models.TextField(blank=True, null=True)
    name_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Name of series
    series = models.ForeignKey(Series, null=True, blank=True, on_delete=models.SET_NULL, related_name="books")

    # New edition general notes
    new_edition_general_notes = models.TextField(blank=True, null=True)
    new_edition_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # New edition type else note
    new_edition_type_else_note = models.TextField(blank=True, null=True)
    new_edition_type_else_note_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # New edition type else ref
    new_edition_type_else_ref = models.TextField(blank=True, null=True)
    new_edition_type_else_ref_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # New edition type elsewhere
    new_edition_type_elsewhere = models.TextField(blank=True, null=True)
    new_edition_type_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # New edition type in text
    new_edition_type_in_text = models.TextField(blank=True, null=True)
    new_edition_type_in_text_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # New edition type notes
    new_edition_type_notes = models.TextField(blank=True, null=True)
    new_edition_type_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                     null=True)

    # New edition type reference
    new_edition_type_reference = models.TextField(blank=True, null=True)
    new_edition_type_reference_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # New York Library ID
    new_york_library_id = models.CharField(max_length=255, blank=True)
    new_york_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Non jewish sources quotes
    non_jewish_sources_quotes = models.TextField(blank=True, null=True)
    non_jewish_sources_quotes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Occasional words languages
    occasional_words_languages = models.ManyToManyField(
        Language,
        blank=True,
        related_name="books_with_occasional_words",
    )

    # Old author addition names
    old_author_addition_names = models.TextField(blank=True, null=True)
    old_author_addition_names_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Old author names other sor
    old_author_names_other_sor = models.TextField(blank=True, null=True)
    old_author_names_other_sor_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Old name in book
    old_name_in_book = models.TextField(blank=True, null=True)
    old_name_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Old text
    old_text = models.TextField(blank=True, null=True)
    old_text_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Old text author in book
    old_text_author_in_book = models.TextField(blank=True, null=True)
    old_text_author_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Original author
    original_author = models.TextField(blank=True, null=True)
    original_author_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                              null=True)

    # Original author else refer
    original_author_else_refer = models.TextField(blank=True, null=True)
    original_author_else_refer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Original author elsewhere
    original_author_elsewhere = models.TextField(blank=True, null=True)
    original_author_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Original author other name
    original_author_other_name = models.TextField(blank=True, null=True)
    original_author_other_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Original language
    original_language = models.ForeignKey(
        Language, null=True, blank=True, on_delete=models.SET_NULL, related_name="original_language_books"
    )

    # Original publication year
    original_publication_year = models.CharField(max_length=255, blank=True)
    original_publication_year_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Original Publisher
    original_publisher = models.ForeignKey(
        Publisher, null=True, blank=True, on_delete=models.SET_NULL, related_name="original_publications"
    )

    # Original sources mention
    original_sources_mention = models.TextField(blank=True, null=True)
    original_sources_mention_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Original text name
    original_text_name = models.TextField(blank=True, null=True)
    original_text_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Original title
    original_title = models.TextField(blank=True, null=True)
    original_title_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Original title else refer
    original_title_else_refer = models.TextField(blank=True, null=True)
    original_title_else_refer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Original title elsewhere
    original_title_elsewhere = models.TextField(blank=True, null=True)
    original_title_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Original type
    original_type = models.ForeignKey(OriginalType, null=True, blank=True, on_delete=models.SET_NULL,
                                      related_name="books")

    # Other books names
    other_books_names = models.TextField(blank=True, null=True)
    other_books_names_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Other libraries
    other_libraries = models.TextField(blank=True, null=True)
    other_libraries_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                              null=True)

    # Other volumes
    other_volumes = models.TextField(blank=True, null=True)
    other_volumes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                            null=True)

    # Pages number
    pages_number = models.CharField(max_length=255, blank=True)
    pages_number_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Partial publication
    partial_publication = models.TextField(blank=True, null=True)
    partial_publication_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Person name appear
    person_name_appear = models.IntegerField(blank=True, null=True)

    # Personal address
    personal_address = models.TextField(blank=True, null=True)

    # Personal address notes
    personal_address_notes = models.TextField(blank=True, null=True)
    personal_address_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                     null=True)

    # Planned volumes
    planned_volumes = models.TextField(blank=True, null=True)
    planned_volumes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                              null=True)

    # Preface
    preface = models.IntegerField(blank=True, null=True)  # Boolean? (Preface Yes/No)

    # Presented as original
    presented_as_original = models.IntegerField(blank=True, null=True)

    # Presented as translation
    presented_as_translation = models.IntegerField(blank=True, null=True)

    # Presented new edition
    presented_new_edition = models.IntegerField(blank=True, null=True)

    # Presented new edition note
    presented_new_edition_note = models.TextField(blank=True, null=True)
    presented_new_edition_note_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Presented new edition refe
    presented_new_edition_refe = models.TextField(blank=True, null=True)
    presented_new_edition_refe_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Presented original referen
    presented_original_referen = models.TextField(blank=True, null=True)
    presented_original_referen_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Presented as translatio notes
    presented_as_translatio_notes = models.TextField(blank=True, null=True)
    presented_as_translatio_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                            blank=True, null=True)

    # Presented as translation refe
    presented_as_translation_refe = models.TextField(blank=True, null=True)
    presented_as_translation_refe_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                            blank=True, null=True)

    # Preservation references
    preservation_references = models.TextField(blank=True, null=True)
    preservation_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Price (Char)
    price = models.TextField(blank=True, null=True)
    price_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Printed originally
    printed_originally = models.IntegerField(blank=True, null=True)

    # Printers
    printers = models.TextField(blank=True, null=True)

    # Printers notes
    printers_notes = models.TextField(blank=True, null=True)
    printers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Printing press notes
    printing_press_notes = models.TextField(blank=True, null=True)
    printing_press_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                   null=True)

    # Printing press references
    printing_press_references = models.TextField(blank=True, null=True)
    printing_press_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Production evidence
    production_evidence = models.TextField(blank=True, null=True)
    production_evidence_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Proofreaders
    proofreaders = models.IntegerField(blank=True, null=True)

    # Proofreaders notes
    proofreaders_notes = models.TextField(blank=True, null=True)
    proofreaders_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Publication place
    publication_place = models.ForeignKey(
        City, null=True, blank=True, on_delete=models.SET_NULL, related_name="publication_place_books"
    )

    # Publication place other
    publication_place_other = models.ForeignKey(
        City, null=True, blank=True, on_delete=models.SET_NULL, related_name="other_publication_place_books"
    )

    # Year in book
    year_in_book = models.CharField(max_length=255, blank=True)
    year_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Year in other
    year_in_other = models.CharField(max_length=255, blank=True)

    # Publisher name
    publisher = models.ForeignKey(
        Publisher, null=True, blank=True, on_delete=models.SET_NULL, related_name="publications"
    )

    # Rabbinical approbation notes
    rabbinical_approbation_notes = models.TextField(blank=True, null=True)
    rabbinical_approbation_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                           blank=True, null=True)

    # Rabbinical approbations
    rabbinical_approbations = models.IntegerField(blank=True, null=True)

    # Recommendations
    recommendations = models.IntegerField(blank=True, null=True)

    # Recommendations notes
    recommendations_notes = models.TextField(blank=True, null=True)
    recommendations_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # References for editions
    references_for_editions = models.TextField(blank=True, null=True)
    references_for_editions_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # References notes
    references_notes = models.TextField(blank=True, null=True)
    references_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Secondary sources
    secondary_sources = models.TextField(blank=True, null=True)
    secondary_sources_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Secondary textual models
    secondary_textual_models = models.ManyToManyField(
        TextualModel, blank=True, related_name="books_as_secondary_model"
    )

    # Sellers
    sellers = models.IntegerField(blank=True, null=True)

    # Sellers notes
    sellers_notes = models.TextField(blank=True, null=True)
    sellers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                            null=True)

    # Series part
    series_part = models.TextField(blank=True, null=True)

    # Sources exist
    sources_exist = models.TextField(blank=True, null=True)

    # Sources list
    sources_list = models.TextField(blank=True, null=True)
    sources_list_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Sources not mentioned (Int)
    sources_not_mentioned = models.IntegerField(blank=True, null=True)

    # Sources not mentioned list
    sources_not_mentioned_list = models.TextField(blank=True, null=True)
    sources_not_mentioned_list_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Sources not mentioned ref
    sources_not_mentioned_ref = models.TextField(blank=True, null=True)
    sources_not_mentioned_ref_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Sources references
    sources_references = models.TextField(blank=True, null=True)
    sources_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Structure preface notes
    structure_preface_notes = models.TextField(blank=True, null=True)
    structure_preface_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Subscribers
    subscribers = models.TextField(blank=True, null=True)

    # Subscribers notes
    subscribers_notes = models.TextField(blank=True, null=True)
    subscribers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Subscription appeal
    subscription_appeal = models.TextField(blank=True, null=True)

    # Subscription appeal notes
    subscription_appeal_notes = models.TextField(blank=True, null=True)
    subscription_appeal_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Table of content (Int)
    table_of_content = models.IntegerField(blank=True, null=True)

    # Target audience
    target_audience = models.ManyToManyField(TargetAudience, blank=True)

    # Target audience notes
    target_audience_notes = models.TextField(blank=True, null=True)
    target_audience_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Tel Aviv Library ID
    tel_aviv_library_id = models.CharField(max_length=255, blank=True)
    tel_aviv_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Textual model notes
    textual_model_notes = models.TextField(blank=True, null=True)
    textual_model_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Thanks (Int)
    thanks = models.TextField(blank=True, null=True)

    # Thanks notes
    thanks_notes = models.TextField(blank=True, null=True)
    thanks_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Title in Latin characters
    title_in_latin_characters = models.TextField(blank=True, null=True)
    title_in_latin_characters_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Translation type
    translation_type = models.ForeignKey(TranslationType, null=True, blank=True, on_delete=models.SET_NULL)

    # Topic
    topic = models.ForeignKey(Topic, null=True, blank=True, on_delete=models.SET_NULL)

    # Topics notes
    topics_notes = models.TextField(blank=True, null=True)
    topics_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Total number of editions
    total_number_of_editions = models.TextField(blank=True, null=True)
    total_number_of_editions_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Translation notes
    translation_notes = models.TextField(blank=True, null=True)
    translation_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Typography
    typography = models.ManyToManyField(Typography, blank=True)

    # Volumes notes
    volumes_notes = models.TextField(blank=True, null=True)
    volumes_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                            null=True)

    # Volumes published number
    volumes_published_number = models.TextField(blank=True, null=True)
    volumes_published_number_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Original publication place
    original_publication_place = models.ForeignKey(
        City,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="original_publication_place_books",
    )

    # Year in other (format for publication_year_in_other)
    year_in_other_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                            null=True)

    # Width
    width = models.CharField(max_length=255, blank=True)
    width_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    #  Titel & Attribute of Digital links
    digital_book_title = models.TextField(blank=True, null=True)
    digital_book_attributes = models.TextField(blank=True, null=True)

    search_fields = [
        index.SearchField("name", partial_match=True),
        index.SearchField("authors", partial_match=True),
    ]

    class Meta:
        verbose_name = "Book"
        verbose_name_plural = "Books"
        ordering = ["name"]  # default ordering in the snippet listing

    def __str__(self):
        return self.name or f"Book {self.pk}"

    def author_names(self):
        """
        Comma-separated list of authors for admin list views.
        """
        return ", ".join(str(a) for a in self.authors.all())

    author_names.short_description = _("Authors")


class HomePage(Page):
    """
    Model for the home page.
    The content is added in the wagtail dashboard.
    """

    # Database fields
    body = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    # parent_page_types = ['HomePage']

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class ContactFormField(AbstractFormField):
    """
    Form field for the contact form.
    """

    page = ParentalKey('ContactPage', on_delete=models.CASCADE, related_name='form_fields')


class ContactPage(AbstractEmailForm):
    """
    Page for the contact form.
    The form fields are defined in the wagtail dashboard.
    """

    body = RichTextField(blank=True)
    thank_you_text = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    content_panels = AbstractEmailForm.content_panels + [
        FormSubmissionsPanel(),
        FieldPanel('body'),
        InlinePanel('form_fields', label="Form fields"),
        FieldPanel('thank_you_text'),
        MultiFieldPanel([
            FieldRowPanel([
                FieldPanel('from_address', classname="col6"),
                FieldPanel('to_address', classname="col6"),
            ]),
            FieldPanel('subject'),
        ], "Email"),
    ]

    template = "contact/contact_page.html"
    landing_page_template = "contact/contact_page_landing.html"

    def serve(self, request, *args, **kwargs):
        """
        Handle form display + submission with success/error messages.
        """
        if request.method == "POST":
            form = self.get_form(request.POST, request.FILES)

            if form.is_valid():
                try:
                    # Standard handling from AbstractEmailForm:
                    # - send email
                    # - save submission
                    self.process_form(form)
                except Exception:
                    messages.error(
                        request,
                        "There was an error sending your message. "
                        "Please try again later."
                    )
                    # Re-render form with error message
                    context = self.get_context(request)
                    context["form"] = form
                    return TemplateResponse(
                        request,
                        self.get_template(request),
                        context,
                    )

                # Success
                messages.success(
                    request,
                    "Thank you, your message has been sent successfully."
                )

                # Render landing page (thank-you page)
                context = self.get_landing_page_context(request, form=form)
                return TemplateResponse(
                    request,
                    self.get_landing_page_template(request),
                    context,
                )

            else:
                # Form validation failed
                messages.error(
                    request,
                    "Please correct the errors below."
                )
                context = self.get_context(request)
                context["form"] = form
                return TemplateResponse(
                    request,
                    self.get_template(request),
                    context,
                )

        # GET: show empty form
        form = self.get_form()
        context = self.get_context(request)
        context["form"] = form
        return TemplateResponse(
            request,
            self.get_template(request),
            context,
        )


class BookDetailPage(Page):
    """
    Page for the detail of a book.
    """
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="detail_pages")
    body = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
        FieldPanel('book'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    parent_page_types = ['BooksPage']
    subpage_types = []

    template = "home/book_detail_page.html"

    @method_decorator(cache_page(60 * 60))
    # Render method for the detail page
    def serve(self, request):
        # Get context and render the page with the book details
        context = self.get_context(request)
        return self.render(request, context)

    def get_context(self, request):
        context = super().get_context(request)
        context['book'] = self.book
        return context

    def save(self, *args, **kwargs):
        if not self.slug and self.book:
            self.slug = slugify(self.book.name or self.book.full_title or self.book.pk)
        super().save(*args, **kwargs)

    def route(self, request, path_components):
        # Custom routing logic can go here
        if len(path_components) == 1:
            book_slug = path_components[0]
            try:
                # Look for a child page with this slug
                book_page = self.get_children().get(slug=book_slug).specific
                return book_page.route(request, [])
            except Page.DoesNotExist:
                pass
        return super().route(request, path_components)


class BooksPage(Page):
    """
    Page for the books overview.
    """

    body = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    # parent_page_types = ['HomePage']
    subpage_types = ['BookDetailPage']

    def get_context(self, request):
        # Fetch a list of all the books from the model.
        context = super().get_context(request)
        context['books'] = Book.objects.all()
        return context

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class DigitalBooksPage(Page):
    """
    Page for the digital books overview.
    """

    body = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    # parent_page_types = ['HomePage']
    subpage_types = ['DigitalBookDetailPage']

    def get_context(self, request):
        # Fetch a list of all the digital books from the model.
        context = super().get_context(request)

        # Filter the books by the digital book URL
        books_with_urls = Book.objects.filter(digital_book_url__isnull=False).exclude(digital_book_url='').filter(
            digital_book_url__regex=r'^https?://').all()

        context.update({
            'books': sort_and_group_by_name(books_with_urls),
        })

        print("Context:", context)
        return context

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class DigitalBookDetailPage(Page):
    """
    Page for the detail of a digital book.
    """
    body = RichTextField(blank=True)
    book = models.ForeignKey(Book, on_delete=models.PROTECT, related_name="digital_detail_pages")

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration

    content_panels = Page.content_panels + [
        FieldPanel('body'),
        FieldPanel('book'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    parent_page_types = ['DigitalBooksPage']
    subpage_types = []

    def get_context(self, request):
        context = super().get_context(request)
        context['digital_book'] = self.book
        return context

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class PlacesPage(Page):
    """
    Page for the places overview.
    """
    body = RichTextField(blank=True)
    nonce = secrets.token_hex(16)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    alphabet = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    hebrew_alphabet = list('אבגדהוזחטיכלמנסעפצקרשת')

    template = "home/places_page.html"

    def get_context(self, request):
        context = super().get_context(request)
        cities_array = group_names_by_first_letter(City.objects.all())
        context.update({
            'alphabet': self.alphabet,
            'hebrew_alphabet': self.hebrew_alphabet,
            'nonce': self.nonce,
            'cities': cities_array,
        })
        return context

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class CitiesPage(Page):
    """
    Page for the cities overview.
    """

    body = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    # parent_page_types = ['HomePage']
    subpage_types = ['CityDetailPage']

    def get_context(self, request):
        # Fetch a list of all the cities from the model.
        context = super().get_context(request)
        context['cities'] = City.objects.all()
        return context

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class CityDetailPage(Page):
    """
    Page for the detail of a city.
    """

    body = RichTextField(blank=True)
    city = models.ForeignKey(City, on_delete=models.PROTECT, related_name="detail_pages")

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
        FieldPanel('city'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    parent_page_types = ['CitiesPage']
    subpage_types = []

    def get_context(self, request):
        context = super().get_context(request)
        context['city'] = self.city
        return context

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class PersonsPage(Page):
    """
    Page for the persons overview.
    """
    # add the people names to the page
    body = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    # parent_page_types = ['HomePage']
    subpage_types = ['PersonDetailPage']

    def get_context(self, request):
        # Fetch a list of all the persons from the model.
        context = super().get_context(request)
        context['persons'] = Person.objects.all().order_by('pref_label', 'german_name', 'hebrew_name')

        return context

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class PersonDetailPage(Page):
    """
    Model for the person detail page.
    """
    # Database fields

    body = RichTextField(blank=True)
    person = models.ForeignKey(Person, on_delete=models.PROTECT, related_name="detail_pages")

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration
    content_panels = Page.content_panels + [
        FieldPanel('body'),
        FieldPanel('person'),
    ]

    promote_panels = [
        MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    ]

    # Parent page / subpage type rules
    parent_page_types = ['PersonsPage']
    subpage_types = []

    def get_context(self, request):
        context = super().get_context(request)
        context['person'] = self.person
        return context

    def __str__(self):
        return self.title

    @method_decorator(cache_page(60 * 60))  # 1 hour
    def serve(self, request, *args, **kwargs):
        return super().serve(request, *args, **kwargs)


class StaticPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel("body"),
    ]


from django.utils.text import slugify

def generate_unique_slug(instance, value, slug_field_name="slug"):
    """
    Generates a unique slug for instance, based on value (e.g. name).
    """
    ModelClass = instance.__class__

    base = slugify(value or "")
    if not base:
        # Fallback if name is empty or only special characters
        base = f"{ModelClass.__name__.lower()}-{instance.pk or ''}".strip("-")

    slug = base
    i = 2
    # Check for collisions and append -2, -3, ... if necessary
    while ModelClass.objects.filter(**{slug_field_name: slug}).exclude(pk=instance.pk).exists():
        slug = f"{base}-{i}"
        i += 1

    return slug
