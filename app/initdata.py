"""Example ("demo") site seed data.

Loaded by `flask initdata` (see app/commands.py). The point is that a fresh
clone can go from `git clone` to a browsable site without a production dump:

    make init      # or: docker compose up -d && make migrate && make initdata

Everything here is written with EXPLICIT primary keys. That is not stylistic --
several ids are load-bearing in the codebase:

  * area_class 7/8/9/10 must be COUNTRY/ADM1/ADM2/ADM3. Those ids are hardcoded
    in Record.get_named_area_map(), NamedArea.get_country(), the record form
    (`filter:area_class_id=7`), the quick-edit country dropdown and the TBIA
    exporter.
  * area_class 5/6 are the "custom" classes (national_park / locality); see
    `custom_area_classes` in app/settings/demo.json and helpers.get_form_layout,
    which selects ids 5..6 for collection 1.
  * collection 1 / site 1 keep the demo aligned with those same assumptions.

Re-running is safe: every row is created only when its primary key is free, and
the sequences are re-synced at the end so later inserts from the admin UI do not
collide with the seeded ids.
"""
from datetime import datetime

from werkzeug.security import generate_password_hash
from sqlalchemy import text

from app.database import session
from app.models.site import (
    Article,
    ArticleCategory,
    Organization,
    Site,
    User,
)
from app.models.gazetter import (
    AreaClass,
    Country,
    NamedArea,
)
from app.models.taxon import (
    Taxon,
    TaxonTree,
)
from app.models.collection import (
    AnnotationType,
    AssertionType,
    AssertionTypeOption,
    Collection,
    CollectionTaxonMap,
    Identification,
    Person,
    Record,
    RecordAssertion,
    RecordNamedAreaMap,
    Unit,
    UnitAssertion,
)

SITE_NAME = 'demo'

# ---------------------------------------------------------------- site/org ---

SITES = [
    {
        'id': 1,
        'name': SITE_NAME,
        'title': '示範自然史典藏',
        'title_en': 'NatureDB Demo Collection',
        'description': '這是 NatureDB 的範例網站，資料皆為示範用途，並非真實館藏。',
        # Exact-host match wins; in dev Site.find_by_host() also falls back to
        # matching Site.name against the first label of the Host header, so
        # http://demo.localhost:5000/ resolves to this site too.
        'host': 'localhost:5000',
    },
]

ORGANIZATIONS = [
    {
        'id': 1,
        'site_id': 1,
        'name': '示範博物館植物標本館',
        'short_name': 'Demo Herbarium',
        'code': 'DEMO',
        'website_url': 'https://example.org',
        'taxonomic_scope': 'Vascular plants',
        'geographic_scope': 'Taiwan',
    },
]

COLLECTIONS = [
    {
        'id': 1,
        'site_id': 1,
        'organization_id': 1,
        'name': 'demo',
        'label': 'Demo Herbarium',
        'sort': 1,
    },
]

# ------------------------------------------------------------- area classes ---
# ids 1-4 are the legacy classes kept only so the ids below line up with the
# rest of the codebase (`AreaClass.id > 4` is used as a filter in api.py).

AREA_CLASSES = [
    {'id': 1, 'name': 'country', 'label': '國家 (legacy)', 'sort': 1, 'collection_id': 1},
    {'id': 2, 'name': 'stateProvince', 'label': '省/州 (legacy)', 'sort': 2, 'collection_id': 1, 'parent_id': 1},
    {'id': 3, 'name': 'county', 'label': '縣/市 (legacy)', 'sort': 3, 'collection_id': 1, 'parent_id': 2},
    {'id': 4, 'name': 'municipality', 'label': '鄉/鎮 (legacy)', 'sort': 4, 'collection_id': 1, 'parent_id': 3},
    {'id': 5, 'name': 'national_park', 'label': '國家公園', 'sort': 5, 'collection_id': 1},
    {'id': 6, 'name': 'locality', 'label': '地名', 'sort': 6, 'collection_id': 1},
    {'id': 7, 'name': 'COUNTRY', 'label': '國家', 'sort': 7},
    {'id': 8, 'name': 'ADM1', 'label': '1級行政區', 'sort': 8, 'parent_id': 7},
    {'id': 9, 'name': 'ADM2', 'label': '2級行政區', 'sort': 9, 'parent_id': 8},
    {'id': 10, 'name': 'ADM3', 'label': '3級行政區', 'sort': 10, 'parent_id': 9},
]

