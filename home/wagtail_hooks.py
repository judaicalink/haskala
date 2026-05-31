from wagtail import hooks
from wagtail.admin.menu import MenuItem
from wagtail.snippets.models import register_snippet
from wagtail.snippets.views.snippets import SnippetViewSet

from .models import Book


@hooks.register('register_admin_menu_item')
def register_front_page_menu_item():
    return MenuItem('Home Page', '/', icon_name='home', order=10000)


class BookViewSet(SnippetViewSet):
    model = Book
    menu_label = "Books"
    menu_icon = "book"
    menu_order = 200

    list_display = ("name", "author_names", "bundle", "gregorian_year")
    list_filter = ("bundle", "gregorian_year")
    search_fields = (
        "name",
        "authors__pref_label",
        "authors__german_name",
        "authors__hebrew_name",
    )


register_snippet(BookViewSet)
