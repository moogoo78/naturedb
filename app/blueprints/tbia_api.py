'''
TBIA partner data-provider API, v2 ("TBIA 夥伴單位資料提供 API 規格").

    GET /tbia/v2/occurrence
    GET /tbia/v2/dataset

Lives under its own `/tbia` namespace, apart from NatureDB's own `/api/v*`
API (the spec fixes the resource names `occurrence` / `dataset` and allows a
version prefix). v2 because the legacy harvester endpoint `/api/v1/occurrence`
(api.get_occurrence) is effectively TBIA contract v1; it keeps its old shape
until TBIA switches over.

TBIA is an external aggregator (the caller), not a NatureDB site. Each
provider site exposes its own feed on its own host, e.g.
https://hast.naturedb.org/tbia/v2/occurrence, and publishes only what its
settings JSON opts in under `aggregator.tbia` (app/settings/hast.json):

    "aggregator.tbia": {
        "collection_ids": [1],
        "institutionCode": "HAST",
        "institutionID": "<GRSciColl institution URL or ROR>",
        "license": "CC-BY-NC",
        "mediaLicense": "CC-BY-NC",
        "kingdom": "Plantae",              # fallback when lineage lacks it
        "require_catalog_number": true,    # default true
        "datasets": {
            "1": {                          # key = local collection id
                "datasetID": "<stable UUID>",   # published id; default: "1"
                "datasetName": "...",
                "resourceContacts": "A|B",
                "collectionID": "<GRSciColl collection URL>",
                "gbifDatasetID": "<GBIF dataset key>"
            }
        }
    }

One dataset == one Collection. The published datasetID is the configured
`datasetID` (spec: unique, stable, UUID recommended), falling back to the
local collection id. Keep datasetName and datasetID stable once TBIA
harvests: TBIA keys rows by (datasetName, occurrenceID).

occurrenceID is the unit's ARK (https://n2t.net/ark:/...), else its public
specimen page URL, else the local unit id; `references` is the page URL.
?occurrenceID= accepts any of the three forms.

Pagination: keyset cursor (spec 做法二). Rows are ordered by unit.id;
`links.next` carries `cursor=<last unit id>` and is null on the last page.
`offset` is also accepted (做法一) for harvesters that prefer it.
'''
import re
from datetime import datetime, timedelta
from urllib.parse import urlencode, urlsplit

from flask import Blueprint, request, jsonify, current_app
from sqlalchemy import select, func
from werkzeug.exceptions import HTTPException

from app.database import session
from app.models.site import Site, Organization
from app.models.collection import (
    Record,
    Person,
    Unit,
    Collection,
)
from app.models.taxon import Taxon, TaxonTree, parse_scientific_name
from app.helpers_image import media_url_rewriter, MEDIA_CDN_SETTINGS_KEY
from app.helpers_unit_query import _detail_paths
from app.utils import strip_catalog_zeros
from app.exporters.tbia import (
    AREA_CLASS_COUNTRY,
    AREA_CLASS_ADM1,
    AREA_CLASS_ADM2,
    fetch_named_areas_by_record,
    fetch_cover_image_urls,
    fetch_taxon_lineage,
    fetch_admin_areas_by_record,
    fetch_iso2_by_iso3,
    fetch_latest_identifiers,
)

tbia_api = Blueprint('tbia_api', __name__)

DEFAULT_LIMIT = 1000
MAX_LIMIT = 1000

# Spec appendix 行政區域表: county (Chinese) -> 戶政資料代碼.
TW_COUNTY_CODES = {
    '臺北市': '63000', '臺中市': '66000', '基隆市': '10017', '臺南市': '67000',
    '高雄市': '64000', '新北市': '65000', '宜蘭縣': '10002', '桃園市': '68000',
    '嘉義市': '10020', '新竹縣': '10004', '苗栗縣': '10005', '南投縣': '10008',
    '彰化縣': '10007', '新竹市': '10018', '雲林縣': '10009', '嘉義縣': '10010',
    '屏東縣': '10013', '花蓮縣': '10015', '臺東縣': '10014', '金門縣': '9020',
    '澎湖縣': '10016', '連江縣': '9007',
}

