from django.contrib import admin
from home.models import City, Production, Preface, Book, Person, Translation, Edition, Mention, Geolocation


admin.site.register(Production)
admin.site.register(City)
admin.site.register(Preface)
admin.site.register(Book)
admin.site.register(Person)
admin.site.register(Translation)
admin.site.register(Edition)
admin.site.register(Mention)
admin.site.register(Geolocation)
