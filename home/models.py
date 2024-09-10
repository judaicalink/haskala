import secrets

import uuid as uuid
from django.db import models
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import defaultdict

from django.template.defaultfilters import slugify
from modelcluster.fields import ParentalKey
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.contrib.forms.models import AbstractFormField, AbstractEmailForm
from wagtail.contrib.forms.panels import FormSubmissionsPanel

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel, MultiFieldPanel, FieldRowPanel
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


# Language model
@register_snippet
class Language(models.Model):
    """
    Model for the languages.
    Has no page view.
    For the languages of the books, not the pages.
    """
    id = models.AutoField(primary_key=True)
    # Todo: add uuid
    name = models.CharField(max_length=255, unique=True)
    language_code = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = "Languages"

    def __str__(self):
        return self.name


@register_snippet
class City(models.Model):
    """
    Model for the cities
    """
    # id = models.AutoField(primary_key=True)
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False, auto_created=True, unique=True)
    name = models.CharField(max_length=255)

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
class Person(models.Model):
    """
    Model for the person.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    def __int__(self, name, pref_label):
        self.name = name
        self.pref_label = pref_label

    # name = models.CharField(max_length=255, blank=True)
    # pref_label = models.CharField(max_length=255, blank=True)
    gender = models.CharField(max_length=255, blank=True)

    # German name
    german_name = models.CharField(max_length=255, blank=True)
    german_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Hebrew name
    hebrew_name = models.CharField(max_length=255, blank=True)
    hebrew_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Occupation
    # TODO: link to the tid of the occupation, can have multiple occupations
    occupation = models.IntegerField(null=True, blank=True)  # links to tid of the occupation

    # VIAF ID
    VIAF_ID = models.CharField(max_length=255, blank=True)
    VIAF_ID_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Same as
    # same_as = models.CharField(max_length=255, blank=True)

    # Date of birth
    date_of_birth = models.CharField(max_length=255, blank=True)

    # Date of death
    date_of_death = models.CharField(max_length=255, blank=True)

    # Place of birth
    # TODO: link to the tid of the place of birth, links to city
    place_of_birth = models.IntegerField(null=True, blank=True)

    # Place of death
    place_of_death = models.IntegerField(null=True, blank=True)

    # Pseudonym
    pseudonym = models.CharField(max_length=255, blank=True)
    pseudonym_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    def __str__(self):
        return self.german_name


@register_snippet
class Edition(models.Model):
    """
    Model for the editions.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True, blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Belongs to book

    # Edition changes, nut the usual created and updated at
    changes = models.CharField(max_length=255, blank=True, null=True)
    changes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Edition city
    # TODO: link to the city
    city = models.IntegerField(blank=True, null=True)  # links to tid of the city

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
class Translation(models.Model):
    """
    Model for the Translations
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book

    # Language
    # TODO: add multiple languages
    language = models.CharField(max_length=255, blank=True, null=True)  # Can have multiple languages over delta

    # City
    # TODO: link to the id of the city
    city = models.IntegerField(blank=True, null=True)  # links to tid of the city

    # References
    references = models.CharField(max_length=255, blank=True, null=True)
    references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Year
    year = models.CharField(max_length=255, blank=True)
    year_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Translator
    # TODO: link to the id of the person
    translator = models.IntegerField(blank=True, null=True)  # links to tid of the person


@register_snippet
class Mention(models.Model):
    """
    Model for Mentions
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book

    # Mentionee
    # TODO: link to the id of the person
    mentionee = models.IntegerField(null=True)  # links to tid of the person

    # Mentionee city
    # TODO: link to the id of the city
    mentionee_city = models.IntegerField(null=True)  # links to tid of the city

    # Mentionee description
    # TODO: link to the id of the description
    mentionee_description = models.IntegerField  # links to tid of the description


