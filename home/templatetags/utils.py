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
    "bar_ilan": (
        "https://biu.primo.exlibrisgroup.com/discovery/search"
        "?vid=972BIU_VU1&query=any,exact,{id}"
    ),
    "berlin": "https://stabikat.de/Record/{id}",
    "british": (
        "https://bll01.primo.exlibrisgroup.com/discovery/search"
        "?vid=44BL_INST:BLL01&query=any,exact,{id}"
    ),
    "frankfurt": "https://hds.hebis.de/ubffm/Record/{id}",
    "huji": (
        "https://huji.primo.exlibrisgroup.com/discovery/search"
        "?vid=972HUJI_MAIN_VU2&query=any,exact,{id}"
    ),
    "new_york": (
        "https://search.library.columbia.edu/catalog?q={id}"
    ),
    "tel_aviv": (
        "https://tau-primo.hosted.exlibrisgroup.com/primo-explore/search"
        "?vid=TAU&query=any,exact,{id}"
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
    """
    if not value:
        return ""
    pattern = LIBRARY_CATALOG_URLS.get(library)
    if not pattern:
        return ""
    return pattern.format(id=value)