# Ancestor ranks emitted as kingdom/phylum/.../genus (+ "<rank>Chinese").
LINEAGE_RANKS = ('kingdom', 'phylum', 'class', 'order', 'family', 'genus')

PARTY_SEP = '|'


class TbiaError(Exception):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code
        self.message = message


def _envelope(code, message, data=None, total=0, limit=None, next_url=None):
    resp = jsonify({
        'status': {'code': code, 'message': message},
        'meta': {'total': total, 'limit': limit},
        'links': {'self': _self_url(), 'next': next_url},
        'data': data if data is not None else [],
    })
    resp.status_code = code
    resp.headers['Content-Type'] = 'application/json; charset=utf-8'
    return resp


@tbia_api.errorhandler(TbiaError)
def _handle_tbia_error(e):
    return _envelope(e.code, e.message)


@tbia_api.errorhandler(HTTPException)
def _handle_http_error(e):
    return _envelope(e.code, e.description or e.name)


@tbia_api.errorhandler(Exception)
def _handle_unexpected(e):
    current_app.logger.exception('tbia_api: unhandled error')
    return _envelope(500, 'Internal Server Error')


# --- URL helpers -------------------------------------------------------------

def _external_base():
    '''request.base_url with the client-facing scheme.

    No ProxyFix is installed, so behind the TLS-terminating proxy
    request.scheme is "http". Spec requires HTTPS links.
    '''
    proto = request.headers.get('X-Forwarded-Proto', '').split(',')[0].strip()
    base = request.base_url
    if proto and base.startswith(f'{request.scheme}://'):
        base = f'{proto}://' + base[len(request.scheme) + 3:]
    return base


def _self_url():
    qs = request.query_string.decode('utf-8')
    return f'{_external_base()}?{qs}' if qs else _external_base()


def _external_root():
    '''https://host -- the client-facing origin (see _external_base).'''
    u = urlsplit(_external_base())
    return f'{u.scheme}://{u.netloc}'


ARK_PREFIX = 'https://n2t.net/ark:/'


def occurrence_id_for(guid, page_url, unit_id):
    '''occurrenceID: the unit's ARK (permanent, survives catalog-number edits
    and domain moves), else its public page URL, else the local unit id.
    TBIA keys rows on (datasetName, occurrenceID): units without an ARK
    should be minted one before the first harvest, or their id changes.'''
    if guid and guid.startswith(ARK_PREFIX):
        return guid
    return page_url or str(unit_id)


def _url_with(**overrides):
    args = request.args.to_dict(flat=True)
    args.pop('offset', None)
    args.update({k: str(v) for k, v in overrides.items()})
    return f'{_external_base()}?{urlencode(args)}'


# --- parameter parsing (pure; unit-tested) -----------------------------------

_DATE_RE = re.compile(r'^\d{8}$')


def parse_modified(value):
    '''"YYYYMMDD" or "YYYYMMDD,YYYYMMDD" -> (start, end_exclusive) datetimes.

    Both ends are inclusive whole days, so end is the following midnight.
    '''
    if value is None or value == '':
        return None
    parts = [p.strip() for p in value.split(',')]
    if len(parts) not in (1, 2) or not all(_DATE_RE.match(p) for p in parts):
        raise TbiaError(400, 'modified must be YYYYMMDD or YYYYMMDD,YYYYMMDD')
    try:
        start = datetime.strptime(parts[0], '%Y%m%d')
        end = datetime.strptime(parts[-1], '%Y%m%d')
    except ValueError:
        raise TbiaError(400, 'modified contains an invalid date')
    if end < start:
        raise TbiaError(400, 'modified range end is before start')
    return start, end + timedelta(days=1)


def parse_int_arg(name, default, minimum, maximum=None):
    raw = request.args.get(name)
    if raw is None or raw == '':
        return default
    try:
        value = int(raw)
    except ValueError:
        raise TbiaError(400, f'{name} must be an integer')
    if value < minimum or (maximum is not None and value > maximum):
        bound = f'{minimum}..{maximum}' if maximum is not None else f'>= {minimum}'
        raise TbiaError(400, f'{name} must be {bound}')
    return value


# --- value formatting (pure; unit-tested) ------------------------------------

