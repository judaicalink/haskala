"""
Builds the BEACON file lines that map Haskala persons to GND identifiers.

BEACON is a flat text format used by German libraries and the Wikipedia
"Personendaten" infrastructure to publish "we know about these GND IDs"
lists. The header lines describe the source and the target URL pattern;
each data line is the bare GND identifier of one of our persons.

See: https://gbv.github.io/beaconspec/beacon.html
"""
from __future__ import annotations

from typing import Iterable

from home.models import Person

DEFAULT_TARGET = "http://data.judaicalink.org/data/haskala/person/{ID}"


def _header_lines(*, target: str, name: str, description: str) -> list[str]:
    return [
        "#FORMAT: BEACON",
        f"#TARGET: {target}",
        f"#NAME: {name}",
        f"#DESCRIPTION: {description}",
    ]


def build_beacon_lines(
    *,
    target: str = DEFAULT_TARGET,
    name: str = "Haskala Bibliography",
    description: str = (
        "Persons covered by the Haskala bibliography, mapped to their "
        "GND identifiers."
    ),
) -> Iterable[str]:
    """
    Yield BEACON file lines. Each yielded string is one line (no
    trailing newline). Persons without a known GND identifier are
    skipped.
    """
    yield from _header_lines(target=target, name=name, description=description)

    persons = Person.objects.exclude(gnd_id__isnull=True).exclude(gnd_id="") \
        if _has_gnd_field() else []

    for person in persons:
        gnd_id = (getattr(person, "gnd_id", "") or "").strip()
        if gnd_id:
            yield gnd_id


def _has_gnd_field() -> bool:
    """Return True if Person has a gnd_id field at this point in time."""
    return any(f.name == "gnd_id" for f in Person._meta.get_fields())
