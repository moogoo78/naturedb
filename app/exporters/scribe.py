"""Batch helpers for the Nature-Scribe explorer (api.scribe_specimens).

The explorer fetches up to 100 specimens per page. Per-row lazy loads on
Record.taxon ancestors and Unit.cover_image turn that into thousands of small
queries. These helpers replace the per-row work with two batched queries and
shape the result into the card-row dict the JS grid consumes.
"""
from sqlalchemy import select

from app.database import session
from app.models.collection import MultimediaObject
from app.models.taxon import Taxon, TaxonRelation


KINGDOM_TO_MEDIUM = {
    'Plantae': 'leaf',
    'Animalia': 'butterfly',
    'Mineralia': 'mineral',
    'Fungi': 'flower',
}

KINGDOM_TO_COLOR = {
    'Plantae': '#6b7a4f',
    'Animalia': '#c8a14a',
    'Mineralia': '#5a4a3a',
    'Fungi': '#8a6f4f',
}

DEFAULT_MEDIUM = 'specimen'
DEFAULT_COLOR = '#7a7a7a'


def fetch_taxon_ranks(taxon_ids, ranks=('family', 'kingdom')):
    """{taxon_id: {rank: full_scientific_name}} for the requested taxa.

    Walks up TaxonRelation to pull each requested rank's ancestor in one query.
    A taxon is considered its own ancestor (depth=0) so a kingdom-rank taxon
    correctly reports itself as its kingdom.
    """
    if not taxon_ids:
        return {}

    stmt = (
        select(
            TaxonRelation.child_id,
            Taxon.rank,
            Taxon.full_scientific_name,
        )
        .join(Taxon, TaxonRelation.parent_id == Taxon.id)
        .where(
            TaxonRelation.child_id.in_(taxon_ids),
            Taxon.rank.in_(ranks),
        )
    )

    result = {}
    for child_id, rank, sci_name in session.execute(stmt).all():
        result.setdefault(child_id, {})[rank] = sci_name
    return result


def fetch_cover_image_urls(cover_image_ids):
    """{multimedia_object_id: thumbnail_url} for the requested ids."""
    if not cover_image_ids:
        return {}

    stmt = select(MultimediaObject.id, MultimediaObject.file_url).where(
        MultimediaObject.id.in_(cover_image_ids)
    )
    return {
        mm_id: (file_url.replace('-m.jpg', '-s.jpg') if file_url else None)
        for mm_id, file_url in session.execute(stmt).all()
    }


def _completeness_pct(record, family_name, catalog_number):
    """Integer 0-100: fraction of 7 key fields that are populated."""
    fields = [
        record.proxy_taxon_scientific_name,
        record.proxy_taxon_common_name,
        family_name,
        record.verbatim_collector or (record.collector.full_name if record.collector_id and record.collector else None),
        record.collect_date or record.verbatim_collect_date,
        record.locality_text or record.verbatim_locality,
        catalog_number,
    ]
    populated = sum(1 for f in fields if f)
    return round(populated / len(fields) * 100)


def shape_specimens_page(rows, *, collection_label_map):
    """Turn a list of (Unit, Record) tuples into card-shaped dicts.

    Runs two batched queries (taxon ranks, cover images) once for the whole
    page, then assembles the dicts in-memory.
    """
    taxon_ids = [r.proxy_taxon_id for _u, r in rows if r.proxy_taxon_id]
    cover_image_ids = [u.cover_image_id for u, _r in rows if u.cover_image_id]

    rank_map = fetch_taxon_ranks(set(taxon_ids))
    image_map = fetch_cover_image_urls(set(cover_image_ids))

    items = []
    for unit, record in rows:
        ranks = rank_map.get(record.proxy_taxon_id, {}) if record.proxy_taxon_id else {}
        family = ranks.get('family')
        kingdom = ranks.get('kingdom')

        catalog = unit.catalog_number or ''
        collector = (
            record.verbatim_collector
            or (record.collector.full_name if record.collector_id and record.collector else None)
            or ''
        )
        collect_date = ''
        if record.collect_date:
            collect_date = record.collect_date.date().isoformat()
        elif record.collect_date_year:
            y = record.collect_date_year
            m = record.collect_date_month or 1
            d = record.collect_date_day or 1
            collect_date = f'{y:04d}-{m:02d}-{d:02d}'
        elif record.verbatim_collect_date:
            collect_date = record.verbatim_collect_date

        cover_url = image_map.get(unit.cover_image_id) if unit.cover_image_id else None

        items.append({
            'id': str(unit.id),
            'catalog': catalog,
            'kingdom': kingdom or '',
            'taxon': record.proxy_taxon_scientific_name or '',
            'common': record.proxy_taxon_common_name or '',
            'family': family or '',
            'collector': collector,
            'collected': collect_date,
            'locality': record.locality_text or record.verbatim_locality or '',
            'completeness': _completeness_pct(record, family, catalog),
            'annotations': 0,
            'pending': 0,
            'status': 'verified' if unit.pub_status == 'P' else 'in-review',
            'medium': KINGDOM_TO_MEDIUM.get(kingdom, DEFAULT_MEDIUM),
            'color': KINGDOM_TO_COLOR.get(kingdom, DEFAULT_COLOR),
            'cover_url': cover_url,
            'collection_id': unit.collection_id,
            'collection_label': collection_label_map.get(unit.collection_id),
        })
    return items
