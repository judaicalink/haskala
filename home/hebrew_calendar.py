"""
Hebrew -> Gregorian calendar conversion helpers for the catalog.

The legacy import records publication dates the way the title page
shows them, which for Maskil books is the Hebrew calendar in
gimatria notation ("תקנד", "תקפ\"ט", occasionally "ה'תקנד" with the
explicit ה=5000 prefix). The catalog also carries numeric Hebrew
years and Gregorian years in the same CharField -- so the public
detail page wants a single helper that:

- detects whether a value is a Hebrew year (gimatria letters or a
  numeric value in the Hebrew range ~5000-5800);
- converts it to a Gregorian year span string ("1729/1730") so
  the reader sees both, since a Hebrew year crosses two Gregorian
  ones;
- passes anything else (already-Gregorian numbers, free text,
  empty, None) through unchanged.

Conversion uses the upstream ``hebrewcal`` package which is the
operator's own implementation. We bridge gimatria parsing in-house
because the package only takes ``HebrewDate(year, month, day)``
integers and doesn't ship a string parser yet.
"""
from __future__ import annotations

import re

import hebrewcal


# Standard gimatria letter -> value mapping. Final-form letters
# (ך / ם / ן / ף / ץ) carry the same value as their non-final
# counterparts; the table includes both shapes so any rendering
# variant works.
_GIMATRIA = {
    "א": 1, "ב": 2, "ג": 3, "ד": 4, "ה": 5,
    "ו": 6, "ז": 7, "ח": 8, "ט": 9,
    "י": 10, "כ": 20, "ך": 20,
    "ל": 30, "מ": 40, "ם": 40,
    "נ": 50, "ן": 50,
    "ס": 60, "ע": 70,
    "פ": 80, "ף": 80,
    "צ": 90, "ץ": 90,
    "ק": 100, "ר": 200, "ש": 300, "ת": 400,
}

# Anything that is neither a Hebrew letter nor a digit gets
# stripped before parsing -- handles geresh ' / gershayim " /
# punctuation / whitespace.
_NON_LETTER = re.compile(r"[^֐-׿0-9]+")

# A Hebrew year written without the ה'-prefix is implied to be in
# the 5th millennium of the Hebrew calendar (i.e. add 5000). The
# catalog universally uses this short form for years 5400-5800
# (= 1640-2040 in the Gregorian calendar) which covers everything
# the Haskala period and its modern surroundings need.
_IMPLICIT_MILLENNIUM = 5000

# Numeric Hebrew years live in this range for Haskala-era titles;
# anything outside is treated as a Gregorian year and passed
# through. Wide-set on purpose so we don't accidentally convert a
# random 4-digit gregorian (1700s/1800s/...) as if it were Hebrew.
_NUMERIC_HEBREW_MIN = 5000
_NUMERIC_HEBREW_MAX = 5999


def parse_hebrew_year(value):
    """Return the integer Hebrew year from *value*, or ``None`` if
    the value doesn't look like a Hebrew year.

    Accepts:

    - Integer or numeric string in the Hebrew range
      (e.g. ``5554`` / ``"5554"``).
    - Gimatria string with the millennium implicit
      (e.g. ``"תקנד"`` = 5554) or explicit (``"ה'תקנד"`` = 5554,
      where the leading ה followed by geresh marks the
      5000-thousand prefix rather than the letter value 5).
    - Mixed text containing one of the above plus
      punctuation / whitespace.

    Returns ``None`` for empty input, Gregorian years, free-text
    descriptions, or anything else that doesn't decode to an
    integer in the expected range.
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # Fast path: purely numeric input.
    if s.isdigit():
        n = int(s)
        if _NUMERIC_HEBREW_MIN <= n <= _NUMERIC_HEBREW_MAX:
            return n
        return None

    # Detect the explicit millennium prefix BEFORE stripping
    # punctuation: a single ``ה`` followed by a geresh / apostrophe
    # right after means "5000" rather than the letter value 5.
    # Without the geresh ה is just a normal gimatria letter.
    explicit_millennium = False
    if len(s) >= 2 and s[0] == "ה" and s[1] in ("'", "׳", "ʼ", "’"):
        explicit_millennium = True
        s = s[2:]

    # Gimatria. Strip geresh / gershayim / spaces, then sum the
    # letter values. Reject if a non-Hebrew character survived
    # (e.g. the input was actually a Gregorian year wrapped in
    # random punctuation).
    cleaned = _NON_LETTER.sub("", s)
    if not cleaned:
        return None
    total = 0
    has_hebrew = False
    for ch in cleaned:
        if ch in _GIMATRIA:
            total += _GIMATRIA[ch]
            has_hebrew = True
        elif ch.isdigit():
            # Pure-digit slice inside a mostly-Hebrew value -- we
            # already handled the numeric-only case above, so a
            # mixed string is too ambiguous to interpret.
            return None
        else:
            # Unknown character: probably not a Hebrew year.
            return None
    if not has_hebrew or total <= 0:
        return None

    # Resolve the millennium: explicit ה' adds 5000; otherwise
    # values below the Hebrew range get promoted via the implicit
    # millennium constant. Already-in-range values pass through.
    if explicit_millennium or total < _NUMERIC_HEBREW_MIN:
        total += _IMPLICIT_MILLENNIUM

    if _NUMERIC_HEBREW_MIN <= total <= _NUMERIC_HEBREW_MAX:
        return total
    return None


def hebrew_year_to_gregorian_span(year):
    """Return the Gregorian-year span for the Hebrew year *year*
    as a string. A Hebrew year starts on 1 Tishri (autumn of the
    previous Gregorian year) and ends on 29 Elul (autumn of the
    current Gregorian year), so it always straddles two Gregorian
    years.

    Examples:

      >>> hebrew_year_to_gregorian_span(5554)
      '1793/1794'

    Returns the empty string if the input is not a positive int.
    """
    if not isinstance(year, int) or year <= 0:
        return ""
    # 1 Tishri = month 7 in hebrewcal's Nissan-counted indexing.
    start = hebrewcal.to_gregorian(hebrewcal.HebrewDate(year, 7, 1))
    end = hebrewcal.to_gregorian(hebrewcal.HebrewDate(year, 6, 29))
    if start.year == end.year:
        return str(start.year)
    return f"{start.year}/{end.year}"


def to_gregorian_year(value):
    """High-level helper used by the template filter.

    Returns:

    - ``""`` for empty / None / unparseable input.
    - ``""`` when the input is already a Gregorian year (the
      caller already has it; rendering it twice is noise).
    - ``"YYYY"`` or ``"YYYY/YYYY"`` Gregorian span string when the
      input parses as a Hebrew year.
    """
    year = parse_hebrew_year(value)
    if year is None:
        return ""
    return hebrew_year_to_gregorian_span(year)
