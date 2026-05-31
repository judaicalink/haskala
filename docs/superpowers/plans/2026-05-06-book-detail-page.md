# Book detail page Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Book detail page as a long sectioned record with a sticky TOC, surfacing all ~150 Book fields and the recently imported relations (Editions, Translations, Productions, Prefaces, Mentions, BookAuthor with role), plus BibTeX/RIS/plain citation export.

**Architecture:** Server-side rendered Django templates extending `base.html`, with a left-hand sticky TOC + right-hand content grid. Each section is its own partial, rendered only when it has data. Section visibility is computed once in the view via a `visible_sections(book)` helper and passed to both TOC and content. Citation export is two new views serving plain-text BibTeX/RIS templates; plain citation is rendered inline in a Bootstrap modal.

**Tech Stack:** Django 5 + Wagtail, Bootstrap 5.3 + custom SCSS (compiled with sass), JS bundled via esbuild from `app-entry.js`. Tests run with Django's built-in test runner.

**Spec:** `docs/superpowers/specs/2026-05-06-book-detail-page-design.md`

---

## Pre-flight assumptions

- Working directory is the repo root `/mnt/data/coding/judaicalink/haskala`.
- The Django virtualenv is at `/home/benni/coding/judaicalink/haskala/venv`. Every `python manage.py …` step assumes it is activated; engineers running the plan can prepend `source /home/benni/coding/judaicalink/haskala/venv/bin/activate && ` or activate once per shell session.
- Tests are placed under `home/tests/` (a new directory; current project has no tests). Django's default test runner discovers them via `python manage.py test home`.
- Commits go on `feature/model-tweaks` (current branch). No PR is opened by the plan; user does that.

---

## Task 1: Add Mention → Book FK and backfill via importer

**Files:**
- Modify: `home/models.py` (Mention class)
- Create: `home/migrations/0022_mention_book.py` (auto-generated)
- Modify: `home/management/commands/import_haskala_relations.py` (import_mentions method)

- [ ] **Step 1: Add `book` FK to Mention model**

Locate the Mention class in `home/models.py` (around line 529). Add a nullable FK to Book mirroring Preface's pattern:

```python
class Mention(LegacyImportedModel):
    """
    Model for Mentions
    """
    uuid = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book = models.ForeignKey(
        "Book",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="mentions",
    )

    # Mentionee
    mentionee = models.ForeignKey(Person, null=True, blank=True, on_delete=models.SET_NULL)

    # Mentionee city
    mentionee_city = models.ForeignKey(City, null=True, blank=True, on_delete=models.SET_NULL)

    # Mentionee description
    mentionee_description = models.ForeignKey("MentionDescription", null=True, blank=True, on_delete=models.SET_NULL)
```

Delete the now-obsolete `# Belongs to book, but not found in tables` comment if present.

- [ ] **Step 2: Generate and apply migration**

Run:

```bash
python manage.py makemigrations home
python manage.py migrate home
```

Expected: migration named `0022_mention_book.py` is created with one `AddField` operation; migrate applies it without errors.

- [ ] **Step 3: Update `import_mentions` to set the book FK via backlink**

Open `home/management/commands/import_haskala_relations.py`. Locate `import_mentions` (around line 270; verify). It currently takes only `export_dir` because it had no book link to resolve. Change the signature and body to accept `book_backlink` and to look up the book like `import_prefaces` does:

```python
def import_mentions(self, export_dir: Path, book_backlink: dict[int, int]):
    path = export_dir / "mentions_for_django.csv"
    if not path.exists():
        self.stdout.write(self.style.WARNING(f"Skipping mentions: {path} not found."))
        return

    books = self._book_by_nid()
    persons = self._person_by_nid()
    cities = self._city_by_tid()
    descriptions = self._mention_description_by_tid()
    created = updated = without_book = 0

    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            legacy_nid = parse_int(row.get("nid"))
            if legacy_nid is None:
                continue

            book_nid = book_backlink.get(legacy_nid)
            book = books.get(book_nid) if book_nid else None
            if book is None:
                without_book += 1

            defaults = {
                "legacy_vid": parse_int(row.get("vid")),
                "legacy_status": parse_bool(row.get("status")),
                "legacy_created": parse_timestamp(row.get("created")),
                "legacy_changed": parse_timestamp(row.get("changed")),
                "book": book,
                "mentionee": persons.get(parse_int(row.get("mentionee_target_id"))),
                "mentionee_city": cities.get(parse_int(row.get("mentionee_city_tid"))),
                "mentionee_description": descriptions.get(parse_int(row.get("mentionee_description_tid"))),
            }
            _, created_flag = Mention.objects.update_or_create(
                legacy_nid=legacy_nid, defaults=defaults
            )
            if created_flag:
                created += 1
            else:
                updated += 1

    self.stdout.write(self.style.SUCCESS(
        f"Mention: {created} created, {updated} updated, {without_book} without book link."
    ))
```

Inspect the existing method first to confirm the exact CSV column names used (`mentionee_target_id`, etc.) — they were already correct in the prior implementation; this step only adds the book lookup.

Then update the `handle()` method's call site to pass `book_backlink`:

Find:

```python
self.import_mentions(export_dir)
```

Replace with:

```python
self.import_mentions(export_dir, book_backlink)
```

- [ ] **Step 4: Re-run the relations importer**

```bash
python manage.py import_haskala_relations --export-dir research/export --drupal-dir Database
```

Expected output line (counts must match — 1867 is the row total):

```
Mention: 0 created, 1867 updated, <N> without book link.
```

The `without book link` count should be small (most mentions belong to a book via the backlink table). Record the number in the commit message for visibility.

- [ ] **Step 5: Verify in DB**

```bash
python manage.py shell -c "from home.models import Mention; \
print('linked to a book:', Mention.objects.filter(book__isnull=False).count()); \
print('unlinked:', Mention.objects.filter(book__isnull=True).count())"
```

Expected: large number linked (>1500), the remainder unlinked (these are mentions Drupal did not assign to a book).

- [ ] **Step 6: Commit**

```bash
git add home/models.py home/migrations/0022_mention_book.py \
        home/management/commands/import_haskala_relations.py
git commit -m "feat(models): link Mention to Book via FK and backfill from import

Mention had no FK to Book; the legacy importer was creating orphan rows.
Add a nullable Book FK, regenerate the import via the same backlink
table used for Preface and Production, and reuse the existing
book_backlink lookup so unlinkable rows degrade gracefully."
```

---

## Task 2: View prefetch + visible_sections helper + smoke test

**Files:**
- Create: `home/book_detail.py`
- Modify: `home/views.py` (book_detail_view, around line 20)
- Create: `home/tests/__init__.py`
- Create: `home/tests/test_book_detail.py`

- [ ] **Step 1: Define SECTIONS and predicates**

Create `home/book_detail.py` with the ordered section list plus a predicate per section that returns True iff the section has data. Predicates are intentionally explicit; resist the urge to introspect Book._meta:

```python
"""
Defines the 16 ordered sections of the Book detail page and which sections
have data for a given Book. Used by the view to compute visible_sections
once and pass it to both the TOC and the content templates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Book


@dataclass(frozen=True)
class Section:
    slug: str  # used as anchor id and TOC key
    label: str  # display name in TOC and section heading
    has_data: Callable[[Book], bool]


def _any(*values) -> bool:
    return any(bool(v) for v in values)


def _identity_has_data(b: Book) -> bool:
    return _any(
        b.full_title, b.title_in_latin_characters, b.motto, b.old_name_in_book,
        b.other_books_names, b.original_text_name, b.original_title,
        b.original_title_else_refer, b.original_title_elsewhere,
        b.presented_as_original, b.presented_as_translation,
        b.presented_new_edition,
    )


def _authors_has_data(b: Book) -> bool:
    return (
        b.bookauthor_set.exists()
        or _any(b.original_author, b.original_author_else_refer,
                b.original_author_elsewhere, b.original_author_other_name,
                b.founders, b.proofreaders)
    )


def _publication_has_data(b: Book) -> bool:
    return _any(
        b.publisher_id, b.original_publisher_id,
        b.publication_place_id, b.publication_place_other_id,
        b.gregorian_year, b.year_in_book, b.year_in_other,
        b.hebrew_year_of_publication, b.hebrew_year_pub_other,
        b.gregorian_year_pub_other, b.format_of_publication_date_id,
        b.partial_publication, b.printed_originally,
        b.original_publication_place_id, b.original_publication_year,
        b.printers, b.printing_press_notes, b.printing_press_references,
        b.production_evidence, b.series_id, b.series_part,
    )


def _physical_has_data(b: Book) -> bool:
    return _any(
        b.pages_number, b.height, b.width,
        b.fonts.exists(), b.typography.exists(),
        b.illustrations_diagrams, b.diagrams_notes, b.diagrams_book_pages,
        b.alignment_id,
    )


def _languages_has_data(b: Book) -> bool:
    return (
        b.languages.exists() or b.footnote_languages.exists()
        or b.occasional_words_languages.exists()
        or _any(b.languages_number_id, b.location_of_footnotes_id, b.original_language_id)
    )


def _content_structure_has_data(b: Book) -> bool:
    return (
        b.target_audience.exists()
        or b.main_textual_models.exists()
        or b.secondary_textual_models.exists()
        or _any(
            b.topic_id, b.target_audience_notes, b.target_general_notes,
            b.textual_model_notes, b.original_type_id,
            b.structure_notes, b.structure_preface_notes,
            b.table_of_content, b.contents_table_notes,
            b.preface, b.epilogue, b.epilogue_notes,
            b.dedications, b.dedications_notes,
        )
    )


def _editions_has_data(b: Book) -> bool:
    return (
        b.editions.exists()
        or _any(
            b.total_number_of_editions, b.last_known_edition, b.editions_notes,
            b.references_for_editions, b.new_edition_general_notes,
            b.new_edition_type_in_text_id, b.new_edition_type_elsewhere_id,
            b.new_edition_type_reference, b.new_edition_type_else_ref,
            b.new_edition_type_notes, b.new_edition_type_else_note,
            b.expanded_in_edition, b.contradict_new_edition,
            b.copy_of_book_used, b.examined_volume_number,
            b.other_volumes, b.volumes_notes,
            b.volumes_published_number, b.planned_volumes,
        )
    )


def _translations_has_data(b: Book) -> bool:
    return (
        b.translations.exists()
        or _any(
            b.translation_notes, b.translation_type_id,
            b.expanded_in_translation,
            b.presented_as_translation, b.presented_as_translation_refe,
            b.presented_as_translatio_notes,
        )
    )


def _productions_has_data(b: Book) -> bool:
    return b.productions.exists()


def _prefaces_has_data(b: Book) -> bool:
    return b.prefaces.exists()


def _mentions_has_data(b: Book) -> bool:
    return (
        b.mentions.exists()
        or _any(
            b.mention_general_notes, b.mentions_in_reviews,
            b.contemporary_disputes, b.contemporary_references,
            b.later_references,
        )
    )


def _sources_has_data(b: Book) -> bool:
    return _any(
        b.bibliographical_citations, b.studies,
        b.sources_exist, b.sources_list,
        b.sources_not_mentioned, b.sources_not_mentioned_list,
        b.sources_not_mentioned_ref, b.sources_references,
        b.jewish_sources_quotes, b.non_jewish_sources_quotes,
        b.original_sources_mention, b.references_notes,
        b.secondary_sources,
    )


def _censorship_has_data(b: Book) -> bool:
    return _any(
        b.censorship, b.bans, b.rabbinical_approbations,
        b.rabbinical_approbation_notes,
    )


def _subscription_has_data(b: Book) -> bool:
    return _any(
        b.subscribers, b.subscribers_notes,
        b.subscription_appeal, b.subscription_appeal_notes,
        b.recommendations, b.recommendations_notes,
        b.price, b.sellers, b.sellers_notes,
        b.thanks, b.thanks_notes,
        b.contacts_official_agents, b.contacts_other_people,
        b.personal_address, b.personal_address_notes,
    )


def _availability_has_data(b: Book) -> bool:
    return _any(
        b.not_available is True, b.availability_notes,
        b.other_libraries,
        b.bar_ilan_library_id, b.berlin_library_id, b.british_library_id,
        b.frankfurt_library_id, b.huji_library_id,
        b.new_york_library_id, b.tel_aviv_library_id,
        b.digital_book_url, b.digital_book_title, b.digital_book_attributes,
        b.preservation_references, b.catalog_numbers_notes,
    )


def _record_metadata_has_data(b: Book) -> bool:
    return _any(b.legacy_nid, b.legacy_created, b.legacy_changed)


SECTIONS: list[Section] = [
    Section("identity", "Identity & Titles", _identity_has_data),
    Section("authors", "Authors & Persons", _authors_has_data),
    Section("publication", "Publication", _publication_has_data),
    Section("physical", "Physical & Typography", _physical_has_data),
    Section("languages", "Language & Footnotes", _languages_has_data),
    Section("content_structure", "Content & Structure", _content_structure_has_data),
    Section("editions", "Editions", _editions_has_data),
    Section("translations", "Translations", _translations_has_data),
    Section("productions", "Productions", _productions_has_data),
    Section("prefaces", "Prefaces", _prefaces_has_data),
    Section("mentions", "Mentions & Reception", _mentions_has_data),
    Section("sources", "Sources & References", _sources_has_data),
    Section("censorship", "Censorship & Approbation", _censorship_has_data),
    Section("subscription", "Subscription & Marketing", _subscription_has_data),
    Section("availability", "Availability & Catalog", _availability_has_data),
    Section("record_metadata", "Record metadata", _record_metadata_has_data),
]


def visible_sections(book: Book) -> list[Section]:
    """Return SECTIONS in order, filtered to those with data for this book."""
    return [s for s in SECTIONS if s.has_data(book)]
```

