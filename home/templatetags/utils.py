import re

from django import template
from django.utils.text import slugify as django_slugify

register = template.Library()


# Strip stray HTML-tag annotations that crept in from the legacy
# Drupal import — e.g. ``Ez 6310<a>`` for "Ez 6310, copy a" in Berlin.
# The tag wasn't a real shelfmark suffix, so it makes the catalog
# search miss when included. We strip them both from the displayed
# label and from the URL query parameter.
_STRAY_HTML_TAG = re.compile(r'</?[a-z][a-z0-9]*\s*/?>', re.IGNORECASE)


def _strip_html_noise(value):
    if not value:
        return value
    return _STRAY_HTML_TAG.sub('', str(value)).strip()


@register.filter
def slugify(value):
    return django_slugify(value)


# Catalog URL templates for the library-side identifiers that the
# catalogue records ship with. Each value is a Python format string
# with a single {id} placeholder. Missing entries render as plain
# text (the template guards on the lookup).
#
# The URL patterns aim at each library's public discovery UI so a
# reader can immediately verify the record. They reflect the systems
# in service in 2026 and are the best public links we have today —
# corrections welcome as systems migrate.
LIBRARY_CATALOG_URLS = {
    # All shelf-mark searches go through each library's current public
    # discovery UI with a CONTAINS query. The legacy templates tried
    # `any,exact,{id}` against record-by-ID slots; the catalog field
    # actually holds signatures (e.g. "A02 MAI (MAI)") so exact-match
    # on the system ID never resolved.
    "bar_ilan": (
        "https://biu.primo.exlibrisgroup.com/discovery/search"
        "?query=any,contains,{id}"
        "&vid=972BIU_INST:972BIU"
    ),
    # StabiKat shelf-mark search — type=CallNumber returns records
    # filed under that signature instead of a free-text any-field hit.
    "berlin": (
        "https://stabikat.de/Search/Results"
        "?join=AND&lookfor0%5B%5D={id}&type0%5B%5D=CallNumber"
    ),
    "british": (
        "https://catalogue.bl.uk/nde/search"
        "?query={id}&tab=LibraryCatalog&search_scope=MyInstitution"
        "&vid=44BL_MAIN:BLL01_NDE&lang=en"
    ),
    # Frankfurt mixes URNs (urn:nbn:de:hebis:30-…) with shelf marks;
    # the URN form is handled in library_catalog_url() below so the
    # NBN resolver opens the record directly. Shelf marks go through
    # the UB Frankfurt PICA OPAC; ACT=SRCHA + IKT=8060 is the
    # signature-search index ("Signatur").
    "frankfurt": (
        "http://cbsopac.rz.uni-frankfurt.de/LNG=DU/DB=2.1/"
        "CMD?ACT=SRCHA&IKT=8060&TRM={id}"
    ),
    "huji": (
        "https://huji.primo.exlibrisgroup.com/discovery/search"
        "?query=any,contains,{id}"
        "&vid=972HUJI_INST:972HUJI_V1"
    ),
    # CLIO (Columbia) catalog. The negative f[-format] filter
    # excludes FOIA Documents that otherwise show up at the top of
    # most signature searches.
    "new_york": (
        "https://clio.columbia.edu/catalog"
        "?datasource=catalog&f%5B-format%5D%5B%5D=FOIA+Document&q={id}"
    ),
    "tel_aviv": (
        "https://tau-primo.hosted.exlibrisgroup.com/primo-explore/search"
        "?query=any,contains,{id}"
        "&tab=default_tab&search_scope=default_scope&vid=TAU"
    ),
}


# (label, attribute, lookup-key) tuples — the order they should
# appear in the public detail page. Used by the catalog_ids filter.
LIBRARY_CATALOG_FIELDS = [
    ("Bar Ilan",       "bar_ilan_library_id",   "bar_ilan"),
    ("Berlin",         "berlin_library_id",     "berlin"),
    ("British Library", "british_library_id",   "british"),
    ("Frankfurt",      "frankfurt_library_id",  "frankfurt"),
    ("HUJI",           "huji_library_id",       "huji"),
    ("New York",       "new_york_library_id",   "new_york"),
    ("Tel Aviv",       "tel_aviv_library_id",   "tel_aviv"),
]