@register_snippet
class Preface(models.Model):
    """
    Model for the Prefaces
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book
    # book = models.ForeignKey('Book', on_delete=models.CASCADE)

    # Notes
    notes = models.CharField(max_length=255, blank=True, null=True)
    notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Number
    number = models.IntegerField(default=1, blank=True, null=True)
    number_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Title
    title = models.CharField(max_length=255, blank=True, null=True)
    title_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Writer
    writer = models.IntegerField(blank=True, null=True)  # links to tid of the person
    writer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    class Meta:
        verbose_name_plural = "Prefaces"


@register_snippet
class Production(models.Model):
    """
    Model for the Production
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255, blank=True, null=True)
    # Belongs to book

    # Producer
    # TODO: link to the id of the person
    producer = models.IntegerField(blank=True, null=True)  # links to tid of the person

    # Role
    # TODO: link to the id of the role, can have multiple roles
    role = models.IntegerField(blank=True, null=True)  # links to tid of the role


@register_snippet
class Book(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)

    bundle = models.CharField(max_length=255, choices=BUNDLE_CHOICES)

    # entity_id = models.CharField(max_length=255, blank=True)
    # revision_id = models.CharField(max_length=255, blank=True)

    language = models.CharField(max_length=255, blank=True)
    # field_book_target_id = models.CharField(max_length=255, blank=True)

    # Alignment
    alignment = models.CharField(max_length=255, blank=True)  # tid

    # Availability
    availability_notes = models.CharField(max_length=255, blank=True)
    availability_notes_format = models.CharField(max_length=255, blank=True)
    not_available = models.BooleanField()

    # Notes
    structure_notes = models.CharField(max_length=255, blank=True)
    structure_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Studies
    studies = models.CharField(max_length=255, blank=True)
    studies_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Type general
    type_general_notes = models.CharField(max_length=255, blank=True)
    type_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Bans
    bans = models.CharField(max_length=255, blank=True)
    bans_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Bar Ilan Library ID
    bar_ilan_library_id = models.CharField(max_length=255, blank=True)
    bar_ilan_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Berlin Library ID
    berlin_library_id = models.CharField(max_length=255, blank=True)
    bar_ilan_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Bibliographical citations
    bibliographical_citations = models.CharField(max_length=255, blank=True)
    bibliographical_citations_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # British Library ID
    british_library_id = models.CharField(max_length=255, blank=True)
    british_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Catalog numbers
    catalog_numbers_notes = models.CharField(max_length=255, blank=True)
    catalog_numbers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Censorship
    censorship = models.CharField(max_length=255, blank=True)
    censorship_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Contacts official agents
    contacts_official_agents = models.CharField(max_length=255, blank=True)
    contacts_official_agents_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Contacts other people
    contacts_other_people = models.CharField(max_length=255, blank=True)
    contacts_other_people_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, blank=True, null=True)

    # Contemporary disputes
    contemporary_disputes = models.CharField(max_length=255, blank=True)
    contemporary_disputes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Contemporary references
    contemporary_references = models.CharField(max_length=255, blank=True)
    contemporary_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Contents table notes
    contents_table_notes = models.CharField(max_length=255, blank=True)
    contents_table_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                   null=True)

    # Contradict new edition
    contradict_new_edition = models.IntegerField(default=1)

    # Contradict original
    contradict_original = models.IntegerField(default=1)

    # Copy of book used
    copy_of_book_used = models.CharField(max_length=255, blank=True)
    copy_of_book_used_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Dedications
    dedications = models.CharField(max_length=255, blank=True)

    # Dedications notes
    dedications_notes = models.CharField(max_length=255, blank=True)
    dedications_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Diagrams book pages
    diagrams_book_pages = models.CharField(max_length=255, blank=True)
    diagrams_book_pages_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Diagrams notes
    diagrams_notes = models.CharField(max_length=255, blank=True)
    diagrams_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Editions notes
    editions_notes = models.CharField(max_length=255, blank=True)
    editions_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Epilogue
    epilogue = models.IntegerField(default=0, blank=True, null=True)

    # Epilogue notes
    epilogue_notes = models.CharField(max_length=255, blank=True)
    epilogue_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Examined volume number
    examined_volume_number = models.IntegerField(default=1, blank=True, null=True)

    # Expanded in edition
    expanded_in_edition = models.IntegerField(default=1, blank=True, null=True)

    # Expanded in translation
    expanded_in_translation = models.IntegerField(default=1, blank=True, null=True)

    # Fonts
    # TODO: link to tid of the fonts
    fonts = models.IntegerField(blank=True, null=True)

    # Format of publication date
    # TODO: link to tid of the format of publication date
    format_of_publication_date = models.IntegerField(blank=True, null=True)

    # Founders notes
    founders_notes = models.CharField(max_length=255, blank=True)
    founders_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Frankfurt Library ID
    frankfurt_library_id = models.CharField(max_length=255, blank=True)
    frankfurt_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                   null=True)

    # Full title
    full_title = models.CharField(max_length=255, blank=True)
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
    jewish_sources_quotes = models.CharField(max_length=255, blank=True)
    jewish_sources_quotes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Language
    # TODO: add multiple languages
    language = models.IntegerField(blank=True, null=True)  # Can have multiple languages over delta

    # Languages of footnotes
    # TODO: add multiple languages
    languages_of_footnotes = models.IntegerField(blank=True, null=True)  # Can have multiple languages over delta

    # Languages number
    languages_number = models.IntegerField(blank=True, null=True)  # Can have multiple languages over delta

    # Last known edition
    last_known_edition = models.CharField(max_length=255, blank=True)
    last_known_edition_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Later references
    later_references = models.CharField(max_length=255, blank=True)
    later_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Link to digital book
    digital_book_url = models.CharField(max_length=255, blank=True)
    digital_book_url_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Location of footnotes
    # TODO: link to the tid
    location_of_footnotes = models.IntegerField(blank=True, null=True)  # links to tid

    # Main textual models
    # TODO: link to the tid
    main_textual_models = models.IntegerField(blank=True, null=True)  # links to tid

    # Mention general notes
    mention_general_notes = models.CharField(max_length=255, blank=True)
    mention_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Mentions in reviews
    mentions_in_reviews = models.CharField(max_length=255, blank=True)
    mentions_in_reviews_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Motto
    motto = models.CharField(max_length=255, blank=True)
    motto_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Name in book
    name_in_book = models.CharField(max_length=255, blank=True)
    name_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Name of series
    # TODO: link to the tid
    name_of_series = models.IntegerField(blank=True, null=True)  # links to tid

    # New edition general notes
    new_edition_general_notes = models.CharField(max_length=255, blank=True)
    new_edition_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # New edition type else note
    new_edition_type_else_note = models.CharField(max_length=255, blank=True)
    new_edition_type_else_note_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # New edition type else ref
    new_edition_type_else_ref = models.CharField(max_length=255, blank=True)
    new_edition_type_else_ref_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # New edition type elsewhere
    new_edition_type_elsewhere = models.CharField(max_length=255, blank=True)
    new_edition_type_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # New edition type in text
    new_edition_type_in_text = models.CharField(max_length=255, blank=True)
    new_edition_type_in_text_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # New edition type notes
    new_edition_type_notes = models.CharField(max_length=255, blank=True)
    new_edition_type_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                     null=True)

    # New edition type reference
    new_edition_type_reference = models.CharField(max_length=255, blank=True)
    new_edition_type_reference_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # New York Library ID
    new_york_library_id = models.CharField(max_length=255, blank=True)
    new_york_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Non jewish sources quotes
    non_jewish_sources_quotes = models.CharField(max_length=255, blank=True)
    non_jewish_sources_quotes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Occasional words languages
    # TODO: link to the tid
    occasional_words_languages = models.IntegerField(blank=True, null=True)

    # Old author addition names
    old_author_addition_names = models.CharField(max_length=255, blank=True)
    old_author_addition_names_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Old author names other sor
    # Was empty
    old_author_names_other_sor = models.CharField(max_length=255, blank=True)
    old_author_names_other_sor_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Old name in book
    old_name_in_book = models.CharField(max_length=255, blank=True)
    old_name_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Old text
    old_text = models.CharField(max_length=255, blank=True)
    old_text_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Old text author
    # TODO: link to the tid of author
    old_text_author = models.IntegerField(blank=True, null=True)

    # Old text author in book
    old_text_author_in_book = models.CharField(max_length=255, blank=True)
    old_text_author_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Original author
    original_author = models.CharField(max_length=255, blank=True)
    original_author_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                              null=True)

    # Original author else refer
    original_author_else_refer = models.CharField(max_length=255, blank=True)
    original_author_else_refer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Original author elsewhere
    original_author_elsewhere = models.CharField(max_length=255, blank=True)
    original_author_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Original author other name
    original_author_other_name = models.CharField(max_length=255, blank=True)
    original_author_other_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Original language
    # TODO: link to the tid of the original language
    original_language = models.IntegerField(blank=True, null=True)

    # Original publication year
    original_publication_year = models.CharField(max_length=255, blank=True)
    original_publication_year_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Original Publisher
    # TODO: link to the tid of the original publisher
    original_publisher = models.IntegerField(blank=True, null=True)

    # Original sources mention
    original_sources_mention = models.CharField(max_length=255, blank=True)
    original_sources_mention_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Original text author
    # TODO: link to the tid of the original text author
    original_text_author = models.IntegerField(blank=True, null=True)

    # Original text name
    original_text_name = models.CharField(max_length=255, blank=True)
    original_text_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Original title
    original_title = models.CharField(max_length=255, blank=True)
    original_title_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Original title else refer
    original_title_else_refer = models.CharField(max_length=255, blank=True)
    original_title_else_refer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Original title elsewhere
    original_title_elsewhere = models.CharField(max_length=255, blank=True)
    original_title_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Original type
    # TODO: link to the tid of the original type
    original_type = models.IntegerField(blank=True, null=True)

    # Other books names
    other_books_names = models.CharField(max_length=255, blank=True)
    other_books_names_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Other libraries
    other_libraries = models.CharField(max_length=255, blank=True)
    other_libraries_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                              null=True)

    # Other volumes
    other_volumes = models.CharField(max_length=255, blank=True)
    other_volumes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                            null=True)

    # Pages number
    pages_number = models.CharField(max_length=255, blank=True)
    pages_number_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Partial publication
    partial_publication = models.CharField
    partial_publication_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Person name appear
    person_name_appear = models.IntegerField(blank=True, null=True)  # does not link to a person

    # Personal address
    personal_address = models.IntegerField(blank=True, null=True)

    # Personal address notes
    personal_address_notes = models.CharField(max_length=255, blank=True)
    personal_address_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                     null=True)

    # Planned volumes
    planned_volumes = models.CharField(max_length=255, blank=True)
    planned_volumes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                              null=True)

    # Preface
    preface = models.IntegerField(blank=True, null=True)  # Boolean? (Preface Yes/No)

    # Structure preface notes
    structure_preface_notes = models.CharField(max_length=255, blank=True)
    structure_preface_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Presented as original
    presented_as_original = models.IntegerField(blank=True, null=True)

    # Presented as translation
    presented_as_translation = models.IntegerField(blank=True, null=True)

    # Presented new edition
    presented_new_edition = models.IntegerField(blank=True, null=True)

    # Presented new edition note
    presented_new_edition_note = models.CharField(max_length=255, blank=True)
    presented_new_edition_note_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Presented new edition refe
    presented_new_edition_refe = models.CharField(max_length=255, blank=True)
    presented_new_edition_refe_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Presented original referen
    presented_original_referen = models.CharField(max_length=255, blank=True)
    presented_original_referen_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Presented as translatio notes
    presented_as_translatio_notes = models.CharField(max_length=255, blank=True)
    presented_as_translatio_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                            blank=True, null=True)

    # Presented as translation refe
    presented_as_translation_refe = models.CharField(max_length=255, blank=True)
    presented_as_translation_refe_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                            blank=True, null=True)

    # Preservation references
    preservation_references = models.CharField(max_length=255, blank=True)
    preservation_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Price (Char)
    price = models.CharField(max_length=255, blank=True)
    price_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True, null=True)

    # Printed originally
    printed_originally = models.IntegerField(blank=True, null=True)

    # Printers (Int)
    printers = models.IntegerField(blank=True, null=True)

    # Printers notes
    printers_notes = models.CharField(max_length=255, blank=True)
    printers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                             null=True)

    # Printing press notes
    printing_press_notes = models.CharField(max_length=255, blank=True)
    printing_press_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                   null=True)

    # Printing press references
    printing_press_references = models.CharField(max_length=255, blank=True)
    printing_press_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Production evidence
    production_evidence = models.CharField(max_length=255, blank=True)
    production_evidence_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Proofreaders
    proofreaders = models.IntegerField(blank=True, null=True)

    # Proofreaders notes
    proofreaders_notes = models.CharField(max_length=255, blank=True)
    proofreaders_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Publication place
    # TODO: link to the tid of the publication place
    publication_place = models.IntegerField(blank=True, null=True)

    # Publication place other
    # TODO: link to the tid of the publication place
    publication_place_other = models.IntegerField(blank=True, null=True)

    # Year in book
    year_in_book = models.CharField(max_length=255, blank=True)
    year_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Year in other
    year_in_other = models.CharField(max_length=255, blank=True)

    # Publisher name
    # TODO: link to the tid of the publisher
    publisher_name = models.IntegerField(blank=True, null=True)

    # Rabbinical approbation notes
    rabbinical_approbation_notes = models.CharField(max_length=255, blank=True)
    rabbinical_approbation_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                           blank=True, null=True)

    # Rabbinical approbations
    rabbinical_approbations = models.IntegerField(blank=True, null=True)

    # Recommendations
    recommendations = models.IntegerField(blank=True, null=True)

    # Recommendations notes
    recommendations_notes = models.CharField(max_length=255, blank=True)
    recommendations_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # References for editions
    references_for_editions = models.CharField(max_length=255, blank=True)
    references_for_editions_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # References notes
    references_notes = models.CharField(max_length=255, blank=True)
    references_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                               null=True)

    # Secondary sources
    secondary_sources = models.CharField(max_length=255, blank=True)
    secondary_sources_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Secondary textual models
    # TODO: link to the tid of the secondary textual models
    secondary_textual_models = models.IntegerField(blank=True, null=True)

    # Sellers
    sellers = models.IntegerField(blank=True, null=True)

    # Sellers notes
    sellers_notes = models.CharField(max_length=255, blank=True)
    sellers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                            null=True)

    # Series part
    series_part = models.IntegerField(blank=True, null=True)

    # Sources exist  (Int)
    sources_exist = models.IntegerField(blank=True, null=True)

    # Sources list
    sources_list = models.CharField(max_length=255, blank=True)
    sources_list_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Sources not mentioned (Int)
    sources_not_mentioned = models.IntegerField(blank=True, null=True)

    # Sources not mentioned list
    sources_not_mentioned_list = models.CharField(max_length=255, blank=True)
    sources_not_mentioned_list_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                         blank=True, null=True)

    # Sources not mentioned ref
    sources_not_mentioned_ref = models.CharField(max_length=255, blank=True)
    sources_not_mentioned_ref_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Sources references
    sources_references = models.CharField(max_length=255, blank=True)
    sources_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                 null=True)

    # Structure preface notes
    structure_preface_notes = models.CharField(max_length=255, blank=True)
    structure_preface_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                      blank=True, null=True)

    # Subscribers
    subscribers = models.IntegerField(blank=True, null=True)

    # Subscribers notes
    subscribers_notes = models.CharField(max_length=255, blank=True)
    subscribers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Subscription appeal (Int)
    subscription_appeal = models.IntegerField(blank=True, null=True)

    # Subscription appeal notes
    subscription_appeal_notes = models.CharField(max_length=255, blank=True)
    subscription_appeal_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Table of content (Int)
    table_of_content = models.IntegerField(blank=True, null=True)

    # Target audience
    # TODO: link to the tid of the target audience
    target_audience = models.IntegerField(blank=True, null=True)

    # Target audience notes
    target_audience_notes = models.CharField(max_length=255, blank=True)
    target_audience_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                    null=True)

    # Tel Aviv Library ID
    tel_aviv_library_id = models.CharField(max_length=255, blank=True)
    tel_aviv_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Textual model notes
    textual_model_notes = models.CharField(max_length=255, blank=True)
    textual_model_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                  null=True)

    # Thanks (Int)
    thanks = models.IntegerField(blank=True, null=True)

    # Thanks notes
    thanks_notes = models.CharField(max_length=255, blank=True)
    thanks_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Title in Latin characters
    title_in_latin_characters = models.CharField(max_length=255, blank=True)
    title_in_latin_characters_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                        blank=True, null=True)

    # Topic
    # TODO: link to the tid of the topic
    topic = models.IntegerField(blank=True, null=True)

    # Topics notes
    topics_notes = models.CharField(max_length=255, blank=True)
    topics_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                           null=True)

    # Total number of editions
    total_number_of_editions = models.CharField(max_length=255, blank=True)
    total_number_of_editions_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Translation notes
    translation_notes = models.CharField(max_length=255, blank=True)
    translation_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                                null=True)

    # Translation type
    # links to translation type
    translation_type = models.IntegerField(blank=True, null=True)

    # Typography
    # TODO: link to the tid of the typography
    typography = models.IntegerField(blank=True, null=True)

    # Volumes notes
    volumes_notes = models.CharField(max_length=255, blank=True)
    volumes_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL', blank=True,
                                            null=True)

    # Volumes published number
    volumes_published_number = models.CharField(max_length=255, blank=True)
    volumes_published_number_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL',
                                                       blank=True, null=True)

    # Methods
    def __str__(self):
        return self.name

    def get_revision(self):
        # How do the revisions work?
        # id -> revision_id
        # revision contain the old data (can be skipped)
        pass

    def load_myself(self):
        pass

    def fetch_from_rdf(self):
        pass

    def dump_to_rdf(self):
        try:

            return True
        except Exception as e:
            print(e)
            return None