def fmt_datetime(dt):
    '''Spec time format "YYYYMMDD HHMMSS". Stored timestamps are already
    Taiwan local time (app.utils.get_time = UTC+8).'''
    return dt.strftime('%Y%m%d %H%M%S') if dt else None


def fmt_rank(rank):
    '''Controlled vocab 鑑定層級: "Species", "Subspecies", ...'''
    if not rank:
        return None
    return rank[0].upper() + rank[1:]


def fmt_type_status(type_status):
    '''Controlled vocab typeStatus is upper-case (HOLOTYPE, ...).'''
    if not type_status:
        return None
    return PARTY_SEP.join(x.strip().upper() for x in type_status.split('|') if x.strip())


def split_taxon_name(canonical, full, author, rank):
    '''(scientificName, scientificNameAuthorship) without the author inline.

    TaiCOL taxa have canonical_name/author split; HAST-legacy taxa store the
    author inside full_scientific_name, so parse it out for species-level
    names. Higher ranks in legacy trees carry no author.
    '''
    if canonical:
        return canonical, author or None
    if not full:
        return None, None
    parsed, _binomial, parsed_author = parse_scientific_name(full)
    if parsed:
        return parsed, (parsed_author or author or None)
    return full, author or None


def person_display(full_name, full_name_en):
    if full_name_en and full_name:
        return f'{full_name_en} ({full_name})'
    return full_name or full_name_en or None


def nullable(value):
    '''Spec: missing values are null, never "" (strings are stripped).'''
    if isinstance(value, str):
        value = value.strip()
        return value or None
    return value


# --- provider site / settings ------------------------------------------------
#
# The Host header picks the *provider* site whose data is served; TBIA itself
# is only the harvesting client.
SETTINGS_KEY = 'aggregator.tbia'


def _resolve_site_config():
    host = request.headers.get('Host')
    site = Site.find_by_host(host) if host else None
    if site is None:
        raise TbiaError(404, 'unknown provider site')
    conf = site.get_settings(SETTINGS_KEY)
    if not conf:
        raise TbiaError(404, 'this site does not publish a TBIA feed')

    collection_ids = list(conf.get('collection_ids') or site.collection_ids)
    try:
        dataset_map = build_dataset_map(conf, collection_ids)
    except TbiaError:
        current_app.logger.error(f'{SETTINGS_KEY} of site {site.name!r}: duplicate datasetID')
        raise
    return site, conf, collection_ids, dataset_map


def _dataset_conf(conf, collection_id):
    return (conf.get('datasets') or {}).get(str(collection_id), {})


def dataset_id_for(conf, collection_id):
    '''Published datasetID: configured value, else the local collection id.'''
    return str(_dataset_conf(conf, collection_id).get('datasetID') or collection_id)


def build_dataset_map(conf, collection_ids):
    '''{published datasetID: collection_id}; duplicates are a config error.

    Two collections sharing a datasetID would be merged into one dataset on
    TBIA's side, so fail loudly instead of serving it.
    '''
    dataset_map = {}
    for cid in collection_ids:
        did = dataset_id_for(conf, cid)
        if did in dataset_map:
            raise TbiaError(500, f'duplicate datasetID in {SETTINGS_KEY} settings')
        dataset_map[did] = cid
    return dataset_map


def _base_conditions(conf, collection_ids):
    conds = [
        Unit.pub_status == 'P',
        Unit.collection_id.in_(collection_ids),
    ]
    if conf.get('require_catalog_number', True):
        conds.append(Unit.catalog_number != '')
        conds.append(Unit.catalog_number.isnot(None))
    return conds


def _resolve_occurrence_id(value, conds):
    '''Unit id for an occurrenceID in any form the feed emits (ARK, page
    URL, local id), within the feed's own conditions; None if unknown.'''
    def first(*extra):
        return session.execute(select(Unit.id).join(Record, Unit.record_id == Record.id)
                               .where(*conds, *extra).limit(2)).scalars().all()

    if value.startswith(ARK_PREFIX):
        ids = first(Unit.guid == value)
        return ids[0] if len(ids) == 1 else None
    if '/specimens/' in value:
        # page URL: candidates by catalog number, then the one whose page it is
        key = value.rstrip('/').rsplit('/specimens/', 1)[1].rsplit(':', 1)[-1]
        if not key:
            return None
        rows = session.execute(
            select(Unit.id, Unit.catalog_number, Unit.collection_id, Unit.pub_status)
            .join(Record, Unit.record_id == Record.id)
            .where(*conds, func.ltrim(Unit.catalog_number, '0') == key.lstrip('0'))
            .limit(50)).all()
        path = value[value.index('/specimens/'):]
        hits = [uid for uid, p in _detail_paths(rows).items() if p.rstrip('/') == path.rstrip('/')]
        return hits[0] if len(hits) == 1 else None
    if value.isdigit():
        return int(value)
    return None


