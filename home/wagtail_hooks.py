from django.contrib.admin import ModelAdmin
from wagtail import hooks
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.menu import MenuItem
from django.urls import reverse
from django.utils.html import format_html


from .models import City


@hooks.register('register_admin_menu_item')
def register_front_page_menu_item():
    # URL of the front page of your app
    url = '/'

    # Create a new menu item
    menu_item = MenuItem('Front Page', url, icon_name='home', order=10000)

    return menu_item


def CityForm(WagtailAdminModelForm):
    class Meta:
        model = City
        fields = '__all__'

