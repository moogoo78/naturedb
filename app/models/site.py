from sqlalchemy import (
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
)
from sqlalchemy.orm import (
    relationship,
    backref,
    validates,
)
from sqlalchemy.dialects.postgresql import JSONB
from flask_login import UserMixin

from app.database import (
    Base,
    session,
    TimestampMixin,
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
    passwd = Column(String(500))
    status = Column(String(1), default='P')
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    #default_collection_id = Column(Integer, ForeignKey('collection.id', on
    organization = relationship('Organization')
    favorites = relationship('Favorite', primaryjoin='User.id == Favorite.user_id')

class Favorite(Base):
    __tablename__ = 'favorite'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    record = Column(String(500)) # TODO: entity


class Organization(Base, TimestampMixin):
    '''
    for registered admin user or collection
    '''
    __tablename__ = 'organization'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    other_name = Column(String(500))
    short_name = Column(String(500))
    code = Column(String(500))
    related_link_categories = relationship('RelatedLinkCategory')
    website_url = Column(String(500))
    logo_url = Column(String(500))
    taxonomic_scope = Column(String(1000))
    geographic_scope = Column(String(1000))
    description = Column(Text)
    #collections = relationship('Collection', secondary=organization_collection)
    collections = relationship('Collection')
    data = Column(JSONB) # country
    #default_collection_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'), nullable=True)
    #default_collection = relationship('Collection', primaryjoin='Organization.default_collection_id == Collection.id')
    is_site = Column(Boolean, default=False)
    subdomain = Column(String(100))
    domain = Column(String(500))
    settings = Column(JSONB)

    def __repr__(self):
        return f'<Organization id="{self.id}" name={self.name}>'

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'abbreviation': self.abbreviation,
        }

    @staticmethod
    def get_site(domain=''):
        if site := Organization.query.filter(Organization.is_site==True, Organization.domain.ilike(f'%{domain}%')).first():
            return site
        return None


    @property
    def collection_ids(self):
        return [x.id for x in self.collections]


class ArticleCategory(Base):
    __tablename__ = 'article_category'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    label = Column(String(500))
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)

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
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
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
    organization_id = Column(ForeignKey('organization.id', ondelete='SET NULL'))
    related_links = relationship('RelatedLink')

class RelatedLink(Base, TimestampMixin):
    __tablename__ = 'related_link'

    id = Column(Integer, primary_key=True)
    category_id = Column(ForeignKey('related_link_category.id', ondelete='SET NULL'))
    title = Column(String(500))
    url = Column(String(1000))
    note = Column(String(1000))
    status = Column(String(4), default='P')
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)

    category = relationship('RelatedLinkCategory', back_populates='related_links')