COUNTRIES = [
    {'id': 1, 'name_en': 'Taiwan', 'name_zh': '臺灣', 'continent': 'Asia', 'iso3166_1': 'TW', 'iso3': 'TWN', 'sort': 1},
    {'id': 2, 'name_en': 'Japan', 'name_zh': '日本', 'continent': 'Asia', 'iso3166_1': 'JP', 'iso3': 'JPN', 'sort': 2},
]

NAMED_AREAS = [
    {'id': 1, 'area_class_id': 7, 'name': '臺灣', 'name_en': 'Taiwan', 'code': 'TWN'},
    {'id': 2, 'area_class_id': 7, 'name': '日本', 'name_en': 'Japan', 'code': 'JPN'},

    {'id': 3, 'area_class_id': 8, 'parent_id': 1, 'name': '南投縣', 'name_en': 'Nantou County'},
    {'id': 4, 'area_class_id': 8, 'parent_id': 1, 'name': '臺北市', 'name_en': 'Taipei City'},
    {'id': 5, 'area_class_id': 8, 'parent_id': 1, 'name': '花蓮縣', 'name_en': 'Hualien County'},

    {'id': 6, 'area_class_id': 9, 'parent_id': 3, 'name': '仁愛鄉', 'name_en': "Ren'ai Township"},
    {'id': 7, 'area_class_id': 9, 'parent_id': 3, 'name': '信義鄉', 'name_en': 'Xinyi Township'},
    {'id': 8, 'area_class_id': 9, 'parent_id': 4, 'name': '北投區', 'name_en': 'Beitou District'},
    {'id': 9, 'area_class_id': 9, 'parent_id': 5, 'name': '秀林鄉', 'name_en': 'Xiulin Township'},

    {'id': 10, 'area_class_id': 5, 'name': '玉山國家公園', 'name_en': 'Yushan National Park'},
    {'id': 11, 'area_class_id': 5, 'name': '陽明山國家公園', 'name_en': 'Yangmingshan National Park'},
    {'id': 12, 'area_class_id': 5, 'name': '太魯閣國家公園', 'name_en': 'Taroko National Park'},

    {'id': 13, 'area_class_id': 6, 'name': '塔塔加', 'name_en': 'Tataka'},
    {'id': 14, 'area_class_id': 6, 'name': '大屯山', 'name_en': 'Mt. Datun'},
    {'id': 15, 'area_class_id': 6, 'name': '合歡山', 'name_en': 'Mt. Hehuan'},
]

# ------------------------------------------------------------------ taxa ------

TAXON_TREES = [
    {
        'id': 1,
        'name': 'Demo backbone',
        'memo': '範例分類樹，僅收錄示範資料所需的科／屬／種。',
        'hierarchy': list(Taxon.RANK_HIERARCHY_MAJOR),
        'is_external': False,
    },
]