def _modified_expr():
    # A record edit (locality, collector, ...) changes every unit it carries,
    # so the occurrence is as new as the newer of the two rows. GREATEST
    # ignores NULLs in PostgreSQL; created is the last-resort fallback.
    return func.coalesce(func.greatest(Unit.updated, Record.updated), Unit.created)


# --- /occurrence ---------------------------------------------------------------

@tbia_api.route('/occurrence', methods=['GET'])
def get_occurrence():
    site, conf, collection_ids, dataset_map = _resolve_site_config()

    limit = parse_int_arg('limit', DEFAULT_LIMIT, 1, MAX_LIMIT)
    offset = parse_int_arg('offset', None, 0)
    cursor = parse_int_arg('cursor', None, 0)
    if offset is not None and cursor is not None:
        raise TbiaError(400, 'use either offset or cursor, not both')

    modified_expr = _modified_expr()
    conds = _base_conditions(conf, collection_ids)

    if occurrence_id := request.args.get('occurrenceID'):
        # Unknown id -> valid query, zero rows (spec: 200 + []).
        uid = _resolve_occurrence_id(occurrence_id.strip(), conds)
        conds.append(Unit.id == uid if uid is not None else Unit.id.is_(None))
    if catalog_number := request.args.get('catalogNumber'):
        conds.append(Unit.catalog_number == catalog_number)
    if dataset_id := request.args.get('datasetID'):
        # Unknown id -> valid query, zero rows (spec: 200 + []).
        cid = dataset_map.get(dataset_id)
        conds.append(Unit.collection_id == cid if cid is not None else Unit.id.is_(None))
    if rng := parse_modified(request.args.get('modified')):
        conds.append(modified_expr >= rng[0])
        conds.append(modified_expr < rng[1])

    total = session.execute(
        select(func.count())
        .select_from(Unit)
        .join(Record, Unit.record_id == Record.id)
        .where(*conds)
    ).scalar()

    page_conds = list(conds)
    if cursor is not None:
        page_conds.append(Unit.id > cursor)

    stmt = (
        select(
            Unit.id,
            Unit.catalog_number,
            Unit.type_status,
            Unit.basis_of_record,
            Unit.kind_of_unit,
            Unit.preparation_type,
            Unit.guid,
            Unit.pub_status,
            Unit.cover_image_id,
            Unit.collection_id,
            Unit.created,
            modified_expr.label('modified'),
            Record.id.label('record_id'),
            Record.field_number,
            Record.verbatim_collector,
            Record.companion_text,
            Record.companion_text_en,
            Record.collect_date,
            Record.collect_date_year,
            Record.collect_date_month,
            Record.collect_date_day,
            Record.verbatim_collect_date,
            Record.locality_text,
            Record.locality_text_en,
            Record.verbatim_locality,
            Record.latitude_decimal,
            Record.longitude_decimal,
            Record.verbatim_latitude,
            Record.verbatim_longitude,
            Record.geodetic_datum,
            Record.coordinate_uncertainty_in_meters,
            Record.proxy_taxon_id,
            Record.proxy_taxon_scientific_name,
            Record.proxy_taxon_common_name,
            Person.full_name.label('collector_name'),
            Person.full_name_en.label('collector_name_en'),
            Taxon.rank.label('taxon_rank'),
            Taxon.canonical_name,
            Taxon.full_scientific_name,
            Taxon.author,
            Taxon.common_name,
            Collection.label.label('collection_label'),
            Organization.code.label('organization_code'),
        )
        .join(Record, Unit.record_id == Record.id)
        .join(Collection, Unit.collection_id == Collection.id)
        .join(Organization, Collection.organization_id == Organization.id, isouter=True)
        .join(Person, Record.collector_id == Person.id, isouter=True)
        .join(Taxon, Record.proxy_taxon_id == Taxon.id, isouter=True)
        .where(*page_conds)
        .order_by(Unit.id)  # unique + immutable: stable for cursor and offset
        .limit(limit)
    )
    if offset is not None:
        stmt = stmt.offset(offset)

    page = session.execute(stmt).all()

    record_ids = [r.record_id for r in page]
    taxon_ids = [r.proxy_taxon_id for r in page if r.proxy_taxon_id]
    custom_area_class_ids = [x.id for x in site.get_custom_area_classes()]

    # Administrative areas go to countryCode/county/municipality, not locality.
    named_areas = fetch_named_areas_by_record(record_ids, custom_area_class_ids, include_admin=False)
    admin_areas = fetch_admin_areas_by_record(record_ids)
    # Public specimen page per unit -> references, and occurrenceID for units without an ARK.
    root = _external_root()
    page_urls = {uid: root + path for uid, path in _detail_paths(page).items()}
    cover_urls = fetch_cover_image_urls([r.cover_image_id for r in page if r.cover_image_id])
    # Publish media via the site's CDN host (stable URL TBIA can store), not raw S3.
    to_public = media_url_rewriter(site.get_settings(MEDIA_CDN_SETTINGS_KEY))
    # Record's own name -> verbatim*; its TaiCOL (reference tree) match ->
    # scientificName/taxonID/taxonRank/lineage + nameAccordingTo.
    ref_by_taxon, ref_lineages, name_according_to = match_reference_taxa(site, taxon_ids)
    lineages = fetch_taxon_lineage(taxon_ids)
    identifiers = fetch_latest_identifiers(record_ids)
    iso2 = fetch_iso2_by_iso3(
        [a[AREA_CLASS_COUNTRY][2] for a in admin_areas.values() if AREA_CLASS_COUNTRY in a]
    )

    data = [
        serialize_occurrence(
            r, conf,
            named_areas=named_areas.get(r.record_id, []),
            admin_areas=admin_areas.get(r.record_id, {}),
            iso2=iso2,
            cover_url=to_public(cover_urls.get(r.cover_image_id)),
            page_url=page_urls.get(r.id),
            lineage=lineages.get(r.proxy_taxon_id, {}),
            identified_by=identifiers.get(r.record_id),
            ref=(ref := ref_by_taxon.get(r.proxy_taxon_id)),
            ref_lineage=ref_lineages.get(ref.id, {}) if ref else {},
            name_according_to=name_according_to,
        )
        for r in page
    ]

    next_url = None
    if len(page) == limit:
        if offset is not None:
            if offset + limit < total:
                next_url = _url_with(offset=offset + limit)
        else:
            # Probe instead of comparing with total: total ignores the cursor.
            has_more = session.execute(
                select(Unit.id)
                .join(Record, Unit.record_id == Record.id)
                .where(*conds, Unit.id > page[-1].id)
                .limit(1)
            ).first()
            if has_more:
                next_url = _url_with(cursor=page[-1].id)

    return _envelope(200, 'Success', data=data, total=total, limit=limit, next_url=next_url)


