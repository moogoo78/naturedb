"""Batch helpers for the TBIA occurrence harvester (api.get_occurrence).

The harvester fetches up to a few hundred specimens per request. Per-row lazy
loads on Record.named_area_maps, Unit.cover_image, and Taxon ancestor walks
turn that into thousands of small queries. These helpers replace the per-row
work with three batched queries.
"""
from sqlalchemy import select

from app.database import session
from app.models.collection import RecordNamedAreaMap, MultimediaObject
from app.models.gazetter import NamedArea, AreaClass
from app.models.taxon import Taxon, TaxonRelation


# Default area classes shown in TBIA locality string (mirrors Record.get_named_area_map).
DEFAULT_AREA_CLASS_IDS = [7, 8, 9, 10]


def _named_area_display(name_en, name):
    """Mirror NamedArea.display_name without an ORM round-trip."""
    parts = name_en or ''
    if name and name.strip():
        parts = f'{parts} ({name})'
    return parts


def fetch_named_areas_by_record(record_ids, custom_area_class_ids=None):
    """{record_id: [display_name, ...]} for the requested records.

    Includes only named_areas whose area_class is in the default set or the
    site's custom_area_class_ids. Order within a record is undefined — TBIA
    joins them with ', ' so order is not significant.
    """
    if not record_ids:
        return {}

    area_class_ids = list(DEFAULT_AREA_CLASS_IDS)
    if custom_area_class_ids:
        area_class_ids.extend(custom_area_class_ids)

    stmt = (
        select(
            RecordNamedAreaMap.record_id,
            NamedArea.name,
            NamedArea.name_en,
        )
        .join(NamedArea, RecordNamedAreaMap.named_area_id == NamedArea.id)
        .where(
            RecordNamedAreaMap.record_id.in_(record_ids),
            NamedArea.area_class_id.in_(area_class_ids),
        )
    )

    result = {}
    for record_id, name, name_en in session.execute(stmt).all():
        result.setdefault(record_id, []).append(_named_area_display(name_en, name))
    return result


def fetch_cover_image_urls(cover_image_ids):
    """{multimedia_object_id: file_url} for the requested ids."""
    if not cover_image_ids:
        return {}

    stmt = select(MultimediaObject.id, MultimediaObject.file_url).where(
        MultimediaObject.id.in_(cover_image_ids)
    )
    return {mm_id: file_url for mm_id, file_url in session.execute(stmt).all()}


def fetch_taxon_ancestors(taxon_ids):
    """{taxon_id: [(rank, display_text), ...]} for the requested taxa.

    display_text is the parent's full_scientific_name with common_name appended
    when present — same shape as the inline loop in get_occurrence used to
    produce. Ordered by depth descending (root first) to mirror
    Taxon.get_parents().
    """
    if not taxon_ids:
        return {}

    stmt = (
        select(
            TaxonRelation.child_id,
            TaxonRelation.depth,
            Taxon.rank,
            Taxon.full_scientific_name,
            Taxon.common_name,
        )
        .join(Taxon, TaxonRelation.parent_id == Taxon.id)
        .where(
            TaxonRelation.child_id.in_(taxon_ids),
            TaxonRelation.parent_id != TaxonRelation.child_id,
        )
        .order_by(TaxonRelation.child_id, TaxonRelation.depth.desc())
    )

    result = {}
    for child_id, _depth, rank, sci_name, common_name in session.execute(stmt).all():
        text = sci_name
        if common_name:
            text = f'{text} {common_name}'
        result.setdefault(child_id, []).append((rank, text))
    return result
