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


class Continent(object):
    ID_MAP = {
        'Asia': '20576,20586,20595,20596,20604,20608,20619,20625,20628,20629,20632,20633,20639,20640,20643,20644,20652,20661,20665,20667,20671,20679,20682,20689,20692,20697,20701,20703,20705,20710,20712,20717,20718,20721,20725,20727,20728,20729,20733,20744,20745,20755,20756,20762,20763,20766,20768,20769,20770,20777,20779,20780,20784,20785,20792,20793,20795,20811,20816,20823',
        'Europe': '20571,20572,20573,20574,20575,20578,20581,20587,20588,20602,20603,20605,20606,20621,20626,20631,20635,20637,20653,20663,20669,20670,20678,20683,20690,20696,20699,20708,20716,20731,20732,20734,20735,20738,20749,20752,20757,20758,20760,20767,20783,20796,20800,20803,20804,20810,20812,20813,20818,20821,20824,20825',
        'Africa': '20570,20579,20582,20584,20593,20594,20598,20599,20601,20607,20610,20613,20614,20624,20627,20630,20636,20641,20642,20645,20651,20656,20658,20659,20664,20668,20673,20676,20677,20686,20687,20691,20694,20695,20700,20702,20704,20706,20707,20709,20713,20722,20726,20740,20743,20747,20753,20759,20773,20774,20776,20778,20781,20786,20788,20797,20798,20801,20806,20807,20817,20819,20822',
        'Americas': '20577,20580,20583,20589,20591,20592,20597,20600,20609,20611,20612,20615,20618,20622,20634,20647,20648,20649,20650,20655,20657,20660,20662,20666,20674,20675,20680,20681,20693,20698,20711,20715,20720,20724,20730,20739,20741,20742,20746,20750,20751,20772,20782,20787,20789,20790,20791,20794,20802,20805,20809,20815,20820',
        'Oceania': '20585,20590,20616,20617,20623,20638,20646,20654,20672,20684,20685,20688,20714,20719,20723,20736,20748,20754,20761,20764,20775,20799,20808,20814',
        'Antarctica': '20620,20737,20765,20771',
    }

    def get_named_area_ids(self, continent):
        if x := self.ID_MAP.get(continent.capitalize()):
            return x.split(',')
        return []

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

    @property
    def display_name(self):
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