# `parents` maps rank -> taxon id and is fed to Taxon.make_relations(), which
# maintains the taxon_relation closure table (depth 0 self row included).
TAXA = [
    {'id': 1, 'rank': 'family', 'full_scientific_name': 'Fagaceae', 'canonical_name': 'Fagaceae', 'common_name': '殼斗科'},
    {'id': 2, 'rank': 'genus', 'full_scientific_name': 'Quercus', 'canonical_name': 'Quercus', 'common_name': '櫟屬',
     'parents': {'family': 1}},
    {'id': 3, 'rank': 'species', 'full_scientific_name': 'Quercus glauca Thunb.', 'canonical_name': 'Quercus glauca',
     'specific_epithet': 'glauca', 'author': 'Thunb.', 'common_name': '青剛櫟', 'parents': {'family': 1, 'genus': 2}},
    {'id': 4, 'rank': 'species', 'full_scientific_name': 'Quercus variabilis Blume', 'canonical_name': 'Quercus variabilis',
     'specific_epithet': 'variabilis', 'author': 'Blume', 'common_name': '栓皮櫟', 'parents': {'family': 1, 'genus': 2}},

    {'id': 5, 'rank': 'family', 'full_scientific_name': 'Lauraceae', 'canonical_name': 'Lauraceae', 'common_name': '樟科'},
    {'id': 6, 'rank': 'genus', 'full_scientific_name': 'Cinnamomum', 'canonical_name': 'Cinnamomum', 'common_name': '樟屬',
     'parents': {'family': 5}},
    {'id': 7, 'rank': 'species', 'full_scientific_name': 'Cinnamomum camphora (L.) J.Presl',
     'canonical_name': 'Cinnamomum camphora', 'specific_epithet': 'camphora', 'author': '(L.) J.Presl',
     'common_name': '樟樹', 'parents': {'family': 5, 'genus': 6}},
    {'id': 8, 'rank': 'genus', 'full_scientific_name': 'Machilus', 'canonical_name': 'Machilus', 'common_name': '楨楠屬',
     'parents': {'family': 5}},
    {'id': 9, 'rank': 'species', 'full_scientific_name': 'Machilus thunbergii Siebold & Zucc.',
     'canonical_name': 'Machilus thunbergii', 'specific_epithet': 'thunbergii', 'author': 'Siebold & Zucc.',
     'common_name': '紅楠', 'parents': {'family': 5, 'genus': 8}},

    {'id': 10, 'rank': 'family', 'full_scientific_name': 'Asteraceae', 'canonical_name': 'Asteraceae', 'common_name': '菊科'},
    {'id': 11, 'rank': 'genus', 'full_scientific_name': 'Bidens', 'canonical_name': 'Bidens', 'common_name': '鬼針草屬',
     'parents': {'family': 10}},
    {'id': 12, 'rank': 'species', 'full_scientific_name': 'Bidens pilosa L.', 'canonical_name': 'Bidens pilosa',
     'specific_epithet': 'pilosa', 'author': 'L.', 'common_name': '大花咸豐草', 'parents': {'family': 10, 'genus': 11}},
    {'id': 13, 'rank': 'genus', 'full_scientific_name': 'Ainsliaea', 'canonical_name': 'Ainsliaea', 'common_name': '兔兒風屬',
     'parents': {'family': 10}},
    {'id': 14, 'rank': 'species', 'full_scientific_name': 'Ainsliaea latifolia (D.Don) Sch.Bip.',
     'canonical_name': 'Ainsliaea latifolia', 'specific_epithet': 'latifolia', 'author': '(D.Don) Sch.Bip.',
     'common_name': '燈臺兔兒風', 'parents': {'family': 10, 'genus': 13}},
]

# collection -> branch of a taxon tree, drives the family filter on /data
COLLECTION_TAXON_MAPS = [
    {'id': 1, 'collection_id': 1, 'taxon_tree_id': 1, 'taxon_id': 1},
    {'id': 2, 'collection_id': 1, 'taxon_tree_id': 1, 'taxon_id': 5},
    {'id': 3, 'collection_id': 1, 'taxon_tree_id': 1, 'taxon_id': 10},
]

# ---------------------------------------------------------------- people ------

PEOPLE = [
    {'id': 1, 'full_name': '王小明', 'full_name_en': 'Wang, Hsiao-Ming', 'given_name_en': 'Hsiao-Ming',
     'inherited_name_en': 'Wang', 'abbreviated_name': 'H.M. Wang', 'sorting_name': 'Wang',
     'is_collector': True, 'is_identifier': True},
    {'id': 2, 'full_name': '陳美玲', 'full_name_en': 'Chen, Mei-Ling', 'given_name_en': 'Mei-Ling',
     'inherited_name_en': 'Chen', 'abbreviated_name': 'M.L. Chen', 'sorting_name': 'Chen',
     'is_collector': True},
    {'id': 3, 'full_name': '林大山', 'full_name_en': 'Lin, Ta-Shan', 'given_name_en': 'Ta-Shan',
     'inherited_name_en': 'Lin', 'abbreviated_name': 'T.S. Lin', 'sorting_name': 'Lin',
     'is_identifier': True},
]

