"""
Defines the ordered sections of the Person detail page and which sections
have data for a given Person. Used by the view to compute visible_sections
once and pass it to both the TOC and the content templates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Person


@dataclass(frozen=True)
class Section:
    slug: str
    label: str
    has_data: Callable[[Person], bool]


def _any(*values) -> bool:
    return any(bool(v) for v in values)


def _identity_has_data(p: Person) -> bool:
    return _any(p.german_name, p.hebrew_name, p.pseudonym, p.gender_id,
                p.occupations.exists())


def _biographical_has_data(p: Person) -> bool:
    return _any(p.date_of_birth, p.date_of_death,
                p.place_of_birth_id, p.place_of_death_id)


def _works_has_data(p: Person) -> bool:
    return p.bookauthor_set.exists()


def _prefaces_has_data(p: Person) -> bool:
    return p.preface_set.exists()


def _productions_has_data(p: Person) -> bool:
    return p.production_set.exists()


def _mentions_has_data(p: Person) -> bool:
    return p.mention_set.exists()


def _identifiers_has_data(p: Person) -> bool:
    return bool(p.viaf_id)


def _record_metadata_has_data(p: Person) -> bool:
    return _any(p.legacy_nid, p.legacy_created, p.legacy_changed)


SECTIONS: list[Section] = [
    Section("identity", "Identity & Names", _identity_has_data),
    Section("biographical", "Life", _biographical_has_data),
    Section("works", "Works & Roles", _works_has_data),
    Section("prefaces", "Prefaces", _prefaces_has_data),
    Section("productions", "Productions", _productions_has_data),
    Section("mentions", "Mentions", _mentions_has_data),
    Section("identifiers", "Identifiers", _identifiers_has_data),
    Section("record_metadata", "Record metadata", _record_metadata_has_data),
]


def visible_sections(person: Person) -> list[Section]:
    """Return SECTIONS in order, filtered to those with data for this person."""
    return [s for s in SECTIONS if s.has_data(person)]
