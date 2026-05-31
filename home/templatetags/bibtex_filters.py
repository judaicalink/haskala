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


@register.filter
def ris_escape(value):
    """
    Flatten newlines in RIS field values. RIS is strictly one tag per
    line, so a stray \\r or \\n inside a TI / AU / PB / CY / LA value
    would corrupt the record and confuse reference managers. Replace
    such characters with a single space; collapse adjacent whitespace.
    Returns "" for None to keep templates simple.
    """
    if value is None:
        return ""
    text = str(value).replace("\r", " ").replace("\n", " ")
    return " ".join(text.split())