# ---------------------------------------------- assertion / annotation types ---
# `options` become AssertionTypeOption rows (only meaningful for select inputs).

ASSERTION_TYPES = [
    {'id': 1, 'collection_id': 1, 'name': 'veget', 'label': '植群型', 'target': 'record',
     'input_type': 'select', 'sort': 1,
     'options': ['闊葉林', '針闊葉混淆林', '針葉林', '草生地', '灌叢']},
    {'id': 2, 'collection_id': 1, 'name': 'habitat', 'label': '微生育地', 'target': 'record',
     'input_type': 'select', 'sort': 2,
     'options': ['林內', '林緣', '路邊', '溪畔', '岩壁']},
    {'id': 3, 'collection_id': 1, 'name': 'topography', 'label': '地形位置', 'target': 'record',
     'input_type': 'select', 'sort': 3,
     'options': ['稜線', '山坡', '谷地', '平地']},
    {'id': 4, 'collection_id': 1, 'name': 'light-intensity', 'label': '環境光度', 'target': 'record',
     'input_type': 'select', 'sort': 4,
     'options': ['全日照', '半日照', '遮蔭']},
    {'id': 5, 'collection_id': 1, 'name': 'life-form', 'label': '生長型', 'target': 'unit',
     'input_type': 'select', 'sort': 1,
     'options': ['喬木', '灌木', '草本', '藤本', '附生']},
    {'id': 6, 'collection_id': 1, 'name': 'plant-h', 'label': '植株高度', 'target': 'unit',
     'input_type': 'input', 'sort': 2},
    {'id': 7, 'collection_id': 1, 'name': 'flower-color', 'label': '花色', 'target': 'unit',
     'input_type': 'select', 'sort': 3,
     'options': ['白', '黃', '紅', '紫', '綠']},
    {'id': 8, 'collection_id': 1, 'name': 'sex-char', 'label': '性狀描述', 'target': 'unit',
     'input_type': 'text', 'sort': 4},
]

ANNOTATION_TYPES = [
    {'id': 1, 'collection_id': 1, 'name': 'location', 'label': '存放位置', 'target': 'unit',
     'input_type': 'input', 'sort': 1},
    {'id': 2, 'collection_id': 1, 'name': 'remark', 'label': '典藏備註', 'target': 'record',
     'input_type': 'text', 'sort': 1},
]

# --------------------------------------------------------------- specimens ----
# One record == one gathering; one unit == one physical sheet. `named_areas` is
# a list of NAMED_AREAS ids; `assertions` maps an assertion type name to a value.