INFRASPECIFIC_RANKS = ('subspecies', 'variety', 'form')


def name_according_to_for(tree):
    '''"TaiCOL260224" -> "臺灣物種名錄 20260224版本" (spec example style);
    other trees publish their name as-is.'''
    if not tree or not tree.name:
        return None
    m = re.match(r'^TaiCOL[\s\-_]*(\d{6}|\d{8})$', tree.name)
    if m:
        v = m.group(1)
        return f'臺灣物種名錄 {"20" + v if len(v) == 6 else v}版本'
    return tree.name


def match_reference_taxa(site, taxon_ids):
    '''Match the page's taxa into the site's reference tree (TaiCOL).

    Returns ({taxon_id: ref Taxon}, {ref_id: lineage}, nameAccordingTo).
    Uses `frontend.taxon.reference` -- the same match the specimen page shows.
    '''
    ref_conf = site.get_settings('frontend.taxon.reference') or {}
    tree_id = ref_conf.get('tree_id')
    if not tree_id or not taxon_ids:
        return {}, {}, None

    taxa = session.execute(select(Taxon).where(Taxon.id.in_(set(taxon_ids)))).scalars().all()
    # stored matches (incl. synonyms), live name match for taxa not built yet
    matches = Taxon.get_reference_matches(taxa, tree_id, ref_conf.get('prefer_kingdoms'))
    ref_by_taxon = {tid: ref for tid, (ref, _) in matches.items() if ref}

    refs = {ref.id: ref for ref in ref_by_taxon.values()}
    ref_lineages = fetch_taxon_lineage(list(refs))
    # TaiCOL infraspecific taxa are unlinked in the closure table: borrow the
    # species' lineage (same as the specimen page).
    orphans = {}
    for ref in refs.values():
        if ref.rank in INFRASPECIFIC_RANKS and not ref_lineages.get(ref.id):
            _, binomial, _ = parse_scientific_name(ref.canonical_name or ref.full_scientific_name)
            if binomial:
                orphans.setdefault(binomial, []).append(ref.id)
    if orphans:
        species = session.execute(select(Taxon.id, Taxon.canonical_name).where(
            Taxon.tree_id == tree_id, Taxon.rank == 'species',
            Taxon.canonical_name.in_(list(orphans)))).all()
        sp_ids = {name: sid for sid, name in species}
        sp_lineages = fetch_taxon_lineage(list(sp_ids.values()))
        for binomial, ref_ids in orphans.items():
            if binomial in sp_ids:
                for rid in ref_ids:
                    ref_lineages[rid] = sp_lineages.get(sp_ids[binomial], {})

    return ref_by_taxon, ref_lineages, name_according_to_for(session.get(TaxonTree, tree_id))


