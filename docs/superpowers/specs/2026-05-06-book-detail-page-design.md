# Book detail page — design spec

**Date:** 2026-05-06
**Status:** approved (brainstorming)
**Slice:** 1 of 7 in the frontend overhaul; subsequent slices listed under "Future work".

## Goal

Rebuild the Book detail page so the full bibliographic record imported from the legacy Drupal database is visible in one organized, scannable view, suitable for academic researchers. The current template surfaces ~15-20 of the Book model's ~150 fields and shows none of the recently imported relation types (Editions, Translations, Productions, Prefaces, Mentions, BookAuthor with role).

## Audience

Academic researchers. Optimize for:

- bibliographic completeness over visual minimalism;
- machine-readable citation output (BibTeX, RIS) plus a copyable plain string;
- fast jumping across sections of a long record (sticky table of contents);
- traceability back to the Drupal source (record metadata section with legacy IDs).

## Non-goals (this slice)

- Dedicated detail pages for Edition, Translation, Production, Preface, Mention — those are a separate slice. Relation cards on the Book page must therefore be self-contained.
- Listing-page redesign (Books, Persons, Topics, etc.) — separate slice.
- Search/results UI — separate slice.
- Internationalisation of UI labels (current EN-only behavior continues).
- Print-perfect typography beyond a usable citation print.

## Page architecture

Long single-page layout with a sticky left-hand TOC and a right-hand content column. Sections are ordered from essential (identity, authorship, publication) toward specialised (reception, sources, availability, record metadata). Empty sections are omitted from both the TOC and the content; within a rendered section, empty individual fields are omitted (current behavior preserved).

### Header (always visible at top of page)

- Breadcrumb: Home → Books → [Book name]
- H1: `book.full_title` or fallback `book.name`
- Subline (small italics): `book.title_in_latin_characters`
- Author chips: one chip per BookAuthor, ordered by role (old_text_author, original_text_author, producer); each chip links to the Person detail page and shows the role label
- Publication line: place · publisher · year (concise, comma-separated)
- Action bar: "View digital copy" (if `digital_book_url`), "Cite", "Permalink"

### TOC (sticky sidebar)

- Renders only sections that have at least one populated field or non-empty relation.
- Active section highlights via `IntersectionObserver` while the user scrolls.
- Mobile (`< md` breakpoint): TOC becomes a Bootstrap offcanvas triggered by a floating button anchored bottom-right; clicking an entry scrolls to the section and closes the offcanvas.

### Section list (in render order)

1. **Identity & Titles** — name forms, motto, subtitle, old_name_in_book, other_books_names, original_text_name, original_title (+ `*_else_refer`, `*_elsewhere`, `*_other_name`), presented_as_original / presented_as_translation / presented_new_edition flag fields.
2. **Authors & Persons** — `BookAuthor` cards (grouped by role) using `_person_chip.html`; free-text `original_author` and its variants; founders, proofreaders.
3. **Publication** — publisher, original_publisher, publication_place(_other), gregorian_year, year_in_book, year_in_other, hebrew_year_of_publication and its `_pub_other` companion, gregorian_year_pub_other, format_of_publication_date, partial_publication, printed_originally, original_publication_place/year, printers, printing_press_notes, printing_press_references, production_evidence, series + series_part.
4. **Physical & Typography** — pages_number, height, width, fonts, typography, illustrations_diagrams, diagrams_notes, diagrams_book_pages, alignment.
5. **Language & Footnotes** — languages, languages_number, footnote_languages, occasional_words_languages, location_of_footnotes, original_language.
6. **Content & Structure** — topic, target_audience, target_audience_notes, target_general_notes, main_textual_models, secondary_textual_models, textual_model_notes, original_type, structure_notes, structure_preface_notes, table_of_content, contents_table_notes, preface, epilogue, epilogue_notes, dedications, dedications_notes.
7. **Editions** — Edition cards + Book-level edition fields (total_number_of_editions, last_known_edition, editions_notes, references_for_editions, new_edition_general_notes, new_edition_type_* family, expanded_in_edition, contradict_new_edition, copy_of_book_used, examined_volume_number, other_volumes, volumes_notes, volumes_published_number, planned_volumes).
8. **Translations** — Translation cards + Book-level translation fields (translation_notes, translation_type, expanded_in_translation, presented_as_translation*, presented_as_original*).
9. **Productions** — Production cards (printers, typesetters, dedicators etc., with role from `ProductionRole`/Occupation).
10. **Prefaces** — Preface cards (writer chip, title, notes preview, number).
11. **Mentions & Reception** — Mention cards (mentionee chip, mentionee_city, mentionee_description) + mention_general_notes, mentions_in_reviews, contemporary_disputes, contemporary_references, later_references.
12. **Sources & References** — bibliographical_citations, studies, sources_exist, sources_list, sources_not_mentioned (+ `_list`, `_ref`), sources_references, jewish_sources_quotes, non_jewish_sources_quotes, original_sources_mention, references_notes, secondary_sources.
13. **Censorship & Approbation** — censorship, bans, rabbinical_approbations, rabbinical_approbation_notes.
14. **Subscription & Marketing** — subscribers, subscribers_notes, subscription_appeal, subscription_appeal_notes, recommendations, recommendations_notes, price, sellers, sellers_notes, thanks, thanks_notes, contacts_official_agents, contacts_other_people, personal_address, personal_address_notes.
15. **Availability & Catalog** — not_available, availability_notes, other_libraries, library identifiers (Bar-Ilan, Berlin, British, Frankfurt, HUJI, New York, Tel Aviv), digital_book_url, digital_book_title, digital_book_attributes, preservation_references, catalog_numbers_notes.
16. **Record metadata** — legacy_nid, legacy_created, legacy_changed; rendered in a small monospace block at the bottom for citation traceability.

