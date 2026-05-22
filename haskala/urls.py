from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.conf.urls.static import static

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from django.views.generic import RedirectView
from wagtail.documents import urls as wagtaildocs_urls

from django.contrib.sitemaps.views import sitemap
from home.sitemaps import (
    StaticViewSitemap,
    BookSitemap,
    PersonSitemap,
    PlaceSitemap,
    WagtailPageSitemap,
)

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView,
)

from .api import api_router
from home.views import book_detail_view, books_list_view, book_cite_bibtex, digital_books_list_view, persons_list_view, \
    person_detail_view, place_detail_view, places_list_view, search_view, topics_list_view, topic_detail_view, \
    publishers_list_view, publisher_detail_view, occupation_detail_view, occupations_list_view, robots_txt, \
    security_txt, series_list_view, series_detail_view, search_api_view

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

#from search import views as search_views

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = debug_toolbar_urls()
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns = []

sitemaps = {
    "static": StaticViewSitemap,
    "books": BookSitemap,
    "persons": PersonSitemap,
    "places": PlaceSitemap,
    "pages": WagtailPageSitemap,
}


urlpatterns += [
    path('admin/', admin.site.urls),

    path('dashboard/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),

    #path('books/books-detail-page/', include(wagtail_urls)),

    # Book detail page
    path('books/', books_list_view, name='books-list'),
    path('books/<title>/cite.bib', book_cite_bibtex, name='book-cite-bibtex'),
    path('books/<title>/', book_detail_view, name='book-detail'),

    # Digital books
    path('digital-books/', digital_books_list_view, name='digital-books-list'),

    # Persons
    path("persons/", persons_list_view, name="persons-list"),
    path("persons/<uuid:person_uuid>/", person_detail_view, name="person-detail"),

    # Places
    path("places/", places_list_view, name="places-list"),
    path("places/<slug:city_slug>/", place_detail_view, name="place-detail"),

    # Topics
    path("topics/", topics_list_view, name="topics-list"),
    path("topics/<slug:topic_slug>/", topic_detail_view, name="topic-detail"),

    #  Publishers
    path("publishers/", publishers_list_view, name="publishers-list"),
    path("publishers/<slug:publisher_slug>/", publisher_detail_view, name="publisher-detail"),

    #  Occupations
    path("occupations/", occupations_list_view, name="occupations-list"),
    path("occupations/<slug:occupation_slug>/", occupation_detail_view, name="occupation-detail"),

    # Series
    path("series/", series_list_view, name="series-list"),
    path("series/<slug:series_slug>/", series_detail_view, name="series-detail"),

    # Search
    path("search/", search_view, name="search"),

    # Sitemaps and robots.txt
    path("sitemap.xml", sitemap, {"sitemaps": sitemaps}, name="django_sitemap"),

    # Custom search endpoint
    path("api/search/", search_api_view, name="api-search"),

    # OpenAPI schema
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),

    # Swagger UI
    path(
        "api/docs/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),

    # ReDoc
    path(
        "api/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),

    # REST API (DRF router)
    path("api/", api_router.urls),

    # Wagtail
    path('', include(wagtail_urls)),
]


urlpatterns += [
    path("robots.txt", robots_txt, name="robots_txt"),
    path(".well-known/security.txt", security_txt),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.ico")),
]

handler404 = "home.views.custom_404"
handler400 = "home.views.custom_400"
handler403 = "home.views.custom_403"
handler500 = "home.views.custom_500"