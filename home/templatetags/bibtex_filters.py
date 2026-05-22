from django import template

register = template.Library()


@register.filter
def bibtex_escape(value):
    """
    Escape characters with special meaning in BibTeX field values:
    - backslash → doubled
    - braces → preceded by a backslash
    Returns "" for None to keep templates simple.
    """
    if value is None:
        return ""
    text = str(value)
    text = text.replace("\\", "\\\\")
    text = text.replace("{", "\\{").replace("}", "\\}")
    return text
