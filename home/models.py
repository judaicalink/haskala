from django.db import models
from SPARQLWrapper import SPARQLWrapper, JSON

from wagtail.models import Page
from wagtail.fields import RichTextField
from wagtail.admin.panels import FieldPanel



def get_people_names(self):
    # make a request to the rdf file
    sparql = SPARQLWrapper("http://localhost:3030/haskala/sparql")
    #write the query which selects all instances of the class Person per name
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
    #print(results)
    return results


class HomePage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class PeoplePage(Page):
    body = RichTextField(blank=True)
    # add the people names to the page
    people = get_people_names(None)
    people_names = []
    for result in people["results"]["bindings"]:
        people_names.append(result["name"]["value"])

    print(people_names)
    body = RichTextField(default=people_names)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


class PersonPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


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


class PlacesPage(Page):
    body = RichTextField(blank=True)

    content_panels = Page.content_panels + [
        FieldPanel('body'),
    ]


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

    def __int__(self, name, pref_label):
        self.name = name
        self.pref_label = pref_label

    # name = models.CharField(max_length=100)
    # pref_label = models.CharField(max_length=100)
    gender = models.CharField(max_length=100)
    occupation = models.CharField(max_length=100)
    german_name = models.CharField(max_length=100)
    hebrew_name = models.CharField(max_length=100)
    VIAF_ID = models.CharField(max_length=100)
    same_as = models.CharField(max_length=100)

    def __str__(self):
        return self.name


class People(models.Model):
    people = get_people_names(None)
    people_names = []
    for result in people["results"]["bindings"]:
        people_names.append(result["name"]["value"])

    def __str__(self):
        return self.people_names