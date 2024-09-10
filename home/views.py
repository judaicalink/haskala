# views.py
from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse
from .models import BooksPage, Book

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


def book_detail_view(request, title):
    print("Title: ", title)
    # Fetch the book page using the title (slug)
    book = get_object_or_404(Book, name=title)
    print("Book: ", book)

    # You can pass additional context here if needed
    return render(request, 'book_detail.html', {'book': book})