# views.py
import json
import secrets
from collections import defaultdict

from django.db.models import Q
from django.http import Http404, HttpResponse
from django.shortcuts import render, get_object_or_404
from django.utils.text import slugify
from django.views.decorators.cache import cache_page
from requests import Response
from rest_framework.decorators import api_view

from .models import Book, Person, Geolocation, City, Edition, Translation, Mention, Language, Occupation, Topic, \
    Publisher, BookAuthor, Preface, Production, Series
from .serializers import BookSerializer, PersonSerializer, CitySerializer


@cache_page(60 * 60)  # cache for 15 minutes
def book_detail_view(request, title):
    # Fetch the book page using the title (slug)
    book = get_object_or_404(Book, name=title)

    # You can pass additional context here if needed
    return render(request, 'books/book_detail_page.html', {'book': book})


@cache_page(60 * 60)
def books_list_view(request):
    """
    Lists all books alphabetically grouped by the first letter of the name.
    """
    # Fetch all books, ideally sorted by name
    books = Book.objects.all().order_by("name")

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

    # Alphabets for the filter navigation
    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    hebrew_alphabet = list("אבגדהוזחטיכלמנסעפצקרשת")

    context = {
        "alphabet": alphabet,
        "hebrew_alphabet": hebrew_alphabet,
        "books_by_letter": books_by_letter,
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
        .filter(digital_book_url__isnull=False)
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

    # sort dict by letter
    books_by_letter = dict(sorted(grouped.items(), key=lambda item: item[0]))

    alphabet = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
    hebrew_alphabet = list("אבגדהוזחטיכלמנסעפצקרשת")

    context = {
        "alphabet": alphabet,
        "hebrew_alphabet": hebrew_alphabet,
        "books_by_letter": books_by_letter,
    }

    return render(request, "digital-books/digital_books_page.html", context)


def persons_list_view(request):
    """
    Lists all persons alphabetically, grouped by first letter
    of the display name (pref_label / german_name / hebrew_name).
    """
    persons_qs = Person.objects.all().order_by("pref_label", "german_name", "hebrew_name")

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
    }
    return render(request, "persons/persons_page.html", context)


@cache_page(60 * 60)
def person_detail_view(request, person_uuid):
    """
    Detail view of a person, identified by UUID.
    """
    person = get_object_or_404(Person, pk=person_uuid)

    # Group books by role (BookAuthor through model)
    books_by_role = defaultdict(list)
    for ba in (
        BookAuthor.objects
        .filter(person=person)
        .select_related("book")
        .order_by("book__name")
    ):
        if not ba.book:
            continue
        role_label = ba.get_role_display()  # e.g. "Old text author"
        books_by_role[role_label].append(ba.book)

    # Prefaces, productions, mentions
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
        .select_related("mentionee_city", "mentionee_description")
        .order_by("mentionee_city__name")
    )

    has_additional_info = bool(books_by_role or prefaces or productions or mentions)

    context = {
        "person": person,
        "person_books_by_role": dict(books_by_role),
        "prefaces_by_person": prefaces,
        "productions_by_person": productions,
        "mentions_of_person": mentions,
        "has_additional_info": has_additional_info,
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
    cities_qs = City.objects.all().order_by("name")

    for city in cities_qs:
        name = (city.name or "").strip()
        if not name:
            continue
        first_letter = name[0].upper()
        grouped[first_letter].append(name)

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
    }
    return render(request, "places/places_page.html", context)


def _get_place_by_slug(city_slug: str) -> City:
    """
    Helper: finds a city by slug.
    Slug is generated via slugify(city.name).
    """
    for city in City.objects.all():
        if slugify(city.name) == city_slug:
            return city
    raise Http404("Place not found")


@cache_page(60 * 60)
def place_detail_view(request, city_slug):
    """
    Detail view of a city as a regular Django view.
    """
    city = _get_place_by_slug(city_slug)

    # Geocoordinates
    geolocation = Geolocation.objects.filter(city=city).first()

    # Books published here
    books_published_here = Book.objects.filter(
        Q(publication_place=city)
        | Q(publication_place_other=city)
        | Q(original_publication_place=city)
    ).distinct()

    # Editions & translations
    editions_here = Edition.objects.filter(city=city).select_related("book").distinct()
    translations_here = (
        Translation.objects.filter(city=city)
        .select_related("book", "language")
        .distinct()
    )

    # Mentions / persons
    mentions_here = Mention.objects.filter(mentionee_city=city).select_related(
        "mentionee", "mentionee_description"
    )

    # Persons born/died here (via related_name)
    born_here = city.born_here.all()
    died_here = city.died_here.all()

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
    return render(request, "places/place_detail_page.html", context)


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
        Book.objects.all()
        .select_related("publication_place", "publisher")
        .prefetch_related("languages", "authors")
    )
    persons_qs = (
        Person.objects.all()
        .select_related("place_of_birth", "place_of_death")
        .prefetch_related("occupations")
    )
    places_qs = City.objects.all()

    # --- Full-text query ----------------------------------------------------
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
        "result_type": result_type,
        "languages": languages,
        "places_choices": places_choices,
        "bundle_choices": bundle_choices,
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
    Simple helper: finds an object via slugify(obj.name).
    Used for Topic, Publisher, Occupation.
    """
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
    }
    return render(request, "topics/topics_page.html", context)


def topic_detail_view(request, topic_slug):
    """
    Detail view of a topic with associated books.
    Slug is based on slugify(topic.name).
    """
    topic = _get_object_by_slug(Topic.objects.all(), topic_slug)

    books_with_topic = Book.objects.filter(topic=topic).order_by("name").distinct()

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

    publishers_qs = get_object_or_404(Publisher, slug=publisher_slug)
    Publisher.objects.all().order_by("name")

    print("Publishers QS:", publishers_qs)

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
    }
    return render(request, "publishers/publishers_page.html", context)


def publisher_detail_view(request, publisher_slug):
    """
    Detail view of a publisher with all associated books
    (publisher AND original_publisher).
    """
    publisher = _get_object_by_slug(Publisher.objects.all(), publisher_slug)

    books_published = Book.objects.filter(
        Q(publisher=publisher) | Q(original_publisher=publisher)
    ).order_by("name").distinct()

    context = {
        "publisher": publisher,
        "books_published": books_published,
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
    }
    return render(request, "occupations/occupations_page.html", context)


def occupation_detail_view(request, occupation_slug):
    """
    Detail view of an occupation with all persons who have this profession.
    """
    occupation = _get_object_by_slug(Occupation.objects.all(), occupation_slug)

    persons_with_occupation = (
        Person.objects.filter(occupations=occupation)
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
    }
    return render(request, "series/series_page.html", context)


def series_detail_view(request, series_slug):
    """
    Detail view of a series: all books in this series.
    Slug is based on slugify(series.name).
    """
    series = _get_object_by_slug(Series.objects.all(), series_slug)

    books_in_series = (
        Book.objects.filter(series=series)
        .order_by("name")
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
        Book.objects.all()
        .select_related("publication_place", "publisher")
        .prefetch_related("languages", "authors")
    )
    persons_qs = (
        Person.objects.all()
        .select_related("place_of_birth", "place_of_death")
        .prefetch_related("occupations")
    )
    places_qs = City.objects.all()

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
