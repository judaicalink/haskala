from django.conf import settings
from django.urls import include, path, re_path
from django.contrib import admin
from django.conf.urls.static import static

from wagtail import urls as wagtail_urls
from wagtail.admin import urls as wagtailadmin_urls
from django.views.generic import RedirectView
from wagtail.documents import urls as wagtaildocs_urls
#from wagtail.contrib.sitemaps.views import sitemap
from .api import api_router
from home.views import book_detail_view

from django.contrib.staticfiles.urls import staticfiles_urlpatterns

#from search import views as search_views

if settings.DEBUG:
    from debug_toolbar.toolbar import debug_toolbar_urls

    urlpatterns = debug_toolbar_urls()
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
else:
    urlpatterns = []

urlpatterns += [
    path('admin/', admin.site.urls),

    path('dashboard/', include(wagtailadmin_urls)),
    path('documents/', include(wagtaildocs_urls)),

    path('books/books-detail-page/', include(wagtail_urls)),

    # Book detail page
    path('books/<title>/', book_detail_view, name='book-detail'),


    path('', include(wagtail_urls)),


    #path('api/v2/', api_router.urls),
    #path(r'', include(allauth.urls)),
    #re_path(r"^dashboard/", include(wagtailadmin_urls)),
    #path("search/", search_views.search, name="search"),

    #re_path(r'^places/(?P<place_slug>[\w-]+)/$', place_view, name='place_view'),
    #re_path(r'^cities/(?P<place_slug>[\w-]+)/$', cities_view, name='cities_view'),
    #re_path(r"^sitemap\.xml$", sitemap),
]

# TODO: reenable

"""
urlpatterns += [
    #path("robots.txt", robots_txt),
    #path(".well-known/security.txt", security_txt),
    path("favicon.ico", RedirectView.as_view(url="/static/img/favicon.ico")),
]
"""