### Relation card design

Cards are self-contained: every field on the related model is shown inline. No links are added to non-existent detail pages in this slice; when those pages are built in a follow-up slice, a "View full record" link is added.

- **Edition card** — name/title, edition_year, city (chip with link to City detail), references, references_format, changes (collapsible if long).
- **Translation card** — title, translator (Person chip), city, language, references, year.
- **Production card** — title or name_in_book, producer (Person chip), role badge, person_name_appear.
- **Preface card** — title, writer (Person chip), number, notes preview (truncate at ~200 chars, expand on click).
- **Mention card** — mentionee (Person chip), mentionee_city, mentionee_description.

Long free-text values are clamped to ~6 lines with a "Show more / Show less" toggle (CSS `-webkit-line-clamp` plus a small JS toggle).

## File layout

```
haskala/templates/books/
  book_detail_page.html        rewritten outer template
  _book_header.html            hero
  _book_toc.html               sidebar TOC
  _book_cite_modal.html        cite modal
  _sections/
    identity.html              one partial per section, all 16
    authors.html
    publication.html
    physical.html
    languages.html
    content_structure.html
    editions.html
    translations.html
    productions.html
    prefaces.html
    mentions.html
    sources.html
    censorship.html
    subscription.html
    availability.html
    record_metadata.html
  _cards/
    edition_card.html
    translation_card.html
    production_card.html
    preface_card.html
    mention_card.html
    _person_chip.html
  cite/
    bibtex.txt
    ris.txt
    plain.html
```

Existing `_book_metadata.html` is removed; its content moves into the new section partials.

## View layer

### Detail view

Update `book_detail_view` in `home/views.py` to prefetch all relations needed by the template in one pass, removing the current N+1:

```python
book = get_object_or_404(
    Book.objects.select_related(
        "publisher", "original_publisher",
        "publication_place", "publication_place_other",
        "original_publication_place",
        "topic", "series", "alignment", "original_type",
        "location_of_footnotes", "format_of_publication_date",
        "languages_number", "original_language",
    ).prefetch_related(
        Prefetch("bookauthor_set",
                 queryset=BookAuthor.objects.select_related("person")),
        Prefetch("editions",
                 queryset=Edition.objects.select_related("city")
                                          .order_by("edition_year")),
        Prefetch("translations",
                 queryset=Translation.objects.select_related(
                     "translator", "city", "language")),
        Prefetch("prefaces",
                 queryset=Preface.objects.select_related("writer")
                                          .order_by("number")),
        Prefetch("productions",
                 queryset=Production.objects.select_related(
                     "producer", "role")),
        "main_textual_models", "secondary_textual_models",
        "languages", "footnote_languages", "occasional_words_languages",
        "fonts", "typography", "target_audience",
    ),
    name=title,
)
```