class HomePage(Page):
    """
    Model for the home page.
    The content is added in the wagtail dashboard.
    """

    # Database fields
    body = RichTextField(blank=True)

    # TODO add the tag cloud dynamically

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


class AboutPage(Page):
    """
    About page.
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
    subpage_types = []


class ContactFormField(AbstractFormField):
    """
    Form field for the contact form.
    """

    page = ParentalKey('ContactPage', on_delete=models.CASCADE, related_name='form_fields')


class ContactPage(AbstractEmailForm):
    """
    Page for the contact form.
    """
    # TODO: add the contact form

    body = RichTextField(blank=True)
    thank_you_text = RichTextField(blank=True)

    # Search index configuration
    search_fields = Page.search_fields + [
        index.SearchField('title'),
        index.SearchField('body'),
    ]

    # Editor panels configuration

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

    #promote_panels = [
    #    MultiFieldPanel(Page.promote_panels, "Common page configuration"),
    #]

    # Parent page / subpage type rules
    # parent_page_types = ['HomePage']
    #subpage_types = []


class ImprintPage(Page):
    """
    Page for the imprint.
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
    subpage_types = []


class DocumentationsPage(Page):
    """
    Page for the documentations.
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
    subpage_types = []


class PrivacyPolicyPage(Page):
    """
    Page for the privacy policy.
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
    subpage_types = []