def _taicol_name_id(ref):
    '''TaiCOL name_id (numeric string, e.g. "2905") from the ref taxon's source_data.'''
    data = ref.source_data if ref is not None else None
    return nullable(data.get('name_id')) if isinstance(data, dict) else None


def _primary_common(name):
    '''TaiCOL common names are "primary|alt,alt"; publish the primary one.'''
    return nullable(name.split('|')[0]) if name else None


def serialize_occurrence(r, conf, named_areas, admin_areas, iso2, cover_url, lineage, identified_by,
                         ref=None, ref_lineage=None, name_according_to=None, page_url=None):
    ds = _dataset_conf(conf, r.collection_id)

    # scientificName & co. describe the TaiCOL match only (spec: 校定 = the
    # TaiCOL name for the adopted taxon_id); no match -> null, TBIA matches
    # from verbatimScientificName + the higher ranks.
    if ref:
        sci_name, sci_author = split_taxon_name(
            ref.canonical_name, ref.full_scientific_name, ref.author, ref.rank,
        )
        lineage = ref_lineage or {}
        own_rank, own_common = ref.rank, _primary_common(ref.common_name)
    else:
        sci_name = sci_author = None
        local_name, _ = split_taxon_name(
            r.canonical_name, r.full_scientific_name, r.author, r.taxon_rank,
        )
        own_rank, own_common = r.taxon_rank, nullable(r.common_name)

    # locality: site-specific (non-administrative) named areas such as national
    # park, then the free-text locality. Administrative levels are published
    # separately (countryCode/county/municipality), so they are not repeated.
    locality_parts = list(named_areas)
    for x in (r.locality_text, r.locality_text_en):
        if x and x.strip():
            locality_parts.append(x.strip())
    locality = ', '.join(locality_parts) or nullable(r.verbatim_locality)

    lat = float(r.latitude_decimal) if r.latitude_decimal is not None else None
    lon = float(r.longitude_decimal) if r.longitude_decimal is not None else None

    verbatim_lat = nullable(r.verbatim_latitude)
    verbatim_lon = nullable(r.verbatim_longitude)
    verbatim_cs = verbatim_srs = None
    if verbatim_lat is None and verbatim_lon is None and lat is not None and lon is not None:
        # Only decimal degrees are stored; mirror them as the verbatim pair.
        verbatim_lat, verbatim_lon = str(lat), str(lon)
        verbatim_cs, verbatim_srs = 'DecimalDegrees', 'EPSG:4326'

    country = admin_areas.get(AREA_CLASS_COUNTRY)
    adm1 = admin_areas.get(AREA_CLASS_ADM1)
    adm2 = admin_areas.get(AREA_CLASS_ADM2)
    country_code = iso2.get(country[2]) if country else None
    county = county_code = municipality = None
    if adm1 and adm1[0] in TW_COUNTY_CODES:
        # 行政區域表 covers Taiwan only; foreign ADM1 stay in `locality`.
        county = adm1[0]
        county_code = TW_COUNTY_CODES[county]
        municipality = nullable(adm2[0]) if adm2 else None

    year, month, day = r.collect_date_year, r.collect_date_month, r.collect_date_day
    if r.collect_date and not year:
        year, month, day = r.collect_date.year, r.collect_date.month, r.collect_date.day
    verbatim_date = nullable(r.verbatim_collect_date)
    if verbatim_date is None and r.collect_date:
        verbatim_date = r.collect_date.strftime('%Y-%m-%d')

    preparations = Unit.KIND_OF_UNIT_MAP.get(r.kind_of_unit) or nullable(r.kind_of_unit)
    if not preparations and r.preparation_type:
        preparations = Unit.PREPARATION_TYPE_MAP.get(r.preparation_type) or r.preparation_type

    associated_media = cover_url.replace('-m.jpg', '-l.jpg') if cover_url else None

    row = {
        'occurrenceID': occurrence_id_for(r.guid, page_url, r.id),
        'catalogNumber': nullable(r.catalog_number),
        'eventID': None,
        'created': fmt_datetime(r.created),
        'modified': fmt_datetime(r.modified),
        'selfProduced': bool(conf.get('selfProduced', True)),
        'license': conf.get('license'),
        'basisOfRecord': nullable(r.basis_of_record) or conf.get('basisOfRecord', 'PreservedSpecimen'),
        'recordNumber': nullable(r.field_number),
        'recordedBy': person_display(r.collector_name, r.collector_name_en) or nullable(r.verbatim_collector),
        'samplingProtocol': None,
        'partner': nullable(r.companion_text) or nullable(r.companion_text_en),
        'identifiedBy': identified_by,
        'datasetName': ds.get('datasetName') or r.collection_label,
        'datasetID': dataset_id_for(conf, r.collection_id),
        'resourceCitationIdentifier': ds.get('resourceCitationIdentifier'),
        'resourceContacts': ds.get('resourceContacts') or conf.get('resourceContacts'),
        'associatedMedia': associated_media,
        'mediaLicense': conf.get('mediaLicense') if associated_media else None,
        'individualCount': 1,
        'organismQuantity': None,
        'organismQuantityType': None,
        # The human-readable page (spec: 來源資料庫的網頁URL); the ARK is occurrenceID.
        'references': page_url or nullable(r.guid),
        'typeStatus': fmt_type_status(r.type_status),
        'preparations': preparations,
        'institutionCode': conf.get('institutionCode') or nullable(r.organization_code),
        'institutionID': conf.get('institutionID'),
        # Settings only: Collection.name is a local slug, not a published code.
        'collectionCode': nullable(ds.get('collectionCode')),
        'collectionID': ds.get('collectionID'),
        'locality': locality,
        'verbatimLongitude': verbatim_lon,
        'verbatimLatitude': verbatim_lat,
        'verbatimCoordinateSystem': verbatim_cs,
        'verbatimSRS': verbatim_srs,
        'geodeticDatum': nullable(r.geodetic_datum) or ('EPSG:4326' if lat is not None else None),
        'coordinateUncertaintyInMeters': (
            float(r.coordinate_uncertainty_in_meters)
            if r.coordinate_uncertainty_in_meters is not None else None
        ),
        # Raw coordinates are sent on purpose: TBIA does the masking itself.
        'dataGeneralizations': None,
        'decimalLatitude': lat,
        'decimalLongitude': lon,
        'countryCode': country_code,
        'county': county,
        'countyCode': county_code,
        'municipality': municipality,
        'verbatimEventDate': verbatim_date,
        'year': year,
        'month': month,
        'day': day,
        'eventTime': None,
        # C: required only when nothing else names the taxon; the verbatim
        # scientific name below already does.
        'verbatimIdentification': None,
        # The record's own identification, as stored.
        'verbatimScientificName': nullable(r.proxy_taxon_scientific_name),
        'verbatimVernacularName': nullable(r.proxy_taxon_common_name),
        # The TaiCOL match (reference tree); all null when unmatched.
        'taxonID': nullable(ref.source_id) if ref else None,
        'scientificName': sci_name,
        'scientificNameAuthorship': sci_author,
        'vernacularName': _primary_common(ref.common_name) if ref else None,
        # TaiCOL name_id of the accepted name (the CSV row loaded into source_data).
        'scientificNameID': _taicol_name_id(ref),
        'nameAccordingTo': name_according_to if ref else None,
        # M: the TaiCOL rank; unmatched rows keep the local rank so the field is filled.
        'taxonRank': fmt_rank(own_rank),
        # Per-occurrence group is derived by TBIA from its TaiCOL match; a
        # dataset-wide value ("裸子植物|被子植物|...") would be wrong per row.
        'taxonGroup': None,
        'sensitiveCategory': None,
    }

    # The closure lookup returns ancestors only; a record identified at
    # genus/family must fill its own rank slot too.
    own_name = sci_name if ref else local_name
    if own_rank in LINEAGE_RANKS and own_name:
        lineage = {**lineage, own_rank: (own_name, own_common)}

    for rank in LINEAGE_RANKS:
        name, common = lineage.get(rank, (None, None))
        row[rank] = name
        row[f'{rank}Chinese'] = common
    if row['kingdom'] is None:
        row['kingdom'] = conf.get('kingdom')

    return row


