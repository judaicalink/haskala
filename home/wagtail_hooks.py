from django.contrib.admin import ModelAdmin
from wagtail import hooks
from wagtail.admin.forms import WagtailAdminModelForm
from wagtail.admin.menu import MenuItem
from django.urls import reverse
from django.utils.html import format_html
from wagtail.admin.forms.models import WagtailAdminModelForm

from .models import City, MyCustomModel


# TODO: reenable
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


class MyCustomModelAdmin(ModelAdmin):
    model = MyCustomModel
    menu_label = 'Custom Data'
    menu_icon = 'snippet'  # You can choose an appropriate icon here
    list_display = ('title', 'description')
    search_fields = ('title', 'description')
