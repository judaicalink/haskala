"""
Template + Python helpers for cleaning legacy Drupal-6 field values.

The original importer stored every yes/no flag as a literal string
``"0.0"`` / ``"1.0"`` and every integer count as ``"0.0"`` / ``"1.0"``
/ ``"2.0"`` etc. That noise leaked into the detail templates as
``Subscribers 0.0`` / ``Subscription appeal 0.0``, which reads as
"the value is zero" when it really means "no value".

``clean_value`` collapses every "false-y but truthy in Python" shape
to the empty string and strips trailing ``.0`` from whole-number
floats so ``"1.0"`` renders as ``1``. Used both in
:mod:`home.book_detail` (Python-side, to drive ``visible_sections``)
and inside templates via the registered ``|clean_value`` filter.
"""
from __future__ import annotations

import re

from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe

register = template.Library()


# Values we treat as "no value" regardless of how the importer wrote
# them. The float and int forms cover any future code that hands the
# filter a real number.
_ZEROISH = {"", "0", "0.0", "0.00", "0.000", 0, 0.0, False, None}

# Drupal-6 emitted PHP-serialised empty arrays into TextField columns
# whenever a multi-value form was left blank. The wire format is
# ``a:0:{}`` for an empty array and ``a:N:{ … }`` for non-empty. The
# regex below catches every empty form (``a:0:{}``, ``a:0:{};``) so
# the rendered detail rows don't surface "a:0:{}" as the field value.
_PHP_EMPTY_ARRAY = re.compile(r'^a:0:\{\}\s*;?\s*$')


def clean_value(value):
    """
    Normalise *value* for both truth-tests and display:

    - empty / zero-ish (``"0.0"``, ``"0"``, ``0``, ``False``, ``None``)
      becomes the empty string;
    - whole-number floats (``1.0``, ``12.0``, or their string forms)
      lose the decimal tail (``"1"``, ``"12"``);
    - real fractional values keep their decimal point (``"3.5"``);
    - any other value passes through unchanged so the filter is safe
      to apply to plain text, model objects, dates, etc.
    """
    if isinstance(value, bool):
        return "" if not value else value
    if value in _ZEROISH:
        return ""

    if isinstance(value, float):
        return str(int(value)) if value.is_integer() else str(value)

    if isinstance(value, int):
        return str(value)

    if isinstance(value, str):
        stripped = value.strip()
        if stripped in _ZEROISH:
            return ""
        if _PHP_EMPTY_ARRAY.match(stripped):
            return ""
        try:
            as_float = float(stripped)
        except ValueError:
            return stripped
        if as_float == 0:
            return ""
        if as_float.is_integer():
            return str(int(as_float))
        # Keep the user-typed form so 3.50 doesn't become 3.5 just
        # because float parsing normalised it. Only if the original
        # had a numeric .0 tail and a leading integer we replace it.
        return stripped

    return value


# Inline HTML tags carried over from the Drupal-6 import that we
# want to render rather than display as escaped text. Anything else
# (script, style, iframe, attributes, etc.) stays escaped, so the
# filter is safe to use on legacy editor-controlled content.
_ALLOWED_INLINE = re.compile(
    r'&lt;(?P<close>/?)(?P<tag>strong|em|b|i|u|br|p|sub|sup)(?P<slash>\s*/?)&gt;',
    re.IGNORECASE,
)


def safe_inline(value):
    """
    HTML-escape *value*, then re-introduce a small allowlist of inline
    formatting tags (``<strong>``, ``<em>``, ``<b>``, ``<i>``, ``<u>``,
    ``<br>``, ``<p>``, ``<sub>``, ``<sup>``). The result is marked safe
    for template output. Attributes are NOT preserved — that closes the
    door on inline event handlers / javascript URLs.
    """
    if not value:
        return value
    escaped = escape(str(value))
    rendered = _ALLOWED_INLINE.sub(
        lambda m: f'<{m.group("close")}{m.group("tag").lower()}{m.group("slash")}>',
        escaped,
    )
    return mark_safe(rendered)


@register.filter
def clean_value_filter(value):
    """Template-side wrapper. Name kept short via the alias below."""
    return clean_value(value)


# Register under the short ``clean_value`` name as well — that's the
# form the templates actually use.
register.filter("clean_value", clean_value)
register.filter("safe_inline", safe_inline)
