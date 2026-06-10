from django import template
from django.utils.text import slugify as django_slugify

register = template.Library()


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
        "&tab=Everything&search_scope=MyInst_and_CI&vid=972BIU_VU1"
    ),
    "berlin": "https://stabikat.de/Search/Results?lookfor={id}&type=AllFields",
    "british": (
        "https://bll01.primo.exlibrisgroup.com/discovery/search"
        "?query=any,contains,{id}"
        "&tab=Everything&search_scope=Not_BL_Suppress&vid=44BL_INST:BLL01"
    ),
    # Frankfurt mixes URNs (urn:nbn:de:hebis:30-…) with shelf marks;
    # the URN form is handled in library_catalog_url() below so the
    # NBN resolver opens the record directly.
    "frankfurt": "https://hds.hebis.de/ubffm/Search/Results?lookfor={id}&type=AllFields",
    "huji": (
        "https://huji.primo.exlibrisgroup.com/discovery/search"
        "?query=any,contains,{id}"
        "&tab=Everything&search_scope=MyInst_and_CI&vid=972HUJI_MAIN_VU2"
    ),
    "new_york": "https://search.library.columbia.edu/catalog?q={id}",
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
    each ID as a link.
    """
    for label, attr, key in LIBRARY_CATALOG_FIELDS:
        yield label, getattr(book, attr, ""), key


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
    raw = str(value).strip()

    # Frankfurt records that carry a Nationalbibliographie URN are
    # routed through the NBN resolver — it returns the actual record
    # without going through the search UI.
    if library == "frankfurt" and raw.lower().startswith("urn:nbn:"):
        return f"https://nbn-resolving.org/{raw}"

    pattern = LIBRARY_CATALOG_URLS.get(library)
    if not pattern:
        return ""
    return pattern.format(id=quote_plus(raw))
