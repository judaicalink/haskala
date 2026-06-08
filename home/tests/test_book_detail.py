from django.test import TestCase, Client, override_settings
from django.urls import reverse

from home.models import Book, BookAuthor, City, Language, Person, Publisher


# Tests that hit views rendered through base.html need a non-manifest static
# files storage; tests that hit cached views need a dummy cache so a stale
# Redis entry from a prior run does not bleed in.
TEST_OVERRIDES = override_settings(
    # The production STORAGES uses ManifestStaticFilesStorage, which
    # walks every static file the template touches and aborts when one
    # is missing. The test DB does not need that guarantee and most
    # collected admin assets are never written for the test
    # in-memory finder — so drop the hashing step for tests.
    STORAGES={
        "default": {
            "BACKEND": "django.core.files.storage.FileSystemStorage",
        },
        "staticfiles": {
            "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage",
        },
    },
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
        resp = Client().get(reverse("book-detail", args=[self.book.slug]))
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
        resp = Client().get(reverse("book-cite-bibtex", args=[self.book.slug]))
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
        resp = Client().get(reverse("book-cite-bibtex", args=[self.book.slug]))
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
        resp = Client().get(reverse("book-cite-bibtex", args=[nasty.slug]))
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
        resp = Client().get(reverse("book-cite-bibtex", args=[self.book.slug]))
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
        resp = Client().get(reverse("book-cite-ris", args=[self.book.slug]))
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
        resp = Client().get(reverse("book-cite-ris", args=[self.book.slug]))
        body = resp.content.decode()
        au_lines = [ln for ln in body.splitlines() if ln.startswith("AU  - ")]
        self.assertEqual(len(au_lines), 2)
        self.assertIn("AU  - Mendelssohn, Moses", au_lines)
        self.assertIn("AU  - Maimon, Salomon", au_lines)

    def test_ris_emits_one_la_line_per_language(self):
        resp = Client().get(reverse("book-cite-ris", args=[self.book.slug]))
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
        resp = Client().get(reverse("book-cite-ris", args=[self.book.slug]))
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
        resp = Client().get(reverse("book-detail", args=[self.book.slug]))
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
            reverse("book-detail", args=[self.book.slug])
        ).content.decode()
        self.assertIn("Header Book: A Subtitle", html)
        self.assertIn("Sefer Test", html)
        self.assertIn("Pemberton, Dr.", html)
        self.assertIn("Leipzig", html)
        self.assertIn("Header Verlag", html)
        self.assertIn("1800", html)
        # Person chip links to the person detail
        self.assertIn(f"/persons/{self.person.slug}/", html)


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

    def test_only_sections_with_data_render(self):
        html = Client().get(
            reverse("book-detail", args=[self.book.slug])
        ).content.decode()
        # Publication has data -> the section element shows up.
        self.assertIn('id="publication"', html)
        # Censorship has no data -> must not be rendered at all.
        self.assertNotIn('id="censorship"', html)


@TEST_OVERRIDES
class SlugLookupTest(TestCase):
    """Auto-slug generation transliterates non-ASCII names so the
    URL always lands on something readable."""

    def test_book_slug_is_set_automatically(self):
        book = Book.objects.create(name="Voß: Phädon (1789)")
        self.assertEqual(book.slug, "voss-phadon-1789")
        self.assertEqual(book.get_absolute_url(), f"/books/{book.slug}/")

    def test_mixed_latin_hebrew_drops_the_hebrew_half(self):
        person = Person.objects.create(
            pref_label="Aaron, Joseph Philipp - אהרן, יוסף",
        )
        self.assertEqual(person.slug, "aaron-joseph-philipp")

    def test_hebrew_only_person_falls_back_to_short_uuid(self):
        person = Person.objects.create(hebrew_name="אהרן יוסף")
        prefix, _, suffix = person.slug.partition("-")
        self.assertEqual(prefix, "person")
        self.assertEqual(len(suffix), 8)

    def test_city_slug_is_unique_on_collision(self):
        a = City.objects.create(name="Vienna")
        b = City.objects.create(name="Vienna")
        self.assertEqual(a.slug, "vienna")
        self.assertEqual(b.slug, "vienna-2")

    def test_cyrillic_dropped_like_hebrew(self):
        person = Person.objects.create(pref_label="Pushkin, Aleksander Сергеевич")
        self.assertEqual(person.slug, "pushkin-aleksander")

    def test_diacritics_survive_via_anyascii(self):
        # Strip only non-Latin scripts; Latin-1 supplement diacritics
        # should still flow through anyascii as expected.
        book = Book.objects.create(name="Łódź für Voß")
        self.assertEqual(book.slug, "lodz-fur-voss")