class TermsAndConditionsPage(Page):
    """
    Page for the terms and conditions.
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
    subpage_types = []


class BookDetailPage(Page):
    """
    Page for the detail of a book.
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
    parent_page_types = ['BooksPage']
    subpage_types = []

    template = "home/book_detail_page.html"

    # Render method for the detail page
    def serve(self, request):
        # Get context and render the page with the book details
        context = self.get_context(request)
        return self.render(request, context)

    def get_context(self, request):
        print("BookDetailPage", request)
        # Fetch the detail of a book from the model.
        context = super().get_context(request)
        context['book'] = Book.objects.get(id=self.id)  # TODO: get the book by id from the url parameter
        return context

    def save(self, *args, **kwargs):
        # Automatically generate a slug based on the book title
        if not self.slug:
            self.slug = slugify(self.book_title)
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

    # get all the books
    books = Book.objects.all()
    print(books)
    print(sort_and_group_by_name(books))

    context = {
        'books': sort_and_group_by_name(books),
    }

    def get_context(self, request):
        # Fetch a list of all the books from the model.
        context = super().get_context(request)
        context['books'] = Book.objects.all()
        return context




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
        books_with_urls = Book.objects.filter(digital_book_url__isnull=False).exclude(digital_book_url='').filter(digital_book_url__regex=r'^https?://').all()

        context = {
            'books': sort_and_group_by_name(books_with_urls),
        }

        print("Context:", context)
        return context


