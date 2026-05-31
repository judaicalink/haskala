from django.test import TestCase, Client, override_settings
from django.urls import reverse

from home.models import Book, BookAuthor, City, Language, Person, Publisher


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
class BookCiteBibtexMultiAuthorTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first = Person.objects.create(pref_label="Mendelssohn, Moses")
        cls.second = Person.objects.create(pref_label="Maimon, Salomon")
        cls.book = Book.objects.create(
            name="Two Author Book",
            full_title="Two Author Book",
            gregorian_year="1789",
        )
        BookAuthor.objects.create(
            book=cls.book, person=cls.first, role="original_text_author",
        )
        BookAuthor.objects.create(
            book=cls.book, person=cls.second, role="old_text_author",
        )

    def test_bibtex_joins_multiple_authors_with_and(self):
        resp = Client().get(reverse("book-cite-bibtex", args=[self.book.name]))
        body = resp.content.decode()
        self.assertIn("Mendelssohn, Moses and Maimon, Salomon", body)


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
class BookCiteRisMultiAuthorLanguageTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.first = Person.objects.create(pref_label="Mendelssohn, Moses")
        cls.second = Person.objects.create(pref_label="Maimon, Salomon")
        cls.hebrew = Language.objects.create(name="Hebrew")
        cls.german = Language.objects.create(name="German")
        cls.book = Book.objects.create(
            name="RIS Multi Book",
            full_title="RIS Multi Book",
            gregorian_year="1789",
        )
        BookAuthor.objects.create(
            book=cls.book, person=cls.first, role="original_text_author",
        )
        BookAuthor.objects.create(
            book=cls.book, person=cls.second, role="old_text_author",
        )
        cls.book.languages.add(cls.hebrew, cls.german)

    def test_ris_emits_one_au_line_per_author(self):
        resp = Client().get(reverse("book-cite-ris", args=[self.book.name]))
        body = resp.content.decode()
        au_lines = [ln for ln in body.splitlines() if ln.startswith("AU  - ")]
        self.assertEqual(len(au_lines), 2)
        self.assertIn("AU  - Mendelssohn, Moses", au_lines)
        self.assertIn("AU  - Maimon, Salomon", au_lines)

    def test_ris_emits_one_la_line_per_language(self):
        resp = Client().get(reverse("book-cite-ris", args=[self.book.name]))
        body = resp.content.decode()
        la_lines = [ln for ln in body.splitlines() if ln.startswith("LA  - ")]
        self.assertEqual(len(la_lines), 2)
        self.assertIn("LA  - Hebrew", la_lines)
        self.assertIn("LA  - German", la_lines)


@TEST_OVERRIDES
class BookCiteRisNewlineSafetyTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        # An author whose pref_label happens to contain a newline must
        # not be allowed to split the AU line into two lines that RIS
        # readers would then misinterpret.
        cls.person = Person.objects.create(
            pref_label="Smith,\nJohn",
        )
        cls.publisher = Publisher.objects.create(name="Multi\rLine\nVerlag")
        cls.book = Book.objects.create(
            name="Newline Book",
            full_title="Title\nWith\nNewlines",
            gregorian_year="1800",
            publisher=cls.publisher,
        )
        BookAuthor.objects.create(
            book=cls.book, person=cls.person, role="original_text_author",
        )

    def test_ris_keeps_one_tag_per_line(self):
        resp = Client().get(reverse("book-cite-ris", args=[self.book.name]))
        body = resp.content.decode()
        for line in body.splitlines():
            if line and not line.startswith(("TY", "TI", "AU", "PY", "PB",
                                             "CY", "LA", "ER")):
                self.fail(
                    f"Found a RIS line with no leading tag, indicating a "
                    f"smuggled newline: {line!r}"
                )


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