RECORDS = [
    {
        'id': 1, 'collection_id': 1, 'field_number': '1024', 'collector_id': 1,
        'collect_date': '2021-04-18', 'taxon_id': 3, 'identifier_id': 1, 'identified': '2021-05-02',
        'named_areas': [1, 3, 6, 15], 'locality_text': '合歡山昆陽停車場旁步道',
        'locality_text_en': 'Trail beside Kunyang parking lot, Mt. Hehuan',
        'verbatim_locality': '南投縣仁愛鄉 合歡山 昆陽',
        'altitude': 3050, 'altitude2': 3100,
        'latitude_decimal': 24.1361, 'longitude_decimal': 121.2769,
        'field_note': '族群數量普遍，果實已成熟。',
        'assertions': {'veget': '針葉林', 'habitat': '林緣', 'topography': '稜線', 'light-intensity': '全日照'},
        'units': [{'id': 1, 'catalog_number': '000001', 'assertions': {'life-form': '喬木', 'plant-h': '4 m'}}],
    },
    {
        'id': 2, 'collection_id': 1, 'field_number': '1025', 'collector_id': 1,
        'collect_date': '2021-04-18', 'taxon_id': 4, 'identifier_id': 3, 'identified': '2021-06-11',
        'named_areas': [1, 3, 6, 15], 'locality_text': '合歡山南側林道',
        'locality_text_en': 'Forest road on the south side of Mt. Hehuan',
        'verbatim_locality': '南投縣仁愛鄉 合歡山南側',
        'altitude': 2400,
        'latitude_decimal': 24.1204, 'longitude_decimal': 121.2854,
        'assertions': {'veget': '針闊葉混淆林', 'habitat': '路邊', 'topography': '山坡'},
        'units': [{'id': 2, 'catalog_number': '000002', 'assertions': {'life-form': '喬木', 'plant-h': '8 m'}}],
    },
    {
        'id': 3, 'collection_id': 1, 'field_number': '87', 'collector_id': 2,
        'collect_date': '2019-11-03', 'taxon_id': 7, 'identifier_id': 1, 'identified': '2020-01-15',
        'named_areas': [1, 4, 8, 11, 14], 'locality_text': '陽明山國家公園大屯山登山口',
        'locality_text_en': 'Mt. Datun trailhead, Yangmingshan National Park',
        'verbatim_locality': '臺北市北投區 大屯山',
        'altitude': 820,
        'latitude_decimal': 25.1758, 'longitude_decimal': 121.5223,
        'field_note': '路旁栽植個體，葉具樟腦味。',
        'assertions': {'veget': '闊葉林', 'habitat': '路邊', 'light-intensity': '半日照'},
        'units': [{'id': 3, 'catalog_number': '000003', 'assertions': {'life-form': '喬木', 'plant-h': '12 m',
                                                                      'sex-char': '花期未見，葉背灰白。'}}],
    },
    {
        'id': 4, 'collection_id': 1, 'field_number': '92', 'collector_id': 2,
        'collect_date': '2019-11-04', 'taxon_id': 9, 'identifier_id': 3, 'identified': '2020-01-15',
        'named_areas': [1, 4, 8, 11], 'locality_text': '陽明山國家公園七星山東側步道',
        'locality_text_en': 'East trail of Mt. Qixing, Yangmingshan National Park',
        'verbatim_locality': '臺北市北投區 七星山',
        'altitude': 950, 'altitude2': 1010,
        'latitude_decimal': 25.1721, 'longitude_decimal': 121.5535,
        'assertions': {'veget': '闊葉林', 'habitat': '林內', 'topography': '山坡', 'light-intensity': '遮蔭'},
        'units': [{'id': 4, 'catalog_number': '000004', 'assertions': {'life-form': '喬木'}}],
    },
    {
        'id': 5, 'collection_id': 1, 'field_number': '1130', 'collector_id': 1,
        'collect_date': '2022-08-27', 'taxon_id': 12, 'identifier_id': 1, 'identified': '2022-09-01',
        'named_areas': [1, 5, 9, 12], 'locality_text': '太魯閣國家公園天祥附近路旁',
        'locality_text_en': 'Roadside near Tianxiang, Taroko National Park',
        'verbatim_locality': '花蓮縣秀林鄉 天祥',
        'altitude': 480,
        'latitude_decimal': 24.1817, 'longitude_decimal': 121.4931,
        'field_note': '歸化種，路旁大量群生。',
        'assertions': {'veget': '草生地', 'habitat': '路邊', 'topography': '谷地', 'light-intensity': '全日照'},
        'units': [{'id': 5, 'catalog_number': '000005', 'assertions': {'life-form': '草本', 'plant-h': '0.8 m',
                                                                      'flower-color': '白'}}],
    },
    {
        'id': 6, 'collection_id': 1, 'field_number': '1131', 'collector_id': 1,
        'collect_date': '2022-08-28', 'taxon_id': 14, 'identifier_id': 3, 'identified': '2022-10-20',
        'named_areas': [1, 5, 9, 12], 'locality_text': '太魯閣國家公園白楊步道',
        'locality_text_en': 'Baiyang Trail, Taroko National Park',
        'verbatim_locality': '花蓮縣秀林鄉 白楊步道',
        'altitude': 560,
        'latitude_decimal': 24.1899, 'longitude_decimal': 121.4568,
        'assertions': {'veget': '闊葉林', 'habitat': '岩壁', 'light-intensity': '遮蔭'},
        'units': [{'id': 6, 'catalog_number': '000006', 'assertions': {'life-form': '草本', 'flower-color': '白'}}],
    },
    {
        'id': 7, 'collection_id': 1, 'field_number': '204', 'collector_id': 2,
        'collect_date': '2023-05-09', 'taxon_id': 3, 'identifier_id': 1, 'identified': '2023-05-30',
        'named_areas': [1, 3, 7, 10, 13], 'locality_text': '玉山國家公園塔塔加鞍部',
        'locality_text_en': 'Tataka Saddle, Yushan National Park',
        'verbatim_locality': '南投縣信義鄉 塔塔加',
        'altitude': 2610,
        'latitude_decimal': 23.4855, 'longitude_decimal': 120.8875,
        'assertions': {'veget': '針闊葉混淆林', 'habitat': '林緣', 'topography': '稜線'},
        'units': [
            {'id': 7, 'catalog_number': '000007', 'assertions': {'life-form': '喬木', 'plant-h': '5 m'}},
            # a duplicate sheet from the same gathering
            {'id': 8, 'catalog_number': '000008', 'assertions': {'life-form': '喬木'}},
        ],
    },
    {
        'id': 8, 'collection_id': 1, 'field_number': '211', 'collector_id': 2,
        'collect_date': '2023-05-10', 'taxon_id': 7, 'identifier_id': 3, 'identified': '2023-07-04',
        'named_areas': [1, 3, 7, 10, 13], 'locality_text': '玉山國家公園塔塔加遊客中心周邊',
        'locality_text_en': 'Around the Tataka visitor center, Yushan National Park',
        'verbatim_locality': '南投縣信義鄉 塔塔加遊客中心',
        'altitude': 2580,
        'latitude_decimal': 23.4832, 'longitude_decimal': 120.8901,
        'field_note': '栽植個體，供解說使用。',
        'assertions': {'veget': '闊葉林', 'habitat': '林緣'},
        'units': [{'id': 9, 'catalog_number': '000009', 'type_status': 'holotype', 'type_is_published': True,
                   'typified_name': 'Cinnamomum camphora (L.) J.Presl',
                   'assertions': {'life-form': '喬木', 'plant-h': '10 m'}}],
    },
]