Field-name spot-checks: cross-reference with `home/models.py`. Field names used above were drawn from the spec; if any name is off, fix that predicate. Run `python -c "from home.book_detail import SECTIONS; print(len(SECTIONS))"` to confirm the module imports cleanly. Expected: `16`.

- [ ] **Step 2: Update book_detail_view to prefetch and pass visible_sections**

In `home/views.py`, replace the existing `book_detail_view` (around line 20):

```python
def book_detail_view(request, title):
    from django.db.models import Prefetch
    from .book_detail import visible_sections

    book = get_object_or_404(
        Book.objects.select_related(
            "publisher", "original_publisher",
            "publication_place", "publication_place_other",
            "original_publication_place",
            "topic", "series", "alignment", "original_type",
            "location_of_footnotes", "format_of_publication_date",
            "languages_number", "original_language",
            "translation_type",
            "new_edition_type_in_text", "new_edition_type_elsewhere",
        ).prefetch_related(
            Prefetch(
                "bookauthor_set",
                queryset=BookAuthor.objects.select_related("person"),
            ),
            Prefetch(
                "editions",
                queryset=Edition.objects.select_related("city").order_by("edition_year"),
            ),
            Prefetch(
                "translations",
                queryset=Translation.objects.select_related("translator", "city", "language"),
            ),
            Prefetch(
                "prefaces",
                queryset=Preface.objects.select_related("writer").order_by("number"),
            ),
            Prefetch(
                "productions",
                queryset=Production.objects.select_related("producer", "role"),
            ),
            Prefetch(
                "mentions",
                queryset=Mention.objects.select_related(
                    "mentionee", "mentionee_city", "mentionee_description",
                ),
            ),
            "main_textual_models",
            "secondary_textual_models",
            "languages",
            "footnote_languages",
            "occasional_words_languages",
            "fonts",
            "typography",
            "target_audience",
        ),
        name=title,
    )

    return render(request, "books/book_detail_page.html", {
        "book": book,
        "visible_sections": visible_sections(book),
    })
```

Inspect the existing `home/views.py` top-level imports first — `Prefetch` may need to be added to the `django.db.models` import group at the top of the file. If so, move the local import out of the function.

- [ ] **Step 3: Create test scaffold**

Create `home/tests/__init__.py` (empty file).

Create `home/tests/test_book_detail.py`:

```python
from django.test import TestCase, Client
from django.urls import reverse

from home.models import Book, Person, City, Publisher


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
```

- [ ] **Step 4: Run the test to confirm baseline**

```bash
python manage.py test home.tests.test_book_detail -v 2
```

