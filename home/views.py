# views.py
from django.shortcuts import render
from django.http import HttpResponse

def place_view(request, place_slug):
    # You can customize the handling logic here.
    # For example, you might fetch data from the database or render a template.
    context = {'place_slug': place_slug}
    return render(request, 'place.html', context)


def cities_view(request, cities_slug):
    # You can customize the handling logic here.
    # For example, you might fetch data from the database or render a template.
    context = {'place_slug': cities_slug}
    return render(request, 'cities.html', context)