@register.filter
def catalog_ids(book):
    """
    Yield (label, value, key) for each library catalog ID set on this
    Book. Use together with the library_catalog_url filter to render
    each ID as a link. Stray HTML-tag annotations carried over from
    the Drupal import (``Ez 6310<a>`` → ``Ez 6310``) are stripped
    from the displayed label.
    """
    for label, attr, key in LIBRARY_CATALOG_FIELDS:
        yield label, _strip_html_noise(getattr(book, attr, "")), key


@register.filter
def library_catalog_url(value, library):
    """
    Build a public discovery-UI link for a library catalog identifier.

    Usage in templates:

        {{ book.bar_ilan_library_id|library_catalog_url:"bar_ilan" }}

    Returns the URL string, or "" if the library key is unknown or
    the value is empty. Templates can compare the result to "" to
    decide whether to render an anchor or plain text.

    Special-case: Frankfurt rows whose value starts with ``urn:nbn:``
    are persistent NBN identifiers — those resolve straight to the
    record via the NBN resolver, bypassing the shelf-mark search UI.
    """
    from urllib.parse import quote_plus

    if not value:
        return ""
    raw = _strip_html_noise(value)
    if not raw:
        return ""

    # Frankfurt records that carry a Nationalbibliographie URN are
    # routed through the NBN resolver — it returns the actual record
    # without going through the search UI.
    if library == "frankfurt" and raw.lower().startswith("urn:nbn:"):
        return f"https://nbn-resolving.org/{raw}"

    pattern = LIBRARY_CATALOG_URLS.get(library)
    if not pattern:
        return ""
    return pattern.format(id=quote_plus(raw))


# ---------------------------------------------------------------------
# Header-stats join: drop zero entries before joining
# ---------------------------------------------------------------------
@register.simple_tag
def nonzero_stats(*pairs, sep=" · "):
    """Render header stats lines such as
    ``27 books · 7 editions · 0 translations · 0 born · 0 died``
    without the zero-count tail, leaving ``27 books · 7 editions``.

    Accepts an even-length argument list of alternating
    ``(count, label_template)`` pairs::

        {% nonzero_stats
            books|length "{n} book{s}"
            editions|length "{n} edition{s}"
            translations|length "{n} translation{s}"
            born|length "{n} born"
            died|length "{n} died"
        %}

    The ``label_template`` is a ``str.format``-style string with
    ``{n}`` substituted with the count and ``{s}`` substituted with
    "s" when count != 1 (English plural). Curated labels that don't
    pluralize (e.g. "born", "died") simply omit ``{s}``.

    Entries whose count is zero (or falsy) are skipped entirely so
    the join doesn't surface noise. Returns the empty string when
    no pair survives so the surrounding ``<p>`` can also be hidden
    with ``{% if %}`` if desired.
    """
    if len(pairs) % 2:
        return ""
    out = []
    for i in range(0, len(pairs), 2):
        count = pairs[i]
        try:
            n = int(count)
        except (TypeError, ValueError):
            n = 0
        if not n:
            continue
        tpl = pairs[i + 1] or "{n}"
        out.append(
            str(tpl).format(n=n, s="" if n == 1 else "s")
        )
    return sep.join(out)


# ---------------------------------------------------------------------
# Alias-name helpers — surface Wikidata-sourced + manually curated
# alternative names on the public site.
# ---------------------------------------------------------------------

# Languages shown on the index-page inline preview. Kept short on
# purpose: the long tail (Latin, Ukrainian, Lithuanian, Belarusian,
# Russian, ...) is interesting on the detail page but noisy in the
# alphabetical city list. Order matters -- output respects it.
INLINE_INDEX_LANGUAGES = ("en", "de", "he")

# Languages shown on the detail-page "Also known as" block. Order
# matters: rows render top-to-bottom in this sequence so the most
# audience-relevant translations land first. Anything else (Russian,
# Polish, Czech, Latin, ...) is intentionally hidden -- they're in
# the AliasName table for search + RDF, just not for display.
DETAIL_BLOCK_LANGUAGES = ("en", "de", "he", "yi")


