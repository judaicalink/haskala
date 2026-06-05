#  Copyright 2018-2023, UB JCS, Goethe University Frankfurt am Main

from django import template
from django.conf import settings
from wagtail.models import Site

register = template.Library()


@register.inclusion_tag("tags/matomo.html", takes_context=True)
def matomo_tracker(context):
    if hasattr(settings, "MATOMO_URL") and hasattr(settings, "MATOMO_SITE_IDS"):
        hostname = Site.find_for_request(context["request"]).hostname
        matomo_site_id = None
        if hostname is not None:
            matomo_site_id = settings.MATOMO_SITE_IDS.get(hostname)
        if matomo_site_id is None:
            matomo_site_id = settings.MATOMO_SITE_IDS.get("default")
        if settings.MATOMO_URL and matomo_site_id:
            return {"MATOMO_URL": settings.MATOMO_URL, "MATOMO_SITE_ID": matomo_site_id}