UNIT_DEFAULTS = {
    'collection_id': 1,
    'basis_of_record': 'PreservedSpecimen',
    'kind_of_unit': 'HS',
    'preparation_type': 'S',
    'disposition': 'in collection',
    'acquisition_type': 'collecting',
    'pub_status': 'P',
}

# ------------------------------------------------------------------ news ------

ARTICLE_CATEGORIES = [
    {'id': 1, 'site_id': 1, 'name': 'news', 'label': '本館消息'},
    {'id': 2, 'site_id': 1, 'name': 'research', 'label': '研究成果'},
]

ARTICLES = [
    {
        'id': 1, 'site_id': 1, 'category_id': 1, 'publish_date': '2024-03-01',
        'subject': '示範網站上線',
        'content': (
            '這是 NatureDB 的**範例網站**，用來展示標本資料的瀏覽、搜尋與後台編輯流程。\n\n'
            '網站中的標本、採集者與地點皆為虛構資料，僅供測試使用。\n'
        ),
    },
    {
        'id': 2, 'site_id': 1, 'category_id': 1, 'publish_date': '2024-05-20',
        'subject': '如何替換範例資料',
        'content': (
            '範例資料由 `flask initdata` 建立，內容定義在 `app/initdata.py`。\n\n'
            '要建立自己的館所網站，可以：\n\n'
            '1. 修改 `app/initdata.py` 中的網站、單位與典藏設定。\n'
            '2. 複製 `app/settings/demo.json` 成 `app/settings/<你的網站名稱>.json`。\n'
            '3. 用 `flask importdata` 匯入實際的標本 CSV。\n'
        ),
    },
    {
        'id': 3, 'site_id': 1, 'category_id': 2, 'publish_date': '2024-09-12',
        'subject': '範例：合歡山地區殼斗科植物調查',
        'content': (
            '本文為範例文章，示範「研究成果」分類的呈現方式。\n\n'
            '調查於 2021 年進行，共採集青剛櫟與栓皮櫟等標本，'
            '相關標本可於搜尋頁以採集者「王小明」查詢。\n'
        ),
    },
]