Mentions need clarification before implementation: the current `Mention` model has no FK to Book. Either (a) backlink via the Drupal `field_data_field_book.csv`-derived store already used by importers, or (b) add an FK during this slice. The plan step for Mentions will start with a 10-minute investigation and decide; for now the template renders an empty Mentions section if no source is wired.

### Citation views

Two new URLs and views in `home/urls.py` / `home/views.py`:

- `/books/<slug:title>/cite.bib` → `book_cite_bibtex(request, title)` → renders `cite/bibtex.txt` with `Content-Type: text/x-bibtex; charset=utf-8` and a `Content-Disposition: attachment` filename.
- `/books/<slug:title>/cite.ris` → `book_cite_ris(request, title)` → renders `cite/ris.txt` with `Content-Type: application/x-research-info-systems`.

Plain citation is rendered inline in the cite modal via `cite/plain.html`; copy-to-clipboard happens client-side.

Citation key derivation: `<first author surname or "Anon"><year>` lower-snake-cased, e.g. `pemberton1797`. Year prefers `gregorian_year`, then `year_in_book`, else `n.d.`.

### TOC data helper

A view-level helper `_visible_sections(book)` returns the ordered list of section names that have at least one rendered field or relation, used by both the TOC partial and the content area to skip empty sections without duplicating predicate logic in two templates.

## CSS / SCSS

- New partial `haskala/static/scss/_book_detail.scss`, included from `haskala.scss`. Owns: hero spacing, TOC sticky positioning, active-link styles, card styles, line-clamp utility, print rules for citation.
- No changes to `_overrides.scss` (foundation refactor is a separate slice). Keep additions scoped to the new partial so the future SCSS refactor can absorb them cleanly.

## JS

- New small module `haskala/static/js/book_detail.js`, bundled via `esbuild` into `app.js` through `app-entry.js`. Responsibilities:
  - `IntersectionObserver` over rendered section IDs, updates `aria-current="true"` on the matching TOC anchor.
  - Citation modal: copy button uses `navigator.clipboard.writeText`; success feedback via aria-live region.
  - "Show more / Show less" toggle for clamped free-text blocks (single delegated click handler).
- Smooth scroll uses CSS `scroll-behavior: smooth` on `html`; no JS for that.

## Tests

In `home/tests/test_book_detail.py` (new file):

- `test_renders_for_sample_book` — fixture book with author + edition + translation; assert HTTP 200, presence of expected section IDs, person chip text.
- `test_hides_empty_sections` — sparse book; assert absent section IDs are not in HTML.
- `test_n_plus_one_under_budget` — `assertNumQueries(<=12)` for the detail view (number to be tuned during implementation; the assertion's purpose is to catch regressions).
- `test_bibtex_export` — endpoint returns 200, body contains `@book{` and required fields (`author`, `title`, `year`).
- `test_ris_export` — endpoint returns 200, body contains `TY  - BOOK` and `ER  -` terminator.
- `test_plain_citation_in_modal` — detail page HTML contains a copyable plain citation block.

## Risks and open items

1. **Mention → Book linkage.** Not currently expressed in the data model as a direct FK. Implementation must resolve this in step one; spec assumes a backlink store similar to other relation imports is feasible. Acceptable fallback: ship the Mentions section empty in this slice and surface it in a follow-up slice once linkage is added.
2. **Person chip ordering across multiple BookAuthor roles.** A person may appear in two roles for the same book in principle; UI shows them once per role chip — deduplication is intentional only within a role.
3. **Citation key uniqueness.** Authorless or anonymous books collide on `anonNNNN`. Acceptable for citation suggestions; downstream tooling can disambiguate.
4. **Permalink button.** Currently uses the existing slug-based URL; if the slugify rule changes (e.g. for series), the URL may diverge. No mitigation in this slice — flagged for a future slugging review.

## Future work (not in this slice)

- Detail pages for Edition / Translation / Production / Preface / Mention; once available, add "View full record" links to the cards on this page.
- SCSS foundation refactor (slice 2 originally numbered 1 in the decomposition discussion).
- Listing pages (Books filter/sort, then Persons / Topics / etc.).
- Search & results UI.
- Mobile + accessibility audit across all surfaces.
- CSS/JS payload reduction.
