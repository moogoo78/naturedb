from pathlib import Path
import json

from flask import (
    current_app,
)
from sqlalchemy import (
    select,
    Table,
    Column,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
    desc,
    func,
)
from sqlalchemy.orm import (
    relationship,
    backref,
    validates,
)
from sqlalchemy.dialects.postgresql import JSONB

from werkzeug.security import (
    generate_password_hash,
 )
from flask_login import (
    UserMixin,
    current_user,
)

from app.database import (
    Base,
    session,
    TimestampMixin,
)
from app.utils import (
    decode_key,
    get_time,
)
# organization_collection = Table(
#     'organization_collection',
#     Base.metadata,
#     Column('organization_id', ForeignKey('organization.id')),
#     Column('collection_id', ForeignKey('collection.id')),
# )

class User(Base, UserMixin, TimestampMixin):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    username = Column(String(500))
    name = Column(String(500), nullable=True)
    passwd = Column(String(500))
    status = Column(String(1), default='P')
    role = Column(String(4), default='B') # A: admin, B: input data
    site_id = Column(Integer, ForeignKey('site.id', ondelete='SET NULL'), nullable=True)
    #default_collection_id = Column(Integer, ForeignKey('collection.id', on
    site = relationship('Site')
    user_list_categories = relationship('UserListCategory', order_by="desc(UserListCategory.id)")
    user_lists = relationship('UserList')

    def reset_passwd(self, passwd):
        hashed_password = generate_password_hash(passwd)
        self.passwd = hashed_password
        session.commit()

class UserListCategory(Base):
    __tablename__ = 'user_list_category'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)


class UserList(Base):
    __tablename__ = 'user_list'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    entity_id = Column(String(100))
    category_id = Column(Integer, ForeignKey('user_list_category.id', ondelete='SET NULL'))
    category = relationship('UserListCategory')
    created = Column(DateTime, default=get_time)

class Site(Base):
    '''
    for register admin, organization, collection
    '''
    __tablename__ = 'site'

    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    title_en = Column(String(500))
    logo_url = Column(String(500))
    name = Column(String(50))
    description = Column(Text)
    host = Column(String(500))
    data = Column(JSONB)
    related_link_categories = relationship('RelatedLinkCategory')
    organizations = relationship('Organization', back_populates='site')
    collections = relationship('Collection')

    @property
    def collection_ids(self):
        collections = sorted(self.collections, key=lambda x: x.sort if x.sort else 0)
        return [x.id for x in collections]

    @staticmethod
    def find_by_host(host='foo'):
        if site := Site.query.filter(Site.host.ilike(f'{host}')).first():
            return site

        elif current_app.config['WEB_ENV'] == 'dev': # dev just match Site.name
            hostname = host.split('.')[0]
            if site := Site.query.filter(Site.name==hostname).first():
                return site
        elif current_app.config['WEB_ENV'] == 'staging': # staging just match Site.name
            hostname = host.split('.')[0].replace('staging-', '')
            if site := Site.query.filter(Site.name==hostname).first():
                return site
        return None

    def get_type_specimens(self):
        from app.helpers import get_or_set_type_specimens

        cids = [x.id for x in self.collections]
        return get_or_set_type_specimens(cids)

    def get_service_keys(self):
        return decode_key(current_app.config['SERVICE_KEY'])[self.name]

    def get_settings(self, key=''):
        settings = None
        with open(f'app/settings/{self.name}.json', 'r') as setting_file:
            try:
                settings = json.loads(setting_file.read())
                if key == '':
                    return settings
                else:
                    return settings.get(key, None)

                current_app.logger.debug(f'read settings json, key: {key}')
            except json.JSONDecodeError as msg:
                current_app.logger.error(f'read settings error) {msg}')

        return None

    def get_custom_area_classes(self):
        from app.models.collection import AreaClass
        if custom := self.get_settings('custom_area_classes'):
            rows = AreaClass.query.filter(AreaClass.name.in_(custom), AreaClass.collection_id.in_(self.collection_ids)).all()
            return rows

        return []

    @property
    def layout(self):
        data = {}
        DEFAULT_LAYOUT = {
            'navbar': '_inc_navbar.html',
            'footer_links': '_inc_footer_links.html',
        }
        for key, filename in DEFAULT_LAYOUT.items():
            template_path = Path('sites', self.name, filename)
            path = Path('app', 'templates', template_path)
            if path.exists():
                data[key] = template_path.as_posix()
        return data