@TEST_OVERRIDES
class EntityExportTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            name="Export Test Book", full_title="Export Test Book",
            gregorian_year="1797",
        )
        cls.person = Person.objects.create(
            pref_label="Test, Tester", viaf_id="12345", gnd_id="118582143",
        )
        cls.city = City.objects.create(name="Hamburg")

    def test_book_turtle_export(self):
        resp = Client().get(reverse("book-export", args=[self.book.slug, "ttl"]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/turtle", resp["Content-Type"])
        body = resp.content.decode()
        self.assertIn("@prefix", body)
        self.assertIn(self.book.uuid.hex, body.replace("-", ""))

    def test_person_jsonld_export(self):
        resp = Client().get(reverse("person-export", args=[self.person.slug, "jsonld"]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/ld+json", resp["Content-Type"])
        body = resp.content.decode()
        # GND alignment shows up in the body.
        self.assertIn("118582143", body)

    def test_place_rdfxml_export(self):
        resp = Client().get(reverse("place-export", args=[self.city.slug, "rdf"]))
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/rdf+xml", resp["Content-Type"])
        self.assertIn(b"<rdf:RDF", resp.content)

    def test_unknown_format_404(self):
        resp = Client().get(reverse("book-export", args=[self.book.slug, "yaml"]))
        self.assertEqual(resp.status_code, 404)


@TEST_OVERRIDES
class ContentNegotiationTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(name="Neg Book", full_title="Neg Book")
        cls.person = Person.objects.create(pref_label="Neg, Person")
        cls.city = City.objects.create(name="Negstadt")

    def test_text_html_returns_html(self):
        resp = Client().get(
            reverse("book-detail", args=[self.book.slug]),
            HTTP_ACCEPT="text/html",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/html", resp["Content-Type"])

    def test_text_turtle_returns_turtle(self):
        resp = Client().get(
            reverse("book-detail", args=[self.book.slug]),
            HTTP_ACCEPT="text/turtle",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("text/turtle", resp["Content-Type"])
        self.assertEqual(resp["Vary"], "Accept")

    def test_jsonld_on_person_detail(self):
        resp = Client().get(
            reverse("person-detail", args=[self.person.slug]),
            HTTP_ACCEPT="application/ld+json",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/ld+json", resp["Content-Type"])

    def test_rdfxml_on_place_detail(self):
        resp = Client().get(
            reverse("place-detail", args=[self.city.slug]),
            HTTP_ACCEPT="application/rdf+xml",
        )
        self.assertEqual(resp.status_code, 200)
        self.assertIn("application/rdf+xml", resp["Content-Type"])


@TEST_OVERRIDES
class DraftStateVisibilityTest(TestCase):
    """DraftStateMixin: live=False rows must 404 on every public path."""

    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(name="Draft Book", full_title="Draft Book")
        cls.person = Person.objects.create(pref_label="Draft, Person")
        cls.city = City.objects.create(name="Draftstadt")

    def _toggle_live(self, obj, value):
        obj.live = value
        obj.save(update_fields=["live"])

    def test_book_draft_returns_404_on_detail(self):
        self._toggle_live(self.book, False)
        resp = Client().get(reverse("book-detail", args=[self.book.slug]))
        self.assertEqual(resp.status_code, 404)

    def test_person_draft_returns_404_on_detail(self):
        self._toggle_live(self.person, False)
        resp = Client().get(reverse("person-detail", args=[self.person.slug]))
        self.assertEqual(resp.status_code, 404)

    def test_city_draft_returns_404_on_detail(self):
        self._toggle_live(self.city, False)
        resp = Client().get(reverse("place-detail", args=[self.city.slug]))
        self.assertEqual(resp.status_code, 404)

    def test_book_draft_404s_on_export(self):
        self._toggle_live(self.book, False)
        resp = Client().get(reverse("book-export", args=[self.book.slug, "ttl"]))
        self.assertEqual(resp.status_code, 404)

    def test_book_draft_hidden_from_list(self):
        self._toggle_live(self.book, False)
        html = Client().get(reverse("books-list")).content.decode()
        self.assertNotIn(self.book.slug, html)

    def test_live_book_is_visible(self):
        # Sanity check the default state — live=True out of the box.
        self.assertTrue(self.book.live)
        resp = Client().get(reverse("book-detail", args=[self.book.slug]))
        self.assertEqual(resp.status_code, 200)


@TEST_OVERRIDES
class InlineAuthorsTest(TestCase):
    """ParentalKey on BookAuthor.book lets the Wagtail admin form
    show authors inline. Confirm the new wiring still lets the
    public detail page render the author chip."""

    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(name="Inline Book", full_title="Inline Book")
        cls.first = Person.objects.create(pref_label="Inline, Alpha")
        cls.second = Person.objects.create(pref_label="Inline, Beta")
        BookAuthor.objects.create(
            book=cls.book, person=cls.first, role="original_text_author",
        )
        BookAuthor.objects.create(
            book=cls.book, person=cls.second, role="old_text_author",
        )

    def test_book_detail_lists_both_authors(self):
        html = Client().get(
            reverse("book-detail", args=[self.book.slug])
        ).content.decode()
        self.assertIn("Inline, Alpha", html)
        self.assertIn("Inline, Beta", html)

    def test_book_panels_include_inline_panel(self):
        from wagtail.admin.panels import InlinePanel
        # The Authors & persons MultiFieldPanel's first child should
        # be the BookAuthor InlinePanel, mounted on bookauthor_set.
        authors_section = next(
            p for p in Book.panels if getattr(p, "heading", "") == "Authors & persons"
        )
        children = list(authors_section.children)
        self.assertTrue(any(isinstance(c, InlinePanel) for c in children),
                        "Authors panel should expose an InlinePanel")
        inline = next(c for c in children if isinstance(c, InlinePanel))
        self.assertEqual(inline.relation_name, "bookauthor_set")
