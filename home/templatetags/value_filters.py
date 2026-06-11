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


def safe_inline(value):
    """
    Render legacy editor-supplied HTML verbatim.

    The Drupal-6 imported notes / references / dedications carry a
    long tail of formatting tags — ``<strong>``, ``<em>``, ``<sub>``,
    ``<sup>``, ``<ins>``, ``<del>``, ``<a>``, ``<span>``, occasional
    ``<table>`` — and the curators want all of them to render so
    the public site looks like the editor intended. The values are
    not user input; they came in through the legacy CMS from
    trusted editors, so we mark the string safe directly instead of
    running it through an allowlist.

    Empty / falsy values short-circuit so chained ``|clean_value``
    output (which collapses zero-ish to ``""``) still renders
    nothing instead of an empty mark_safe wrapper.
    """
    if not value:
        return value
    return mark_safe(str(value))


@register.filter
def clean_value_filter(value):
    """Template-side wrapper. Name kept short via the alias below."""
    return clean_value(value)


# Register under the short ``clean_value`` name as well — that's the
# form the templates actually use.
register.filter("clean_value", clean_value)
register.filter("safe_inline", safe_inline)
