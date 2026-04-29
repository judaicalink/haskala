# home/sitemaps.py
from django.contrib.sitemaps import Sitemap
from django.urls import reverse
from django.utils.text import slugify

from .models import Book, Person, City, HomePage, ContactPage, StaticPage

from wagtail.models import Page


class StaticViewSitemap(Sitemap):
    """
    Statically routed views without a model relation
    (only URL names defined in urls.py).
    """
    changefreq = "weekly"
    priority = 0.7

    def items(self):
        # these names come from your urls.py
        return [
            "index",
            "books-list",
            "digital-books-list",
            "persons-list",
            "places-list",
            "search",
        ]

    def location(self, item):
        return reverse(item)


class BookSitemap(Sitemap):
    """
    All book detail pages (/books/<title>/)
    """
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Book.objects.all()

    def lastmod(self, obj):
        # created_at / updated_at are available on the Book model
        return obj.updated_at

    def location(self, obj):
        # URL pattern: path('books/<title>/', book_detail_view, name='book-detail')
        # -> <title> corresponds to Book.name
        return reverse("book-detail", kwargs={"title": obj.name})


class PersonSitemap(Sitemap):
    """
    All person detail pages (/persons/<uuid>/)
    """
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return Person.objects.all()

    def location(self, obj):
        # URL pattern: path("persons/<uuid:person_uuid>/", ..., name="person-detail")
        return reverse("person-detail", kwargs={"person_uuid": obj.pk})


class PlaceSitemap(Sitemap):
    """
    All place/city detail pages (/places/<slug>/)
    Slug is generated from City.name via slugify - same as in _get_place_by_slug().
    """
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return City.objects.all()

    def location(self, obj):
        slug = slugify(obj.name)
        # URL pattern: path("places/<slug:city_slug>/", ..., name="place-detail")
        return reverse("place-detail", kwargs={"city_slug": slug})


class WagtailPageSitemap(Sitemap):
    """
    All live + public Wagtail pages (Home, About, Contact, Imprint, ...).
    For finer control, individual page types can also be used.
    """
    changefreq = "monthly"
    priority = 0.5

    def items(self):
        # only specific page types (HomePage, AboutPage, ...)
        return Page.objects.type(
            HomePage,
            ContactPage,
            StaticPage
        ).live().public()

    def lastmod(self, obj):
        return obj.last_published_at

    def location(self, obj):
        # wagtail Page has .url
        return obj.url
