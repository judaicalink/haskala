import secrets

import uuid as uuid
from django.db import models
from SPARQLWrapper import SPARQLWrapper, JSON
from collections import defaultdict

from modelcluster.fields import ParentalKey
from wagtail.admin.forms.models import WagtailAdminModelForm
from wagtail.contrib.forms.models import AbstractFormField, AbstractForm

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel, InlinePanel


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


class HomePage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class PeoplePage(Page):
    body = RichTextField(blank=True)
    # add the people names to the page
    people = get_people_names(None)
    # print("People: ", people)
    people_names = []

    if people is not None:
        for result in people["results"]["bindings"]:
            people_names.append(result["name"]["value"])
    else:
        people_names.append("No people found")

    # print(people_names)
    body = RichTextField(default=people_names)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]

    template = "home/people_page.html"


class PersonPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class Language(models.Model):
    """
    Model for the languages
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True)
    language_code = models.CharField(max_length=255, unique=True)

    class Meta:
        verbose_name_plural = "Languages"

    def __str__(self):
        return self.name


class Edition(models.Model):
    """
    Model for the editions
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255, unique=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Belongs to book

    # Edition changes, nut the usual created and updated at
    changes = models.CharField(max_length=255)
    changes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Edition city
    # TODO: link to the city
    city = models.IntegerField()  # links to tid of the city

    # Edition references
    references = models.CharField(max_length=255)
    references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Edition year
    year = models.CharField(max_length=255)
    year_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')


    class Meta:
        verbose_name_plural = "Editions"

    def __str__(self):
        return self.name


class Translation(models.Model):
    """
    Model for the Translations
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book

    # Language
    # TODO: add multiple languages
    language = models.CharField(max_length=255)  # Can have multiple languages over delta


class Mention(models.Model):
    """
    Model for Mentions
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book

    # Mentionee
    # TODO: link to the id of the person
    mentionee = models.IntegerField()  # links to tid of the person

    # Mentionee city
    # TODO: link to the id of the city
    mentionee_city = models.IntegerField()  # links to tid of the city

    # Mentionee description
    # TODO: link to the id of the description
    mentionee_description = models.IntegerField # links to tid of the description


class Preface(models.Model):
    """
    Model for the Prefaces
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    # Belongs to book


class Production(models.Model):
    """
    Model for the Production
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    title = models.CharField(max_length=255)
    # Belongs to book


