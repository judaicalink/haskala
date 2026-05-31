# Detail pages

Books, persons and places have the longest detail pages. They follow
the same anatomy.

## Hero

The top of every detail page carries:

- A breadcrumb back to the matching list view.
- The record's primary title or name as an `<h1>`.
- Alternative or transliterated forms (Latin script for Hebrew titles,
  alternative German/Hebrew names for persons).
- A short statistics line (book counts on places, lifespan on persons).
- Action buttons — at minimum a **Permalink** copy, and on books also
  **Cite** and (if available) **View digital copy**.

## Table of contents

The second column on desktop is a sticky TOC that lists only the
sections with actual data for this record. Empty sections are hidden,
not greyed out — the page mentions only what is known.

On mobile the TOC moves to a floating **Sections** button at the
bottom-left that opens a side drawer.

## Sections

Each section corresponds to a coherent slice of the record:

### Book sections

| Section                       | What it shows                                                           |
| ----------------------------- | ----------------------------------------------------------------------- |
| Identity & Titles             | Full title, Latin transliteration, motto, original-title variants       |
| Authors & Persons             | BookAuthors with their roles, plus free-text author / founder fields    |
| Publication                   | Publisher, place, Gregorian/Hebrew year, series and series part         |
| Physical & Typography         | Pages, height/width, fonts, typography, illustrations                   |
| Language & Footnotes          | Main, original, footnote, occasional-words languages; footnote location |
| Content & Structure           | Topic, target audience, textual models, table of contents, preface     |
| Editions                      | Known editions and edition-level notes                                  |
| Translations                  | Known translations into other languages                                 |
| Productions                   | Producers (printers, type-setters, etc.) and their roles                |
| Prefaces                      | Listed prefaces with their writers                                      |
| Mentions & Reception          | Mentions of this book in reviews, disputes, later references            |
| Sources & References          | Bibliographical citations, studies, source lists                        |
| Censorship & Approbation      | Censorship records, bans, rabbinical approbations                       |
| Subscription & Marketing      | Subscribers, sellers, prices, contacts                                  |
| Availability & Catalog        | Holding libraries, digital copy URL, catalog IDs                        |
| Record metadata               | Provenance from the previous-system import                              |

### Person sections

Identity & Names, Life (birth/death dates + places), Works & Roles
(books grouped by `BookAuthor.role`), Prefaces, Productions, Mentions,
Identifiers (VIAF), Record metadata.

### Place sections

Books published here, Editions printed here, Translations from here,
People born here, People died here, Mentions in this city, Record
metadata. Places also carry an embedded Leaflet map in the hero.

## Linking

Every record links to its neighbours. Click an author chip in a book
header to open the person; click a place name in a Publication or
Born-here section to open the place. The TOC on the destination page
adapts to which sections have data for that record.
