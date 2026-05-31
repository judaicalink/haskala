# Citations

Every book detail page exposes three citation formats.

## Plain citation

The **Cite** button opens a modal whose first line is a ready-to-copy
human-readable citation. The format is:

```
<author>. (<year>). <Title> (Latin: <transliterated title>). <City>: <Publisher>.
```

Each optional component is dropped when the dataset has no value for
it. A small clipboard button copies the citation to your clipboard.

## BibTeX

The **BibTeX** download in the same modal returns a `.bib` file
containing one `@book` entry. The citation key is built from the
first author's surname plus the publication year, lower-cased and
stripped to ASCII characters; collisions are accepted and your
reference manager can disambiguate them.

```bibtex
@book{mendelssohn1783,
  title     = {{Phädon}},
  author    = {Mendelssohn, Moses},
  year      = {1783},
  publisher = {{Voß}},
  address   = {{Berlin}},
}
```

Curly braces and backslashes in titles and author names are escaped so
that the entry parses cleanly in BibTeX-aware tools.

## RIS

The **RIS** download returns a `.ris` file in [Research Information
Systems](https://en.wikipedia.org/wiki/RIS_(file_format)) format —
useful for Zotero, EndNote, Mendeley and similar tools:

```
TY  - BOOK
TI  - Phädon
AU  - Mendelssohn, Moses
PY  - 1783
PB  - Voß
CY  - Berlin
LA  - German
ER  -
```

Each multi-valued field (authors, languages) appears on its own line.
Embedded newlines in source data are flattened so the record remains
syntactically valid for downstream parsers.

## Programmatic access

The same data is available as RDF (Turtle) at
`http://data.judaicalink.org/data/haskala/`. See the
[RDF export developer doc](../developers/rdf-export.md) for the
ontology shape.