# Tables whose ids are assigned explicitly above; their sequences need a bump
# afterwards or the next admin-created row would collide with a seeded id.
SEQUENCE_TABLES = [
    'site', 'organization', 'collection', 'area_class', 'country', 'named_area',
    'taxon_tree', 'taxon', 'taxon_relation', 'collection_taxon_map', 'person',
    'assertion_type', 'assertion_type_option', 'annotation_type',
    'record', 'identification', 'unit', 'record_assertion', 'unit_assertion',
    'article_category', 'article', '"user"',
]


def _parse_date(value):
    return datetime.strptime(value, '%Y-%m-%d') if value else None


def _create(model, pk, fields, log):
    '''Create `model` with primary key `pk` unless that row already exists.'''
    if session.get(model, pk):
        return None

    obj = model(id=pk, **fields)
    session.add(obj)
    log(f'  + {model.__tablename__} {pk}')
    return obj


def load(admin_username='admin', admin_password='admin', log=print):
    site = session.get(Site, 1)
    if site and site.name != SITE_NAME:
        raise RuntimeError(
            f'site id=1 is already "{site.name}", not "{SITE_NAME}". '
            'The demo data expects site/collection id 1; refusing to touch an existing database.'
        )

    log('site / organization / collection')
    for row in SITES:
        _create(Site, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    for row in ORGANIZATIONS:
        _create(Organization, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    for row in COLLECTIONS:
        _create(Collection, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()

    log('gazetteer')
    for row in AREA_CLASSES:
        _create(AreaClass, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    for row in COUNTRIES:
        _create(Country, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()
    for row in NAMED_AREAS:
        _create(NamedArea, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()

    log('taxa')
    for row in TAXON_TREES:
        _create(TaxonTree, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()
    for row in TAXA:
        fields = {k: v for k, v in row.items() if k not in ('id', 'parents')}
        fields['tree_id'] = 1
        fields['is_accepted'] = True
        _create(Taxon, row['id'], fields, log)
    session.commit()
    # closure table; make_relations() commits per taxon and is itself idempotent
    for row in TAXA:
        session.get(Taxon, row['id']).make_relations(row.get('parents', {}))
    for row in COLLECTION_TAXON_MAPS:
        _create(CollectionTaxonMap, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()

    log('people')
    for row in PEOPLE:
        _create(Person, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()

    log('assertion / annotation types')
    option_id = 0
    for row in ASSERTION_TYPES:
        fields = {k: v for k, v in row.items() if k not in ('id', 'options')}
        _create(AssertionType, row['id'], fields, log)
        session.commit()
        for value in row.get('options', []):
            option_id += 1
            _create(AssertionTypeOption, option_id, {'value': value, 'assertion_type_id': row['id']}, log)
    for row in ANNOTATION_TYPES:
        _create(AnnotationType, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()

    log('records / units')
    assertion_type_ids = {x['name']: x['id'] for x in ASSERTION_TYPES}
    option_ids = {}  # (assertion_type_id, value) -> option id
    for opt in session.query(AssertionTypeOption).all():
        option_ids[(opt.assertion_type_id, opt.value)] = opt.id

    identification_id = 0
    record_assertion_id = 0
    unit_assertion_id = 0
    for row in RECORDS:
        collect_date = _parse_date(row['collect_date'])
        taxon = session.get(Taxon, row['taxon_id'])
        fields = {
            'collection_id': row['collection_id'],
            'field_number': row['field_number'],
            'field_number_int': int(row['field_number']) if row['field_number'].isdigit() else None,
            'collector_id': row['collector_id'],
            'collect_date': collect_date,
            'collect_date_year': collect_date.year,
            'collect_date_month': collect_date.month,
            'collect_date_day': collect_date.day,
            'verbatim_locality': row.get('verbatim_locality'),
            'locality_text': row.get('locality_text'),
            'locality_text_en': row.get('locality_text_en'),
            'altitude': row.get('altitude'),
            'altitude2': row.get('altitude2'),
            'latitude_decimal': row.get('latitude_decimal'),
            'longitude_decimal': row.get('longitude_decimal'),
            'geodetic_datum': 'WGS84',
            'field_note': row.get('field_note'),
            # denormalised columns the search/list views read directly
            'proxy_taxon_id': taxon.id,
            'proxy_taxon_scientific_name': taxon.full_scientific_name,
            'proxy_taxon_common_name': taxon.common_name,
        }
        _create(Record, row['id'], fields, log)
        session.commit()

        identification_id += 1
        _create(Identification, identification_id, {
            'record_id': row['id'],
            'taxon_id': row['taxon_id'],
            'identifier_id': row['identifier_id'],
            'date': _parse_date(row.get('identified')),
            'sequence': 0,
        }, log)

        for named_area_id in row.get('named_areas', []):
            exists = session.get(RecordNamedAreaMap, (row['id'], named_area_id))
            if not exists:
                session.add(RecordNamedAreaMap(record_id=row['id'], named_area_id=named_area_id, via='manual'))

        for name, value in row.get('assertions', {}).items():
            record_assertion_id += 1
            type_id = assertion_type_ids[name]
            _create(RecordAssertion, record_assertion_id, {
                'record_id': row['id'],
                'assertion_type_id': type_id,
                'value': value,
                'option_id': option_ids.get((type_id, value)),
            }, log)

        for unit_row in row['units']:
            fields = dict(UNIT_DEFAULTS)
            fields.update({k: v for k, v in unit_row.items() if k not in ('id', 'assertions')})
            fields['record_id'] = row['id']
            _create(Unit, unit_row['id'], fields, log)
            for name, value in unit_row.get('assertions', {}).items():
                unit_assertion_id += 1
                type_id = assertion_type_ids[name]
                _create(UnitAssertion, unit_assertion_id, {
                    'unit_id': unit_row['id'],
                    'assertion_type_id': type_id,
                    'value': value,
                    'option_id': option_ids.get((type_id, value)),
                }, log)
        session.commit()

    log('news')
    for row in ARTICLE_CATEGORIES:
        _create(ArticleCategory, row['id'], {k: v for k, v in row.items() if k != 'id'}, log)
    session.commit()
    for row in ARTICLES:
        fields = {k: v for k, v in row.items() if k != 'id'}
        fields['publish_date'] = _parse_date(fields['publish_date']).date()
        fields['is_markdown'] = True
        _create(Article, row['id'], fields, log)
    session.commit()

    log('admin user')
    existing = User.query.filter(User.username == admin_username, User.site_id == 1).first()
    if existing:
        log(f'  = user {admin_username} already exists, password left unchanged')
    else:
        session.add(User(
            username=admin_username,
            name='Demo Administrator',
            passwd=generate_password_hash(admin_password),
            site_id=1,
            role=User.ROLE_ROOT,
            status='P',
        ))
        session.commit()
        log(f'  + user {admin_username}')

    _sync_sequences(log)
    session.commit()

    return {
        'site': SITE_NAME,
        'admin_username': admin_username,
        'records': len(RECORDS),
        'units': sum(len(x['units']) for x in RECORDS),
    }


def _sync_sequences(log):
    '''Move each id sequence past the highest explicitly-seeded id.

    Without this the first row the admin UI inserts would reuse an id that the
    seed already took. The third setval argument is `is_called`: false for an
    empty table so the sequence still hands out 1.
    '''
    for table in SEQUENCE_TABLES:
        session.execute(text(
            "SELECT setval(pg_get_serial_sequence(:table, 'id'), "
            f"COALESCE((SELECT MAX(id) FROM {table}), 1), "
            f"(SELECT MAX(id) FROM {table}) IS NOT NULL)"
        ), {'table': table.strip('"')})
    log('sequences synced')
