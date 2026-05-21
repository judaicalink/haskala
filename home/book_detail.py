"""
Defines the 16 ordered sections of the Book detail page and which sections
have data for a given Book. Used by the view to compute visible_sections
once and pass it to both the TOC and the content templates.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .models import Book


@dataclass(frozen=True)
class Section:
    slug: str  # used as anchor id and TOC key
    label: str  # display name in TOC and section heading
    has_data: Callable[[Book], bool]


def _any(*values) -> bool:
    return any(bool(v) for v in values)


def _identity_has_data(b: Book) -> bool:
    return _any(
        b.full_title, b.title_in_latin_characters, b.motto, b.old_name_in_book,
        b.other_books_names, b.original_text_name, b.original_title,
        b.original_title_else_refer, b.original_title_elsewhere,
        b.presented_as_original, b.presented_as_translation,
        b.presented_new_edition,
    )


def _authors_has_data(b: Book) -> bool:
    return (
        b.bookauthor_set.exists()
        or _any(b.original_author, b.original_author_else_refer,
                b.original_author_elsewhere, b.original_author_other_name,
                b.founders, b.proofreaders)
    )


def _publication_has_data(b: Book) -> bool:
    return _any(
        b.publisher_id, b.original_publisher_id,
        b.publication_place_id, b.publication_place_other_id,
        b.gregorian_year, b.year_in_book, b.year_in_other,
        b.hebrew_year_of_publication, b.hebrew_year_pub_other,
        b.gregorian_year_pub_other, b.format_of_publication_date_id,
        b.partial_publication, b.printed_originally,
        b.original_publication_place_id, b.original_publication_year,
        b.printers, b.printing_press_notes, b.printing_press_references,
        b.production_evidence, b.series_id, b.series_part,
    )


def _physical_has_data(b: Book) -> bool:
    return _any(
        b.pages_number, b.height, b.width,
        b.fonts.exists(), b.typography.exists(),
        b.illustrations_diagrams, b.diagrams_notes, b.diagrams_book_pages,
        b.alignment_id,
    )


def _languages_has_data(b: Book) -> bool:
    return (
        b.languages.exists() or b.footnote_languages.exists()
        or b.occasional_words_languages.exists()
        or _any(b.languages_number_id, b.location_of_footnotes_id, b.original_language_id)
    )


def _content_structure_has_data(b: Book) -> bool:
    return (
        b.target_audience.exists()
        or b.main_textual_models.exists()
        or b.secondary_textual_models.exists()
        or _any(
            b.topic_id, b.target_audience_notes,
            b.textual_model_notes, b.original_type_id,
            b.structure_notes, b.structure_preface_notes,
            b.table_of_content, b.contents_table_notes,
            b.preface, b.epilogue, b.epilogue_notes,
            b.dedications, b.dedications_notes,
        )
    )


def _editions_has_data(b: Book) -> bool:
    return (
        b.editions.exists()
        or _any(
            b.total_number_of_editions, b.last_known_edition, b.editions_notes,
            b.references_for_editions, b.new_edition_general_notes,
            b.new_edition_type_in_text, b.new_edition_type_elsewhere,
            b.new_edition_type_reference, b.new_edition_type_else_ref,
            b.new_edition_type_notes, b.new_edition_type_else_note,
            b.copy_of_book_used,
            b.other_volumes, b.volumes_notes,
            b.volumes_published_number, b.planned_volumes,
        )
    )


def _translations_has_data(b: Book) -> bool:
    return (
        b.translations.exists()
        or _any(
            b.translation_notes, b.translation_type_id,
            b.presented_as_translation, b.presented_as_translation_refe,
            b.presented_as_translatio_notes,
        )
    )


def _productions_has_data(b: Book) -> bool:
    return b.productions.exists()


def _prefaces_has_data(b: Book) -> bool:
    return b.prefaces.exists()


def _mentions_has_data(b: Book) -> bool:
    return (
        b.mentions.exists()
        or _any(
            b.mention_general_notes, b.mentions_in_reviews,
            b.contemporary_disputes, b.contemporary_references,
            b.later_references,
        )
    )


def _sources_has_data(b: Book) -> bool:
    return _any(
        b.bibliographical_citations, b.studies,
        b.sources_exist, b.sources_list,
        b.sources_not_mentioned, b.sources_not_mentioned_list,
        b.sources_not_mentioned_ref, b.sources_references,
        b.jewish_sources_quotes, b.non_jewish_sources_quotes,
        b.original_sources_mention, b.references_notes,
        b.secondary_sources,
    )


def _censorship_has_data(b: Book) -> bool:
    return _any(
        b.censorship, b.bans, b.rabbinical_approbations,
        b.rabbinical_approbation_notes,
    )


def _subscription_has_data(b: Book) -> bool:
    return _any(
        b.subscribers, b.subscribers_notes,
        b.subscription_appeal, b.subscription_appeal_notes,
        b.recommendations, b.recommendations_notes,
        b.price, b.sellers, b.sellers_notes,
        b.thanks, b.thanks_notes,
        b.contacts_official_agents, b.contacts_other_people,
        b.personal_address, b.personal_address_notes,
    )


def _availability_has_data(b: Book) -> bool:
    return _any(
        b.not_available is True, b.availability_notes,
        b.other_libraries,
        b.bar_ilan_library_id, b.berlin_library_id, b.british_library_id,
        b.frankfurt_library_id, b.huji_library_id,
        b.new_york_library_id, b.tel_aviv_library_id,
        b.digital_book_url, b.digital_book_title, b.digital_book_attributes,
        b.preservation_references, b.catalog_numbers_notes,
    )


def _record_metadata_has_data(b: Book) -> bool:
    return _any(b.legacy_nid, b.legacy_created, b.legacy_changed)


SECTIONS: list[Section] = [
    Section("identity", "Identity & Titles", _identity_has_data),
    Section("authors", "Authors & Persons", _authors_has_data),
    Section("publication", "Publication", _publication_has_data),
    Section("physical", "Physical & Typography", _physical_has_data),
    Section("languages", "Language & Footnotes", _languages_has_data),
    Section("content_structure", "Content & Structure", _content_structure_has_data),
    Section("editions", "Editions", _editions_has_data),
    Section("translations", "Translations", _translations_has_data),
    Section("productions", "Productions", _productions_has_data),
    Section("prefaces", "Prefaces", _prefaces_has_data),
    Section("mentions", "Mentions & Reception", _mentions_has_data),
    Section("sources", "Sources & References", _sources_has_data),
    Section("censorship", "Censorship & Approbation", _censorship_has_data),
    Section("subscription", "Subscription & Marketing", _subscription_has_data),
    Section("availability", "Availability & Catalog", _availability_has_data),
    Section("record_metadata", "Record metadata", _record_metadata_has_data),
]


def visible_sections(book: Book) -> list[Section]:
    """Return SECTIONS in order, filtered to those with data for this book."""
    return [s for s in SECTIONS if s.has_data(book)]
