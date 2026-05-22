from django.test import TestCase, Client, override_settings
from django.urls import reverse

from home.models import Book, Person, City, Publisher


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class BookDetailViewSmokeTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            name="Test Book",
            full_title="Test Book: A Subtitle",
            gregorian_year="1797",
        )

    def test_returns_200_for_existing_book(self):
        resp = Client().get(reverse("book-detail", args=[self.book.name]))
        self.assertEqual(resp.status_code, 200)

    def test_404_for_unknown_book(self):
        resp = Client().get(reverse("book-detail", args=["nonexistent-book"]))
        self.assertEqual(resp.status_code, 404)


@override_settings(
    STATICFILES_STORAGE="django.contrib.staticfiles.storage.StaticFilesStorage"
)
class BookCiteBibtexTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publisher = Publisher.objects.create(name="Sample Verlag")
        cls.city = City.objects.create(name="Berlin")
        cls.book = Book.objects.create(
            name="Cited Book",
            full_title="Cited Book: With Subtitle",
            gregorian_year="1797",
            publisher=cls.publisher,
            publication_place=cls.city,
        )

    def test_bibtex_endpoint_returns_bibtex(self):
        resp = Client().get(reverse("book-cite-bibtex", args=[self.book.name]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/x-bibtex", resp["Content-Type"])
        body = resp.content.decode()
        self.assertIn("@book{", body)
        self.assertIn("title", body)
        self.assertIn("Cited Book", body)
        self.assertIn("1797", body)
        self.assertIn("Sample Verlag", body)
        self.assertIn("Berlin", body)

    def test_bibtex_escapes_special_chars(self):
        nasty = Book.objects.create(
            name="Nasty Book",
            full_title="A {weird} title with } a brace",
            gregorian_year="1800",
        )
        resp = Client().get(reverse("book-cite-bibtex", args=[nasty.name]))
        body = resp.content.decode()
        # The brace in the title must be escaped, not leak through as raw.
        self.assertNotIn("title with } a brace", body)  # raw form must not appear
        self.assertIn("title with \\} a brace", body)   # escaped form must appear
