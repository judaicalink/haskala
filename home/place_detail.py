"""
Defines the ordered sections of the Place (City) detail page and which
sections have data for a given place. Section visibility depends on
cross-relation querysets the view already computes, so has_data takes
the view's context dict rather than the City instance.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable


@dataclass(frozen=True)
class Section:
    slug: str
    label: str
    has_data: Callable[[dict[str, Any]], bool]


def _nonempty(ctx: dict[str, Any], key: str) -> bool:
    value = ctx.get(key)
    if value is None:
        return False
    try:
        return bool(len(value))
    except TypeError:
        return bool(value)


def _books_has_data(ctx): return _nonempty(ctx, "books_published_here")
def _editions_has_data(ctx): return _nonempty(ctx, "editions_here")
def _translations_has_data(ctx): return _nonempty(ctx, "translations_here")
def _born_has_data(ctx): return _nonempty(ctx, "born_here")
def _died_has_data(ctx): return _nonempty(ctx, "died_here")
def _mentions_has_data(ctx): return _nonempty(ctx, "mentions_here")


SECTIONS: list[Section] = [
    Section("books_published", "Books published here", _books_has_data),
    Section("editions", "Editions printed here", _editions_has_data),
    Section("translations", "Translations from here", _translations_has_data),
    Section("persons_born", "People born here", _born_has_data),
    Section("persons_died", "People died here", _died_has_data),
    Section("mentions", "Mentions in this city", _mentions_has_data),
]


def visible_sections(ctx: dict[str, Any]) -> list[Section]:
    """Return SECTIONS in order, filtered to those with data."""
    return [s for s in SECTIONS if s.has_data(ctx)]