class DigitalBookDetailPage(Page):
    """
    Page for the detail of a digital book.
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
    parent_page_types = ['DigitalBooksPage']
    subpage_types = []

    def get_context(self, request):
        # Fetch the detail of a digital book from the model.
        context = super().get_context(request)
        context['digital_book'] = Book.objects.get(id=self.id)
        return context


class PlacesPage(Page):
    def group_names_by_first_letter(names):
        grouped_names = defaultdict(list)

        for name in names:
            first_letter = name[0].upper()
            grouped_names[first_letter].append(name)

        return dict(grouped_names)

    body = RichTextField(blank=True)
    nonce = secrets.token_hex(16)

    # For testing
    # Todo: Get the cities
    # cities = City.objects.all()
    # print(cities)
    cities_list = ["Amsterdam", "Hamburg", "Berlin", "Frankfurt", "Munich", "Vienna", "Prague", "Budapest",
                   "Bratislava"]
    cities_array = group_names_by_first_letter(cities_list)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    alphabet = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    hebrew_alphabet = list('אבגדהוזחטיכלמנסעפצקרשת')
    context = {
        'alphabet': alphabet,
        'hebrew_alphabet': hebrew_alphabet,
        'nonce': nonce,
        'cities': cities_array,
    }

    template = "home/places_page.html"


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


class CityDetailPage(Page):
    """
    Page for the detail of a city.
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
    parent_page_types = ['CitiesPage']
    subpage_types = []

    def get_context(self, request):
        # Fetch the detail of a city from the model.
        context = super().get_context(request)
        context['city'] = City.objects.get(id=self.id)
        return context


