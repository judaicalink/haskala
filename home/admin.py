from django.contrib import admin
from home.models import City


class CityAdmin(admin.ModelAdmin):
    pass


admin.site.register(City, CityAdmin)