# home/templatetags/topic_tags.py
from django import template

from home.models import Topic

register = template.Library()


@register.inclusion_tag("partials/tagcloud.html")
def topic_tagcloud():
    """
    Renders a tag cloud with all topics as pills.
    """
    topics = Topic.objects.order_by("name")
    return {"topics": topics}