class Book(models.Model):
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, default=1)

    bundle = models.CharField(max_length=255, choices=BUNDLE_CHOICES)

    # entity_id = models.CharField(max_length=255)
    # revision_id = models.CharField(max_length=255)

    language = models.CharField(max_length=255)
    # field_book_target_id = models.CharField(max_length=255)

    # Alignment
    alignment = models.CharField(max_length=255)  # tid

    # Availability
    availability_notes = models.CharField(max_length=255)
    availability_notes_format = models.CharField(max_length=255)
    not_available = models.BooleanField()

    # Notes
    structure_notes = models.CharField(max_length=255)
    structure_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Studies
    studies = models.CharField(max_length=255)
    studies_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Type general
    type_general_notes = models.CharField(max_length=255)
    type_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Bans
    bans = models.CharField(max_length=255)
    bans_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Bar Ilan Library ID
    bar_ilan_library_id = models.CharField(max_length=255)
    bar_ilan_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Berlin Library ID
    berlin_library_id = models.CharField(max_length=255)
    bar_ilan_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Bibliographical citations
    bibliographical_citations = models.CharField(max_length=255)
    bibliographical_citations_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # British Library ID
    british_library_id = models.CharField(max_length=255)
    british_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Catalog numbers
    catalog_numbers_notes = models.CharField(max_length=255)
    catalog_numbers_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Censorship
    censorship = models.CharField(max_length=255)
    censorship_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Contacts official agents
    contacts_official_agents = models.CharField(max_length=255)
    contacts_official_agents_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Contacts other people
    contacts_other_people = models.CharField(max_length=255)
    contacts_other_people_format = models.CharField(max_length=255, choices=FORMAT_CHOICES)

    # Contemporary disputes
    contemporary_disputes = models.CharField(max_length=255)
    contemporary_disputes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Contemporary references
    contemporary_references = models.CharField(max_length=255)
    contemporary_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Contents table notes
    contents_table_notes = models.CharField(max_length=255)
    contents_table_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Contradict new edition
    contradict_new_edition = models.IntegerField(default=1)

    # Contradict original
    contradict_original = models.IntegerField(default=1)

    # Copy of book used
    copy_of_book_used = models.CharField(max_length=255)
    copy_of_book_used_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Dedications
    dedications = models.CharField(max_length=255)

    # Dedications notes
    dedications_notes = models.CharField(max_length=255)
    dedications_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Diagrams book pages
    diagrams_book_pages = models.CharField(max_length=255)
    diagrams_book_pages_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Diagrams notes
    diagrams_notes = models.CharField(max_length=255)
    diagrams_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Editions notes
    editions_notes = models.CharField(max_length=255)
    editions_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Epilogue
    epilogue = models.IntegerField(default=0)

    # Epilogue notes
    epilogue_notes = models.CharField(max_length=255)
    epilogue_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Examined volume number
    examined_volume_number = models.IntegerField(default=1)

    # Expanded in edition
    expanded_in_edition = models.IntegerField(default=1)

    # Expanded in translation
    expanded_in_translation = models.IntegerField(default=1)

    # Fonts
    # TODO: link to tid of the fonts
    fonts = models.IntegerField()

    # Format of publication date
    # TODO: link to tid of the format of publication date
    format_of_publication_date = models.IntegerField()

    # Founders notes
    founders_notes = models.CharField(max_length=255)
    founders_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Frankfurt Library ID
    frankfurt_library_id = models.CharField(max_length=255)
    frankfurt_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Full title
    full_title = models.CharField(max_length=255)
    full_title_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Founders
    founders = models.IntegerField(default=0)

    # Gregorian year
    gregorian_year = models.IntegerField(default=0)

    # Gregorian year pub other
    gregorian_year_pub_other = models.CharField(max_length=255)
    gregorian_year_pub_other_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Hebrew year publication other
    hebrew_year_pub_other = models.CharField(max_length=255)
    hebrew_year_pub_other_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Hebrew year of publication
    hebrew_year_of_publication = models.CharField(max_length=255)
    hebrew_year_of_publication_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Height
    height = models.CharField(max_length=255)
    height_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # HUJI library ID
    huji_library_id = models.CharField(max_length=255)
    huji_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Illustrations diagrams
    illustrations_diagrams = models.IntegerField(default=0)

    # Jewish sources quotes
    jewish_sources_quotes = models.CharField(max_length=255)
    jewish_sources_quotes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Language
    # TODO: add multiple languages
    language = models.IntegerField() # Can have multiple languages over delta

    # Languages of footnotes
    # TODO: add multiple languages
    languages_of_footnotes = models.IntegerField() # Can have multiple languages over delta

    # Languages number
    languages_number = models.IntegerField() # Can have multiple languages over delta

    # Last known edition
    last_known_edition = models.CharField(max_length=255)
    last_known_edition_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Later references
    later_references = models.CharField(max_length=255)
    later_references_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Link to digital book
    digital_book_url = models.CharField(max_length=255)
    digital_book_url_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Location of footnotes
    # TODO: link to the tid
    location_of_footnotes = models.IntegerField() # links to tid

    # Main textual models
    # TODO: link to the tid
    main_textual_models = models.IntegerField() # links to tid

    # Mention general notes
    mention_general_notes = models.CharField(max_length=255)
    mention_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Mentions in reviews
    mentions_in_reviews = models.CharField(max_length=255)
    mentions_in_reviews_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Motto
    motto = models.CharField(max_length=255)
    motto_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Name in book
    name_in_book = models.CharField(max_length=255)
    name_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Name of series
    # TODO: link to the tid
    name_of_series = models.IntegerField() # links to tid

    # New edition general notes
    new_edition_general_notes = models.CharField(max_length=255)
    new_edition_general_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # New edition type else note
    new_edition_type_else_note = models.CharField(max_length=255)
    new_edition_type_else_note_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # New edition type else ref
    new_edition_type_else_ref = models.CharField(max_length=255)
    new_edition_type_else_ref_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # New edition type elsewhere
    new_edition_type_elsewhere = models.CharField(max_length=255)
    new_edition_type_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # New edition type in text
    new_edition_type_in_text = models.CharField(max_length=255)
    new_edition_type_in_text_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # New edition type notes
    new_edition_type_notes = models.CharField(max_length=255)
    new_edition_type_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # New edition type reference
    new_edition_type_reference = models.CharField(max_length=255)
    new_edition_type_reference_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # New York Library ID
    new_york_library_id = models.CharField(max_length=255)
    new_york_library_id_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Non jewish sources quotes
    non_jewish_sources_quotes = models.CharField(max_length=255)
    non_jewish_sources_quotes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Occasional words languages
    # TODO: link to the tid
    occasional_words_languages = models.IntegerField()

    # Old author addition names
    old_author_addition_names = models.CharField(max_length=255)
    old_author_addition_names_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Old author names other sor
    # Was empty
    old_author_names_other_sor = models.CharField(max_length=255)
    old_author_names_other_sor_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Old name in book
    old_name_in_book = models.CharField(max_length=255)
    old_name_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Old text
    old_text = models.CharField(max_length=255)
    old_text_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Old text author
    # TODO: link to the tid of author
    old_text_author = models.IntegerField()

    # Old text author in book
    old_text_author_in_book = models.CharField(max_length=255)
    old_text_author_in_book_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original author
    original_author = models.CharField(max_length=255)
    original_author_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original author else refer
    original_author_else_refer = models.CharField(max_length=255)
    original_author_else_refer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Original author elsewhere
    original_author_elsewhere = models.CharField(max_length=255)
    original_author_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original author other name
    original_author_other_name = models.CharField(max_length=255)
    original_author_other_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original language
    # TODO: link to the tid of the original language
    original_language = models.IntegerField()

    # Original publication year
    original_publication_year = models.CharField(max_length=255)
    original_publication_year_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original Publisher
    # TODO: link to the tid of the original publisher
    original_publisher = models.IntegerField()

    # Original sources mention
    original_sources_mention = models.CharField(max_length=255)
    original_sources_mention_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Original text author
    # TODO: link to the tid of the original text author
    original_text_author = models.IntegerField()

    # Original text name
    original_text_name = models.CharField(max_length=255)
    original_text_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original title
    original_title = models.CharField(max_length=255)
    original_title_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original title else refer
    original_title_else_refer = models.CharField(max_length=255)
    original_title_else_refer_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Original title elsewhere
    original_title_elsewhere = models.CharField(max_length=255)
    original_title_elsewhere_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Original type
    # TODO: link to the tid of the original type
    original_type = models.IntegerField()

    # Other books names
    other_books_names = models.CharField(max_length=255)
    other_books_names_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Other libraries
    other_libraries = models.CharField(max_length=255)
    other_libraries_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Other volumes
    other_volumes = models.CharField(max_length=255)
    other_volumes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Pages number
    pages_number = models.CharField(max_length=255)
    pages_number_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Partial publication
    partial_publication = models.CharField
    partial_publication_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Person name appear
    person_name_appear = models.IntegerField() # does not link to a person

    # Personal address
    personal_address = models.IntegerField()

    # Personal address notes
    personal_address_notes = models.CharField(max_length=255)
    personal_address_notes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Planned volumes
    planned_volumes = models.CharField(max_length=255)
    planned_volumes_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='filtered_html')

    # Preface


    # Preface notes



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


class BooksPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class BookPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class DigitalBooksPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class City(models.Model):
    """
    Model for the cities
    """
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255, unique=True),
    geolocation_lat = models.FloatField(max_length=255, blank=True, null=True),
    geolocation_lng = models.FloatField(max_length=255, blank=True, null=True),
    geolocation_lat_sin = models.FloatField(max_length=255, blank=True, null=True),
    geolocation_lat_cos = models.FloatField(max_length=255, blank=True, null=True),
    geolocation_lng_rad = models.FloatField(max_length=255, blank=True, null=True),

    class Meta:
        verbose_name_plural = "Cities"

    def __str__(self):
        return self.name


"""
class CityForm(WagtailAdminModelForm):
    class Meta:
        model = City
        fields = '__all__'

"""
"""
class FormField(AbstractFormField):
    page = ParentalKey('FormPage', on_delete=models.CASCADE, related_name='form_fields')


class CityFormPage(AbstractForm):
    intro = RichTextField(blank=True)

    content_panels = AbstractForm.content_panels + [
        FieldPanel('intro'),
        InlinePanel('form_fields', label="Form fields"),

    ]
"""


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
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class AboutPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class ContactPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class Person(models.Model):
    """
    Model for the person.
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # FIXME: duplicated

    def __int__(self, name, pref_label):
        self.name = name
        self.pref_label = pref_label

    # name = models.CharField(max_length=255)
    # pref_label = models.CharField(max_length=255)
    gender = models.CharField(max_length=255)

    # German name
    german_name = models.CharField(max_length=255)
    german_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Hebrew name
    hebrew_name = models.CharField(max_length=255)
    hebrew_name_format = models.CharField(max_length=255, choices=FORMAT_CHOICES, default='NULL')

    # Occupation
    # TODO: link to the tid of the occupation, can have multiple occupations
    occupation = models.IntegerField()  # links to tid of the occupation

    # VIAF ID
    VIAF_ID = models.CharField(max_length=255)

    # Same as
    same_as = models.CharField(max_length=255)

    # Date of birth
    date_of_birth = models.CharField(max_length=255)

    # Date of death
    date_of_death = models.CharField(max_length=255)

    # Place of birth
    # TODO: link to the tid of the place of birth, links to city
    place_of_birth = models.IntegerField()

    # Place of death
    place_of_death = models.IntegerField()

    def __str__(self):
        return self.name


class People(models.Model):
    """
    Model for the people.
    """
    id = models.AutoField(primary_key=True)
    people = get_people_names(None)
    people_names = []

    if people is not None:
        for result in people["results"]["bindings"]:
            people_names.append(result["name"]["value"])

    else:
        people_names.append("No people found")

    def __str__(self):
        return self.people_names
