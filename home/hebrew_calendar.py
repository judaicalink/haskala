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


# ---------------------------------------------------------------------
# Hebrew month names -> hebrewcal month indices (Nissan-counted).
# Multiple spellings accepted: "חשון" / "מרחשון", "כסלו" / "כסליו",
# bare Adar maps to month 12 (the catalog's data doesn't carry leap-
# year disambiguation; if it ever does, "אדר א" and "אדר ב" can be
# added without breaking the simple "אדר" lookup).
# ---------------------------------------------------------------------
HEBREW_MONTHS = {
    "ניסן": 1,
    "אייר": 2, "איר": 2,
    "סיון": 3, "סיוון": 3,
    "תמוז": 4,
    "אב": 5, "מנחם-אב": 5, "מנחם אב": 5,
    "אלול": 6,
    "תשרי": 7,
    "חשון": 8, "חשוון": 8, "מרחשון": 8, "מרחשוון": 8,
    "כסלו": 9, "כסליו": 9,
    "טבת": 10,
    "שבט": 11,
    "אדר": 12, "אדר א": 12, "אדר ב": 12, "אדר א'": 12, "אדר ב'": 12,
}

# Tokeniser splits on whitespace + the geresh / gershayim cluster
# so "כ\"א אדר תקנד" yields three meaningful tokens. Inner punctuation
# inside a single token (e.g. "תקפ\"ט") is then handled by the
# per-token gimatria parser.
_SPACE_RE = re.compile(r"\s+")


def _gimatria_sum(token):
    """Sum the gimatria values of every Hebrew letter in *token*,
    ignoring punctuation. Returns 0 if no Hebrew letter is present."""
    total = 0
    for ch in token:
        if ch in _GIMATRIA:
            total += _GIMATRIA[ch]
    return total


def parse_hebrew_date(value):
    """Best-effort parse of a Hebrew-calendar date string into a
    ``(year, month, day)`` tuple where missing components are
    ``None``.

    Recognises the common Maskil-era shapes:

    - year-only gimatria: ``"תקנד"``         -> ``(5554, None, None)``
    - month + year:       ``"אדר תקנד"``     -> ``(5554, 12, None)``
    - full date:          ``"כ' אדר תקנד"``  -> ``(5554, 12, 20)``
    - explicit millennium prefix on the year:
                           ``"ה'תקנד"``       -> year 5554

    Returns ``None`` when no recognisable Hebrew calendar
    information is found (the caller can fall back to the plain
    year-only ``parse_hebrew_year`` path).
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None

    # Tokenise. Compound month names like "מנחם אב" / "אדר א" need
    # special handling: we try the longest match first by also
    # joining adjacent tokens.
    tokens = [t for t in _SPACE_RE.split(s) if t]
    if not tokens:
        return None

    year = month = day = None

    # Walk left-to-right. Order matters: month -> day -> year.
    # We check day BEFORE year because a one- or two-letter
    # gimatria token like ``כ'`` (= 20) would otherwise be
    # promoted to a 5xxx year by parse_hebrew_year and steal the
    # day slot. A true Hebrew year token carries enough letters
    # to push the gimatria sum past 30 (e.g. ``תקנד`` = 554), so
    # the day check naturally rejects it and falls through to
    # the year parser. Multi-token shapes (``"5554"`` etc.) still
    # land via parse_hebrew_year because their gimatria sum is
    # large enough to exit the 1..30 window.
    i = 0
    while i < len(tokens):
        tok = tokens[i]
        # Month: greedy 2-token then 1-token lookup.
        if i + 1 < len(tokens):
            joined = f"{tok} {tokens[i + 1]}"
            if joined in HEBREW_MONTHS:
                month = HEBREW_MONTHS[joined]
                i += 2
                continue
        if tok in HEBREW_MONTHS:
            month = HEBREW_MONTHS[tok]
            i += 1
            continue
        # Day: gimatria sum in 1..30 wins before the year parser
        # gets a chance to promote it.
        if day is None:
            d = _gimatria_sum(tok)
            if 1 <= d <= 30:
                day = d
                i += 1
                continue
        # Year: full year parser handles numerics, implicit /
        # explicit millennium prefixes, gimatria.
        y = parse_hebrew_year(tok)
        if y is not None:
            year = y
            i += 1
            continue
        # Token didn't fit any slot -- skip and move on.
        i += 1

    if year is None and month is None and day is None:
        return None
    return (year, month, day)


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


# English month-name lookup used when we materialise a Hebrew date
# back to a human-readable Gregorian string. Keeps the catalog
# language-consistent with the rest of the UI (which is English).
_GREGORIAN_MONTH_NAMES = [
    "", "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def to_gregorian_string(value):
    """High-level helper for the template filter: convert a
    Hebrew-calendar string (year-only, year + month, or full
    date) into a human-readable Gregorian rendering.

    Returns:

    - ``""`` for empty / unparseable input or for input that's
      already a Gregorian year (the caller already has it).
    - ``"YYYY"`` or ``"YYYY/YYYY"`` for a year-only Hebrew input.
    - ``"<Month> YYYY"`` (e.g. ``"March 1794"``) for a year+month
      Hebrew input.
    - ``"D <Month> YYYY"`` (e.g. ``"12 March 1794"``) for a full
      Hebrew date.

    A Hebrew calendar date converts cleanly to one Gregorian date;
    only year-only inputs straddle two Gregorian years.
    """
    parsed = parse_hebrew_date(value)
    if parsed is None:
        return ""
    year, month, day = parsed
    if year is None:
        # Without a year we can't compute anything Gregorian.
        return ""
    if month is None and day is None:
        return hebrew_year_to_gregorian_span(year)
    # Default the day to the first of the month so we have a
    # legal HebrewDate even for year+month inputs; the rendered
    # output then drops the day.
    g = hebrewcal.to_gregorian(
        hebrewcal.HebrewDate(year, month or 7, day or 1),
    )
    month_name = _GREGORIAN_MONTH_NAMES[g.month]
    if day is not None:
        return f"{g.day} {month_name} {g.year}"
    return f"{month_name} {g.year}"
