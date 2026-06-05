from django import template
from django.utils.text import slugify as django_slugify

register = template.Library()


@register.filter
def slugify(value):
    return django_slugify(value)
