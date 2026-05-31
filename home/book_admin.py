"""
Builds the Wagtail admin edit form for Book. Grouping mirrors the visible
sections of the public detail page (see home/book_detail.py) so editors
can find each field where they expect to see it on the site.

The pure storage-of-format flag columns (*_format) and read-only system
columns (uuid, created_at, updated_at) are intentionally omitted from
the editor; they remain accessible via the API and the Django admin.
"""
from __future__ import annotations

from wagtail.admin.panels import FieldPanel, MultiFieldPanel


def _panels(field_names):
    return [FieldPanel(name) for name in field_names]


# Each entry: (heading, [field names]).
# Section order matches the public detail page.
SECTIONS: list[tuple[str, list[str]]] = [
    ("Basics", [
        "name", "full_title", "bundle",
    ]),
    ("Identity & titles", [
        "title_in_latin_characters", "motto", "old_name_in_book", "name_in_book",
        "other_books_names", "original_text_name", "original_title",
        "original_title_else_refer", "original_title_elsewhere",
        "presented_as_original", "presented_as_translation", "presented_new_edition",
        "presented_new_edition_note", "presented_new_edition_refe",
        "presented_original_referen",
    ]),
    ("Authors & persons", [
        "original_author", "original_author_else_refer", "original_author_elsewhere",
        "original_author_other_name", "old_author_addition_names",
        "old_author_names_other_sor", "founders", "founders_notes",
        "proofreaders", "proofreaders_notes", "old_text", "old_text_author_in_book",
        "person_name_appear",
    ]),
    ("Publication", [
        "publisher", "original_publisher", "publication_place",
        "publication_place_other", "original_publication_place",
        "original_publication_year", "gregorian_year", "year_in_book",
        "year_in_other", "hebrew_year_of_publication", "hebrew_year_pub_other",
        "gregorian_year_pub_other", "format_of_publication_date",
        "partial_publication", "printed_originally", "printers", "printers_notes",
        "printing_press_notes", "printing_press_references", "production_evidence",
        "series", "series_part",
    ]),
    ("Physical & typography", [
        "pages_number", "height", "width", "fonts", "typography",
        "illustrations_diagrams", "diagrams_notes", "diagrams_book_pages",
        "alignment",
    ]),
    ("Language & footnotes", [
        "languages", "footnote_languages", "occasional_words_languages",
        "languages_number", "location_of_footnotes", "original_language",
    ]),
    ("Content & structure", [
        "target_audience", "main_textual_models", "secondary_textual_models",
        "topic", "target_audience_notes", "textual_model_notes", "original_type",
        "structure_notes", "structure_preface_notes", "table_of_content",
        "contents_table_notes", "preface", "epilogue", "epilogue_notes",
        "dedications", "dedications_notes", "topics_notes",
    ]),
    ("Editions", [
        "total_number_of_editions", "last_known_edition", "editions_notes",
        "references_for_editions", "new_edition_general_notes",
        "new_edition_type_in_text", "new_edition_type_elsewhere",
        "new_edition_type_reference", "new_edition_type_else_ref",
        "new_edition_type_notes", "new_edition_type_else_note",
        "copy_of_book_used", "other_volumes", "volumes_notes",
        "volumes_published_number", "planned_volumes", "expanded_in_edition",
        "contradict_new_edition", "contradict_original", "examined_volume_number",
    ]),
    ("Translations", [
        "translation_notes", "translation_type",
        "presented_as_translation_refe", "presented_as_translatio_notes",
        "expanded_in_translation",
    ]),
    ("Mentions & reception", [
        "mention_general_notes", "mentions_in_reviews", "contemporary_disputes",
        "contemporary_references", "later_references",
    ]),
    ("Sources & references", [
        "bibliographical_citations", "studies", "sources_exist", "sources_list",
        "sources_not_mentioned", "sources_not_mentioned_list",
        "sources_not_mentioned_ref", "sources_references", "jewish_sources_quotes",
        "non_jewish_sources_quotes", "original_sources_mention", "references_notes",
        "secondary_sources",
    ]),
    ("Censorship & approbation", [
        "censorship", "bans", "rabbinical_approbations",
        "rabbinical_approbation_notes", "type_general_notes",
    ]),
    ("Subscription & marketing", [
        "subscribers", "subscribers_notes", "subscription_appeal",
        "subscription_appeal_notes", "recommendations", "recommendations_notes",
        "price", "sellers", "sellers_notes", "thanks", "thanks_notes",
        "contacts_official_agents", "contacts_other_people", "personal_address",
        "personal_address_notes",
    ]),
    ("Availability & catalog", [
        "not_available", "availability_notes", "other_libraries",
        "bar_ilan_library_id", "berlin_library_id", "british_library_id",
        "frankfurt_library_id", "huji_library_id", "new_york_library_id",
        "tel_aviv_library_id", "digital_book_url", "digital_book_title",
        "digital_book_attributes", "preservation_references",
        "catalog_numbers_notes",
    ]),
    ("Record metadata", [
        "legacy_nid", "legacy_created", "legacy_changed",
    ]),
]


def build_book_panels():
    panels = []
    for heading, fields in SECTIONS:
        if heading == "Basics":
            panels.append(MultiFieldPanel(_panels(fields), heading=heading))
        else:
            panels.append(MultiFieldPanel(
                _panels(fields),
                heading=heading,
                classname="collapsed",
            ))
    return panels
