# views.py
import json
import secrets
from collections import defaultdict

from django.db.models import Prefetch, Q
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.template.loader import render_to_string
from django.utils.text import slugify
from django.views.decorators.cache import cache_page
from django.views.decorators.vary import vary_on_headers
from requests import Response
from rest_framework.decorators import api_view

from .book_detail import visible_sections, citation_key
from .person_detail import visible_sections as person_visible_sections
from .place_detail import visible_sections as place_visible_sections
from .models import Book, Person, Geolocation, City, Edition, Translation, Mention, Language, Occupation, Topic, \
    Publisher, BookAuthor, Preface, Production, Series
from .serializers import BookSerializer, PersonSerializer, CitySerializer


def _negotiate_rdf_response(request, obj):
    """
    If the request's Accept header asks for an RDF mime type, return
    the serialized graph directly. Otherwise return None so the view
    falls back to the HTML template.
    """
    from haskala_rdf.entity import ACCEPT_TO_FORMAT, serialize_entity

    accept = request.headers.get("Accept", "")
    if not accept:
        return None
    # Walk the Accept header in declaration order; the first RDF type
    # found wins. text/html and */* short-circuit to HTML.
    for chunk in accept.split(","):
        mime = chunk.split(";", 1)[0].strip().lower()
        if mime in ("text/html", "application/xhtml+xml", "*/*", ""):
            return None
        if mime in ACCEPT_TO_FORMAT:
            fmt = ACCEPT_TO_FORMAT[mime]
            body, served_mime = serialize_entity(obj, fmt)
            response = HttpResponse(body, content_type=f"{served_mime}; charset=utf-8")
            response["Vary"] = "Accept"
            return response
    return None