def _target_primary(target):
    """Best-effort 'this is the row's main display name' string,
    used to filter the row's own name out of the alias output."""
    return (
        getattr(target, "name", None)
        or getattr(target, "pref_label", None)
        or ""
    ).strip()


@register.simple_tag
def aliases_inline(target):
    """Return a short comma-separated alias string for the gray
    "(Lwów, Lviv, ...)" suffix on index-page entries.

    Picks at most one alias per language from ``INLINE_INDEX_LANGUAGES``
    in declared order (``en``, ``de``, ``he``). Skips an entry when
    its value equals the row's own primary name -- e.g. Berlin's
    German label is "Berlin", same as the catalog name, so we
    don't surface "Berlin (Berlin, ברלין)"; just "Berlin (ברלין)".

    Prefers the ``is_preferred`` label per language; falls back to
    the first available alias when no preferred row exists."""
    if target is None or not hasattr(target, "aliases"):
        return ""
    primary_lower = _target_primary(target).lower()

    # Only consider the ``is_preferred`` row per language. If the
    # preferred label matches the catalog row's own primary name we
    # skip the whole language; we never fall back to a non-preferred
    # alias because the goal is exactly one canonical alternative per
    # language. ``preferred_by_lang`` is built fresh from the queryset
    # so duplicate ``is_preferred=True`` rows (shouldn't happen in
    # practice) collapse to the first one Django returns.
    preferred_by_lang = {}
    for alias in (
        target.aliases.all()
        .filter(language__in=INLINE_INDEX_LANGUAGES, is_preferred=True)
        .order_by("language", "value")
    ):
        preferred_by_lang.setdefault(
            alias.language, (alias.value or "").strip(),
        )

    out = []
    for lang in INLINE_INDEX_LANGUAGES:
        val = preferred_by_lang.get(lang, "")
        if val and val.lower() != primary_lower and val not in out:
            out.append(val)
    return ", ".join(out)


@register.inclusion_tag("partials/_aliases_block.html")
def aliases_block(target):
    """Render the "Also known as" section under the detail-page
    title as a flat one-line-per-language list.

    Order: ``DETAIL_BLOCK_LANGUAGES`` (en, de, he, yi). The catalog
    row's own name acts as the implicit "Default" anchor displayed
    above this block (the H1), so when one of the four languages'
    preferred label equals that primary name we skip the row to
    avoid surfacing the same spelling twice.

    Per language we emit the preferred label first followed by any
    additional aliases for that language, deduped and joined with
    commas.

    Returns ``{"rows": []}`` when no row survives so the template
    can be included unconditionally and won't render a stray empty
    <section>."""
    if target is None or not hasattr(target, "aliases"):
        return {"rows": []}
    primary = _target_primary(target)
    primary_lower = primary.lower()

    # Build per-language value lists. The queryset is ordered
    # preferred-first so by_lang[lang][0] is the canonical label
    # for that language.
    by_lang = {}
    for alias in (
        target.aliases.all()
        .filter(language__in=DETAIL_BLOCK_LANGUAGES)
        .order_by("language", "-is_preferred", "value")
    ):
        val = (alias.value or "").strip()
        if not val:
            continue
        by_lang.setdefault(alias.language, []).append(val)

    rows = []
    for lang in DETAIL_BLOCK_LANGUAGES:
        raw_values = by_lang.get(lang, [])
        if not raw_values:
            continue
        # All-or-nothing per language: if the preferred label
        # (first entry) equals the catalog row's own name, skip
        # the whole language. We don't want to surface stray
        # ``Germany`` / ``DE-BE`` aliases that Wikidata attaches
        # to Q64's English entry just because the English label
        # itself is "Berlin", same as ours.
        if raw_values[0].lower() == primary_lower:
            continue
        # Dedupe within the language, preserving preferred-first
        # order. Drop any later entry that happens to equal the
        # catalog primary too (rare but possible).
        seen, kept = set(), []
        for v in raw_values:
            if v.lower() == primary_lower or v in seen:
                continue
            seen.add(v)
            kept.append(v)
        if kept:
            rows.append({"language": lang, "values": kept})

    return {"rows": rows}