class Organization(Base, TimestampMixin):
    '''
    for collection
    '''
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    other_name = Column(String(500))
    short_name = Column(String(500))
    code = Column(String(500))
    #related_link_categories = relationship('RelatedLinkCategory')
    website_url = Column(String(500))
    #logo_url = Column(String(500))
    taxonomic_scope = Column(String(1000))
    geographic_scope = Column(String(1000))
    #description = Column(Text)
    #collections = relationship('Collection', secondary=organization_collection)
    collections = relationship('Collection')
    data = Column(JSONB) # country
    #default_collection_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'), nullable=True)
    #default_collection = relationship('Collection', primaryjoin='Organization.default_collection_id == Collection.id')
    #is_site = Column(Boolean, default=False)
    #subdomain = Column(String(100))
    #domain = Column(String(500))
    #ark_nma = Column(String(500)) # Name Mapping Authority (NMA)
    #settings = Column(JSONB)
    site_id = Column(Integer, ForeignKey('site.id', ondelete='SET NULL'))

    site = relationship('Site', back_populates='organizations')
    pids = relationship('PersistentIdentifierOrganization')

    def __repr__(self):
        return f'<Organization id="{self.id}" name={self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'abbreviation': self.abbreviation,
        }

    @property
    def collection_ids(self):
        return [x.id for x in self.collections]

    def get_identifier(self, pid_type=''):
        for i in self.pids:
            if i.pid_type == pid_type:
                return i.key
        return None

class ArticleCategory(Base):
    __tablename__ = 'article_category'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    label = Column(String(500))
    site_id = Column(Integer, ForeignKey('site.id', ondelete='SET NULL'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id, 
            'name': self.name,
            'label': self.label,
        }


class Article(Base, TimestampMixin):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    subject = Column(String(500))
    content = Column(Text)
    site_id = Column(Integer, ForeignKey('site.id', ondelete='SET NULL'), nullable=True)
    category_id = Column(Integer, ForeignKey('article_category.id', ondelete='SET NULL'), nullable=True)
    category = relationship('ArticleCategory')
    publish_date = Column(Date)
    # published_by = Column(String(500))
    data = Column(JSONB) # language, url, published_by
    is_markdown = Column(Boolean, default=True)

    def to_dict(self):
        return {
            'id': self.id or '',
            'subject': self.subject or '',
            'content': self.content or '',
            'category_id': self.category_id or '',
            'publish_date': self.publish_date.strftime('%Y-%m-%d') if self.publish_date else'',
            'created': self.created or '',
            'category': self.category.to_dict() if self.category else None,
        }

    def get_form_layout(self):
        return {
            'categories': [x.to_dict() for x in ArticleCategory.query.all()]
        }

class RelatedLinkCategory(Base):
    __tablename__ = 'related_link_category'

    id = Column(Integer, primary_key=True)
    label = Column(String(500))
    name = Column(String(500))
    sort = Column(Integer, nullable=True)
    site_id = Column(ForeignKey('site.id', ondelete='SET NULL'))
    related_links = relationship('RelatedLink')

class RelatedLink(Base, TimestampMixin):
    __tablename__ = 'related_link'

    id = Column(Integer, primary_key=True)
    category_id = Column(ForeignKey('related_link_category.id', ondelete='SET NULL'))
    title = Column(String(500))
    url = Column(String(1000))
    note = Column(String(1000))
    status = Column(String(4), default='P')
    site_id = Column(Integer, ForeignKey('site.id', ondelete='SET NULL'), nullable=True)

    category = relationship('RelatedLinkCategory', back_populates='related_links')