@cache_page(60 * 60)  # cache for 1 hour
@vary_on_headers("Accept")
def book_detail_view(request, slug):
    book = get_object_or_404(
        Book.objects.filter(live=True).select_related(
            "publisher", "original_publisher",
            "publication_place", "publication_place_other",
            "original_publication_place",
            "topic", "series", "alignment", "original_type",
            "location_of_footnotes", "format_of_publication_date",
            "languages_number", "original_language",
            "translation_type",
        ).prefetch_related(
            Prefetch(
                "bookauthor_set",
                queryset=BookAuthor.objects.select_related("person"),
            ),
            Prefetch(
                "editions",
                queryset=Edition.objects.select_related("city").order_by("year"),
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
        slug=slug,
    )

    rdf_response = _negotiate_rdf_response(request, book)
    if rdf_response is not None:
        return rdf_response

    return render(request, "books/book_detail_page.html", {
        "book": book,
        "visible_sections": visible_sections(book),
    })


@cache_page(60 * 60)
def books_list_view(request):
    """
    Lists all books alphabetically grouped by the first letter of the name.
    """
    # Fetch all books, ideally sorted by name
    books = Book.objects.filter(live=True).order_by("name")

    # Group by first letter
    grouped = defaultdict(list)
    for book in books:
        name = (book.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(book)

    # Sort dictionary by letter
    books_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    hebrew_alphabet = list("אבגדהוזחטיכלמנסעפצקרשת")

    context = {
        "alphabet": alphabet,
        "hebrew_alphabet": hebrew_alphabet,
        "books_by_letter": books_by_letter,
        "total_count": sum(len(v) for v in books_by_letter.values()),
    }

    return render(request, "books/books_page.html", context)


@cache_page(60 * 60)
def digital_books_list_view(request):
    """
    Lists all books that have a valid digital URL,
    alphabetically grouped by the first letter.
    """

    # Only books with a non-empty http/https URL
    books_qs = (
        Book.objects
        .filter(live=True, digital_book_url__isnull=False)
        .exclude(digital_book_url='')
        .filter(digital_book_url__regex=r'^https?://')
        .order_by("name")
    )

    grouped = defaultdict(list)
    for book in books_qs:
        name = (book.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(book)

    books_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    hebrew_alphabet = list("אבגדהוזחטיכלמנסעפצקרשת")

    context = {
        "alphabet": alphabet,
        "hebrew_alphabet": hebrew_alphabet,
        "books_by_letter": books_by_letter,
        "total_count": sum(len(v) for v in books_by_letter.values()),
    }

    return render(request, "digital-books/digital_books_page.html", context)


def persons_list_view(request):
    """
    Lists all persons alphabetically, grouped by first letter
    of the display name (pref_label / german_name / hebrew_name).
    """
    persons_qs = Person.objects.filter(live=True).order_by("pref_label", "german_name", "hebrew_name")

    grouped = defaultdict(list)
    for person in persons_qs:
        name = str(person).strip()  # __str__ uses pref_label/german/hebrew name
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(person)

    persons_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    hebrew_alphabet = list("אבגדהוזחטיכלמנסעפצקרשת")

    context = {
        "alphabet": alphabet,
        "hebrew_alphabet": hebrew_alphabet,
        "persons_by_letter": persons_by_letter,
        "total_count": sum(len(v) for v in persons_by_letter.values()),
    }
    return render(request, "persons/persons_page.html", context)


@cache_page(60 * 60)
@vary_on_headers("Accept")
def person_detail_view(request, slug):
    """
    Detail view of a person, identified by slug.
    """
    person = (
        Person.objects
        .select_related("gender", "place_of_birth", "place_of_death")
        .prefetch_related("occupations")
        .filter(slug=slug, live=True)
        .first()
    )
    if person is None:
        raise Http404("Person not found")

    books_by_role: dict[str, list[Book]] = defaultdict(list)
    for ba in (
        BookAuthor.objects
        .filter(person=person)
        .select_related("book")
        .order_by("role", "book__name")
    ):
        if not ba.book:
            continue
        books_by_role[ba.get_role_display()].append(ba.book)

    prefaces = (
        Preface.objects
        .filter(writer=person)
        .select_related("book")
        .order_by("book__name")
    )
    productions = (
        Production.objects
        .filter(producer=person)
        .select_related("book", "role")
        .order_by("book__name")
    )
    mentions = (
        Mention.objects
        .filter(mentionee=person)
        .select_related("book", "mentionee_city", "mentionee_description")
        .order_by("mentionee_city__name")
    )

    rdf_response = _negotiate_rdf_response(request, person)
    if rdf_response is not None:
        return rdf_response

    context = {
        "person": person,
        "visible_sections": person_visible_sections(person),
        "person_books_by_role": dict(books_by_role),
        "prefaces_by_person": prefaces,
        "productions_by_person": productions,
        "mentions_of_person": mentions,
    }

    return render(request, "persons/person_detail_page.html", context)


@cache_page(60 * 60)
def places_list_view(request):
    """
    Overview of all cities with alphabet list and Leaflet map.
    """
    # Alphabet (Latin + Hebrew) - same as in the PlacesPage model
    alphabet = list('ABCDEFGHIJKLMNOPQRSTUVWXYZ')
    hebrew_alphabet = list('אבגדהוזחטיכלמנסעפצקרשת')

    # Group cities alphabetically
    grouped = defaultdict(list)
    cities_qs = City.objects.filter(live=True).order_by("name")

    for city in cities_qs:
        name = (city.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(city)

    cities_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    # Leaflet markers from Geolocation
    geos = (
        Geolocation.objects
        .exclude(lat__isnull=True)
        .exclude(lng__isnull=True)
        .select_related("city")
    )

    markers = []
    for geo in geos:
        if geo.lat is None or geo.lng is None:
            continue
        city_name = geo.city.name
        markers.append({
            "lat": geo.lat,
            "lng": geo.lng,
            "name": city_name,
            # URL based on the old /cities/<slug> pattern
            "url": f"/places/{slugify(city_name)}/",
        })

    context = {
        "alphabet": alphabet,
        "hebrew_alphabet": hebrew_alphabet,
        "cities_by_letter": cities_by_letter,
        "city_markers_json": json.dumps(markers),
        "nonce": secrets.token_hex(16),
        "total_count": sum(len(v) for v in cities_by_letter.values()),
    }
    return render(request, "places/places_page.html", context)


@cache_page(60 * 60)
@vary_on_headers("Accept")
def place_detail_view(request, slug):
    """
    Detail view of a city, addressed by slug.
    """
    city = get_object_or_404(City, slug=slug, live=True)

    geolocation = Geolocation.objects.filter(city=city).first()

    books_published_here = (
        Book.objects.filter(live=True)
        .filter(
            Q(publication_place=city)
            | Q(publication_place_other=city)
            | Q(original_publication_place=city)
        )
        .order_by("gregorian_year", "name")
        .distinct()
    )

    editions_here = (
        Edition.objects.filter(city=city)
        .select_related("book")
        .order_by("year")
        .distinct()
    )
    translations_here = (
        Translation.objects.filter(city=city)
        .select_related("book", "language")
        .order_by("year")
        .distinct()
    )

    mentions_here = (
        Mention.objects.filter(mentionee_city=city)
        .select_related("book", "mentionee", "mentionee_description")
        .order_by("mentionee__pref_label")
    )

    born_here = city.born_here.filter(live=True).order_by("pref_label")
    died_here = city.died_here.filter(live=True).order_by("pref_label")

    context = {
        "city": city,
        "geolocation": geolocation,
        "books_published_here": books_published_here,
        "editions_here": editions_here,
        "translations_here": translations_here,
        "mentions_here": mentions_here,
        "born_here": born_here,
        "died_here": died_here,
        "nonce": secrets.token_hex(16),
    }
    context["visible_sections"] = place_visible_sections(context)

    rdf_response = _negotiate_rdf_response(request, city)
    if rdf_response is not None:
        return rdf_response

    return render(request, "places/place_detail_page.html", context)


# Field names skipped by the introspective search helper. Slug / uuid
# / id wouldn't surface a meaningful free-text hit; ``legacy_language``
# is a 2-3 letter code that matches everything; the Drupal-6 importer
# also dropped ``*_format`` sister columns for every editable text
# field which only ever carry the value ``"filtered_html"`` / ``"php"``.
_SEARCH_SKIP_FIELDS = {"slug", "uuid", "id", "legacy_language"}


def _text_field_q(q, model_cls, extra_paths=()):
    """Build an OR'd ``Q`` that searches every TextField / CharField on
    *model_cls* with ``__icontains``. *extra_paths* gets the same
    treatment and is meant for related-model traversals
    (e.g. ``authors__pref_label`` on Book)."""
    q_obj = Q()
    for f in model_cls._meta.fields:
        if f.get_internal_type() not in ("TextField", "CharField"):
            continue
        if f.name in _SEARCH_SKIP_FIELDS or f.name.endswith("_format"):
            continue
        q_obj |= Q(**{f"{f.name}__icontains": q})
    for path in extra_paths:
        q_obj |= Q(**{f"{path}__icontains": q})
    return q_obj


@cache_page(60 * 5)
def search_view(request):
    """
    Simple + advanced search over books, persons and places
    with facets (count per type).
    """

    q = (request.GET.get("q") or "").strip()
    result_type = request.GET.get("type", "all")  # all | books | people | places

    year_from = (request.GET.get("year_from") or "").strip()
    year_to = (request.GET.get("year_to") or "").strip()
    language_id = (request.GET.get("language") or "").strip()
    place_id = (request.GET.get("place") or "").strip()
    has_digital = (request.GET.get("has_digital") or "").strip()  # "", "yes", "no"

    # --- Base querysets -----------------------------------------------------
    books_qs = (
        Book.objects.filter(live=True)
        .select_related("publication_place", "publisher")
        .prefetch_related("languages", "authors")
    )
    persons_qs = (
        Person.objects.filter(live=True)
        .select_related("place_of_birth", "place_of_death")
        .prefetch_related("occupations")
    )
    places_qs = City.objects.filter(live=True)

    # --- Full-text query ----------------------------------------------------
    # The query runs an OR'd icontains across every TextField /
    # CharField on Book, Person, and City — built by introspection so
    # the search stays exhaustive as new columns are added to the
    # models. ``_text_field_q`` skips the Drupal-6 ``*_format`` sister
    # columns, primary keys, slug fields, and ``legacy_language``
    # tokens; Book also gets the author M2M traversal paths.
    if q:
        books_qs = books_qs.filter(
            _text_field_q(q, Book, extra_paths=(
                "authors__pref_label",
                "authors__german_name",
                "authors__hebrew_name",
            ))
        ).distinct()

        persons_qs = persons_qs.filter(_text_field_q(q, Person)).distinct()

        places_qs = places_qs.filter(_text_field_q(q, City))

    # --- Advanced filters for books only ------------------------------------
    # Year range (gregorian_year)
    if year_from:
        try:
            yf = int(year_from)
            books_qs = books_qs.filter(gregorian_year__gte=yf)
        except ValueError:
            pass

    if year_to:
        try:
            yt = int(year_to)
            books_qs = books_qs.filter(gregorian_year__lte=yt)
        except ValueError:
            pass

    # Language
    if language_id:
        try:
            lang_pk = int(language_id)
            books_qs = books_qs.filter(languages__pk=lang_pk)
        except ValueError:
            pass

    # Place (publication place)
    if place_id:
        try:
            c_pk = int(place_id)
            books_qs = books_qs.filter(
                Q(publication_place__pk=c_pk)
                | Q(publication_place_other__pk=c_pk)
                | Q(original_publication_place__pk=c_pk)
            )
        except ValueError:
            pass

    # Digital link present / not present
    if has_digital == "yes":
        books_qs = books_qs.filter(digital_book_url__regex=r"^https?://")
    elif has_digital == "no":
        books_qs = books_qs.exclude(digital_book_url__regex=r"^https?://")

    # --- Facets (counts per type) -------------------------------------------
    facet_books_count = books_qs.count()
    facet_persons_count = persons_qs.count()
    facet_places_count = places_qs.count()

    # --- Which type should be visible in the result list? -------------------
    # An empty query with no filters returns no results — the index pages
    # already exist for "browse everything" and dumping every Book +
    # Person + City into the search view confused users into thinking
    # the search was broken.
    has_search = bool(q or year_from or year_to or language_id or place_id or has_digital)

    if not has_search:
        books = Book.objects.none()
        persons = Person.objects.none()
        places = City.objects.none()
    elif result_type == "books":
        books = books_qs
        persons = Person.objects.none()
        places = City.objects.none()
    elif result_type == "persons":
        books = Book.objects.none()
        persons = persons_qs
        places = City.objects.none()
    elif result_type == "places":
        books = Book.objects.none()
        persons = Person.objects.none()
        places = places_qs
    else:
        books = books_qs
        persons = persons_qs
        places = places_qs

    # hard limit so the page does not explode
    books = books[:100]
    persons = persons[:100]
    places = places[:100]

    # Dropdown choices for filters
    languages = Language.objects.order_by("name")
    places_choices = City.objects.order_by("name")
    bundle_choices = Book._meta.get_field("bundle").choices  # for later integration of Bundle

    context = {
        "query": q,
        "books": books,
        "persons": persons,
        "places": places,
        "facet_books_count": facet_books_count,
        "facet_persons_count": facet_persons_count,
        "facet_places_count": facet_places_count,
        "facet_total_count": facet_books_count + facet_persons_count + facet_places_count,
        "result_type": result_type,
        "languages": languages,
        "places_choices": places_choices,
        "bundle_choices": bundle_choices,
        "has_search": has_search,
        "selected": {
            "year_from": year_from,
            "year_to": year_to,
            "language": language_id,
            "place": place_id,
            "has_digital": has_digital,
        },
    }
    return render(request, "search/search_results.html", context)


def robots_txt(request):
    domain = request.get_host()
    content = (
        "User-agent: *\n"
        "Disallow:\n"
        f"Sitemap: https://{domain}/sitemap.xml\n"
    )
    return HttpResponse(content, content_type="text/plain")


def _get_object_by_slug(queryset, slug: str):
    """
    Find an object via its persisted .slug column first (the path the
    new templates use). Falls back to the legacy slugify(obj.name)
    match so old bookmarks built before the slug columns existed
    keep resolving. Used for Topic, Publisher, Series, Occupation.
    """
    if hasattr(queryset.model, "slug"):
        match = queryset.filter(slug=slug).first()
        if match is not None:
            return match
    for obj in queryset:
        name = getattr(obj, "name", "") or ""
        if slugify(name) == slug:
            return obj
    raise Http404("Object not found")


# ---------- TOPICS ----------

def topics_list_view(request):
    """
    Overview of all topics, alphabetically grouped.
    """
    topics_qs = Topic.objects.all().order_by("name")

    grouped = defaultdict(list)
    for topic in topics_qs:
        name = (topic.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(topic)

    topics_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    context = {
        "alphabet": alphabet,
        "topics_by_letter": topics_by_letter,
        "total_count": sum(len(v) for v in topics_by_letter.values()),
    }
    return render(request, "topics/topics_page.html", context)


def topic_detail_view(request, topic_slug):
    """
    Detail view of a topic with associated books.
    Slug is based on slugify(topic.name).
    """
    topic = _get_object_by_slug(Topic.objects.all(), topic_slug)

    books_with_topic = (
        Book.objects.filter(live=True, topic=topic)
        .order_by("gregorian_year", "name")
        .distinct()
    )

    context = {
        "topic": topic,
        "books_with_topic": books_with_topic,
    }
    return render(request, "topics/topic_detail_page.html", context)


# ---------- PUBLISHERS ----------

def publishers_list_view(request):
    """
    Overview of all publishers, alphabetically grouped.
    """

    publishers_qs = Publisher.objects.all().order_by("name")

    grouped = defaultdict(list)
    for pub in publishers_qs:
        name = (pub.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(pub)

    publishers_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    hebrew_alphabet = list("אבגדהוזחטיכלמנסעפצקרשת")

    context = {
        "alphabet": alphabet,
        "hebrew_alphabet": hebrew_alphabet,
        "publishers_by_letter": publishers_by_letter,
        "total_count": sum(len(v) for v in publishers_by_letter.values()),
    }
    return render(request, "publishers/publishers_page.html", context)


def publisher_detail_view(request, publisher_slug):
    """
    Detail view of a publisher with all associated books
    (publisher AND original_publisher).
    """
    publisher = _get_object_by_slug(Publisher.objects.all(), publisher_slug)

    books_published = (
        Book.objects.filter(live=True, publisher=publisher)
        .order_by("gregorian_year", "name")
        .distinct()
    )
    books_original = (
        Book.objects.filter(live=True, original_publisher=publisher)
        .exclude(publisher=publisher)
        .order_by("gregorian_year", "name")
        .distinct()
    )

    context = {
        "publisher": publisher,
        "books_published": books_published,
        "books_original": books_original,
    }
    return render(request, "publishers/publisher_detail_page.html", context)


# ---------- OCCUPATIONS ----------

def occupations_list_view(request):
    """
    Overview of all occupations, alphabetically grouped.
    """
    occs_qs = Occupation.objects.all().order_by("name")

    grouped = defaultdict(list)
    for occ in occs_qs:
        name = (occ.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(occ)

    occupations_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    context = {
        "alphabet": alphabet,
        "occupations_by_letter": occupations_by_letter,
        "total_count": sum(len(v) for v in occupations_by_letter.values()),
    }
    return render(request, "occupations/occupations_page.html", context)


def occupation_detail_view(request, occupation_slug):
    """
    Detail view of an occupation with all persons who have this profession.
    """
    occupation = _get_object_by_slug(Occupation.objects.all(), occupation_slug)

    persons_with_occupation = (
        Person.objects.filter(live=True, occupations=occupation)
        .select_related("place_of_birth", "place_of_death")
        .order_by("pref_label", "german_name", "hebrew_name")
        .distinct()
    )

    context = {
        "occupation": occupation,
        "persons_with_occupation": persons_with_occupation,
    }
    return render(request, "occupations/occupation_detail_page.html", context)


# Error pages
def custom_400(request, exception):
    return render(request, "errors/400.html", status=400)


def custom_403(request, exception):
    return render(request, "errors/403.html", status=403)


def custom_404(request, exception):
    return render(request, "errors/404.html", status=404)


def custom_500(request):
    return render(request, "errors/500.html", status=500)


# .well-known/security.txt
def security_txt(request):
    domain = request.get_host()
    content = (
        f"Contact: mailto:info@{domain}\n"
        "Expires: 2026-01-01T00:00:00Z\n"
        "Preferred-Languages: en, de\n"
        "Canonical: https://{domain}.well-known/security.txt\n"
        "Policy: https://{domain}/security-policy\n"
    )
    return HttpResponse(content, content_type="text/plain")


# ---------- SERIES ----------

def series_list_view(request):
    """
    Overview of all series, alphabetically grouped.
    """
    series_qs = Series.objects.all().order_by("name")

    grouped = defaultdict(list)
    for s in series_qs:
        name = (s.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(s)

    series_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))
    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")

    context = {
        "alphabet": alphabet,
        "series_by_letter": series_by_letter,
        "total_count": sum(len(v) for v in series_by_letter.values()),
    }
    return render(request, "series/series_page.html", context)


def series_detail_view(request, series_slug):
    """
    Detail view of a series: all books in this series.
    Slug is based on slugify(series.name).
    """
    series = _get_object_by_slug(Series.objects.all(), series_slug)

    books_in_series = (
        Book.objects.filter(live=True, series=series)
        .order_by("series_part", "gregorian_year", "name")
        .distinct()
    )

    context = {
        "series": series,
        "books_in_series": books_in_series,
    }
    return render(request, "series/series_detail_page.html", context)


@api_view(["GET"])
def search_api_view(request):
    """
    REST API for searching across books, persons and places.
    Same logic as search_view, but with JSON output.
    """

    q = (request.GET.get("q") or "").strip()
    result_type = request.GET.get("type", "all")  # all | books | people | places

    year_from = (request.GET.get("year_from") or "").strip()
    year_to = (request.GET.get("year_to") or "").strip()
    language_id = (request.GET.get("language") or "").strip()
    place_id = (request.GET.get("place") or "").strip()
    has_digital = (request.GET.get("has_digital") or "").strip()  # "", "yes", "no"

    # Base querysets (as in search_view)
    books_qs = (
        Book.objects.filter(live=True)
        .select_related("publication_place", "publisher")
        .prefetch_related("languages", "authors")
    )
    persons_qs = (
        Person.objects.filter(live=True)
        .select_related("place_of_birth", "place_of_death")
        .prefetch_related("occupations")
    )
    places_qs = City.objects.filter(live=True)

    # Full-text
    if q:
        books_qs = books_qs.filter(
            Q(name__icontains=q)
            | Q(full_title__icontains=q)
            | Q(title_in_latin_characters__icontains=q)
            | Q(authors__pref_label__icontains=q)
            | Q(authors__german_name__icontains=q)
            | Q(authors__hebrew_name__icontains=q)
        ).distinct()

        persons_qs = persons_qs.filter(
            Q(pref_label__icontains=q)
            | Q(german_name__icontains=q)
            | Q(hebrew_name__icontains=q)
            | Q(pseudonym__icontains=q)
        ).distinct()

        places_qs = places_qs.filter(name__icontains=q)

    # Advanced filters for books
    if year_from:
        try:
            yf = int(year_from)
            books_qs = books_qs.filter(gregorian_year__gte=yf)
        except ValueError:
            pass

    if year_to:
        try:
            yt = int(year_to)
            books_qs = books_qs.filter(gregorian_year__lte=yt)
        except ValueError:
            pass

    if language_id:
        try:
            lang_pk = int(language_id)
            books_qs = books_qs.filter(languages__pk=lang_pk)
        except ValueError:
            pass

    if place_id:
        try:
            c_pk = int(place_id)
            books_qs = books_qs.filter(
                Q(publication_place__pk=c_pk)
                | Q(publication_place_other__pk=c_pk)
                | Q(original_publication_place__pk=c_pk)
            )
        except ValueError:
            pass

    if has_digital == "yes":
        books_qs = books_qs.filter(digital_book_url__regex=r"^https?://")
    elif has_digital == "no":
        books_qs = books_qs.exclude(digital_book_url__regex=r"^https?://")

    # Facets
    facet_books_count = books_qs.count()
    facet_persons_count = persons_qs.count()
    facet_places_count = places_qs.count()

    # Visible type
    if result_type == "books":
        books = books_qs
        persons = Person.objects.none()
        places = City.objects.none()
    elif result_type == "persons":
        books = Book.objects.none()
        persons = persons_qs
        places = City.objects.none()
    elif result_type == "places":
        books = Book.objects.none()
        persons = Person.objects.none()
        places = places_qs
    else:
        books = books_qs
        persons = persons_qs
        places = places_qs

    books = books[:100]
    persons = persons[:100]
    places = places[:100]

    return Response({
        "query": q,
        "result_type": result_type,
        "facets": {
            "books": facet_books_count,
            "persons": facet_persons_count,
            "places": facet_places_count,
        },
        "selected_filters": {
            "year_from": year_from,
            "year_to": year_to,
            "language": language_id,
            "place": place_id,
            "has_digital": has_digital,
        },
        "results": {
            "books": BookSerializer(books, many=True).data,
            "persons": PersonSerializer(persons, many=True).data,
            "places": CitySerializer(places, many=True).data,
        },
    })


def book_cite_bibtex(request, slug):
    book = get_object_or_404(Book, slug=slug, live=True)
    authors = [
        ba.person.pref_label or str(ba.person)
        for ba in book.bookauthor_set.select_related("person")
        if ba.person
    ]
    key = citation_key(book)
    response = render(
        request,
        "books/cite/bibtex.txt",
        {"book": book, "key": key, "authors": authors},
        content_type="text/x-bibtex; charset=utf-8",
    )
    response["Content-Disposition"] = f'attachment; filename="{key}.bib"'
    return response


def book_cite_ris(request, slug):
    book = get_object_or_404(Book, slug=slug, live=True)
    authors = [
        ba.person.pref_label or str(ba.person)
        for ba in book.bookauthor_set.select_related("person")
        if ba.person
    ]
    languages = [str(lang) for lang in book.languages.all()]
    response = render(
        request,
        "books/cite/ris.txt",
        {"book": book, "authors": authors, "languages": languages},
        content_type="application/x-research-info-systems; charset=utf-8",
    )
    key = citation_key(book)
    response["Content-Disposition"] = f'attachment; filename="{key}.ris"'
    return response


# ---------- Entity export (Turtle / JSON-LD / RDF/XML) ----------

def _serialize_entity_response(obj, fmt, *, attachment_basename):
    """Serialize one entity to RDF and wrap it in an HttpResponse."""
    from haskala_rdf.entity import SERIALIZATION, serialize_entity

    if fmt not in SERIALIZATION:
        raise Http404("Unknown export format")
    body, mime = serialize_entity(obj, fmt)
    response = HttpResponse(body, content_type=f"{mime}; charset=utf-8")
    extension = "ttl" if fmt in ("ttl", "turtle") else \
                "jsonld" if fmt in ("jsonld", "json-ld") else \
                "nt" if fmt == "nt" else "rdf"
    response["Content-Disposition"] = (
        f'attachment; filename="{attachment_basename}.{extension}"'
    )
    return response


def _pdf_entity_response(request, obj, *, template_name, attachment_basename, context_extra=None):
    """Render *obj* via *template_name* and return the result as a PDF."""
    from weasyprint import HTML

    context = {"object": obj, "request": request, **(context_extra or {})}
    html_string = render_to_string(template_name, context, request=request)
    base_url = request.build_absolute_uri("/")
    pdf_bytes = HTML(string=html_string, base_url=base_url).write_pdf()
    response = HttpResponse(pdf_bytes, content_type="application/pdf")
    response["Content-Disposition"] = (
        f'attachment; filename="{attachment_basename}.pdf"'
    )
    return response


def book_export(request, slug, fmt):
    book = get_object_or_404(Book, slug=slug, live=True)
    if fmt == "pdf":
        return _pdf_entity_response(
            request, book,
            template_name="books/_pdf/book_pdf.html",
            attachment_basename=book.slug,
            context_extra={"book": book, "visible_sections": visible_sections(book)},
        )
    return _serialize_entity_response(book, fmt, attachment_basename=book.slug)


def person_export(request, slug, fmt):
    person = get_object_or_404(Person, slug=slug, live=True)
    if fmt == "pdf":
        return _pdf_entity_response(
            request, person,
            template_name="persons/_pdf/person_pdf.html",
            attachment_basename=person.slug,
            context_extra={"person": person,
                           "visible_sections": person_visible_sections(person)},
        )
    return _serialize_entity_response(person, fmt, attachment_basename=person.slug)


def place_export(request, slug, fmt):
    city = get_object_or_404(City, slug=slug, live=True)
    if fmt == "pdf":
        # Pass the same context the HTML place_detail_view assembles
        # so the PDF picks up books_published_here / born_here / etc.
        ctx = _place_context_for_pdf(request, city)
        return _pdf_entity_response(
            request, city,
            template_name="places/_pdf/place_pdf.html",
            attachment_basename=city.slug,
            context_extra=ctx,
        )
    return _serialize_entity_response(city, fmt, attachment_basename=city.slug)


def _place_context_for_pdf(request, city):
    """Reuse the place detail view's context for the PDF render."""
    geolocation = Geolocation.objects.filter(city=city).first()
    books_published_here = (
        Book.objects.filter(live=True)
        .filter(
            Q(publication_place=city)
            | Q(publication_place_other=city)
            | Q(original_publication_place=city)
        )
        .order_by("gregorian_year", "name")
        .distinct()
    )
    editions_here = (
        Edition.objects.filter(city=city).select_related("book")
        .order_by("year").distinct()
    )
    translations_here = (
        Translation.objects.filter(city=city).select_related("book", "language")
        .order_by("year").distinct()
    )
    mentions_here = (
        Mention.objects.filter(mentionee_city=city)
        .select_related("book", "mentionee", "mentionee_description")
        .order_by("mentionee__pref_label")
    )
    born_here = city.born_here.filter(live=True).order_by("pref_label")
    died_here = city.died_here.filter(live=True).order_by("pref_label")
    ctx = {
        "city": city,
        "geolocation": geolocation,
        "books_published_here": books_published_here,
        "editions_here": editions_here,
        "translations_here": translations_here,
        "mentions_here": mentions_here,
        "born_here": born_here,
        "died_here": died_here,
    }
    ctx["visible_sections"] = place_visible_sections(ctx)
    return ctx