class PersonsPage(Page):
    """
    Page for the persons overview.
    """
    # add the people names to the page

    # TODO: refactor this. The result should be a list of names from the function.
    """
    people = get_people_names(None)
    # print("People: ", people)
    people_names = []

    if people is not None:
        for result in people["results"]["bindings"]:
            people_names.append(result["name"]["value"])
    else:
        people_names.append("No people found")
    """
    # print(people_names)

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
        context['persons'] = Person.objects.all()

        # context['people'] = get_people_names(None) # see above

        return context


class PersonDetailPage(Page):
    """
    Model for the person detail page.
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
    parent_page_types = ['PersonsPage']
    subpage_types = []

    def get_context(self, request):
        # Fetch the detail of a person from the model.
        context = super().get_context(request)
        context['person'] = Person.objects.get(id=self.id)
        return context

    def __str__(self):
        return self.title


# TODO: remove when not needed anymore
# @register_snippet
class MyCustomModel(models.Model):
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField()

    panels = [
        FieldPanel('description'),
    ]

    def __str__(self):
        return self.title


class MyCustomPage(Page):
    # You can add any fields that relate to the page itself here
    introduction = models.CharField(max_length=255, blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('introduction'),
    ]

    def get_context(self, request):
        # Update context to include snippet data
        context = super().get_context(request)
        context['my_custom_data'] = MyCustomModel.objects.all()
        return context