# --- /dataset ------------------------------------------------------------------

@tbia_api.route('/dataset', methods=['GET'])
def get_dataset():
    site, conf, collection_ids, dataset_map = _resolve_site_config()

    limit = parse_int_arg('limit', DEFAULT_LIMIT, 1, MAX_LIMIT)
    offset = parse_int_arg('offset', 0, 0)
    rng = parse_modified(request.args.get('modified'))
    dataset_id = request.args.get('datasetID')
    dataset_name = request.args.get('datasetName')

    collections = session.execute(
        select(Collection).where(Collection.id.in_(collection_ids)).order_by(Collection.id)
    ).scalars().all()

    # One grouped pass for counts and coverage dates of every dataset.
    unit_conds = _base_conditions(conf, collection_ids)
    stats = {
        cid: (count, date_min, date_max)
        for cid, count, date_min, date_max in session.execute(
            select(
                Unit.collection_id,
                func.count(Unit.id),
                func.min(Record.collect_date),
                func.max(Record.collect_date),
            )
            .join(Record, Unit.record_id == Record.id)
            .where(*unit_conds)
            .group_by(Unit.collection_id)
        ).all()
    }

    items = []
    for c in collections:
        ds = _dataset_conf(conf, c.id)
        count, date_min, date_max = stats.get(c.id, (0, None, None))
        modified_at = c.updated or c.created
        item = {
            'datasetName': ds.get('datasetName') or c.label,
            'datasetID': dataset_id_for(conf, c.id),
            'gbifDatasetID': ds.get('gbifDatasetID'),
            'resourceContacts': ds.get('resourceContacts') or conf.get('resourceContacts'),
            'occurrenceCount': count,
            'datasetDateStart': date_min.strftime('%Y%m%d') if date_min else None,
            'datasetDateEnd': date_max.strftime('%Y%m%d') if date_max else None,
            'resourceCitationIdentifier': ds.get('resourceCitationIdentifier'),
            'datasetPublisher': ds.get('datasetPublisher') or conf.get('datasetPublisher'),
            'datasetLicense': ds.get('datasetLicense') or conf.get('license'),
            'datasetTaxonGroup': ds.get('taxonGroup'),
            'created': fmt_datetime(c.created),
            'modified': fmt_datetime(modified_at),
        }

        if dataset_id and item['datasetID'] != dataset_id:
            continue
        if dataset_name and item['datasetName'] != dataset_name:
            continue
        if rng and not (modified_at and rng[0] <= modified_at < rng[1]):
            continue
        items.append(item)

    total = len(items)
    page = items[offset:offset + limit]
    next_url = _url_with(offset=offset + limit) if offset + limit < total else None
    return _envelope(200, 'Success', data=page, total=total, limit=limit, next_url=next_url)
