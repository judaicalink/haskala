from django.test import TestCase, Client, override_settings
from django.urls import reverse

from home.models import Book, BookAuthor, City, Person, Publisher


# Tests that hit views rendered through base.html need a non-manifest static
# files storage; tests that hit cached views need a dummy cache so a stale
# Redis entry from a prior run does not bleed in.
TEST_OVERRIDES = override_settings(
    STATICFILES_STORAGE=(
        "django.contrib.staticfiles.storage.StaticFilesStorage"
    ),
    CACHES={
        "default": {
            "BACKEND": "django.core.cache.backends.dummy.DummyCache",
        },
    },
)


@TEST_OVERRIDES
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


@TEST_OVERRIDES
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

    def test_bibtex_has_no_template_comment_leak(self):
        resp = Client().get(reverse("book-cite-bibtex", args=[self.book.name]))
        body = resp.content.decode()
        # Encoding explanation must be stripped by Django's template engine.
        self.assertNotIn("plain-text BibTeX", body)
        self.assertNotIn("Django template delimiters", body)
        # The output must start with the @book header (after optional
        # whitespace.
        self.assertTrue(
            body.lstrip().startswith("@book{"),
            f"BibTeX output should start with @book{{; got: {body[:80]!r}",
        )

    def test_bibtex_escapes_special_chars(self):
        nasty = Book.objects.create(
            name="Nasty Book",
            full_title="A {weird} title with } a brace",
            gregorian_year="1800",
        )
        resp = Client().get(reverse("book-cite-bibtex", args=[nasty.name]))
        body = resp.content.decode()
        # The brace in the title must be escaped, not leak through as raw.
        # Raw form must not appear; escaped form must.
        self.assertNotIn("title with } a brace", body)
        self.assertIn("title with \\} a brace", body)


@TEST_OVERRIDES
class BookCiteRisTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            name="Risky Book",
            full_title="Risky Book: A Subtitle",
            gregorian_year="1797",
        )

    def test_ris_endpoint_returns_ris(self):
        resp = Client().get(reverse("book-cite-ris", args=[self.book.name]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn(
            "application/x-research-info-systems", resp["Content-Type"]
        )
        body = resp.content.decode()
        self.assertIn("TY  - BOOK", body)
        self.assertIn("TI  - Risky Book", body)
        self.assertIn("PY  - 1797", body)
        self.assertTrue(body.rstrip().endswith("ER  -"))


@TEST_OVERRIDES
class BookCiteModalTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publisher = Publisher.objects.create(name="Modal Verlag")
        cls.city = City.objects.create(name="Frankfurt")
        cls.book = Book.objects.create(
            name="Modal Book",
            full_title="Modal Book: With Subtitle",
            gregorian_year="1799",
            publisher=cls.publisher,
            publication_place=cls.city,
        )

    def test_detail_page_includes_cite_modal_with_plain_citation(self):
        resp = Client().get(reverse("book-detail", args=[self.book.name]))
        self.assertEqual(resp.status_code, 200)
        html = resp.content.decode()
        self.assertIn("book-cite-modal", html)
        self.assertIn("Modal Book", html)
        self.assertIn("1799", html)
        self.assertIn("Modal Verlag", html)
        self.assertIn("Frankfurt", html)


@TEST_OVERRIDES
class BookHeaderTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.person = Person.objects.create(pref_label="Pemberton, Dr.")
        cls.publisher = Publisher.objects.create(name="Header Verlag")
        cls.city = City.objects.create(name="Leipzig")
        cls.book = Book.objects.create(
            name="Header Book",
            full_title="Header Book: A Subtitle",
            title_in_latin_characters="Sefer Test",
            gregorian_year="1800",
            publisher=cls.publisher,
            publication_place=cls.city,
        )
        BookAuthor.objects.create(
            book=cls.book, person=cls.person, role="original_text_author",
        )

    def test_header_shows_title_subtitle_author_pub_line(self):
        html = Client().get(
            reverse("book-detail", args=[self.book.name])
        ).content.decode()
        self.assertIn("Header Book: A Subtitle", html)
        self.assertIn("Sefer Test", html)
        self.assertIn("Pemberton, Dr.", html)
        self.assertIn("Leipzig", html)
        self.assertIn("Header Verlag", html)
        self.assertIn("1800", html)
        # Person chip links to the person detail
        self.assertIn(f"/persons/{self.person.uuid}/", html)


@TEST_OVERRIDES
class BookTOCTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publisher = Publisher.objects.create(name="TOC Verlag")
        cls.city = City.objects.create(name="Vienna")
        cls.book = Book.objects.create(
            name="TOC Book",
            full_title="TOC Book",
            gregorian_year="1810",
            publisher=cls.publisher,
            publication_place=cls.city,
        )

    def test_toc_lists_visible_sections_only(self):
        html = Client().get(
            reverse("book-detail", args=[self.book.name])
        ).content.decode()
        # Publication has data -> appears in TOC and as a section anchor.
        self.assertIn('href="#publication"', html)
        self.assertIn('id="publication"', html)
        # Censorship has no data -> must not appear at all.
        self.assertNotIn('href="#censorship"', html)
        self.assertNotIn('id="censorship"', html)
