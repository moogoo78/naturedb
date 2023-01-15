from app.models.site import (
    Article,
    ArticleCategory,
    RelatedLink,
    RelatedLinkCategory,
)
from app.models.collection import (
    AssertionType,
    AreaClass,
    NamedArea,
    Collection,
    Person,
)
from app.models.taxon import (
    Taxon,
)
from app.database import (
    ModelHistory,
)

ADMIN_REGISTER_MAP = {
    'related_link': {
        'name': 'related_link',
        'label': '相關連結',
        'display': 'title',
        'resource_name': 'related_links',
        'model': RelatedLink,
        'fields': {
            'title': { 'label': '標題' },
            'category': { 'label': '類別', 'type': 'select', 'foreign': RelatedLinkCategory, 'display': 'label'},
            'url': { 'label': '連結' },
            'note': { 'label': '註記'},
        },
        'list_display': ('title', 'category', 'url', 'note')
    },
    'related_link_category': {
        'name': 'related_link_category',
        'label': '相關連結分類',
        'display': 'label',
        'resource_name': 'related_link_categories',
        'model': RelatedLinkCategory,
        'fields': {
            'label': { 'label': '標題' },
            'name': { 'label': 'key' },
            #'sort': { 'label': ''},
        },
        'list_display': ('label', 'name')
    },
    'article': {
        'name': 'article',
        'label': '文章',
        'display': 'subject',
        'resource_name': 'articles',
        'model': Article,
        'fields': {
            'subject': { 'label': '標題' },
            'content': { 'label': '內容', 'type': 'textarea'},
            'category': { 'label': '類別', 'type': 'select', 'foreign': ArticleCategory, 'display': 'label'},
            'publish_date': {'label': '發布日期', 'type': 'date'}
        },
        'list_display': ('subject', 'category', 'content', 'publish_date')
    },
    'article_category': {
        'name': 'article_category',
        'label': '文章分類',
        'display': 'label',
        'resource_name': 'article_categories',
        'model': ArticleCategory,
        'fields': {
            'label': { 'label': '標題' },
            'name': { 'label': 'key' },
        },
        'list_display': ('label', 'name')
    },
    'area_class': {
        'name': 'area_class',
        'label': '地理級別',
        'display': 'label',
        'resource_name': 'area_classes',
        'model': AreaClass,
        'fields': {
            'label': { 'label': '標題' },
            'name': { 'label': 'name',},
            'parent': { 'label': '上一層', 'type': 'select', 'foreign': AreaClass, 'display': 'label'},
            'sort': {'label': '排序', 'type': 'number'},
            'collection': { 'label': '資料集', 'type': 'select', 'current_user': 'organization.collections', 'display': 'label'},
        },
        'list_display': ('label', 'name', 'sort', 'collection'),
        'list_collection_filter': {
            'field': AreaClass.collection_id,
        }
    },
    'named_area': {
        'name': 'named_area',
        'label': '地區',
        'display': 'name',
        'resource_name': 'named_areas',
        'model': NamedArea,
        'fields': {
            'name': { 'label': '名稱',},
            'name_en': { 'label': '名稱 (英文)',},
            'area_class': { 'label': '地理分級', 'type': 'select', 'foreign': AreaClass, 'display': 'label'},
        },
        'list_display': ('name', 'name_en', 'area_class')
    },
    'person': {
        'name': 'person',
        'label': '採集者/鑒定者',
        'display': 'full_name',
        'resource_name': 'people',
        'model': Person,
        'fields': {
            'full_name': {'label': '全名'},
            'full_name_en': {'label': '英文全名'},
            'is_collector': {'label': '採集者', 'type': 'boolean'},
            'is_identifier': {'label': '鑑定者', 'type': 'boolean'},
            'collections': {'label': '收藏集', 'type': 'organization_collections'}
        },
        'list_display': ('full_name', 'full_name_en', 'is_collector', 'is_identifier',),
        'list_collection_filter': {
            'related': Collection.people,
        }
    },
    'taxon': {
        'name': 'taxon',
        'label': '物種名錄',
        'display': 'full_scientific_name',
        'resource_name': 'taxa',
        'model': Taxon,
        'list_query': Taxon.query.limit(20),
        'fields': {
            'rank': { 'label': 'rank'},
            'full_scientific_name': { 'label': '完整學名',},
            'common_name': { 'label': '中文名'},
        },
        'list_display':('rank', 'full_scientific_name', 'common_name')
    },
    'collection': {
        'name': 'collection',
        'label': '收藏集',
        'display': 'label',
        'resource_name': 'collections',
        'model': Collection,
        'fields': {
            'label': { 'label': '標題' },
            'name': { 'label': 'key',},
        },
        'list_display': ('label', 'name')
    },
    'assertion_type': {
        'name': 'assertion_type',
        'label': '標註類別',
        'display': 'label',
        'resource_name': 'assertion_types',
        'model': AssertionType,
        'fields': {
            'name': {'label': 'key'},
            'label': {'label': '標題'},
            'target': {'label': 'target', 'type': 'select', 'options': [('entity', 'entity'), ('unit', 'unit')] },
            'input_type': {'label': '輸入格式', 'type': 'select', 'options': [('input', '單行文字'), ('text', '多行文字'), ('select', '下拉選單')] },
            'collection': { 'label': '資料集', 'type': 'select', 'current_user': 'organization.collections', 'display': 'label'},
            'sort': {'label': '排序', 'type': 'number'}
        },
        'list_display': ('name', 'label', 'target', 'input_type', 'sort', 'collection'),
        'list_column_tpl': {
            'sort': '<span class="uk-badge">{{__}}</span>',
        },
        'list_collection_filter': {
            'field': AssertionType.collection_id,
        }
    },
    'model_history': {
        'name': 'model_history',
        'label': '修改記錄',
        'display': 'tablename',
        'resource_name': 'model_histories',
        'model': ModelHistory,
        'fields': {
            'tablename': {'label': 'table name'},
            'item_id': {'label': 'item_id'},
            'action': {'label': 'create/delete/update'},
            'changes': {'label': '', 'type': 'textarea'},
            'created': {'label': '日期時間'},
        },
        'list_display': ('tablename', 'item_id', 'action', 'created'),
    }
}
