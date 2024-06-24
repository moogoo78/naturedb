from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
    Table,
    desc,
    select,
)
from sqlalchemy.orm import (
    relationship,
    backref,
    validates,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declared_attr
from geoalchemy2.types import Geometry
from flask_babel import (
    gettext,
)

from app.database import (
    Base,
    session,
    TimestampMixin,
)

class Country(Base):
    __tablename__ = 'country'

    id = Column(Integer, primary_key=True)
    name_en = Column(String(500))
    name_zh = Column(String(500))
    continent = Column(String(500))
    iso3166_1 = Column(String(2))
    iso3 = Column(String(3))
    status = Column(String(500))
    sort = Column(Integer)

    @staticmethod
    def get_named_area_ids_from_continent(name):
        stmt_country = select(NamedArea.id).join(Country, Country.iso3==NamedArea.code).where(NamedArea.area_class_id==7, Country.continent==name)
        result = session.execute(stmt_country)
        return [x[0] for x in result.all()]

class AreaClass(Base, TimestampMixin):

#HAST: country (249), province (142), hsienCity (97), hsienTown (371), additionalDesc(specimen.locality_text): ref: hast_id: 144954

    __tablename__ = 'area_class'
    # DEFAULT_OPTIONS = [
    #     {'id': 1, 'name': 'country', 'label': '國家'},
    #     {'id': 2, 'name': 'stateProvince', 'label': '省/州', 'parent': 'country', 'root': 'country'},
    #     {'id': 3, 'name': 'county', 'label': '縣/市', 'parent': 'stateProvince', 'root': 'country'},
    #     {'id': 4, 'name': 'municipality', 'label': '鄉/鎮', 'parent': 'county', 'root': 'country'},
    #     {'id': 5, 'name': 'national_park', 'label': '國家公園'},
    #     {'id': 6, 'name': 'locality', 'label': '地名'},
    # ]

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    label = Column(String(500))
    sort = Column(Integer)
    parent_id = Column(Integer, ForeignKey('area_class.id', ondelete='SET NULL'), nullable=True)
    collection_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'), nullable=True)
    # organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    #org = models.ForeignKey(on_delete=models.SET_NULL, null=True, blank=True)
    # parent = relationship('AreaClass', foreign_keys=[parent_id], uselist=False)
    admin_config = Column(JSONB)

    parent = relationship('AreaClass', remote_side=id)
    collection = relationship('Collection', back_populates='area_classes')

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'label': self.label,
            'parent_id': self.parent_id or None,
            'admin_config': self.admin_config or None,
        }


class NamedArea(Base, TimestampMixin):
    __tablename__ = 'named_area'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    name_en = Column(String(500))
    code = Column(String(500))
    #code_standard = models.CharField(max_length=1000, null=True)
    area_class_id = Column(Integer, ForeignKey('area_class.id', ondelete='SET NULL'), nullable=True)
    area_class = relationship('AreaClass', backref=backref('named_area'))
    source_data = Column(JSONB)
    parent_id = Column(Integer, ForeignKey('named_area.id', ondelete='SET NULL'), nullable=True) # DEPRECATED
    geom_mpoly = Column(Geometry(geometry_type='MULTIPOLYGON', srid=4326, spatial_index=True))
    children = relationship('NamedArea', back_populates='parent')
    parent = relationship('NamedArea', back_populates='children', remote_side=[id])
    #parent = relationship('NamedArea', foreign_keys=[parent_id])
    pids = relationship('PersistentIdentifierNamedArea')
    #records = relationship('Record', secondary='record_named_area_map', back_populates='named_areas')
    record_maps = relationship('RecordNamedAreaMap', back_populates='named_area')

    def __str__(self):
        return f'<NamedArea: [{self.area_class.name}]{self.name}|{self.name_en}>'

    def get_country(self):
        if self.area_class_id == 7: # TODO: other class
            return Country.query.filter(Country.iso3==self.code).first()

        return None

    @property
    def display_name(self):
        return '{}{}'.format(
            self.name_en if self.name_en else '',
            f' ({self.name})' if self.name and self.name.strip() else ''
        )

    @property
    def display_text(self):
        return '{}{}'.format(
            self.name_en if self.name_en else '',
            f' ({self.name})' if self.name and self.name.strip() else ''
        )

    def get_parents(self, parents=[]):
        # by organization?

        def recur_parents(obj, parents=[]):
            data = parents[:]
            if obj.parent_id:
                data.append(obj.parent)
                return recur_parents(obj.parent, data)
            else:
                return list(reversed(data))

        return recur_parents(self)

    @property
    def name_best(self):
        if name := self.name:
            return name
        elif name := self.name_en:
            return name
        return ''

    def to_dict(self, with_meta=False):
        data = {
            'id': self.id,
            'parent_id': self.parent_id,
            'name': self.name,
            'name_en': self.name_en,
            'area_class_id': self.area_class_id,
            'area_class': self.area_class.to_dict(),
            #'name_mix': '/'.join([self.name, self.name_en]),
            'display_name': self.display_name or '',
            #'name_best': self.name_best,
            # 'higher_area_classes': self.get_higher_area_classes(),
        }
        if with_meta is True:
            #set_locale()
            data['meta'] = {
                'term': 'named_area',
                'label': gettext('地點'),
                'display': data['display_name'],
            }

        return data


# class GeoName(Base):
#     __tablename__ = 'addon_geoname'
#     geonameid = Column(Integer, primary_key=True, autoincrement=False)
#     name = Column(String(500))
#     asciiname = Column(String(500))
#     alternatenames = Column(Text)
#     latitude = Column(String(500))
#     longitude = Column(String(500))
#     feature_class = Column(String(500))
#     feature_code = Column(String(500))
#     country_code = Column(String(2))
#     cc2 = Column(String(500))
#     admin1_code = Column(String(500))
#     admin2_code = Column(String(500))
#     admin3_code = Column(String(500))
#     admin4_code = Column(String(500))
#     population = Column(Integer)
#     elevation = Column(Integer)
#     dem = Column(String(500))
#     timezone = Column(String(500))
#     modification_date = Column(String(500))


class AlternativeName(Base, TimestampMixin):
    __tablename__ = 'alternative_name'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    lang = Column(String(8))
    named_area_id = Column(Integer, ForeignKey('named_area.id'), primary_key=True)