Expected: 2 tests pass (the existing template still renders; we have not changed it yet, only the view's context and prefetching).

- [ ] **Step 5: Commit**

```bash
git add home/book_detail.py home/views.py home/tests/__init__.py home/tests/test_book_detail.py
git commit -m "feat(book-detail): prefetch relations and compute visible sections

Add home/book_detail.py defining the 16 ordered sections of the detail
page plus a per-section predicate; the view computes visible_sections
once and passes it to the template. The view also prefetches all
relations needed by the upcoming rebuild so the page can render
without N+1 queries. Adds a minimal home/tests scaffold."
```

---

## Task 3: BibTeX citation endpoint

**Files:**
- Create: `haskala/templates/books/cite/bibtex.txt`
- Modify: `home/views.py` (add book_cite_bibtex)
- Modify: `haskala/urls.py` (add route)
- Modify: `home/tests/test_book_detail.py` (add tests)

- [ ] **Step 1: Add a helper for the citation key**

Append to `home/book_detail.py`:

```python
import re


def citation_key(book: Book) -> str:
    """
    Generate a BibTeX-style citation key:
        <surname-of-first-author or 'anon'><year or 'nd'>

    Lowercased, ASCII-only, no spaces. Collisions are accepted; downstream
    tools can disambiguate.
    """
    first_author = (
        book.bookauthor_set.select_related("person").order_by("role").first()
    )
    if first_author and first_author.person:
        label = first_author.person.pref_label or str(first_author.person)
        surname = label.split(",")[0].strip().split()[-1] if label else "anon"
    else:
        surname = "anon"

    year = (book.gregorian_year or book.year_in_book or "nd").strip() or "nd"

    key = f"{surname}{year}".lower()
    key = re.sub(r"[^a-z0-9]", "", key)
    return key or "anonnd"
```

- [ ] **Step 2: Write a failing test for the BibTeX endpoint**

In `home/tests/test_book_detail.py`, add:

```python
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
```

- [ ] **Step 3: Run the test to confirm it fails**

```bash
python manage.py test home.tests.test_book_detail.BookCiteBibtexTest -v 2
```

Expected: FAIL with `NoReverseMatch` for `book-cite-bibtex` — the URL doesn't exist yet.

- [ ] **Step 4: Add the BibTeX template**

Create `haskala/templates/books/cite/bibtex.txt`:

```
@book{{ '{' }}{{ key }},
  title     = {{ '{' }}{{ '{' }}{{ book.full_title|default:book.name }}{{ '}' }}{{ '}' }},{% if authors %}
  author    = {{ '{' }}{% for a in authors %}{{ a }}{% if not forloop.last %} and {% endif %}{% endfor %}{{ '}' }},{% endif %}{% if book.gregorian_year or book.year_in_book %}
  year      = {{ '{' }}{{ book.gregorian_year|default:book.year_in_book }}{{ '}' }},{% endif %}{% if book.publisher %}
  publisher = {{ '{' }}{{ '{' }}{{ book.publisher.name }}{{ '}' }}{{ '}' }},{% endif %}{% if book.publication_place %}
  address   = {{ '{' }}{{ '{' }}{{ book.publication_place.name }}{{ '}' }}{{ '}' }},{% endif %}{% if book.title_in_latin_characters %}
  note      = {{ '{' }}Latin title: {{ book.title_in_latin_characters }}{{ '}' }},{% endif %}
}
```

Note: the awkward `{{ '{' }}` is how Django escapes literal braces. An alternative is to use `{% verbatim %}` blocks, but for a generated record the per-token approach is clear. Confirm output by running step 6 after step 5.

- [ ] **Step 5: Add the view**

Append to `home/views.py`:

```python
def book_cite_bibtex(request, title):
    from .book_detail import citation_key

    book = get_object_or_404(Book, name=title)
    authors = [
        ba.person.pref_label or str(ba.person)
        for ba in book.bookauthor_set.select_related("person")
        if ba.person
    ]
    body = render(
        request,
        "books/cite/bibtex.txt",
        {"book": book, "key": citation_key(book), "authors": authors},
        content_type="text/x-bibtex; charset=utf-8",
    )
    body["Content-Disposition"] = f'attachment; filename="{citation_key(book)}.bib"'
    return body
```

- [ ] **Step 6: Wire the URL**

In `haskala/urls.py`, add to the `urlpatterns` list (anywhere in the `urlpatterns += [...]` block, after the existing book-detail route):

```python
from home.views import book_cite_bibtex  # at the top with the other home.views imports
```

```python
# in the urlpatterns list:
path("books/<title>/cite.bib", book_cite_bibtex, name="book-cite-bibtex"),
```

- [ ] **Step 7: Run the test**

```bash
python manage.py test home.tests.test_book_detail.BookCiteBibtexTest -v 2
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add haskala/templates/books/cite/bibtex.txt home/book_detail.py home/views.py haskala/urls.py home/tests/test_book_detail.py
git commit -m "feat(book-detail): add BibTeX citation export

New endpoint /books/<title>/cite.bib renders a BibTeX entry with a
citation key derived from the first author's surname and the book's
Gregorian year. Authors are joined with 'and'; literal braces protect
mixed-case titles and proper nouns."
```

---

## Task 4: RIS citation endpoint

**Files:**
- Create: `haskala/templates/books/cite/ris.txt`
- Modify: `home/views.py` (add book_cite_ris)
- Modify: `haskala/urls.py` (add route)
- Modify: `home/tests/test_book_detail.py` (add test)

- [ ] **Step 1: Write a failing test**

In `home/tests/test_book_detail.py`, add:

```python
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
        self.assertIn("application/x-research-info-systems", resp["Content-Type"])
        body = resp.content.decode()
        self.assertIn("TY  - BOOK", body)
        self.assertIn("TI  - Risky Book", body)
        self.assertIn("PY  - 1797", body)
        self.assertTrue(body.rstrip().endswith("ER  -"))
```

- [ ] **Step 2: Run test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookCiteRisTest -v 2
```

Expected: FAIL with `NoReverseMatch`.

- [ ] **Step 3: Add the RIS template**

Create `haskala/templates/books/cite/ris.txt`:

```
TY  - BOOK
TI  - {{ book.full_title|default:book.name }}{% for a in authors %}
AU  - {{ a }}{% endfor %}{% if book.gregorian_year or book.year_in_book %}
PY  - {{ book.gregorian_year|default:book.year_in_book }}{% endif %}{% if book.publisher %}
PB  - {{ book.publisher.name }}{% endif %}{% if book.publication_place %}
CY  - {{ book.publication_place.name }}{% endif %}{% for lang in languages %}
LA  - {{ lang }}{% endfor %}
ER  -
```

- [ ] **Step 4: Add the view**

Append to `home/views.py`:

```python
def book_cite_ris(request, title):
    from .book_detail import citation_key

    book = get_object_or_404(Book, name=title)
    authors = [
        ba.person.pref_label or str(ba.person)
        for ba in book.bookauthor_set.select_related("person")
        if ba.person
    ]
    languages = [str(lang) for lang in book.languages.all()]
    body = render(
        request,
        "books/cite/ris.txt",
        {"book": book, "authors": authors, "languages": languages},
        content_type="application/x-research-info-systems; charset=utf-8",
    )
    body["Content-Disposition"] = f'attachment; filename="{citation_key(book)}.ris"'
    return body
```

- [ ] **Step 5: Wire the URL**

In `haskala/urls.py`:

```python
from home.views import book_cite_ris  # add to home.views imports
```

```python
# in urlpatterns:
path("books/<title>/cite.ris", book_cite_ris, name="book-cite-ris"),
```

- [ ] **Step 6: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookCiteRisTest -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add haskala/templates/books/cite/ris.txt home/views.py haskala/urls.py home/tests/test_book_detail.py
git commit -m "feat(book-detail): add RIS citation export

Endpoint /books/<title>/cite.ris returns an RIS record (TY=BOOK,
required ER terminator) suitable for import into reference managers."
```

---

## Task 5: Plain citation + cite modal partial

**Files:**
- Create: `haskala/templates/books/cite/plain.html`
- Create: `haskala/templates/books/_book_cite_modal.html`
- Modify: `home/tests/test_book_detail.py` (add tests)

- [ ] **Step 1: Add a failing test for the modal contents**

In `home/tests/test_book_detail.py`, add:

```python
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
```

- [ ] **Step 2: Run test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookCiteModalTest -v 2
```

Expected: FAIL — the modal isn't included by the current template yet.

- [ ] **Step 3: Create the plain citation template**

Create `haskala/templates/books/cite/plain.html` (Chicago-ish format):

```html
{% spaceless %}
<span class="citation-plain">{% for a in authors %}{{ a }}{% if not forloop.last %}; {% endif %}{% endfor %}{% if authors %}. {% endif %}<em>{{ book.full_title|default:book.name }}</em>.{% if book.publication_place %} {{ book.publication_place.name }}{% if book.publisher %}: {{ book.publisher.name }}{% endif %},{% elif book.publisher %} {{ book.publisher.name }},{% endif %}{% if book.gregorian_year or book.year_in_book %} {{ book.gregorian_year|default:book.year_in_book }}{% endif %}.</span>
{% endspaceless %}
```

- [ ] **Step 4: Create the cite modal partial**

Create `haskala/templates/books/_book_cite_modal.html`:

```html
{% load static %}
<div class="modal fade" id="book-cite-modal" tabindex="-1" aria-labelledby="book-cite-modal-label" aria-hidden="true">
  <div class="modal-dialog modal-dialog-centered">
    <div class="modal-content">
      <div class="modal-header">
        <h2 class="modal-title h5" id="book-cite-modal-label">Cite this record</h2>
        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
      </div>
      <div class="modal-body">

        <h3 class="h6 mb-2">Plain citation</h3>
        <div class="d-flex align-items-start gap-2 mb-4">
          <p class="mb-0 flex-grow-1" id="book-cite-plain">
            {% include "books/cite/plain.html" %}
          </p>
          <button type="button" class="btn btn-sm btn-outline-secondary"
                  data-cite-copy="#book-cite-plain"
                  aria-label="Copy plain citation">
            <i class="bi bi-clipboard"></i>
          </button>
        </div>

        <h3 class="h6 mb-2">Download</h3>
        <p class="mb-0">
          <a href="{% url 'book-cite-bibtex' book.name %}" class="btn btn-sm btn-outline-primary me-2">
            <i class="bi bi-download"></i> BibTeX
          </a>
          <a href="{% url 'book-cite-ris' book.name %}" class="btn btn-sm btn-outline-primary">
            <i class="bi bi-download"></i> RIS
          </a>
        </p>

        <div class="mt-3 small text-muted" id="book-cite-copy-status" aria-live="polite"></div>
      </div>
    </div>
  </div>
</div>
```

- [ ] **Step 5: Include the modal in the existing detail template**

Open `haskala/templates/books/book_detail_page.html`. At the end of the `{% block content %}` (before `{% endblock %}`), include the modal. The cleanest insertion point is just before the closing `</div>` of the outermost container. Append:

```html
        {% include "books/_book_cite_modal.html" %}
    </div>
{% endblock %}
```

The current template (155 lines) has one outer `<div class="container my-4">`. Place the include just before its closing `</div>`.

Also add a temporary placeholder button in the existing template header so the test passes — Task 6 replaces this with the real header. Find the `<header class="mb-4">` block and append, after the existing buttons:

```html
            <p class="mt-2">
                <button type="button" class="btn btn-sm btn-outline-secondary"
                        data-bs-toggle="modal" data-bs-target="#book-cite-modal">
                    <i class="bi bi-quote"></i> Cite
                </button>
            </p>
```

- [ ] **Step 6: Run test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookCiteModalTest -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add haskala/templates/books/cite/plain.html \
        haskala/templates/books/_book_cite_modal.html \
        haskala/templates/books/book_detail_page.html \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): cite modal with plain citation and downloads

Bootstrap modal exposes a Chicago-style plain citation (with clipboard
copy via a later JS task) and direct download buttons for the BibTeX
and RIS endpoints. The current detail template gets a temporary trigger
button; the full header rewrite in Task 6 supersedes it."
```

---

## Task 6: Header partial + person chip

**Files:**
- Create: `haskala/templates/books/_book_header.html`
- Create: `haskala/templates/books/_cards/_person_chip.html`
- Modify: `home/tests/test_book_detail.py` (add tests)

- [ ] **Step 1: Add a failing test for header rendering**

In `home/tests/test_book_detail.py`, add:

```python
from home.models import BookAuthor


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
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("Header Book: A Subtitle", html)
        self.assertIn("Sefer Test", html)
        self.assertIn("Pemberton, Dr.", html)
        self.assertIn("Leipzig", html)
        self.assertIn("Header Verlag", html)
        self.assertIn("1800", html)
        # Person chip links to the person detail
        self.assertIn(f"/persons/{self.person.uuid}/", html)
```

- [ ] **Step 2: Run test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookHeaderTest -v 2
```

Expected: most assertions fail because the existing template renders the title and authors differently or not at all.

- [ ] **Step 3: Create the person chip partial**

Create `haskala/templates/books/_cards/_person_chip.html`:

```html
{# usage: {% include "books/_cards/_person_chip.html" with person=person role=role %} #}
<a class="person-chip" href="{% url 'person-detail' person.uuid %}">
    <span class="person-chip__label">{{ person }}</span>{% if role %}
    <span class="person-chip__role badge text-bg-secondary ms-1">{{ role }}</span>{% endif %}
</a>
```

- [ ] **Step 4: Create the header partial**

Create `haskala/templates/books/_book_header.html`:

```html
{% load static %}
<header class="book-header mb-4">
    <p class="text-muted small mb-1">
        <a href="{% url 'books-list' %}">Books</a>
        <span aria-hidden="true">&rsaquo;</span>
        <span>{{ book.name }}</span>
    </p>

    <h1 class="book-header__title h2 mb-1">
        {{ book.full_title|default:book.name }}
    </h1>

    {% if book.title_in_latin_characters %}
        <p class="book-header__latin text-muted fst-italic mb-2">
            {{ book.title_in_latin_characters }}
        </p>
    {% endif %}

    {% if book.bookauthor_set.all %}
        <p class="book-header__authors mb-2">
            {% for ba in book.bookauthor_set.all %}{% if ba.person %}{% include "books/_cards/_person_chip.html" with person=ba.person role=ba.get_role_display %}{% if not forloop.last %} {% endif %}{% endif %}{% endfor %}
        </p>
    {% endif %}

    <p class="book-header__pub text-muted mb-3">
        {% if book.publication_place %}{{ book.publication_place.name }}{% endif %}
        {% if book.publisher %}{% if book.publication_place %} · {% endif %}{{ book.publisher.name }}{% endif %}
        {% if book.gregorian_year or book.year_in_book %}{% if book.publication_place or book.publisher %} · {% endif %}{{ book.gregorian_year|default:book.year_in_book }}{% endif %}
    </p>

    <div class="book-header__actions">
        {% if book.digital_book_url %}
            <a href="{{ book.digital_book_url }}" target="_blank" rel="noopener"
               class="btn btn-sm btn-outline-info">
                <i class="bi bi-book"></i> View digital copy
            </a>
        {% endif %}
        <button type="button" class="btn btn-sm btn-outline-secondary"
                data-bs-toggle="modal" data-bs-target="#book-cite-modal">
            <i class="bi bi-quote"></i> Cite
        </button>
        <button type="button" class="btn btn-sm btn-outline-secondary"
                data-permalink="{{ request.build_absolute_uri }}"
                aria-label="Copy permalink">
            <i class="bi bi-link-45deg"></i> Permalink
        </button>
    </div>
</header>
```

- [ ] **Step 5: Use the header in the detail page**

Open `haskala/templates/books/book_detail_page.html`. Replace the entire existing `<header class="mb-4"> … </header>` block (including the temporary cite button added in Task 5) with:

```html
        {% include "books/_book_header.html" %}
```

- [ ] **Step 6: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookHeaderTest -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add haskala/templates/books/_book_header.html \
        haskala/templates/books/_cards/_person_chip.html \
        haskala/templates/books/book_detail_page.html \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): hero header with author chips and action bar

Reusable _book_header.html replaces the inline header in the detail
template and shows breadcrumbs, title, Latin transliteration, author
chips (with role badges), publication line, and action buttons (digital
copy, cite, permalink). _person_chip.html is the shared widget used
both in the header and the upcoming relation cards."
```

---

## Task 7: Outer page skeleton + TOC partial

**Files:**
- Modify: `haskala/templates/books/book_detail_page.html` (full rewrite)
- Create: `haskala/templates/books/_book_toc.html`
- Modify: `home/tests/test_book_detail.py` (add tests)

- [ ] **Step 1: Add failing test for the TOC**

In `home/tests/test_book_detail.py`, add:

```python
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
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        # Publication section has data → appears in TOC and as a section anchor.
        self.assertIn('href="#publication"', html)
        self.assertIn('id="publication"', html)
        # Censorship section has no data → must not appear at all.
        self.assertNotIn('href="#censorship"', html)
        self.assertNotIn('id="censorship"', html)
```

- [ ] **Step 2: Run the test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookTOCTest -v 2
```

Expected: FAIL (no TOC yet; the existing template doesn't produce these anchors).

- [ ] **Step 3: Create the TOC partial**

Create `haskala/templates/books/_book_toc.html`:

```html
<nav class="book-toc" aria-label="Sections">
    <p class="book-toc__heading h6 text-uppercase text-muted">On this page</p>
    <ol class="book-toc__list list-unstyled">
        {% for section in visible_sections %}
            <li class="book-toc__item">
                <a class="book-toc__link" href="#{{ section.slug }}">{{ section.label }}</a>
            </li>
        {% endfor %}
    </ol>
</nav>
```

- [ ] **Step 4: Rewrite the detail page outer template**

Replace the entire contents of `haskala/templates/books/book_detail_page.html` with:

```html
{% extends "base.html" %}
{% load wagtailcore_tags %}
{% load utils %}

{% block title %}
    {{ book.full_title|default:book.name|default:"Book detail" }}
{% endblock %}

{% block meta %}
    <meta name="description" content="{{ book.description|truncatechars:160 }}">
    <meta property="og:title" content="{{ book.name }}">
    <meta property="og:description" content="{{ book.description|truncatechars:160 }}">
{% endblock %}

{% block extra_css %}
    {# _book_detail.scss is bundled into haskala.css via _book_detail in haskala.scss #}
{% endblock %}

{% block content %}
    <div class="container book-detail my-4">
        {% include "books/_book_header.html" %}

        <div class="row gx-md-5">
            <aside class="col-md-3 book-detail__toc-col d-none d-md-block">
                <div class="book-toc-sticky">
                    {% include "books/_book_toc.html" %}
                </div>
            </aside>

            <div class="col-md-9 book-detail__content-col">
                {% for section in visible_sections %}
                    <section id="{{ section.slug }}" class="book-section">
                        <h2 class="book-section__heading h4">{{ section.label }}</h2>
                        {% include "books/_sections/"|add:section.slug|add:".html" %}
                    </section>
                {% endfor %}
            </div>
        </div>

        {% include "books/_book_cite_modal.html" %}
    </div>
{% endblock %}

{% block extra_js %}
    <script type="module" src="{% static 'js/book_detail.js' %}"></script>
{% endblock %}
```

This template references `books/_sections/<slug>.html` for each visible section; those partials are created in Tasks 8-12. Until they exist, the template will raise `TemplateDoesNotExist` when rendering a section that has data.

- [ ] **Step 5: Create stub section partials**

To unblock the TOC test, create empty section partials so `TemplateDoesNotExist` does not fire for sections that happen to have data on the test book. Run this loop (one-off in a shell):

```bash
mkdir -p haskala/templates/books/_sections
for slug in identity authors publication physical languages content_structure editions translations productions prefaces mentions sources censorship subscription availability record_metadata; do
  touch "haskala/templates/books/_sections/${slug}.html"
done
```

The stubs are intentionally empty; subsequent tasks replace them with real content.

- [ ] **Step 6: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookTOCTest -v 2
```

Expected: PASS.

- [ ] **Step 7: Run the full test suite to confirm no regressions**

```bash
python manage.py test home.tests -v 2
```

Expected: all previous tests still pass.

- [ ] **Step 8: Commit**

```bash
git add haskala/templates/books/book_detail_page.html \
        haskala/templates/books/_book_toc.html \
        haskala/templates/books/_sections/ \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): two-column layout with sticky TOC

Rewrite book_detail_page.html as a Bootstrap grid: left column is the
sticky TOC populated from visible_sections, right column iterates the
same list and includes a per-section partial. Sections without data
are skipped in both columns. Empty section partials are stubbed so the
page renders before the section content tasks land."
```

---

## Task 8: Sections 1-3 — Identity, Authors, Publication

**Files:**
- Modify: `haskala/templates/books/_sections/identity.html`
- Modify: `haskala/templates/books/_sections/authors.html`
- Modify: `haskala/templates/books/_sections/publication.html`
- Modify: `home/tests/test_book_detail.py` (add test)

- [ ] **Step 1: Add a failing test that asserts identity + publication content**

In `home/tests/test_book_detail.py`, add:

```python
class BookSectionsBatch1Test(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publisher = Publisher.objects.create(name="S1 Verlag")
        cls.city = City.objects.create(name="Prague")
        cls.book = Book.objects.create(
            name="S1 Book",
            full_title="S1 Book",
            motto="A motto",
            other_books_names="Other titles",
            gregorian_year="1820",
            publisher=cls.publisher,
            publication_place=cls.city,
            printers="Joe the Printer",
        )

    def test_identity_section_shows_motto(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("A motto", html)
        self.assertIn("Other titles", html)

    def test_publication_section_shows_printers(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("Joe the Printer", html)
        self.assertIn("S1 Verlag", html)
        self.assertIn("Prague", html)
        self.assertIn("1820", html)
```

- [ ] **Step 2: Run the test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookSectionsBatch1Test -v 2
```

Expected: FAIL — section partials are still empty stubs.

- [ ] **Step 3: Identity section**

Replace `haskala/templates/books/_sections/identity.html`:

```html
<dl class="book-fields">
    {% if book.full_title and book.full_title != book.name %}
        <dt>Full title</dt><dd>{{ book.full_title }}</dd>
    {% endif %}
    {% if book.name %}
        <dt>Name in book</dt><dd>{{ book.name }}</dd>
    {% endif %}
    {% if book.title_in_latin_characters %}
        <dt>Title in Latin characters</dt><dd>{{ book.title_in_latin_characters }}</dd>
    {% endif %}
    {% if book.motto %}
        <dt>Motto</dt><dd>{{ book.motto|linebreaksbr }}</dd>
    {% endif %}
    {% if book.old_name_in_book %}
        <dt>Old name in book</dt><dd>{{ book.old_name_in_book }}</dd>
    {% endif %}
    {% if book.other_books_names %}
        <dt>Other names</dt><dd>{{ book.other_books_names }}</dd>
    {% endif %}
    {% if book.original_text_name %}
        <dt>Original text name</dt><dd>{{ book.original_text_name }}</dd>
    {% endif %}
    {% if book.original_title %}
        <dt>Original title</dt><dd>{{ book.original_title }}</dd>
    {% endif %}
    {% if book.original_title_else_refer %}
        <dt>Original title (else refer)</dt><dd>{{ book.original_title_else_refer }}</dd>
    {% endif %}
    {% if book.original_title_elsewhere %}
        <dt>Original title (elsewhere)</dt><dd>{{ book.original_title_elsewhere }}</dd>
    {% endif %}
    {% if book.presented_as_original %}
        <dt>Presented as original</dt><dd>{{ book.presented_as_original|yesno:"Yes,No,Unknown" }}</dd>
    {% endif %}
    {% if book.presented_as_translation %}
        <dt>Presented as translation</dt><dd>{{ book.presented_as_translation|yesno:"Yes,No,Unknown" }}</dd>
    {% endif %}
    {% if book.presented_new_edition %}
        <dt>Presented as new edition</dt><dd>{{ book.presented_new_edition|yesno:"Yes,No,Unknown" }}</dd>
    {% endif %}
</dl>
```

- [ ] **Step 4: Authors section**

Replace `haskala/templates/books/_sections/authors.html`:

```html
{% regroup book.bookauthor_set.all|dictsort:"role" by get_role_display as authors_by_role %}

{% for group in authors_by_role %}
    <h3 class="h6 mt-3">{{ group.grouper }}</h3>
    <p class="book-section__person-chips">
        {% for ba in group.list %}{% if ba.person %}{% include "books/_cards/_person_chip.html" with person=ba.person role=None %}{% endif %}{% endfor %}
    </p>
{% endfor %}

<dl class="book-fields">
    {% if book.original_author %}
        <dt>Original author (free text)</dt><dd>{{ book.original_author|linebreaksbr }}</dd>
    {% endif %}
    {% if book.original_author_else_refer %}
        <dt>Original author (else refer)</dt><dd>{{ book.original_author_else_refer }}</dd>
    {% endif %}
    {% if book.original_author_elsewhere %}
        <dt>Original author (elsewhere)</dt><dd>{{ book.original_author_elsewhere }}</dd>
    {% endif %}
    {% if book.original_author_other_name %}
        <dt>Original author (other name)</dt><dd>{{ book.original_author_other_name }}</dd>
    {% endif %}
    {% if book.founders %}
        <dt>Founders</dt><dd>{{ book.founders|linebreaksbr }}</dd>
    {% endif %}
    {% if book.proofreaders %}
        <dt>Proofreaders</dt><dd>{{ book.proofreaders|linebreaksbr }}</dd>
    {% endif %}
</dl>
```

- [ ] **Step 5: Publication section**

Replace `haskala/templates/books/_sections/publication.html`:

```html
<dl class="book-fields">
    {% if book.publisher %}
        <dt>Publisher</dt>
        <dd><a href="{% url 'publisher-detail' book.publisher.name|slugify %}">{{ book.publisher.name }}</a></dd>
    {% endif %}
    {% if book.original_publisher %}
        <dt>Original publisher</dt>
        <dd><a href="{% url 'publisher-detail' book.original_publisher.name|slugify %}">{{ book.original_publisher.name }}</a></dd>
    {% endif %}
    {% if book.publication_place %}
        <dt>Place of publication</dt>
        <dd><a href="{% url 'place-detail' book.publication_place.name|slugify %}">{{ book.publication_place.name }}</a></dd>
    {% endif %}
    {% if book.publication_place_other %}
        <dt>Place of publication (other)</dt>
        <dd>{{ book.publication_place_other.name }}</dd>
    {% endif %}
    {% if book.gregorian_year %}<dt>Gregorian year</dt><dd>{{ book.gregorian_year }}</dd>{% endif %}
    {% if book.year_in_book %}<dt>Year in book</dt><dd>{{ book.year_in_book }}</dd>{% endif %}
    {% if book.year_in_other %}<dt>Year (other)</dt><dd>{{ book.year_in_other }}</dd>{% endif %}
    {% if book.hebrew_year_of_publication %}<dt>Hebrew year of publication</dt><dd>{{ book.hebrew_year_of_publication }}</dd>{% endif %}
    {% if book.hebrew_year_pub_other %}<dt>Hebrew year (other)</dt><dd>{{ book.hebrew_year_pub_other }}</dd>{% endif %}
    {% if book.gregorian_year_pub_other %}<dt>Gregorian year (other)</dt><dd>{{ book.gregorian_year_pub_other }}</dd>{% endif %}
    {% if book.format_of_publication_date %}<dt>Format of publication date</dt><dd>{{ book.format_of_publication_date }}</dd>{% endif %}
    {% if book.partial_publication %}<dt>Partial publication</dt><dd>{{ book.partial_publication }}</dd>{% endif %}
    {% if book.printed_originally %}<dt>Printed originally</dt><dd>{{ book.printed_originally }}</dd>{% endif %}
    {% if book.original_publication_place %}<dt>Original publication place</dt><dd>{{ book.original_publication_place.name }}</dd>{% endif %}
    {% if book.original_publication_year %}<dt>Original publication year</dt><dd>{{ book.original_publication_year }}</dd>{% endif %}
    {% if book.printers %}<dt>Printers</dt><dd>{{ book.printers|linebreaksbr }}</dd>{% endif %}
    {% if book.printing_press_notes %}<dt>Printing press notes</dt><dd>{{ book.printing_press_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.printing_press_references %}<dt>Printing press references</dt><dd>{{ book.printing_press_references|linebreaksbr }}</dd>{% endif %}
    {% if book.production_evidence %}<dt>Production evidence</dt><dd>{{ book.production_evidence|linebreaksbr }}</dd>{% endif %}
    {% if book.series %}
        <dt>Series</dt>
        <dd>
            {% with series_slug=book.series.name|slugify %}
                {% if series_slug %}
                    <a href="{% url 'series-detail' series_slug %}">{{ book.series.name }}</a>
                {% else %}
                    {{ book.series.name }}
                {% endif %}
            {% endwith %}
        </dd>
    {% endif %}
    {% if book.series_part %}<dt>Series part</dt><dd>{{ book.series_part }}</dd>{% endif %}
</dl>
```

- [ ] **Step 6: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookSectionsBatch1Test -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add haskala/templates/books/_sections/identity.html \
        haskala/templates/books/_sections/authors.html \
        haskala/templates/books/_sections/publication.html \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): render Identity, Authors, Publication sections

Three description-list partials covering name forms, free-text author
fields, BookAuthor chips grouped by role, and the publication block
(publisher, place, year forms, printers, series). Empty individual
fields are hidden via per-field if-guards."
```

---

## Task 9: Sections 4-6 — Physical, Languages, Content & Structure

**Files:**
- Modify: `haskala/templates/books/_sections/physical.html`
- Modify: `haskala/templates/books/_sections/languages.html`
- Modify: `haskala/templates/books/_sections/content_structure.html`
- Modify: `home/tests/test_book_detail.py` (add tests)

- [ ] **Step 1: Add a failing test including empty-section hiding**

In `home/tests/test_book_detail.py`, add:

```python
class BookSectionsBatch2Test(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book_full = Book.objects.create(
            name="S2 Full",
            full_title="S2 Full",
            pages_number="200",
            height="22cm",
            width="14cm",
            structure_notes="Has three parts.",
        )
        cls.book_empty = Book.objects.create(
            name="S2 Empty",
            full_title="S2 Empty",
        )

    def test_physical_and_structure_rendered(self):
        html = Client().get(reverse("book-detail", args=[self.book_full.name])).content.decode()
        self.assertIn("200", html)
        self.assertIn("22cm", html)
        self.assertIn("Has three parts.", html)

    def test_empty_sections_hidden_for_sparse_book(self):
        html = Client().get(reverse("book-detail", args=[self.book_empty.name])).content.decode()
        # No data for physical/languages/content_structure -> no anchor and no TOC link
        for slug in ("physical", "languages", "content_structure"):
            self.assertNotIn(f'href="#{slug}"', html)
            self.assertNotIn(f'id="{slug}"', html)
```

- [ ] **Step 2: Run the test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookSectionsBatch2Test -v 2
```

Expected: FAIL.

- [ ] **Step 3: Physical section**

Replace `haskala/templates/books/_sections/physical.html`:

```html
<dl class="book-fields">
    {% if book.pages_number %}<dt>Pages</dt><dd>{{ book.pages_number }}</dd>{% endif %}
    {% if book.height %}<dt>Height</dt><dd>{{ book.height }}</dd>{% endif %}
    {% if book.width %}<dt>Width</dt><dd>{{ book.width }}</dd>{% endif %}
    {% if book.fonts.all %}
        <dt>Fonts</dt>
        <dd>{% for f in book.fonts.all %}{{ f }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.typography.all %}
        <dt>Typography</dt>
        <dd>{% for t in book.typography.all %}{{ t }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.illustrations_diagrams %}<dt>Illustrations / diagrams</dt><dd>{{ book.illustrations_diagrams }}</dd>{% endif %}
    {% if book.diagrams_notes %}<dt>Diagrams notes</dt><dd>{{ book.diagrams_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.diagrams_book_pages %}<dt>Diagrams on book pages</dt><dd>{{ book.diagrams_book_pages }}</dd>{% endif %}
    {% if book.alignment %}<dt>Text alignment</dt><dd>{{ book.alignment }}</dd>{% endif %}
</dl>
```

- [ ] **Step 4: Languages section**

Replace `haskala/templates/books/_sections/languages.html`:

```html
<dl class="book-fields">
    {% if book.languages.all %}
        <dt>Languages</dt>
        <dd>{% for l in book.languages.all %}{{ l }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.languages_number %}<dt>Number of languages</dt><dd>{{ book.languages_number }}</dd>{% endif %}
    {% if book.footnote_languages.all %}
        <dt>Footnote languages</dt>
        <dd>{% for l in book.footnote_languages.all %}{{ l }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.occasional_words_languages.all %}
        <dt>Occasional words (languages)</dt>
        <dd>{% for l in book.occasional_words_languages.all %}{{ l }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.location_of_footnotes %}<dt>Location of footnotes</dt><dd>{{ book.location_of_footnotes }}</dd>{% endif %}
    {% if book.original_language %}<dt>Original language</dt><dd>{{ book.original_language }}</dd>{% endif %}
</dl>
```

- [ ] **Step 5: Content & Structure section**

Replace `haskala/templates/books/_sections/content_structure.html`:

```html
<dl class="book-fields">
    {% if book.topic %}
        <dt>Topic</dt>
        <dd><a href="{% url 'topic-detail' book.topic.name|slugify %}">{{ book.topic.name }}</a></dd>
    {% endif %}
    {% if book.target_audience.all %}
        <dt>Target audience</dt>
        <dd>{% for ta in book.target_audience.all %}{{ ta }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.target_audience_notes %}<dt>Target audience notes</dt><dd>{{ book.target_audience_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.target_general_notes %}<dt>Target general notes</dt><dd>{{ book.target_general_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.main_textual_models.all %}
        <dt>Main textual models</dt>
        <dd>{% for m in book.main_textual_models.all %}{{ m }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.secondary_textual_models.all %}
        <dt>Secondary textual models</dt>
        <dd>{% for m in book.secondary_textual_models.all %}{{ m }}{% if not forloop.last %}, {% endif %}{% endfor %}</dd>
    {% endif %}
    {% if book.textual_model_notes %}<dt>Textual model notes</dt><dd>{{ book.textual_model_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.original_type %}<dt>Original type</dt><dd>{{ book.original_type }}</dd>{% endif %}
    {% if book.structure_notes %}<dt>Structure notes</dt><dd>{{ book.structure_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.structure_preface_notes %}<dt>Structure / preface notes</dt><dd>{{ book.structure_preface_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.table_of_content %}<dt>Table of contents</dt><dd>{{ book.table_of_content|linebreaksbr }}</dd>{% endif %}
    {% if book.contents_table_notes %}<dt>Contents table notes</dt><dd>{{ book.contents_table_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.preface %}<dt>Preface (book-level)</dt><dd>{{ book.preface|linebreaksbr }}</dd>{% endif %}
    {% if book.epilogue %}<dt>Epilogue</dt><dd>{{ book.epilogue|linebreaksbr }}</dd>{% endif %}
    {% if book.epilogue_notes %}<dt>Epilogue notes</dt><dd>{{ book.epilogue_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.dedications %}<dt>Dedications</dt><dd>{{ book.dedications|linebreaksbr }}</dd>{% endif %}
    {% if book.dedications_notes %}<dt>Dedications notes</dt><dd>{{ book.dedications_notes|linebreaksbr }}</dd>{% endif %}
</dl>
```

- [ ] **Step 6: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookSectionsBatch2Test -v 2
```

Expected: PASS.

- [ ] **Step 7: Commit**

```bash
git add haskala/templates/books/_sections/physical.html \
        haskala/templates/books/_sections/languages.html \
        haskala/templates/books/_sections/content_structure.html \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): render Physical, Languages, Content sections

Physical & Typography lists pages/dimensions, fonts, typography,
illustrations, alignment. Languages lists the M2Ms for languages,
footnote_languages, occasional_words_languages and the related FKs.
Content & Structure groups topic, audience, textual models,
structural notes, preface, epilogue, and dedications."
```

---

## Task 10: Editions and Translations — cards + sections

**Files:**
- Create: `haskala/templates/books/_cards/edition_card.html`
- Create: `haskala/templates/books/_cards/translation_card.html`
- Modify: `haskala/templates/books/_sections/editions.html`
- Modify: `haskala/templates/books/_sections/translations.html`
- Modify: `home/tests/test_book_detail.py` (add tests)

- [ ] **Step 1: Failing test**

In `home/tests/test_book_detail.py`, add:

```python
from home.models import Edition, Translation


class BookEditionsTranslationsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(name="S3 Book", full_title="S3 Book")
        cls.city = City.objects.create(name="Brno")
        cls.translator = Person.objects.create(pref_label="Cohen, M.")
        Edition.objects.create(book=cls.book, name="2nd edition",
                               edition_year="1815", city=cls.city)
        Translation.objects.create(book=cls.book, title="Russian translation",
                                   translator=cls.translator, year="1820")

    def test_edition_card_renders(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("2nd edition", html)
        self.assertIn("1815", html)
        self.assertIn("Brno", html)

    def test_translation_card_renders(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("Russian translation", html)
        self.assertIn("Cohen, M.", html)
        self.assertIn("1820", html)
```

- [ ] **Step 2: Run the test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookEditionsTranslationsTest -v 2
```

- [ ] **Step 3: Edition card**

Create `haskala/templates/books/_cards/edition_card.html`:

```html
<article class="relation-card relation-card--edition">
    <header class="relation-card__header">
        <h3 class="relation-card__title h6">
            {{ edition.name|default:"Untitled edition" }}
        </h3>
        <p class="relation-card__meta text-muted small mb-0">
            {% if edition.edition_year %}{{ edition.edition_year }}{% endif %}
            {% if edition.city %}{% if edition.edition_year %} · {% endif %}{{ edition.city.name }}{% endif %}
        </p>
    </header>
    {% if edition.changes %}
        <p class="relation-card__field">
            <span class="relation-card__label">Changes:</span>
            {{ edition.changes|linebreaksbr|truncatechars_html:400 }}
        </p>
    {% endif %}
    {% if edition.references %}
        <p class="relation-card__field">
            <span class="relation-card__label">References:</span>
            {{ edition.references|linebreaksbr|truncatechars_html:400 }}
        </p>
    {% endif %}
</article>
```

- [ ] **Step 4: Translation card**

Create `haskala/templates/books/_cards/translation_card.html`:

```html
<article class="relation-card relation-card--translation">
    <header class="relation-card__header">
        <h3 class="relation-card__title h6">
            {{ translation.title|default:"Untitled translation" }}
        </h3>
        <p class="relation-card__meta text-muted small mb-0">
            {% if translation.translator %}{% include "books/_cards/_person_chip.html" with person=translation.translator role=None %}{% endif %}
            {% if translation.year %}{% if translation.translator %} · {% endif %}{{ translation.year }}{% endif %}
            {% if translation.city %}{% if translation.translator or translation.year %} · {% endif %}{{ translation.city.name }}{% endif %}
            {% if translation.language %}{% if translation.translator or translation.year or translation.city %} · {% endif %}{{ translation.language }}{% endif %}
        </p>
    </header>
    {% if translation.references %}
        <p class="relation-card__field">
            <span class="relation-card__label">References:</span>
            {{ translation.references|linebreaksbr|truncatechars_html:400 }}
        </p>
    {% endif %}
</article>
```

- [ ] **Step 5: Editions section**

Replace `haskala/templates/books/_sections/editions.html`:

```html
{% if book.editions.all %}
    <div class="relation-cards">
        {% for edition in book.editions.all %}
            {% include "books/_cards/edition_card.html" with edition=edition %}
        {% endfor %}
    </div>
{% endif %}

<dl class="book-fields">
    {% if book.total_number_of_editions %}<dt>Total number of editions</dt><dd>{{ book.total_number_of_editions }}</dd>{% endif %}
    {% if book.last_known_edition %}<dt>Last known edition</dt><dd>{{ book.last_known_edition }}</dd>{% endif %}
    {% if book.editions_notes %}<dt>Editions notes</dt><dd>{{ book.editions_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.references_for_editions %}<dt>References for editions</dt><dd>{{ book.references_for_editions|linebreaksbr }}</dd>{% endif %}
    {% if book.new_edition_general_notes %}<dt>New edition general notes</dt><dd>{{ book.new_edition_general_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.new_edition_type_in_text %}<dt>New edition type in text</dt><dd>{{ book.new_edition_type_in_text }}</dd>{% endif %}
    {% if book.new_edition_type_elsewhere %}<dt>New edition type elsewhere</dt><dd>{{ book.new_edition_type_elsewhere }}</dd>{% endif %}
    {% if book.new_edition_type_reference %}<dt>New edition type reference</dt><dd>{{ book.new_edition_type_reference|linebreaksbr }}</dd>{% endif %}
    {% if book.new_edition_type_else_ref %}<dt>New edition type (else ref)</dt><dd>{{ book.new_edition_type_else_ref }}</dd>{% endif %}
    {% if book.new_edition_type_notes %}<dt>New edition type notes</dt><dd>{{ book.new_edition_type_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.new_edition_type_else_note %}<dt>New edition type (else note)</dt><dd>{{ book.new_edition_type_else_note }}</dd>{% endif %}
    {% if book.expanded_in_edition %}<dt>Expanded in edition</dt><dd>{{ book.expanded_in_edition }}</dd>{% endif %}
    {% if book.contradict_new_edition %}<dt>Contradicts new edition</dt><dd>{{ book.contradict_new_edition }}</dd>{% endif %}
    {% if book.copy_of_book_used %}<dt>Copy of book used</dt><dd>{{ book.copy_of_book_used|linebreaksbr }}</dd>{% endif %}
    {% if book.examined_volume_number %}<dt>Examined volume number</dt><dd>{{ book.examined_volume_number }}</dd>{% endif %}
    {% if book.other_volumes %}<dt>Other volumes</dt><dd>{{ book.other_volumes }}</dd>{% endif %}
    {% if book.volumes_notes %}<dt>Volumes notes</dt><dd>{{ book.volumes_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.volumes_published_number %}<dt>Volumes published</dt><dd>{{ book.volumes_published_number }}</dd>{% endif %}
    {% if book.planned_volumes %}<dt>Planned volumes</dt><dd>{{ book.planned_volumes }}</dd>{% endif %}
</dl>
```

- [ ] **Step 6: Translations section**

Replace `haskala/templates/books/_sections/translations.html`:

```html
{% if book.translations.all %}
    <div class="relation-cards">
        {% for translation in book.translations.all %}
            {% include "books/_cards/translation_card.html" with translation=translation %}
        {% endfor %}
    </div>
{% endif %}

<dl class="book-fields">
    {% if book.translation_notes %}<dt>Translation notes</dt><dd>{{ book.translation_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.translation_type %}<dt>Translation type</dt><dd>{{ book.translation_type }}</dd>{% endif %}
    {% if book.expanded_in_translation %}<dt>Expanded in translation</dt><dd>{{ book.expanded_in_translation }}</dd>{% endif %}
    {% if book.presented_as_translation_refe %}<dt>Presented as translation (ref)</dt><dd>{{ book.presented_as_translation_refe|linebreaksbr }}</dd>{% endif %}
    {% if book.presented_as_translatio_notes %}<dt>Presented as translation (notes)</dt><dd>{{ book.presented_as_translatio_notes|linebreaksbr }}</dd>{% endif %}
</dl>
```

- [ ] **Step 7: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookEditionsTranslationsTest -v 2
```

Expected: PASS.

- [ ] **Step 8: Commit**

```bash
git add haskala/templates/books/_cards/edition_card.html \
        haskala/templates/books/_cards/translation_card.html \
        haskala/templates/books/_sections/editions.html \
        haskala/templates/books/_sections/translations.html \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): Editions and Translations cards + sections

Self-contained cards show year, place, translator chip and references
with HTML-truncation for long fields. The sections append the
book-level edition/translation metadata fields beneath the card list."
```

---

## Task 11: Productions, Prefaces, Mentions — cards + sections

**Files:**
- Create: `haskala/templates/books/_cards/production_card.html`
- Create: `haskala/templates/books/_cards/preface_card.html`
- Create: `haskala/templates/books/_cards/mention_card.html`
- Modify: `haskala/templates/books/_sections/productions.html`
- Modify: `haskala/templates/books/_sections/prefaces.html`
- Modify: `haskala/templates/books/_sections/mentions.html`
- Modify: `home/tests/test_book_detail.py` (add test)

- [ ] **Step 1: Failing test**

In `home/tests/test_book_detail.py`, add:

```python
from home.models import Production, Preface, Mention, ProductionRole, MentionDescription


class BookProductionsPrefacesMentionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(name="S4 Book", full_title="S4 Book")
        cls.person = Person.objects.create(pref_label="Schreiber, B.")
        cls.role = ProductionRole.objects.create(name="Printer", legacy_tid=9999)
        cls.mention_desc = MentionDescription.objects.create(name="contemporary")
        cls.city = City.objects.create(name="Pressburg")

        Production.objects.create(book=cls.book, title="Printing run",
                                  producer=cls.person, role=cls.role,
                                  name_in_book="B. Schreiber",
                                  person_name_appear="B. Schreiber")
        Preface.objects.create(book=cls.book, title="Author's note",
                               writer=cls.person, number=1,
                               notes="Welcome to the book.")
        Mention.objects.create(book=cls.book, mentionee=cls.person,
                               mentionee_city=cls.city,
                               mentionee_description=cls.mention_desc)

    def test_production_card_renders(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("Printing run", html)
        self.assertIn("Schreiber, B.", html)
        self.assertIn("Printer", html)

    def test_preface_card_renders(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("Author&#x27;s note", html)  # Django auto-escapes apostrophe
        self.assertIn("Welcome to the book.", html)

    def test_mention_card_renders(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("Schreiber, B.", html)
        self.assertIn("Pressburg", html)
        self.assertIn("contemporary", html)
```

The apostrophe escape uses the HTML named-entity form Django emits (`&#x27;`); if this assertion fails because Django emits a different form (e.g., `&#39;`), update the literal accordingly.

- [ ] **Step 2: Run the test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookProductionsPrefacesMentionsTest -v 2
```

- [ ] **Step 3: Production card**

Create `haskala/templates/books/_cards/production_card.html`:

```html
<article class="relation-card relation-card--production">
    <header class="relation-card__header">
        <h3 class="relation-card__title h6">
            {{ production.title|default:production.name_in_book|default:"Production" }}
        </h3>
        <p class="relation-card__meta text-muted small mb-0">
            {% if production.producer %}{% include "books/_cards/_person_chip.html" with person=production.producer role=None %}{% endif %}
            {% if production.role %}{% if production.producer %} · {% endif %}<span class="badge text-bg-secondary">{{ production.role }}</span>{% endif %}
        </p>
    </header>
    {% if production.name_in_book %}
        <p class="relation-card__field">
            <span class="relation-card__label">Name in book:</span> {{ production.name_in_book }}
        </p>
    {% endif %}
    {% if production.person_name_appear %}
        <p class="relation-card__field">
            <span class="relation-card__label">Person name appears as:</span> {{ production.person_name_appear }}
        </p>
    {% endif %}
</article>
```

- [ ] **Step 4: Preface card**

Create `haskala/templates/books/_cards/preface_card.html`:

```html
<article class="relation-card relation-card--preface">
    <header class="relation-card__header">
        <h3 class="relation-card__title h6">
            {{ preface.title|default:"Untitled preface" }}
        </h3>
        <p class="relation-card__meta text-muted small mb-0">
            {% if preface.writer %}{% include "books/_cards/_person_chip.html" with person=preface.writer role=None %}{% endif %}
            {% if preface.number %}{% if preface.writer %} · {% endif %}No. {{ preface.number }}{% endif %}
        </p>
    </header>
    {% if preface.notes %}
        <p class="relation-card__field">
            <span class="relation-card__label">Notes:</span>
            {{ preface.notes|linebreaksbr|truncatechars_html:600 }}
        </p>
    {% endif %}
</article>
```

- [ ] **Step 5: Mention card**

Create `haskala/templates/books/_cards/mention_card.html`:

```html
<article class="relation-card relation-card--mention">
    <header class="relation-card__header">
        <h3 class="relation-card__title h6">
            {% if mention.mentionee %}{% include "books/_cards/_person_chip.html" with person=mention.mentionee role=None %}{% else %}Mention{% endif %}
        </h3>
        <p class="relation-card__meta text-muted small mb-0">
            {% if mention.mentionee_city %}{{ mention.mentionee_city.name }}{% endif %}
            {% if mention.mentionee_description %}{% if mention.mentionee_city %} · {% endif %}<span class="badge text-bg-secondary">{{ mention.mentionee_description }}</span>{% endif %}
        </p>
    </header>
</article>
```

- [ ] **Step 6: Productions section**

Replace `haskala/templates/books/_sections/productions.html`:

```html
{% if book.productions.all %}
    <div class="relation-cards">
        {% for production in book.productions.all %}
            {% include "books/_cards/production_card.html" with production=production %}
        {% endfor %}
    </div>
{% endif %}
```

- [ ] **Step 7: Prefaces section**

Replace `haskala/templates/books/_sections/prefaces.html`:

```html
{% if book.prefaces.all %}
    <div class="relation-cards">
        {% for preface in book.prefaces.all %}
            {% include "books/_cards/preface_card.html" with preface=preface %}
        {% endfor %}
    </div>
{% endif %}
```

- [ ] **Step 8: Mentions section**

Replace `haskala/templates/books/_sections/mentions.html`:

```html
{% if book.mentions.all %}
    <div class="relation-cards">
        {% for mention in book.mentions.all %}
            {% include "books/_cards/mention_card.html" with mention=mention %}
        {% endfor %}
    </div>
{% endif %}

<dl class="book-fields">
    {% if book.mention_general_notes %}<dt>General notes</dt><dd>{{ book.mention_general_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.mentions_in_reviews %}<dt>Mentions in reviews</dt><dd>{{ book.mentions_in_reviews|linebreaksbr }}</dd>{% endif %}
    {% if book.contemporary_disputes %}<dt>Contemporary disputes</dt><dd>{{ book.contemporary_disputes|linebreaksbr }}</dd>{% endif %}
    {% if book.contemporary_references %}<dt>Contemporary references</dt><dd>{{ book.contemporary_references|linebreaksbr }}</dd>{% endif %}
    {% if book.later_references %}<dt>Later references</dt><dd>{{ book.later_references|linebreaksbr }}</dd>{% endif %}
</dl>
```

- [ ] **Step 9: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookProductionsPrefacesMentionsTest -v 2
```

Expected: PASS.

- [ ] **Step 10: Commit**

```bash
git add haskala/templates/books/_cards/production_card.html \
        haskala/templates/books/_cards/preface_card.html \
        haskala/templates/books/_cards/mention_card.html \
        haskala/templates/books/_sections/productions.html \
        haskala/templates/books/_sections/prefaces.html \
        haskala/templates/books/_sections/mentions.html \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): Productions, Prefaces, Mentions cards + sections

Production cards show producer chip and role badge with name_in_book
disambiguation. Preface cards show writer, number and clamped notes.
Mention cards show mentionee chip, city and description badge. The
Mentions section also surfaces book-level reception fields beneath
the cards."
```

---

## Task 12: Sections 12-16 — Sources, Censorship, Subscription, Availability, Record metadata

**Files:**
- Modify: `haskala/templates/books/_sections/sources.html`
- Modify: `haskala/templates/books/_sections/censorship.html`
- Modify: `haskala/templates/books/_sections/subscription.html`
- Modify: `haskala/templates/books/_sections/availability.html`
- Modify: `haskala/templates/books/_sections/record_metadata.html`
- Modify: `home/tests/test_book_detail.py` (add test)

- [ ] **Step 1: Failing test**

In `home/tests/test_book_detail.py`, add:

```python
class BookTailSectionsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.book = Book.objects.create(
            name="Tail Book",
            full_title="Tail Book",
            bibliographical_citations="Smith 2001, p. 14",
            censorship="Banned in Vienna",
            subscribers="123 listed subscribers",
            other_libraries="National Library of Israel",
            digital_book_url="https://example.org/book.pdf",
            legacy_nid=42,
        )

    def test_tail_sections_render(self):
        html = Client().get(reverse("book-detail", args=[self.book.name])).content.decode()
        self.assertIn("Smith 2001, p. 14", html)
        self.assertIn("Banned in Vienna", html)
        self.assertIn("123 listed subscribers", html)
        self.assertIn("National Library of Israel", html)
        self.assertIn("https://example.org/book.pdf", html)
        self.assertIn("42", html)
```

- [ ] **Step 2: Run test (expect failure)**

```bash
python manage.py test home.tests.test_book_detail.BookTailSectionsTest -v 2
```

- [ ] **Step 3: Sources section**

Replace `haskala/templates/books/_sections/sources.html`:

```html
<dl class="book-fields">
    {% if book.bibliographical_citations %}<dt>Bibliographical citations</dt><dd>{{ book.bibliographical_citations|linebreaksbr }}</dd>{% endif %}
    {% if book.studies %}<dt>Studies</dt><dd>{{ book.studies|linebreaksbr }}</dd>{% endif %}
    {% if book.sources_exist %}<dt>Sources exist</dt><dd>{{ book.sources_exist }}</dd>{% endif %}
    {% if book.sources_list %}<dt>Sources list</dt><dd>{{ book.sources_list|linebreaksbr }}</dd>{% endif %}
    {% if book.sources_not_mentioned %}<dt>Sources not mentioned</dt><dd>{{ book.sources_not_mentioned }}</dd>{% endif %}
    {% if book.sources_not_mentioned_list %}<dt>Sources not mentioned (list)</dt><dd>{{ book.sources_not_mentioned_list|linebreaksbr }}</dd>{% endif %}
    {% if book.sources_not_mentioned_ref %}<dt>Sources not mentioned (ref)</dt><dd>{{ book.sources_not_mentioned_ref|linebreaksbr }}</dd>{% endif %}
    {% if book.sources_references %}<dt>Sources references</dt><dd>{{ book.sources_references|linebreaksbr }}</dd>{% endif %}
    {% if book.jewish_sources_quotes %}<dt>Jewish sources / quotes</dt><dd>{{ book.jewish_sources_quotes|linebreaksbr }}</dd>{% endif %}
    {% if book.non_jewish_sources_quotes %}<dt>Non-Jewish sources / quotes</dt><dd>{{ book.non_jewish_sources_quotes|linebreaksbr }}</dd>{% endif %}
    {% if book.original_sources_mention %}<dt>Original sources mention</dt><dd>{{ book.original_sources_mention|linebreaksbr }}</dd>{% endif %}
    {% if book.references_notes %}<dt>References notes</dt><dd>{{ book.references_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.secondary_sources %}<dt>Secondary sources</dt><dd>{{ book.secondary_sources|linebreaksbr }}</dd>{% endif %}
</dl>
```

- [ ] **Step 4: Censorship section**

Replace `haskala/templates/books/_sections/censorship.html`:

```html
<dl class="book-fields">
    {% if book.censorship %}<dt>Censorship</dt><dd>{{ book.censorship|linebreaksbr }}</dd>{% endif %}
    {% if book.bans %}<dt>Bans</dt><dd>{{ book.bans|linebreaksbr }}</dd>{% endif %}
    {% if book.rabbinical_approbations %}<dt>Rabbinical approbations</dt><dd>{{ book.rabbinical_approbations|linebreaksbr }}</dd>{% endif %}
    {% if book.rabbinical_approbation_notes %}<dt>Rabbinical approbation notes</dt><dd>{{ book.rabbinical_approbation_notes|linebreaksbr }}</dd>{% endif %}
</dl>
```

- [ ] **Step 5: Subscription section**

Replace `haskala/templates/books/_sections/subscription.html`:

```html
<dl class="book-fields">
    {% if book.subscribers %}<dt>Subscribers</dt><dd>{{ book.subscribers|linebreaksbr }}</dd>{% endif %}
    {% if book.subscribers_notes %}<dt>Subscribers notes</dt><dd>{{ book.subscribers_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.subscription_appeal %}<dt>Subscription appeal</dt><dd>{{ book.subscription_appeal|linebreaksbr }}</dd>{% endif %}
    {% if book.subscription_appeal_notes %}<dt>Subscription appeal notes</dt><dd>{{ book.subscription_appeal_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.recommendations %}<dt>Recommendations</dt><dd>{{ book.recommendations|linebreaksbr }}</dd>{% endif %}
    {% if book.recommendations_notes %}<dt>Recommendations notes</dt><dd>{{ book.recommendations_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.price %}<dt>Price</dt><dd>{{ book.price }}</dd>{% endif %}
    {% if book.sellers %}<dt>Sellers</dt><dd>{{ book.sellers|linebreaksbr }}</dd>{% endif %}
    {% if book.sellers_notes %}<dt>Sellers notes</dt><dd>{{ book.sellers_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.thanks %}<dt>Thanks</dt><dd>{{ book.thanks|linebreaksbr }}</dd>{% endif %}
    {% if book.thanks_notes %}<dt>Thanks notes</dt><dd>{{ book.thanks_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.contacts_official_agents %}<dt>Contacts (official agents)</dt><dd>{{ book.contacts_official_agents|linebreaksbr }}</dd>{% endif %}
    {% if book.contacts_other_people %}<dt>Contacts (other people)</dt><dd>{{ book.contacts_other_people|linebreaksbr }}</dd>{% endif %}
    {% if book.personal_address %}<dt>Personal address</dt><dd>{{ book.personal_address|linebreaksbr }}</dd>{% endif %}
    {% if book.personal_address_notes %}<dt>Personal address notes</dt><dd>{{ book.personal_address_notes|linebreaksbr }}</dd>{% endif %}
</dl>
```

- [ ] **Step 6: Availability section**

Replace `haskala/templates/books/_sections/availability.html`:

```html
<dl class="book-fields">
    {% if book.not_available %}
        <dt>Not available</dt><dd>Yes</dd>
    {% endif %}
    {% if book.availability_notes %}<dt>Availability notes</dt><dd>{{ book.availability_notes|linebreaksbr }}</dd>{% endif %}
    {% if book.other_libraries %}<dt>Other libraries</dt><dd>{{ book.other_libraries|linebreaksbr }}</dd>{% endif %}
    {% if book.bar_ilan_library_id %}<dt>Bar-Ilan Library ID</dt><dd>{{ book.bar_ilan_library_id }}</dd>{% endif %}
    {% if book.berlin_library_id %}<dt>Berlin Library ID</dt><dd>{{ book.berlin_library_id }}</dd>{% endif %}
    {% if book.british_library_id %}<dt>British Library ID</dt><dd>{{ book.british_library_id }}</dd>{% endif %}
    {% if book.frankfurt_library_id %}<dt>Frankfurt Library ID</dt><dd>{{ book.frankfurt_library_id }}</dd>{% endif %}
    {% if book.huji_library_id %}<dt>HUJI Library ID</dt><dd>{{ book.huji_library_id }}</dd>{% endif %}
    {% if book.new_york_library_id %}<dt>New York Library ID</dt><dd>{{ book.new_york_library_id }}</dd>{% endif %}
    {% if book.tel_aviv_library_id %}<dt>Tel Aviv Library ID</dt><dd>{{ book.tel_aviv_library_id }}</dd>{% endif %}
    {% if book.digital_book_url %}
        <dt>Digital copy</dt>
        <dd>
            <a href="{{ book.digital_book_url }}" target="_blank" rel="noopener">
                {{ book.digital_book_title|default:book.digital_book_url }}
            </a>
            {% if book.digital_book_attributes %}<div class="small text-muted">{{ book.digital_book_attributes }}</div>{% endif %}
        </dd>
    {% endif %}
    {% if book.preservation_references %}<dt>Preservation references</dt><dd>{{ book.preservation_references|linebreaksbr }}</dd>{% endif %}
    {% if book.catalog_numbers_notes %}<dt>Catalog numbers notes</dt><dd>{{ book.catalog_numbers_notes|linebreaksbr }}</dd>{% endif %}
</dl>
```

- [ ] **Step 7: Record metadata section**

Replace `haskala/templates/books/_sections/record_metadata.html`:

```html
<dl class="book-fields book-fields--monospace small text-muted">
    {% if book.legacy_nid %}<dt>Legacy NID</dt><dd>{{ book.legacy_nid }}</dd>{% endif %}
    {% if book.legacy_created %}<dt>Created</dt><dd>{{ book.legacy_created|date:"Y-m-d H:i" }}</dd>{% endif %}
    {% if book.legacy_changed %}<dt>Last changed</dt><dd>{{ book.legacy_changed|date:"Y-m-d H:i" }}</dd>{% endif %}
    <dt>UUID</dt><dd>{{ book.uuid }}</dd>
</dl>
```

Note: the predicate `_record_metadata_has_data` returns True only when at least one of nid/created/changed is set, but the UUID line will always render. That is by design — the section is shown only for books with legacy data, but UUID acts as a permalink anchor when the section appears.

- [ ] **Step 8: Run the test (expect pass)**

```bash
python manage.py test home.tests.test_book_detail.BookTailSectionsTest -v 2
```

Expected: PASS.

- [ ] **Step 9: Run the full suite**

```bash
python manage.py test home.tests -v 2
```

Expected: all tests pass.

- [ ] **Step 10: Commit**

```bash
git add haskala/templates/books/_sections/sources.html \
        haskala/templates/books/_sections/censorship.html \
        haskala/templates/books/_sections/subscription.html \
        haskala/templates/books/_sections/availability.html \
        haskala/templates/books/_sections/record_metadata.html \
        home/tests/test_book_detail.py
git commit -m "feat(book-detail): tail sections (Sources..Record metadata)

Sources & References, Censorship & Approbation, Subscription &
Marketing, Availability & Catalog (including all library IDs and the
digital copy block), and Record metadata (legacy NID/created/changed
+ UUID) complete the 16-section structure."
```

---

## Task 13: SCSS partial + build

**Files:**
- Create: `haskala/static/scss/_book_detail.scss`
- Modify: `haskala/static/scss/haskala.scss`

- [ ] **Step 1: Create the SCSS partial**

Create `haskala/static/scss/_book_detail.scss`:

```scss
// Book detail page — scoped under .book-detail to avoid leakage.

.book-detail {
    // -- Header -----------------------------------------------------------
    .book-header {
        &__title {
            font-weight: 600;
        }
        &__latin {
            line-height: 1.3;
        }
        &__authors .person-chip {
            margin-right: 0.5rem;
        }
        &__actions {
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
        }
    }

    // -- TOC --------------------------------------------------------------
    .book-toc {
        font-size: 0.9rem;

        &__heading {
            letter-spacing: 0.04em;
            margin-bottom: 0.5rem;
        }
        &__list {
            margin-bottom: 0;
            padding-left: 0;
        }
        &__item {
            margin-bottom: 0.25rem;
        }
        &__link {
            display: block;
            padding: 0.25rem 0.5rem;
            border-left: 2px solid transparent;
            color: var(--bs-body-color);
            text-decoration: none;
            border-radius: 0;
            transition: background-color 0.15s, border-color 0.15s, color 0.15s;

            &:hover,
            &:focus {
                background-color: var(--bs-tertiary-bg);
                color: var(--bs-link-color);
            }

            &[aria-current="true"] {
                border-left-color: var(--bs-primary);
                color: var(--bs-primary);
                font-weight: 600;
            }
        }
    }

    .book-toc-sticky {
        position: sticky;
        top: 1.25rem;
        max-height: calc(100vh - 2rem);
        overflow-y: auto;
    }

    // -- Sections ---------------------------------------------------------
    .book-section {
        margin-bottom: 2.5rem;
        scroll-margin-top: 1rem;

        &__heading {
            margin-bottom: 1rem;
            padding-bottom: 0.5rem;
            border-bottom: 1px solid var(--bs-border-color);
        }
    }

    // -- Description-list fields -----------------------------------------
    .book-fields {
        display: grid;
        grid-template-columns: minmax(8rem, 14rem) 1fr;
        gap: 0.25rem 1rem;

        dt {
            font-weight: 600;
            color: var(--bs-secondary-color);
        }
        dd {
            margin: 0;
        }

        &--monospace dd {
            font-family: var(--bs-font-monospace);
        }

        @media (max-width: 575.98px) {
            grid-template-columns: 1fr;
            dt {
                margin-top: 0.5rem;
            }
        }
    }

    // -- Relation cards ---------------------------------------------------
    .relation-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(20rem, 1fr));
        gap: 1rem;
        margin-bottom: 1.5rem;
    }

    .relation-card {
        background: var(--bs-tertiary-bg);
        border: 1px solid var(--bs-border-color);
        border-radius: 0.5rem;
        padding: 0.875rem 1rem;

        &__header {
            margin-bottom: 0.5rem;
        }
        &__title {
            margin: 0 0 0.25rem;
        }
        &__meta {
            line-height: 1.4;
        }
        &__field {
            margin: 0.4rem 0 0;
            font-size: 0.92rem;
        }
        &__label {
            font-weight: 600;
            color: var(--bs-secondary-color);
        }
    }

    // -- Person chip ------------------------------------------------------
    .person-chip {
        display: inline-flex;
        align-items: center;
        gap: 0.25rem;
        text-decoration: none;
        color: var(--bs-link-color);

        &:hover {
            text-decoration: underline;
        }
    }

    // -- Citation modal ---------------------------------------------------
    #book-cite-modal .citation-plain {
        font-family: var(--bs-font-monospace);
        font-size: 0.92rem;
    }
}

// Print: hide TOC, action buttons, modal trigger so a print job yields a
// clean record sheet.
@media print {
    .book-toc-sticky,
    .book-header__actions,
    #book-cite-modal {
        display: none !important;
    }
}
```

- [ ] **Step 2: Include the partial in haskala.scss**

Open `haskala/static/scss/haskala.scss`. Add an import line near the other partial imports:

```scss
@import "book_detail";
```

The exact placement is at the bottom of the file's import list, alongside the existing partials.

- [ ] **Step 3: Build CSS**

```bash
npm run build:css
```

Expected: `haskala/static/css/haskala.css` regenerates without errors.

- [ ] **Step 4: Smoke render**

Start the dev server and open a book detail page in a browser:

```bash
python manage.py runserver
```

Visit `http://localhost:8000/books/<a-known-book-name>/` and verify visually:
- TOC sits in the left column on `md+` widths, content on the right.
- Section headings underline cleanly.
- Person chips have hover underline.
- Relation cards render as a responsive grid (one column on narrow, multiple on wide).

If anything looks broken, fix the SCSS and re-run `npm run build:css`. Stop the dev server before committing.

- [ ] **Step 5: Commit**

```bash
git add haskala/static/scss/_book_detail.scss \
        haskala/static/scss/haskala.scss \
        haskala/static/css/haskala.css
git commit -m "style(book-detail): SCSS for header, TOC, sections, cards

New _book_detail.scss is scoped under .book-detail to avoid leaking
into other pages, defines the grid-based description lists and the
responsive relation-card grid, and hides the TOC/actions in print."
```

---

## Task 14: book_detail.js — IntersectionObserver, copy, show-more

**Files:**
- Create: `haskala/static/js/book_detail.js`
- Modify: `haskala/static/js/app-entry.js` (add import)

- [ ] **Step 1: Inspect current app-entry.js**

```bash
cat haskala/static/js/app-entry.js
```

Note its structure so the new module's import line follows the existing convention. The build script `npm run build:js` bundles via esbuild.

- [ ] **Step 2: Create the module**

Create `haskala/static/js/book_detail.js`:

```javascript
// Book detail page: TOC active-section tracking + cite copy + show-more.

function initTOCTracking() {
    const tocLinks = document.querySelectorAll(".book-toc__link");
    if (!tocLinks.length) return;

    const linkBySlug = new Map();
    tocLinks.forEach((link) => {
        const slug = link.getAttribute("href")?.slice(1);
        if (slug) linkBySlug.set(slug, link);
    });

    const sections = Array.from(document.querySelectorAll(".book-section[id]"));
    if (!sections.length) return;

    const setActive = (slug) => {
        tocLinks.forEach((l) => l.removeAttribute("aria-current"));
        const link = linkBySlug.get(slug);
        if (link) link.setAttribute("aria-current", "true");
    };

    const observer = new IntersectionObserver(
        (entries) => {
            // Prefer the topmost intersecting section.
            const visible = entries
                .filter((e) => e.isIntersecting)
                .sort((a, b) => a.boundingClientRect.top - b.boundingClientRect.top);
            if (visible[0]) setActive(visible[0].target.id);
        },
        { rootMargin: "-20% 0px -65% 0px", threshold: 0 }
    );
    sections.forEach((s) => observer.observe(s));
}

function initCiteCopy() {
    document.body.addEventListener("click", (event) => {
        const button = event.target.closest("[data-cite-copy]");
        if (!button) return;
        const target = document.querySelector(button.dataset.citeCopy);
        const status = document.getElementById("book-cite-copy-status");
        if (!target) return;
        const text = target.innerText.trim();
        navigator.clipboard
            .writeText(text)
            .then(() => {
                if (status) status.textContent = "Citation copied to clipboard.";
            })
            .catch(() => {
                if (status) status.textContent = "Could not copy — please copy manually.";
            });
    });

    document.body.addEventListener("click", (event) => {
        const button = event.target.closest("[data-permalink]");
        if (!button) return;
        navigator.clipboard.writeText(button.dataset.permalink).catch(() => {});
    });
}

document.addEventListener("DOMContentLoaded", () => {
    initTOCTracking();
    initCiteCopy();
});
```

- [ ] **Step 3: Register in app-entry**

Append to `haskala/static/js/app-entry.js`:

```javascript
import "./book_detail.js";
```

If `app-entry.js` uses CommonJS (`require`), use that form instead. Check the existing import style.

- [ ] **Step 4: Build JS**

```bash
npm run build:js
```

Expected: `haskala/static/js/app.js` regenerates without errors.

- [ ] **Step 5: Smoke check in browser**

Start dev server, open a book detail page:
- Scroll: the TOC link for the currently visible section shows the active style (left border, primary color).
- Click "Cite" → modal opens. Click clipboard icon → status text "Citation copied to clipboard." appears. Paste somewhere to confirm.
- Click "Permalink" → URL is on the clipboard.

- [ ] **Step 6: Commit**

```bash
git add haskala/static/js/book_detail.js \
        haskala/static/js/app-entry.js \
        haskala/static/js/app.js
git commit -m "feat(book-detail): TOC active-section tracking and citation copy

book_detail.js uses IntersectionObserver to mark the currently visible
section in the TOC (aria-current=true) and registers delegated click
handlers that copy the plain citation and the page permalink via the
Clipboard API. The module is imported from app-entry.js so esbuild
bundles it into app.js."
```

---

## Task 15: Mobile offcanvas for the TOC

**Files:**
- Modify: `haskala/templates/books/book_detail_page.html` (add offcanvas trigger + offcanvas markup)
- Modify: `haskala/static/scss/_book_detail.scss` (offcanvas-only styles + floating trigger)
- Modify: `haskala/static/js/book_detail.js` (refresh link list if duplicated in offcanvas)

- [ ] **Step 1: Add offcanvas trigger and container to the template**

Open `haskala/templates/books/book_detail_page.html`. Inside `{% block content %}`, inside the outer `<div class="container book-detail my-4">`, just before the `<div class="row gx-md-5">`, add:

```html
        <button type="button"
                class="btn btn-primary book-detail__toc-trigger d-md-none"
                data-bs-toggle="offcanvas" data-bs-target="#book-toc-offcanvas"
                aria-controls="book-toc-offcanvas"
                aria-label="Open table of contents">
            <i class="bi bi-list"></i>
        </button>

        <div class="offcanvas offcanvas-start d-md-none" tabindex="-1"
             id="book-toc-offcanvas" aria-labelledby="book-toc-offcanvas-label">
            <div class="offcanvas-header">
                <h2 class="offcanvas-title h6" id="book-toc-offcanvas-label">On this page</h2>
                <button type="button" class="btn-close" data-bs-dismiss="offcanvas" aria-label="Close"></button>
            </div>
            <div class="offcanvas-body">
                {% include "books/_book_toc.html" %}
            </div>
        </div>
```

- [ ] **Step 2: Add offcanvas styles to _book_detail.scss**

Append inside the existing `.book-detail { … }` block (or just before its closing brace):

```scss
    &__toc-trigger {
        position: fixed;
        bottom: 1rem;
        right: 1rem;
        z-index: 1040;
        border-radius: 50%;
        width: 3rem;
        height: 3rem;
        padding: 0;
        display: flex;
        align-items: center;
        justify-content: center;
        box-shadow: 0 0.5rem 1rem rgba(0,0,0,0.15);
    }
```

- [ ] **Step 3: Close offcanvas when a TOC link is tapped**

Open `haskala/static/js/book_detail.js`. Inside `initTOCTracking`, after the `linkBySlug` population block, add:

```javascript
    tocLinks.forEach((link) => {
        link.addEventListener("click", () => {
            const offcanvasEl = document.getElementById("book-toc-offcanvas");
            if (!offcanvasEl) return;
            const instance = window.bootstrap?.Offcanvas.getInstance(offcanvasEl);
            instance?.hide();
        });
    });
```

This relies on Bootstrap's JS being globally available as `window.bootstrap`. Confirm in `app-entry.js` that the Bootstrap bundle is imported (it is — `bootstrap.bundle.js` is in `haskala/static/js/`).

- [ ] **Step 4: Rebuild CSS and JS**

```bash
npm run build:css
npm run build:js
```

- [ ] **Step 5: Smoke test in browser**

Resize the dev tools viewport to <768px:
- Floating round button appears bottom-right.
- Tap → offcanvas slides in from the left containing the same TOC links.
- Tap a link → page scrolls to that section and the offcanvas closes.

- [ ] **Step 6: Commit**

```bash
git add haskala/templates/books/book_detail_page.html \
        haskala/static/scss/_book_detail.scss \
        haskala/static/js/book_detail.js \
        haskala/static/css/haskala.css \
        haskala/static/js/app.js
git commit -m "feat(book-detail): mobile offcanvas TOC

Below the md breakpoint the inline TOC column is hidden and a floating
round button (bottom-right) opens a Bootstrap offcanvas containing the
same TOC partial. Tapping a link closes the offcanvas and scrolls."
```

---

## Task 16: N+1 query budget + remove obsolete partial

**Files:**
- Modify: `home/tests/test_book_detail.py` (add N+1 test)
- Delete: `haskala/templates/books/_book_metadata.html`

- [ ] **Step 1: Add the N+1 budget test**

In `home/tests/test_book_detail.py`, append:

```python
from home.models import (
    Mention, MentionDescription, Preface, Production, ProductionRole,
    Translation, Edition, BookAuthor,
)


class BookDetailQueryBudgetTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.publisher = Publisher.objects.create(name="Q Verlag")
        cls.city = City.objects.create(name="Hamburg")
        cls.book = Book.objects.create(
            name="Q Book",
            full_title="Q Book",
            gregorian_year="1850",
            publisher=cls.publisher,
            publication_place=cls.city,
        )
        for i in range(3):
            person = Person.objects.create(pref_label=f"Author {i}")
            BookAuthor.objects.create(book=cls.book, person=person, role="producer")
            Edition.objects.create(book=cls.book, name=f"Ed {i}", city=cls.city)
            Translation.objects.create(book=cls.book, title=f"Tr {i}", translator=person)
            Preface.objects.create(book=cls.book, title=f"Pf {i}", writer=person, number=i)
            role = ProductionRole.objects.create(name=f"Role {i}", legacy_tid=10000 + i)
            Production.objects.create(book=cls.book, title=f"Pr {i}", producer=person, role=role)
            Mention.objects.create(book=cls.book, mentionee=person)

    def test_query_count_under_budget(self):
        with self.assertNumQueries(self._budget()):
            Client().get(reverse("book-detail", args=[self.book.name]))

    @staticmethod
    def _budget():
        # Tune this number once after profiling; treat regressions as
        # a signal to inspect new prefetches rather than to raise the
        # budget casually. Initial budget is generous.
        return 30
```

- [ ] **Step 2: Run the test**

```bash
python manage.py test home.tests.test_book_detail.BookDetailQueryBudgetTest -v 2
```

Possible outcomes:
- **Passes** under 30: leave the budget as-is.
- **Fails** with a higher count: read the failure message to see the actual count. If the page is rendering correctly, lower the budget to `actual + 2` and commit; if the count is suspiciously high (e.g. 60+), inspect the SQL using `python manage.py shell -c "..."` with `connection.queries` to find missing prefetches, then fix.

- [ ] **Step 3: Delete the obsolete partial**

```bash
git rm haskala/templates/books/_book_metadata.html
```

Confirm with `grep -rn "_book_metadata" haskala/ home/` that no template still references it. The base detail page rewrite no longer includes it.

- [ ] **Step 4: Run the full suite**

```bash
python manage.py test home.tests -v 2
```

Expected: all tests pass.

- [ ] **Step 5: Manual smoke**

```bash
python manage.py runserver
```

Open three book detail pages with different data shapes:
- A rich book with editions, translations, productions (e.g., the one with nid linked to many relations — pick from `Book.objects.annotate(c=Count('editions')).order_by('-c').first()`).
- A sparse book with few populated fields — confirm only a few TOC entries appear.
- A book with `digital_book_url` — confirm the action bar shows the link.

- [ ] **Step 6: Commit**

```bash
git add home/tests/test_book_detail.py
git commit -m "test(book-detail): query budget + remove obsolete metadata partial

assertNumQueries guards against future prefetch regressions on the
detail view. Deletes the legacy _book_metadata.html since its
contents now live in the per-section partials."
```

---

## Verification before marking complete

- [ ] All Task commits are on `feature/model-tweaks`.
- [ ] `python manage.py test home -v 2` passes with no failures.
- [ ] `npm run build:css && npm run build:js` rebuild cleanly.
- [ ] `git status` shows a clean working tree apart from the always-untracked `research/` directories.
- [ ] Manual visual check on three representative books (rich / sparse / digital-only) confirms the page renders as designed.

---

## Self-review notes

Plan coverage against spec sections:

| Spec section | Plan task(s) |
| --- | --- |
| Header | T6 |
| TOC | T7, T15 |
| 16 sections | T8 (1-3), T9 (4-6), T10 (7-8), T11 (9-11), T12 (12-16) |
| Relation cards | T10 (Edition, Translation), T11 (Production, Preface, Mention), T6 (person chip) |
| View prefetch + visible_sections helper | T2 |
| BibTeX / RIS / Plain citation | T3 / T4 / T5 |
| SCSS partial | T13 |
| JS module | T14 |
| Mobile offcanvas | T15 |
| Tests (smoke, empty-section, N+1, citation, modal) | spread across T2–T16 |
| Remove _book_metadata.html | T16 |
| Mention→Book risk resolution | T1 |
