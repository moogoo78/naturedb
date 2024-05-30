from sqlalchemy import (
    desc,
)
from app.models.site import (
    Article,
    ArticleCategory,
    RelatedLink,
    RelatedLinkCategory,
    Organization,
    UserList,
    UserListCategory,
)
from app.models.collection import (
    AssertionType,
    Collection,
    Person,
    Transaction,
    AnnotationType,
    Annotation,
    MultimediaObjectAnnotation,
)
from app.models.gazetter import (
    NamedArea,
    AreaClass,
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
        'filter_by': 'organization',
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
        'filter_by': 'organization',
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
        'filter_by': 'organization',
        'list_query': Article.query.order_by(desc(Article.publish_date)),
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
        'filter_by': 'organization',
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
        'list_display': ('name', 'name_en', 'area_class'),
        'list_filter': ('name', 'name_en'),
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
            'sorting_name': {'label': '排序名'},
            'abbreviated_name': {'label': '縮寫名'},
            'is_collector': {'label': '採集者', 'type': 'boolean'},
            'is_identifier': {'label': '鑑定者', 'type': 'boolean'},
            'collections': {'label': '收藏集', 'type': 'organization_collections'}
        },
        'list_display': ('full_name', 'full_name_en', 'is_collector', 'is_identifier',),
        'list_collection_filter': {
            'related': Collection.people,
        },
        'list_filter': ('full_name', 'full_name_en'),
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
        'filter_by': 'organization',
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
        'filter_by': 'collection',
        'fields': {
            'name': {'label': 'key'},
            'label': {'label': '標題'},
            'target': {'label': 'target', 'type': 'select', 'options': AssertionType.TARGET_OPTIONS, 'display_func': AssertionType.get_target_display},
            'input_type': {'label': '輸入格式', 'type': 'select', 'options': AssertionType.INPUT_TYPE_OPTIONS, 'display_func': AssertionType.get_input_type_display },
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
    },
    'organization': {
        'name': 'organization',
        'label': '研究單位',
        'display': 'name',
        'resource_name': 'organizations',
        'model': Organization,
        'fields': {
            'name': {'label': '名稱'},
            'short_name': {'label': '簡稱'},
            'code': {'label': '組織代碼'},
        },
        'list_display': ('name', 'short_name', 'code'),
    },
    'transaction': {
        'name': 'transaction',
        'label': '交換/贈送',
        'display': 'title',
        'resource_name': 'transactions',
        'model': Transaction,
        'fields': {
            'title': {'label': '名稱'},
            'transaction_type': {'label': '類別', 'type': 'select', 'options': Transaction.EXCHANGE_TYPE_CHOICES, 'display_func': Transaction.get_type_display },
            'organization': {'label': '研究單位', 'type': 'select', 'foreign': Organization, 'display': 'name'},
            'date': {'label': '日期'},
        },
        'list_display': ('title', 'transaction_type', 'organization', 'date'),
    },
    'annotation_type': {
        'name': 'annotation_type',
        'label': '標本標註',
        'display': 'label',
        'resource_name': 'annotation_types',
        'model': AnnotationType,
        'filter_by': 'collection',
        'fields': {
            'name': {'label': '名稱'},
            'label': {'label': '標題'},
            'input_type': {'label': '管理', 'type': 'select', 'options': AnnotationType.INPUT_TYPE_OPTIONS, 'display_func': AnnotationType.get_input_type_display },
            'collection': { 'label': '資料集', 'type': 'select', 'current_user': 'organization.collections', 'display': 'label'},
            'sort': {'label': '排序', 'type': 'number'},
            'target': {'label': 'target', 'type': 'select', 'options': AnnotationType.TARGET_OPTIONS, 'display_func': AnnotationType.get_target_display},
         },
        'list_display': ('name', 'label', 'target','input_type', 'sort', 'collection'),
    },
    'user_list_category': {
        'name': 'user_list_category',
        'label': '收藏清單類別',
        'display': 'name',
        'resource_name': 'user_list_categories',
        'model': UserListCategory,
        'fields': {
            'name': {'label': '名稱'},
         },
        'has_current_user': 'user_id',
        'list_display': ('name', ),
    },
}
