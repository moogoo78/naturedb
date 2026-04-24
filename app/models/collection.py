from datetime import datetime
import json

from flask import (
    g,
    url_for,
    request,
    current_app,
)
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
    func,
)
from sqlalchemy.orm import (
    relationship,
    backref,
    validates,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.declarative import declared_attr
from flask_babel import (
    get_locale,
    gettext,
)

from app.database import (
    Base,
    session,
    TimestampMixin,
    UpdateMixin,
    ModelHistory,
)
from app.models.site import (
    Organization,
)
from app.models.taxon import (
    Taxon,
    TaxonRelation,
)
from app.models.gazetter import (
    AreaClass,
    NamedArea,
)
from app.utils import (
    dd2dms,
    extract_integer,
    get_time,
)
#from app.helpers import (
#    set_locale,
#)

def get_structed_list(options, value_dict={}):
    '''structed_list
    dict key must use id (str)
    '''
    res = []
    for i, option in enumerate(options):
        name = option.get('name')
        res.append({
            'id': option.get('id', ''),
            'name': name,
            'label': option.get('label', ''),
            'value': value_dict.get(name),
        })
    return res

person_group_map = Table(
    'person_group_map',
    Base.metadata,
    Column('person_id', ForeignKey('person.id'), primary_key=True),
    Column('group_id', ForeignKey('person_group.id'), primary_key=True),
)

def find_options(key, options):
    if option := list(filter(lambda x: (x[0] == key), options)):
        return option
    return None


class Event(Base, TimestampMixin):
    __tablename__ = 'event'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    # event_number = Column(String(500)) # dwc: fieldNumber?
    datetime = Column(DateTime)
    datetime_end = Column(DateTime)

    records = relationship('Record')


class Collection(Base, TimestampMixin):
    __tablename__ = 'collection'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    label = Column(String(500))

    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    site_id = Column(Integer, ForeignKey('site.id', ondelete='SET NULL'), nullable=True)
    sort = Column(Integer, default=0)

    parent_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'))

    parent = relationship('Collection', remote_side=[id], back_populates='children')
    children = relationship('Collection', back_populates='parent')

    area_classes = relationship('AreaClass')
    organization = relationship('Organization', back_populates='collections')
    site = relationship('Site', back_populates='collections')
    taxon_maps = relationship('CollectionTaxonMap', back_populates='collection')

    def get_options(self, key):
        if key == 'assertion_types':
            return AssertionType.query.filter(AssertionType.collection_id==self.id).order_by(AssertionType.sort).all()

        elif key == 'annotation_types':
            return AnnotationType.query.filter(AnnotationType.collection_id==self.id).order_by(AnnotationType.sort).all()
        return []

#record_named_area_map = Table(
class RecordNamedAreaMap(Base):
    '''
    via:
    - A: convert from legacy system (area_class_id from 1 to 4) => migrated
    - B: convert from lon/lat UI => geo-lookup
    - C: choose from select UI => manual

  Claude recommanded:
  Potential Future Via Values:

  - manual - User selection
  - geo-lookup - Coordinate-based lookup
  - imported - Bulk data import
  - auto-corrected - Automated data cleaning
  - migrated - Legacy data migration
  - batch-processed - Batch geocoding

    '''
    __tablename__ = 'record_named_area_map'
    record_id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    named_area_id = Column(Integer, ForeignKey('named_area.id'), primary_key=True)
    via = Column(String(10))
    record = relationship('Record', back_populates='named_area_maps')
    named_area = relationship('NamedArea', back_populates='record_maps')

class Record(Base, TimestampMixin, UpdateMixin):
    __tablename__ = 'record'

    id = Column(Integer, primary_key=True)
    collect_date = Column(DateTime) # abcd: Date
    collect_date_year = Column(Integer)
    collect_date_month = Column(Integer)
    collect_date_day = Column(Integer)
    verbatim_collect_date = Column(String(500))
    # abcd: GatheringAgent, DiversityCollectinoModel: CollectionAgent
    collector_id = Column(Integer, ForeignKey('person.id'))
    verbatim_collector = Column(String(500)) # dwc:recordedBy
    field_number = Column(String(500), index=True)
    field_number_int = Column(Integer, index=True) # for sorting and sequence query
    collector = relationship('Person')
    companions = relationship('RecordPerson', back_populates='record', order_by='RecordPerson.sequence') # companion
    companion_text = Column(String(500)) # unformatted value, # HAST:companions
    companion_text_en = Column(String(500))

    # Locality verbatim
    verbatim_locality = Column(String(1000))
    locality_text = Column(String(1000))
    locality_text_en = Column(String(1000))

    altitude = Column(Integer)
    altitude2 = Column(Integer)
    #depth


    GEOCHRONOLOGIC_RANK_MAP = {}  # populated after class definition

    # Coordinate
    geodetic_datum = Column(String(50))
    latitude_decimal = Column(Numeric(precision=9, scale=6))
    longitude_decimal = Column(Numeric(precision=9, scale=6))
    verbatim_latitude = Column(String(50))
    verbatim_longitude = Column(String(50))
    coordinate_uncertainty_in_meters = Column(Numeric(precision=10, scale=2))

    field_note = Column(Text)
    field_note_en = Column(Text)
    other_field_numbers = relationship('FieldNumber')
    #identifaications = relationship('Identification', back_populates='entity', lazy='dynamic')
    identifications = relationship('Identification', lazy='dynamic')

    proxy_taxon_scientific_name = Column(Text)
    proxy_taxon_common_name = Column(Text)
    proxy_taxon_id = Column(Integer, ForeignKey('taxon.id'))
    # proxy_unit_accession_numbers = Column(String(1000))
    source_data = Column(JSONB)

    # proxy_units = Column(JSONB)

    collection_id = Column(Integer, ForeignKey('collection.id'), index=True)
    project_id = Column(Integer, ForeignKey('project.id'))
    event_id = Column(Integer, ForeignKey('event.id'))

    #named_area_relations = relationship('CollectionNamedArea')
    #named_areas = relationship('NamedArea', secondary='record_named_area_map', back_populates='record')
    #named_areas = relationship('Record', secondary='record_named_area_map', back_populates='records')
    named_area_maps = relationship('RecordNamedAreaMap', back_populates='record', cascade='all, delete-orphan')

    record_groups = relationship('RecordGroup', secondary='record_group_map', back_populates='records') # bypassing arecord_group_map
    record_group_maps = relationship('RecordGroupMap', back_populates='record', overlaps='record_groups', cascade='all, delete-orphan') # association

    assertions = relationship('RecordAssertion')
    annotations = relationship('RecordAnnotation')
    # assertions = relationship('EntityAssertion', secondary=entity_assertion_map, backref='entities')
    project = relationship('Project')
    collection = relationship('Collection')
    units = relationship('Unit')
    taxon = relationship('Taxon', foreign_keys=proxy_taxon_id)
    taxon_family = relationship(
        'Taxon',
        secondary='taxon_relation',
        primaryjoin='and_(TaxonRelation.depth==2, TaxonRelation.child_id==Record.proxy_taxon_id)',
        secondaryjoin='Taxon.id==TaxonRelation.parent_id',
        uselist=False,
        viewonly=True,
    )
    record_multimedia_objects = relationship('MultimediaObject')
    geological_context = relationship('RecordGeologicalContext', uselist=False, back_populates='record', cascade='all, delete-orphan')
    '''
    @validates('altitude')
    def validate_altitude(self, key, value):
        try:
            value_int = int(value)
        except ValueError:
            return None

        return value_int

    @validates('altitude2')
    def validate_altitude2(self, key, value):
        try:
            value_int = int(value)
        except ValueError:
            return None

        return value_int
    '''

    def __repr__(self):
        return '<Record id="{}">'.format(self.id)

    def get_record_number(self):
        name = ''
        if self.collector:
            name = self.collector.display_name
        if fn := self.field_number:
            name = f'{name} {fn}'
        return name

    def get_named_area_map(self, custom_area_class_ids=[]):
        '''return relationship
        '''
        rna_map = {}

        list_name_map = [7, 8, 9, 10] + custom_area_class_ids
        area_class_ids = list_name_map
        for m in self.named_area_maps:
            if m.named_area.area_class_id in area_class_ids:
                rna_map[m.named_area.area_class.name] = m
        return rna_map

    def get_assertion(self, type_name='', part=''):
        if type_name:
            for x in self.assertions:
                if x.assertion_type.name == type_name:
                    return getattr(x, part) if part else x

        return ''

    def get_named_area(self, area_class_name=''):
        if area_class_name:
            for m in self.named_area_maps:
                if m.named_area.area_class.name == area_class_name:
                    return m.named_area
        return ''

    @property
    def key(self):
        unit_keys = [x.key for x in self.units]
        if len(unit_keys):
            return ','.join(unit_keys)
        else:
            return '--'

    @property
    def last_identification(self):
        return self.identifications.order_by(desc(Identification.sequence)).first()

    def update_proxy(self):
        if lid := self.last_identification:
            if taxon := lid.taxon:
                self.proxy_taxon_scientific_name = taxon.full_scientific_name
                self.proxy_taxon_common_name = taxon.common_name
                self.proxy_taxon_id = taxon.id
                session.commit()
            elif x := lid.verbatim_identification:
                self.proxy_taxon_scientific_name = x
        else:
            self.proxy_taxon_scientific_name = ''
            self.proxy_taxon_common_name = ''
            self.proxy_taxon_id = None

        session.commit()


    @staticmethod
    def get_editable_fields(field_types=['date', 'int', 'str', 'decimal', 'remote_id']):
        remote_fields = [
            'collector_id',
            'collection_id',
        ]
        date_fields = [
            'collect_date',
        ]
        int_fields = [
            'altitude',
            'altitude2',
            'collect_date_year',
            'collect_date_month',
            'collect_date_day',
        ]
        str_fields = [
            'field_number',
            'verbatim_collect_date',
            'verbatim_collector',
            'companion_text',
            'companion_text_en',
            'verbatim_longitude',
            'verbatim_latitude',
            'locality_text',
            'locality_text_en',
            'field_note',
            'field_note_en',
            'verbatim_locality',
            'geodetic_datum',
        ]
        decimal_fields = [
            'longitude_decimal',
            'latitude_decimal',
        ]

        fields = []
        for i in field_types:
            if i == 'date':
                fields += date_fields
            if i == 'str':
                fields += str_fields
            if i == 'int':
                fields += int_fields
            if i == 'decimal':
                fields += decimal_fields
            if i == 'remote_id':
                fields += remote_fields
        return fields

    def display_altitude(self):
        alt = []
        if x := self.altitude:
            alt.append(str(x))
        if x := self.altitude2:
            alt.append(str(x))

        if len(alt) == 1:
            return alt[0]
        elif len(alt) > 1:
            return '-'.join(alt)

    def get_coordinate(self, type_=''):
        if self.longitude_decimal and self.latitude_decimal:
            if type_ == '' or type_ == 'dd':
                return {
                    'x': self.longitude_decimal,
                    'y': self.latitude_decimal
                }
            elif type_ == 'dms':
                dms_lng = dd2dms(self.longitude_decimal)
                dms_lat = dd2dms(self.latitude_decimal)
                x_label = '{}{}\u00b0{:02d}\'{:02d}"'.format('E' if dms_lng[0] > 0 else 'W', dms_lng[0], dms_lng[1], round(dms_lng[2]))
                y_label = '{}{}\u00b0{}\'{:02d}"'.format('N' if dms_lat[0] > 0 else 'S', dms_lat[0], dms_lat[1], round(dms_lat[2]))
                return {
                    'x': dms_lng,
                    'y': dms_lat,
                    'x_label': x_label,
                    'y_label': y_label,
                    'simple': f'{x_label}, {y_label}'
                }
        else:
            return None

    def get_first_id(self):
        if id_ := self.identifications.order_by(Identification.sequence).first():
            return id_
        return None

    def get_rest_id(self):
        if ids := self.identifications.filter(Identification.sequence>0).order_by(Identification.sequence).all():
            return ids
        return []

    @property
    def companion_list(self):
        items = []
        for c in self.companions:
            if c.person:
                items.append(c.person.display_name)
        if not items:
            if x := self.companion_text:
                items.append(x)
            if x := self.companion_text_en:
                items.append(x)
        return items

    @validates('field_number')
    def set_field_number_integer(self, key, value):
        if n := extract_integer(value):
            self.field_number_int = n
        return value

    @staticmethod
    def get_items(payload, auth={}, mode=''):
        from app.helpers_query import make_items_stmt
        from app.models.site import User

        stmt, total = make_items_stmt(payload, auth, mode)
        current_app.logger.debug(f'query_items) {stmt}')
        result = session.execute(stmt)
        rows = result.all()

        if not rows:
            return {'data': [], 'total': total}

        record_ids = [r[0] for r in rows]
        unit_ids = [r[1] for r in rows if r[1]]

        # batch: named areas
        na_rows = session.execute(
            select(RecordNamedAreaMap.record_id, NamedArea.name, NamedArea.name_en)
            .join(NamedArea, NamedArea.id == RecordNamedAreaMap.named_area_id)
            .where(RecordNamedAreaMap.record_id.in_(record_ids))
        ).all()
        named_area_map = {}
        for rid, na_name, na_name_en in na_rows:
            display = '{}{}'.format(
                na_name_en if na_name_en else '',
                f' ({na_name})' if na_name and na_name.strip() else ''
            )
            named_area_map.setdefault(rid, []).append(display)

        # batch: identifications (ordered by sequence)
        id_rows = session.execute(
            select(Identification)
            .where(Identification.record_id.in_(record_ids))
            .order_by(Identification.record_id, Identification.sequence)
        ).scalars().all()
        ids_map = {}
        for ident in id_rows:
            ids_map.setdefault(ident.record_id, []).append(ident)

        # batch: model history (latest per record)
        history_sub = session.execute(
            select(
                ModelHistory.item_id,
                ModelHistory.created,
                User.username,
            )
            .join(User, User.id == ModelHistory.user_id, isouter=True)
            .where(
                ModelHistory.tablename == 'record*',
                ModelHistory.item_id.in_([str(rid) for rid in record_ids]),
            )
            .order_by(ModelHistory.item_id, desc(ModelHistory.created))
            .distinct(ModelHistory.item_id)
        ).all()
        history_map = {row[0]: (row[1], row[2]) for row in history_sub}

        # batch: cover images
        cover_image_ids = [r[24] for r in rows if r[24]]  # Unit.cover_image_id
        image_url_map = {}
        if cover_image_ids:
            img_rows = session.execute(
                select(MultimediaObject.id, MultimediaObject.file_url)
                .where(MultimediaObject.id.in_(cover_image_ids))
            ).all()
            image_url_map = {img_id: file_url for img_id, file_url in img_rows}

        # batch: unit annotations (PPI hack)
        ppi_unit_ids = set()
        if unit_ids:
            ppi_rows = session.execute(
                select(UnitAnnotation.unit_id)
                .join(AnnotationType, AnnotationType.id == UnitAnnotation.annotation_type_id)
                .where(
                    UnitAnnotation.unit_id.in_(unit_ids),
                    AnnotationType.name == 'is_ppi_transcribe',
                )
            ).scalars().all()
            ppi_unit_ids = set(ppi_rows)

        # build result data
        data = []
        for r in rows:
            record_id = r[0]
            unit_id = r[1]
            proxy_sci_name = r[2]
            proxy_common_name = r[3]
            proxy_taxon_id = r[4]
            collection_id = r[5]
            collector_id = r[6]
            field_number = r[7]
            collect_date = r[8]
            locality_text = r[9]
            verbatim_locality = r[10]
            verbatim_collector = r[11]
            companion_text = r[12]
            verbatim_collect_date = r[13]
            source_data = r[14] or {}
            altitude = r[15]
            altitude2 = r[16]
            verbatim_longitude = r[17]
            verbatim_latitude = r[18]
            created = r[19]
            updated = r[20]
            person_full_name = r[21]
            person_full_name_en = r[22]
            accession_number = r[23]
            cover_image_id = r[24]
            unit_collection_id = r[25]
            collect_date_year = r[26]
            collect_date_month = r[27]
            collect_date_day = r[28]

            taxon = proxy_sci_name
            if proxy_common_name:
                taxon = f'{taxon} ({proxy_common_name})'

            locality_list = named_area_map.get(record_id, [])
            if locality_text:
                locality_list = locality_list + [locality_text]
            if len(locality_list) == 0 and verbatim_locality:
                locality_list = [verbatim_locality]

            # mod_time
            mod_time = ''
            if created:
                mod_time = created.strftime('%Y-%m-%d')
            if updated:
                mod_time = mod_time + '/' + updated.strftime('%Y-%m-%d')
            hist = history_map.get(str(record_id))
            if hist and hist[1]:
                mod_time = f'{mod_time} ({hist[1]})'

            item = {
                'record_id': record_id,
                'collection_id': collection_id,
                'item_key': f'r{record_id}',
                'mod_time': mod_time,
                'image_url': '',
            }
            if mode == 'raw':
                collector = source_data.get('collector_zh', '')
                if x := source_data.get('collector'):
                    collector = f'{collector} ({x})'
                taxon = source_data.get('species_name', '')
                if x := source_data.get('species_name_zh'):
                    taxon = f'{taxon} ({x})'
                locality_list = []
                # TOOO 中英文
                if x := source_data.get('country', ''):
                    locality_list.append(x)
                if x := source_data.get('county', ''):
                    locality_list.append(x)
                if x := source_data.get('localityc', ''):
                    if y := source_data.get('locality', ''):
                        x = f'{x} ({y})'
                    locality_list.append(x)

                item.update({
                    'collector': collector,
                    'field_number': source_data.get('collect_num', ''),
                    'collect_date': source_data.get('collection_date', ''),
                    'taxon': taxon,
                    'locality': '|'.join(locality_list),
                })
            else:
                # collector display_name inline
                collector_display = ''
                if collector_id:
                    if person_full_name and person_full_name_en:
                        collector_display = f'{person_full_name_en} ({person_full_name})'
                    elif person_full_name:
                        collector_display = person_full_name
                    elif person_full_name_en:
                        collector_display = person_full_name_en

                collect_date_display = ''
                if collect_date:
                    collect_date_display = collect_date.strftime('%Y-%m-%d')
                elif collect_date_year:
                    parts = [str(collect_date_year)]
                    if collect_date_month:
                        parts.append(f'{collect_date_month:02d}')
                        if collect_date_day:
                            parts.append(f'{collect_date_day:02d}')
                    collect_date_display = '-'.join(parts)

                item.update({
                    'collector': collector_display,
                    'field_number': field_number or '',
                    'collect_date': collect_date_display,
                    'taxon': taxon,
                    'locality': ','.join(locality_list),
                })

            # quick edit fields
            verbatim_identification = ''
            if not proxy_taxon_id and proxy_sci_name != '':
                verbatim_identification = proxy_sci_name

            id1 = None
            id2 = None
            ids = ids_map.get(record_id, [])
            if len(ids) > 2:
                id1 = ids[1]
                id2 = ids[2]
            elif len(ids) == 2:
                id1 = ids[1]

            item.update({
                'verbatim_collector': verbatim_collector or '',
                'companion_text': companion_text or '',
                'verbatim_collect_date': verbatim_collect_date or '',
                'quick__scientific_name': source_data.get('quick__scientific_name', ''),
                'quick__verbatim_scientific_name': verbatim_identification or '',
                'verbatim_locality': verbatim_locality or '',
                'quick__other_text_on_label': source_data.get('quick__other_text_on_label', ''),
                'quick__user_note': source_data.get('quick__user_note', ''),
                'altitude': altitude,
                'altitude2': altitude2,
                'verbatim_longitude': verbatim_longitude,
                'verbatim_latitude': verbatim_latitude,
                'quick__id1_id': id1.id if id1 else '',
                'quick__id1_verbatim_identifier': id1.verbatim_identifier if id1 else '',
                'quick__id1_verbatim_date': id1.verbatim_date if id1 else '',
                'quick__id1_verbatim_identification': id1.verbatim_identification if id1 else '',
                'quick__id2_id': id2.id if id2 else '',
                'quick__id2_verbatim_identifier': id2.verbatim_identifier if id2 else '',
                'quick__id2_verbatim_date': id2.verbatim_date if id2 else '',
                'quick__id2_verbatim_identification': id2.verbatim_identification if id2 else '',
            })

            item['quick__ppi_is_transcribed'] = False
            if unit_id:
                # unit display
                image_url = ''
                if cover_image_id and cover_image_id in image_url_map:
                    image_url = image_url_map[cover_image_id].replace('-m.jpg', '-s.jpg')

                if mode == 'raw':
                    cat_num = source_data.get('voucher_id')
                    if unit_id_str := source_data.get('unit_id'):
                        cat_num = f'{cat_num} ({unit_id_str})'
                else:
                    cat_num = accession_number

                item.update({
                    'catalog_number': cat_num,
                    'item_key': f'u{unit_id}',
                    'collection_id': f'u{unit_collection_id}',
                    'image_url': image_url,
                })

                if unit_id in ppi_unit_ids:
                    item['quick__ppi_is_transcribed'] = True

            data.append(item)

        return {
            'data': data,
            'total': total,
        }


    @staticmethod
    def from_dict(data, uid):
        # create new Record
        from app.helpers import put_entity
        if collection := session.get(Collection, data['collection_id']):
            record = Record(collection_id=collection.id)
            session.add(record)
            session.commit()
            item = put_entity(record, data, collection, uid, True)
            return {'message': 'ok', 'next_url': url_for('admin.record_form', entity_key=f'r{record.id}')}, item

        return {'error': 'no collection'}

    @classmethod
    def delete_by_instance(cls, session, instance):
        session.delete(instance)
        session.commit()

    def get_values(self):
        from app.helpers import get_record_values
        return get_record_values(self)

    def get_taxon_display(self):
        name = {
            'full': '',
            'canonical': '',
            'common': '',
            'author': '',
            'id': None,
            'family': {
                'name': '',
                'common': '',
            }
        }

        if x := self.proxy_taxon_common_name:
            name['common'] = x
        if x := self.proxy_taxon_id:
            name['id'] = x
            if taxon := session.get(Taxon, x):
                if family := taxon.get_higher_taxon('family'):
                    name['family']['name'] = family.full_scientific_name
                    name['family']['common'] = family.common_name
                if taxon.source_id:
                    name['taxon_source_id'] = taxon.source_id
                if taxon.tree_id:
                    from app.models.taxon import TaxonTree
                    if tree := session.get(TaxonTree, taxon.tree_id):
                        name['backbone'] = tree.name
                        name['backbone_is_external'] = bool(tree.is_external)
        if x := self.proxy_taxon_scientific_name:
            name['full'] = x
            # stupid parse
            nlist = x.split(' ')
            if len(nlist) >= 2:
                name['canonical'] = f'{nlist[0]} {nlist[1]}'
                name['author'] = ' '.join([x for x in nlist[2:]])

        return name

    def get_info(self, section=''):
        # section: gathering, location, taxon, identification
        info = {
            'gathering': {
                'collector': {
                    'name': '',
                    'companion_list':[],
                },
                'label_taxon_display': '',
            },
            'taxon': self.get_taxon_display(),
            'location': {
                'coordinate_display': '',
            },
            'identifications': [],
        }

        if self.collector_id:
            info['gathering']['collector']['name'] = self.collector.display_name if self.collector_id else ''
            # TODO
            if x := self.companion_text:
                info['gathering']['collector']['companion_list'].append(x)
            if x := self.companion_text_en: # TODO clean data
                info['gathering']['collector']['companion_list'].append(x)

        if self.collect_date:
            info['gathering']['collect_date'] = self.collect_date
            info['gathering']['collect_date_display'] = self.collect_date.strftime('%Y-%m-%d')
        elif self.collect_date_year:
            parts = [str(self.collect_date_year)]
            if self.collect_date_month:
                parts.append(f'{self.collect_date_month:02d}')
                if self.collect_date_day:
                    parts.append(f'{self.collect_date_day:02d}')
            info['gathering']['collect_date_display'] = '-'.join(parts)
        elif x := self.verbatim_collect_date:
            info['gathering']['collect_date_display'] = x

        info['gathering']['field_number'] = self.field_number or ''

        info['location'] = {
            'locality': '',
            'altitude': self.altitude or '',
            'altitude2': self.altitude2 or '',
            'altitude_display': '',
            'latitude_decimal': self.latitude_decimal or '',
            'longitude_decimal': self.longitude_decimal or '',
            'verbatim_latitude': self.verbatim_latitude or '',
            'verbatim_longitude': self.verbatim_longitude or '',
            'coordinate_dms_display': '',
            'coordinate_dd_display': '',
            'country': '',
            'adm_display': '',
            'named_areas': [],
        }
        if self.altitude and self.altitude2:
            info['location']['altitude_display'] = f'{self.altitude} - {self.altitude2}'
        if self.latitude_decimal and self.longitude_decimal:
            dms = self.get_coordinate('dms')
            dd = self.get_coordinate('dd')
            info['location']['coordinate_dms_display'] = dms['simple']
            info['location']['coordinate_dd'] = {
                'x':float(dd['x']),
                'y': float(dd['y'])
            }
            info['location']['coordinate_dd_display'] = f"{dd['x']}, {dd['y']}"

        custom_area_class_ids = [x.id for x in self.collection.site.get_custom_area_classes()]
        na_dict = self.get_named_area_map(custom_area_class_ids)
        if x := na_dict.get('COUNTRY'):
            info['location']['country'] = x.named_area.display_name
        na_adm_list = []
        for x in ['ADM1', 'ADM2', 'ADM3']:
            if m := na_dict.get(x):
                na_adm_list.append(m.named_area.display_name)
        info['location']['adm_display'] = ' • '.join(na_adm_list)
        na_list = []
        for k, v in na_dict.items():
            if k not in ['COUNTRY', 'ADM1', 'ADM2', 'ADM3']:
                na_list.append(v.named_area);

        info['location']['named_areas'] = [[x.area_class.label, x.name] for x in na_list]

        loc_list = []
        if x:= self.locality_text:
            loc_list.append(x);
        if x:= self.locality_text_en:
            loc_list.append(x);
        if x:= self.verbatim_locality:
            loc_list.append(x);

        info['location']['locality_display'] = ' | '.join(loc_list)

        assertions = []
        assertion_type_list = AssertionType.query.filter(AssertionType.target=='record', AssertionType.collection_id==self.collection_id).order_by('sort').all()
        for i in assertion_type_list:
            val = ''
            if a := self.get_assertion(i.name):
                val = a.value
                if a.option_id:
                    opt = session.get(AssertionTypeOption, a.option_id)
                    val = f'{opt.value} ({opt.description})'

            assertions.append([i.label, val])

        info['assertions'] = assertions

        ids = []
        for i in self.identifications.order_by(Identification.sequence).all():
            if i.sequence == 0 and i.taxon_id:
                info['gathering']['label_taxon_display'] = i.taxon.display_name
            ids.append(i.to_dict())

        info['identifications'] = ids

        # Geological context (fossil specimens only)
        if rgc := self.geological_context:
            geo = {}
            # Geochronologic
            geo_parts = []
            if rgc.geochronologic_option_prefix:
                geo_parts.append(rgc.geochronologic_option_prefix)
            if rgc.geochronologic_text:
                geo_parts.append(rgc.geochronologic_text)
            if geo_parts:
                geo['geochronologic'] = ' '.join(geo_parts)
            geo_parts2 = []
            if rgc.geochronologic_prefix2:
                geo_parts2.append(rgc.geochronologic_prefix2)
            if rgc.geochronologic_text2:
                geo_parts2.append(rgc.geochronologic_text2)
            if geo_parts2:
                geo['geochronologic2'] = ' '.join(geo_parts2)
            if rgc.geochronologic_text_en:
                geo['geochronologic_en'] = rgc.geochronologic_text_en
            # Biostratigraphic
            if rgc.biostratigraphic_zone:
                geo['biostratigraphic_zone'] = rgc.biostratigraphic_zone
            if rgc.biostratigraphic_zone2:
                geo['biostratigraphic_zone2'] = rgc.biostratigraphic_zone2
            # Lithostratigraphic
            if rgc.lithostratigraphic_terms:
                geo['lithostratigraphic_terms'] = rgc.lithostratigraphic_terms
            if rgc.geological_context_group:
                geo['group'] = rgc.geological_context_group
            if rgc.formation:
                geo['formation'] = rgc.formation
            if rgc.formation_en:
                geo['formation_en'] = rgc.formation_en
            if rgc.member:
                geo['member'] = rgc.member
            if rgc.bed:
                geo['bed'] = rgc.bed
            if geo:
                info['geological_context'] = geo

        return info

    # DwC field names for each geochronologic rank: (earliest_field, latest_field)
    GEOCHRONOLOGIC_DWC_FIELDS = {
        'eon': ('earliestEonOrLowestEonothem', 'latestEonOrHighestEonothem'),
        'era': ('earliestEraOrLowestErathem', 'latestEraOrHighestErathem'),
        'period': ('earliestPeriodOrLowestSystem', 'latestPeriodOrHighestSystem'),
        'epoch': ('earliestEpochOrLowestSeries', 'latestEpochOrHighestSeries'),
        'age': ('earliestAgeOrLowestStage', 'latestAgeOrHighestStage'),
    }

    def get_geochronologic_dwc(self):
        """Map earliest/latest_geochronologic values to Darwin Core fields.
        Delegates to RecordGeologicalContext child row."""
        rgc = self.geological_context
        if not rgc:
            return {}
        result = {}
        rank_map = Record.GEOCHRONOLOGIC_RANK_MAP
        dwc = Record.GEOCHRONOLOGIC_DWC_FIELDS
        for term, prefix, idx in [
            (rgc.geochronologic_text, rgc.geochronologic_option_prefix, 0),
            (rgc.geochronologic_text2, rgc.geochronologic_prefix2, 1),
        ]:
            if term and term in rank_map:
                rank = rank_map[term]
                value = f'{prefix} {term}' if prefix else term
                result[dwc[rank][idx]] = value
        return result


# Build reverse lookup: value -> rank (eon/era/period/epoch/age)
# (populated after RecordGeologicalContext is defined)


class RecordGeologicalContext(Base, UpdateMixin):
    """Darwin Core GeologicalContext fields stored in a separate table.
    1:1 with Record — only created for fossil specimens."""

    __tablename__ = 'record_geological_context'

    GEO_FIELDS = [
        'geochronologic_text',
        'geochronologic_text_en',
        'geochronologic_option',
        'geochronologic_option_prefix',
        'geochronologic_text2',
        'geochronologic_prefix2',
        'biostratigraphic_zone',
        'biostratigraphic_zone2',
        'lithostratigraphic_terms',
        'geological_context_group',
        'formation',
        'formation_en',
        'member',
        'bed',
    ]

    # Geochronologic options (ICS International Chronostratigraphic Chart)
    EON_OPTIONS = (
        ('Phanerozoic', '顯生宙 Phanerozoic'),
        ('Proterozoic', '元古宙 Proterozoic'),
        ('Archean', '太古宙 Archean'),
        ('Hadean', '冥古宙 Hadean'),
    )
    ERA_OPTIONS = (
        ('Cenozoic', '新生代 Cenozoic'),
        ('Mesozoic', '中生代 Mesozoic'),
        ('Paleozoic', '古生代 Paleozoic'),
        ('Neoproterozoic', '新元古代 Neoproterozoic'),
        ('Mesoproterozoic', '中元古代 Mesoproterozoic'),
        ('Paleoproterozoic', '古元古代 Paleoproterozoic'),
        ('Neoarchean', '新太古代 Neoarchean'),
        ('Mesoarchean', '中太古代 Mesoarchean'),
        ('Paleoarchean', '古太古代 Paleoarchean'),
        ('Eoarchean', '始太古代 Eoarchean'),
    )
    PERIOD_OPTIONS = (
        ('Quaternary', '第四紀 Quaternary'),
        ('Neogene', '新近紀 Neogene'),
        ('Paleogene', '古近紀 Paleogene'),
        ('Cretaceous', '白堊紀 Cretaceous'),
        ('Jurassic', '侏羅紀 Jurassic'),
        ('Triassic', '三疊紀 Triassic'),
        ('Permian', '二疊紀 Permian'),
        ('Carboniferous', '石炭紀 Carboniferous'),
        ('Devonian', '泥盆紀 Devonian'),
        ('Silurian', '志留紀 Silurian'),
        ('Ordovician', '奧陶紀 Ordovician'),
        ('Cambrian', '寒武紀 Cambrian'),
        ('Ediacaran', '埃迪卡拉紀 Ediacaran'),
        ('Cryogenian', '成冰紀 Cryogenian'),
        ('Tonian', '拉伸紀 Tonian'),
        ('Stenian', '狹帶紀 Stenian'),
        ('Ectasian', '延展紀 Ectasian'),
        ('Calymmian', '蓋層紀 Calymmian'),
        ('Statherian', '固結紀 Statherian'),
        ('Orosirian', '造山紀 Orosirian'),
        ('Rhyacian', '層侵紀 Rhyacian'),
        ('Siderian', '成鐵紀 Siderian'),
    )
    EPOCH_OPTIONS = (
        ('Holocene', '全新世 Holocene'),
        ('Pleistocene', '更新世 Pleistocene'),
        ('Pliocene', '上新世 Pliocene'),
        ('Miocene', '中新世 Miocene'),
        ('Oligocene', '漸新世 Oligocene'),
        ('Eocene', '始新世 Eocene'),
        ('Paleocene', '古新世 Paleocene'),
    )
    AGE_OPTIONS = (
        ('Meghalayan', '梅加拉亞期 Meghalayan'),
        ('Northgrippian', '諾斯格瑞比期 Northgrippian'),
        ('Greenlandian', '格陵蘭期 Greenlandian'),
        ('Upper Pleistocene', '上更新世 Upper Pleistocene'),
        ('Chibanian', '奇巴期 Chibanian'),
        ('Calabrian', '卡拉布里亞期 Calabrian'),
        ('Gelasian', '傑拉期 Gelasian'),
        ('Piacenzian', '皮亞琴期 Piacenzian'),
        ('Zanclean', '乍得期 Zanclean'),
        ('Messinian', '墨西拿期 Messinian'),
        ('Tortonian', '托爾頓期 Tortonian'),
        ('Serravallian', '塞拉瓦爾期 Serravallian'),
        ('Langhian', '蘭蓋期 Langhian'),
        ('Burdigalian', '布爾迪加拉期 Burdigalian'),
        ('Aquitanian', '阿基坦期 Aquitanian'),
        ('Chattian', '恰特期 Chattian'),
        ('Rupelian', '呂珀爾期 Rupelian'),
        ('Priabonian', '普里亞邦期 Priabonian'),
        ('Bartonian', '巴爾頓期 Bartonian'),
        ('Lutetian', '盧泰特期 Lutetian'),
        ('Ypresian', '伊普雷斯期 Ypresian'),
        ('Thanetian', '坦尼特期 Thanetian'),
        ('Selandian', '塞蘭特期 Selandian'),
        ('Danian', '丹麥期 Danian'),
        ('Maastrichtian', '馬斯垂克期 Maastrichtian'),
        ('Campanian', '坎帕尼期 Campanian'),
        ('Santonian', '桑托期 Santonian'),
        ('Coniacian', '科尼亞克期 Coniacian'),
        ('Turonian', '土侖期 Turonian'),
        ('Cenomanian', '森諾曼期 Cenomanian'),
        ('Albian', '阿爾布期 Albian'),
        ('Aptian', '阿普第期 Aptian'),
        ('Barremian', '巴列姆期 Barremian'),
        ('Hauterivian', '豪特里維期 Hauterivian'),
        ('Valanginian', '瓦蘭今期 Valanginian'),
        ('Berriasian', '貝里亞斯期 Berriasian'),
        ('Tithonian', '提通期 Tithonian'),
        ('Kimmeridgian', '啟莫里期 Kimmeridgian'),
        ('Oxfordian', '牛津期 Oxfordian'),
        ('Callovian', '卡洛維期 Callovian'),
        ('Bathonian', '巴通期 Bathonian'),
        ('Bajocian', '巴柔期 Bajocian'),
        ('Aalenian', '阿連期 Aalenian'),
        ('Toarcian', '托阿爾期 Toarcian'),
        ('Pliensbachian', '普林斯巴期 Pliensbachian'),
        ('Sinemurian', '錫內穆期 Sinemurian'),
        ('Hettangian', '赫唐期 Hettangian'),
        ('Rhaetian', '瑞替期 Rhaetian'),
        ('Norian', '諾利期 Norian'),
        ('Carnian', '卡尼期 Carnian'),
        ('Ladinian', '拉丁期 Ladinian'),
        ('Anisian', '安尼期 Anisian'),
        ('Olenekian', '奧倫尼克期 Olenekian'),
        ('Induan', '印度期 Induan'),
        ('Changhsingian', '長興期 Changhsingian'),
        ('Wuchiapingian', '吳家坪期 Wuchiapingian'),
        ('Capitanian', '卡匹敦期 Capitanian'),
        ('Wordian', '沃德期 Wordian'),
        ('Roadian', '羅德期 Roadian'),
        ('Kungurian', '空谷期 Kungurian'),
        ('Artinskian', '亞丁斯克期 Artinskian'),
        ('Sakmarian', '薩克馬爾期 Sakmarian'),
        ('Asselian', '阿瑟爾期 Asselian'),
    )

    GEOCHRONOLOGIC_PREFIX_OPTIONS = (
        ('Early', '早期 Early'),
        ('Middle', '中期 Middle'),
        ('Late', '晚期 Late'),
    )

    # Geochronologic hierarchy (stored in RecordGeologicalContext child table)
    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey('record.id', ondelete='CASCADE'), unique=True, nullable=False)
    # Geochronologic
    geochronologic_text = Column(String(500))
    geochronologic_text_en = Column(String(500))
    geochronologic_option = Column(String(50))
    geochronologic_option_prefix = Column(String(50))
    geochronologic_text2 = Column(String(500))
    geochronologic_prefix2 = Column(String(50))
    # Biostratigraphic
    biostratigraphic_zone = Column(String(500))
    biostratigraphic_zone2 = Column(String(500))
    # Lithostratigraphic
    lithostratigraphic_terms = Column(String(500))
    geological_context_group = Column(String(500))  # dwc:group, suffixed to avoid SQL keyword
    formation = Column(String(500))
    formation_en = Column(String(500))
    member = Column(String(500))
    bed = Column(String(500))

    record = relationship('Record', back_populates='geological_context')

    def __repr__(self):
        return f'<RecordGeologicalContext record_id={self.record_id}>'


# Build reverse lookup: value -> rank (eon/era/period/epoch/age)
for _rank, _opts in [('eon', RecordGeologicalContext.EON_OPTIONS),
                     ('era', RecordGeologicalContext.ERA_OPTIONS),
                     ('period', RecordGeologicalContext.PERIOD_OPTIONS),
                     ('epoch', RecordGeologicalContext.EPOCH_OPTIONS),
                     ('age', RecordGeologicalContext.AGE_OPTIONS)]:
    for _val, _label in _opts:
        Record.GEOCHRONOLOGIC_RANK_MAP[_val] = _rank


class Identification(Base, TimestampMixin, UpdateMixin):

    # VER_LEVEL_CHOICES = (
    #     ('0', '初次鑑定'),
    #     ('1', '二次鑑定'),
    #     ('2', '三次鑑定'),
    #     ('3', '四次鑑定'),
    #)

    __tablename__ = 'identification'

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey('record.id', ondelete='SET NULL'), nullable=True)
    record = relationship('Record', back_populates='identifications')
    identifier_id = Column(Integer, ForeignKey('person.id', ondelete='SET NULL'), nullable=True)
    identifier = relationship('Person')
    verbatim_identifier = Column(String(500))
    taxon_id = Column(Integer, ForeignKey('taxon.id', ondelete='set NULL'), nullable=True, index=True)
    taxon = relationship('Taxon', backref=backref('taxon'))
    verbatim_identification = Column(String(500)) # DwC: verbatimIdentification => merged to date_text
    date = Column(DateTime)
    date_text = Column(String(50)) #格式不完整的鑑訂日期, helper: ex: 1999-1
    verbatim_date = Column(String(500)) # DwC: verbatimEventDate
    verification_level = Column(String(50))
    sequence = Column(Integer)

    # abcd: IdentificationSource
    reference = Column(Text)
    note = Column(Text)
    source_data = Column(JSONB)

    def __repr__(self):
        if self.taxon:
            return '<Identification id="{}" taxon="{}">'.format(self.id, self.taxon.display_name)
        return '<Identification id="{}">'.format(self.id)

    @validates('date')
    def validate_date(self, key, date):
        if date == '':
            raise ValueError('date is empty str')
        return date

    def get_date_display(self, fmt='%Y-%m-%d'):
        if x := self.date_text: # TODO 正規化?
            return x
        elif x := self.date:
            return x.strftime(fmt)

        return ''

    def to_dict(self):

        data = {
            'id': self.id,
            #'identification_id': self.id,
            #'collection_id': self.collection_id,
            #'identifier_id': self.identifier_id or '',
            'taxon_id': self.taxon_id or '',
            'date': self.date.strftime('%Y-%m-%d') if self.date else '',
            'date_text': self.date_text or '',
            'verification_level': self.verification_level or '',
            'sequence': self.sequence if self.sequence != None else '',
            'verbatim_date': self.verbatim_date or '',
            'verbatim_identification': self.verbatim_identification or '',
            'note': self.note or '',
            'verbatim_identifier': self.verbatim_identifier or '',
        }
        if self.taxon:
            data['taxon'] =  self.taxon.to_dict() #{'id': self.taxon_id, 'text': self.taxon.display_name}
        if self.identifier:
            data['identifier'] = self.identifier.to_dict()

        return data

    @staticmethod
    def get_editable_fields(field_types=['date', 'int', 'str', 'remote_id']):
        remote_fields = [
            'identifier_id',
            'taxon_id',
        ]
        date_fields = [
            'date',
        ]
        int_fields = [
            'sequence',
        ]
        str_fields = [
            'verbatim_identification',
            'date_text',
            'verbatim_date',
            'note',
            'verbatim_identifier',
        ]

        fields = []
        for i in field_types:
            if i == 'date':
                fields += date_fields
            if i == 'str':
                fields += str_fields
            if i == 'int':
                fields += int_fields
            if i == 'remote_id':
                fields += remote_fields
        return fields


class Propagation(Base, TimestampMixin):
    __tablename__ = 'propagation'

    PROPAGATION_TYPE_OPTIONS = (
        ('greenhouse', '溫室收種'),
        ('give', '贈與'),
        ('outdoor', '野外收種'),
    )

    id = Column(Integer, primary_key=True)
    propagation_type = Column(String(50))
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL'))
    unit = relationship('Unit', back_populates='propagations')
    date = Column(Date)
    note = Column(String(1000), nullable=True)

class Unit(Base, TimestampMixin, UpdateMixin):
    '''mixed abcd: SpecimenUnit/ObservationUnit (phycal state-specific subtypes of the unit reocrd)
    BotanicalGardenUnit/HerbariumUnit/ZoologicalUnit/PaleontologicalUnit
    '''
    BASIS_OF_RECORD_OPTIONS = [
        'MaterialEntity',
        'PreservedSpecimen',
        'FossilSpecimen',
        'LivingSpecimen',
        'MaterialSample',
        'Event',
        'HumanObservation',
        'MachineObservation',
        'Taxon',
        'Occurrence',
        'MaterialCitation',
        'DrawingOrPhotograph',
        'MultimediaObject',
        'AbsenceObservation',
    ]

    KIND_OF_UNIT_MAP = {
        'HS': 'Herbarium Sheet',
        'whole organism': 'whole organizm',
        'seed': 'seed',
        'leaf': 'leaf',
        'leg': 'leg',
    }

    PREPARATION_TYPE_MAP = {
        'S': 'Specimen',
        'DNA': 'DNA',
        'tissue': 'tissue',
    }

    DISPOSITION_OPTIONS = ["in collection", "missing", "source gone", "voucher elsewhere", "duplicates elsewhere", "consumed", "Dead (Disposed of; not retained.)"]

    ACQUISITION_TYPE_OPTIONS = (
        ('collecting', '採集'),
        ('exchange', '交換'),
        ('gift', '贈送'),
        ('bequest', '遺贈'),
        ('donation', '捐贈'),
        ('purchase', '購買'),
        ('found_in_collection', '其他典藏物件'),

    )

    TYPE_STATUS_OPTIONS = (
        ('holotype', 'holotype'),
        ('lectotype', 'lectotype'),
        ('isotype', 'isotype'),
        ('syntype', 'syntype'),
        ('paratype', 'paratype'),
        ('neotype', 'neotype'),
        ('epitype', 'epitype'),
    )

    PUB_STATUS_OPTIONS = (
        ('P', 'Public'),
        ('H', 'Private/Hidden')
    )

    __tablename__ = 'unit'

    id = Column(Integer, primary_key=True)
    guid = Column(String(500))
    record_id = Column(Integer, ForeignKey('record.id', ondelete='SET NULL'), nullable=True)
    collection_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'), nullable=True, index=True)
    #last_editor = Column(String(500)) # link to user

    #owner
    #identifications = relationship('Identification', back_populates='unit')
    kind_of_unit = Column(String(500)) # herbarium sheet (HS), leaf, muscle, leg, blood, ..., ref: https://arctos.database.museum/info/ctDocumentation.cfm?table=ctspecimen_part_name#whole_organism
    basis_of_record = Column(String(50)) # abcd:RecordBasis
    material_entity_id = Column(String(500))

    #material_entity_associated_seequences
    dna_sequence = Column(Text)
    sequencer = Column(String(500))
    # assemblages
    # associations
    # sequences

    assertions = relationship('UnitAssertion')
    #planting_date
    #propagation

    # abcd: SpecimenUnit
    accession_number = Column(String(500), index=True) # TODO: catalog_number
    #accession_uri = Column(String(500)) ark?
    #accession_catalogue = Column(String(500))
    # accession_date
    duplication_number = Column(String(500)) # extend accession_number
    #abcd:preparations
    preparation_type = Column(String(500)) #specimens (S), tissues, DNA
    preparation_date = Column(Date)
    # 暫時不用
    preservation_text = Column(String(500)) # type: freezer, temperature, dateBegin...
    # abcd: Acquisition (use Transaction)
    acquisition_type = Column(String(500)) # bequest, purchase, donation
    acquisition_date = Column(DateTime)
    acquired_from = Column(Integer, ForeignKey('person.id'), nullable=True)
    acquisition_source_text = Column(Text) # hast: provider
    #verified
    #reference

    pids = relationship('PersistentIdentifierUnit')
    #NomenclaturalTypeDesignation
    type_is_published = Column(Boolean, default=False)
    type_status = Column(String(50))
    typified_name = Column(String(500)) # The name based on the specimen.
    type_reference = Column(String(500)) # NomenclaturalReference: Published reference
    type_reference_link = Column(String(500))
    type_note = Column(String(500))

    # type_code = Column(String(100)) # CodeAssessment: ?
    type_identification_id = Column(Integer, ForeignKey('identification.id', ondelete='SET NULL'), nullable=True)

    #specimen_marks = relationship('SpecimenMark')
    collection = relationship('Collection')
    record = relationship('Record', overlaps='units') # TODO warning
    assertions = relationship('UnitAssertion')
    transactions = relationship('TransactionUnit')
    annotations = relationship('UnitAnnotation')
    propagations = relationship('Propagation')
    # abcd: Disposition (in collection/missing...)
    disposition = Column(String(500)) # DwC curatorial extension r. 14: 'The current disposition of the catalogued item. Examples: "in collection", "missing", "source gone", "voucher elsewhere", "duplicates elsewhere","consumed".' 保存狀況
    # location = Column(String(500)) # ABCD:locationInGarden, 用annotation處理

    # observation
    source_data = Column(JSONB)
    information_withheld = Column(Text)
    #verbatim_label = Column(Text) # DwC: MaterialEntity, https://dwc.tdwg.org/examples/verbatimLabel
    # verbatim_label_remarks = Column(Text)
    "human transcription" or "unadulterated OCR output"
    # => move to UnitVerbatim
    pub_status = Column(String(10), default='P') # 'H'

    legal_statement_id = Column(ForeignKey('legal_statement.id', ondelete='SET NULL'))
    legal_statement = relationship('LegalStatement', foreign_keys=[legal_statement_id])
    acquired_from_person = relationship('Person', foreign_keys=[acquired_from])
    notes = Column(Text)

    cover_image_id = Column(ForeignKey('multimedia_object.id', ondelete='SET NULL'), nullable=True)
    cover_image = relationship('MultimediaObject', uselist=False, foreign_keys=[cover_image_id])
    multimedia_objects = relationship('MultimediaObject', back_populates='unit', primaryjoin='Unit.id==MultimediaObject.unit_id')
    tracking_tags = relationship('TrackingTag')

    parent_id = Column(Integer, ForeignKey('unit.id', ondelete='SET NULL'))
    parent = relationship('Unit', remote_side=[id], back_populates='children')
    children = relationship('Unit', back_populates='parent')

    tracking_tags = relationship('TrackingTag', back_populates='unit')

    @property
    def catalog_number(self):
        return self.accession_number

    @property
    def ark(self):
        for x in self.pids:
            if x.pid_type == 'ark':
                return x.key
        return None

    @staticmethod
    def get_public_stmt(collection_ids):
        stmt = select(Unit).where(
            Unit.pub_status=='P',
            Unit.accession_number != '',
            Unit.collection_id.in_(collection_ids)
        )
        return stmt

    def display_kind_of_unit(self):
        if self.kind_of_unit:
            return self.KIND_OF_UNIT_MAP.get(self.kind_of_unit, 'error')
        return ''

    @property
    def key(self):
        if self.accession_number and self.collection_id:
            #return f'{self.collection.organization.code}:{self.collection.name}:{self.accession_number}'
            return f'{self.collection.organization.code}:{self.accession_number}'
        return ''

    def get_link(self):
        # Settings-based URL template -> /specimens/{record_key}
        site = self.record.collection.site
        url_template = site.get_settings('frontend.specimens.url') if site else None

        if url_template:
            org_code = ''
            if self.collection and self.collection.organization:
                org_code = self.collection.organization.code or ''

            record_key = url_template.format(
                org_code=org_code,
                accession_number=self.accession_number or '',
                unit_id=self.id,
                ark='',
            )
            return url_for('frontpage.specimen_detail', record_key=record_key)

        # ARK guid -> /guid/{ark_id}
        if self.guid and 'ark:/' in self.guid:
            ark_id = f'ark:/{self.guid.split("ark:/")[1]}'
            return url_for('frontpage.guid_detail', record_key=ark_id)

        # Fallback: no settings template
        if self.accession_number:
            record_key = f'{self.record.collection.name.upper()}:{self.accession_number}'
            return url_for('frontpage.specimen_detail', record_key=record_key)

        return url_for('frontpage.record_detail', record_id=self.record_id)

    def get_specimen_url_deprecated(self, namespace=''):
        '''
        [guid]
        n2t.net/ark:/18474/b2abcd1234
        [global.ark]
        pid.biodiv.tw/ark:/18474/b2abcd1234
        [local.ark]
        hast.biodiv.tw/ark:/18474/b2abcd1234
        [local.record_key]?
        hast.biodiv.tw/specimens/HAST:1234
        [local.id]
        hast.biodiv.tw/specimens/<id>
        '''
        #if x := self.key:
        #    return url_for('frontend.specimen_detail', record_key=x, lang_code=g.lang_code)
        #return ''

        ## TODO, need rethink, seperate guid, only keep identifier?
        if namespace == '':
            if self.guid:
                return self.guid.replace('n2t.net', self.record.collection.organization.ark_nma)
        elif namespace == 'local.ark':
            if self.guid:
                return self.guid.replace('https://n2t.net/', '/specimens/')

        return self.guid

    # unit.to_dict
    def to_dict(self):
        data = {
            'id': self.id,
            'key': self.key,
            'collection_id': self.collection_id,
            'accession_number': self.accession_number or '',
            'duplication_number': self.duplication_number or '',
            #'collection_id': self.collection_id,
            'kind_of_unit': self.kind_of_unit or '',
            'preparation_type': self.preparation_type or '',
            'preparation_date': self.preparation_date.strftime('%Y-%m-%d') if self.preparation_date else '',
            'acquisition_type': self.acquisition_type,
            'acquisition_date': self.acquisition_date.strftime('%Y-%m-%d') if self.acquisition_date else '',
            'acquired_from': self.acquired_from,
            'acquisition_source_text': self.acquisition_source_text,
            'type_is_published': self.type_is_published,
            'type_status': self.type_status,
            'typified_name': self.typified_name,
            'type_reference': self.type_reference,
            'type_reference_link': self.type_reference_link,
            'type_note': self.type_note,
            'assertions': {}, #self.get_assertions(),
            'annotations': {}, #self.get_annotations(),
            'image_url': self.get_cover_image(),
            'transactions': [x.transaction.to_dict() for x in self.transactions],
            'guid': self.guid,
            'pub_status': self.pub_status,
            'multimedia_objects': [],
            'basis_of_record': self.basis_of_record or '',
            'notes': self.notes or '',
            'tracking_tags': {},
            'parent_id': self.parent_id,
            #'dataset': self.dataset.to_dict(), # too man
        }

        for a in self.assertions:
            data['assertions'][a.assertion_type.name] = {
                'id': a.id,
                'value': a.value,
                'option_id': a.option_id,
            }

        for a in self.annotations:
            data['annotations'][a.annotation_type.name] = {
                'id': a.id,
                'value': a.value,
            }

        for mo in self.multimedia_objects:
            data['multimedia_objects'].append(mo.to_dict())

        if self.cover_image_id:
            data['cover_image'] = self.cover_image.to_dict()

        for tag in self.tracking_tags:
            data['tracking_tags'][tag.tag_type] = {
                'label': tag.label,
                'value': tag.value,
                'id': tag.id,
            }
        return data


    def get_display(self, mode=''):
        #mod_time = ''
        image_url = ''
        if self.cover_image_id:
            image_url = self.get_cover_image('s')

        if mode == '':
            catalog_number = self.catalog_number
        elif mode == 'raw':
            catalog_number = self.record.source_data.get('voucher_id')
            if unit_id := self.record.source_data.get('unit_id'):
                catalog_number = f'{catalog_number} ({unit_id})'
        return {
            'catalog_number': catalog_number,
            'item_key': f'u{self.id}',
            'collection_id': f'u{self.collection_id}',
            #'mod_time': mod_time,
            'image_url': image_url,
        }

    def get_parameters(self, parameter_list=[]):
        params = {f'{x.parameter.name}': x for x in self.measurement_or_facts}

        items = []
        if len(parameter_list) == 0:
            parameter_list = [x for x in params]
        for name in parameter_list:
            if p := params.get(name, ''):
                item = p.to_dict()
                item['name'] = name
                items.append(item)
        return items

    def get_assertion_type_list(self):
        at_list = AssertionType.query.filter(AssertionType.target=='unit').order_by('sort').all() # TODO collection
        return at_list

    def get_assertion(self, type_name='', part=''):
        if type_name:
            for x in self.assertions:
                if x.assertion_type.name == type_name:
                    return getattr(x, part) if part else x

        return ''

    def get_annotation(self, type_name='', part=''):
        if type_name:
            for x in self.annotations:
                if x.annotation_type.name == type_name:
                    return getattr(x, part) if part else x

    def get_cover_image(self, size=''):
        if self.cover_image_id:
            if size:
                # TODO, custom suffix pattern
                return self.cover_image.file_url.replace('-m.jpg', f'-{size}.jpg')
            return self.cover_image.file_url
        return ''


    def get_image__deprecated(self, thumbnail='s'):
        if self.collection_id == 1:
            #if self.multimedia_objects:
            #    accession_number_int = int(self.accession_number)
            #    id_ = f'{accession_number_int:06}'
            #    thumbnail = thumbnail.replace('_', '-')
            #    return f'https://pid.biodiv.tw/ark:/18474/v6cc0ts6j/S_{id_}{thumbnail}.jpg'
            try:
                #accession_number_int = int(self.accession_number)
                #instance_id = f'{accession_number_int:06}'
                #first_3 = instance_id[0:3]
                #image_url = f'https://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{instance_id}{thumbnail}.jpg'
                if self.accession_number:
                    return f'https://brmas-media.s3.ap-northeast-1.amazonaws.com/hast/specimen/S_{int(self.accession_number):06}-{thumbnail}.jpg'
                else:
                    return None
            except:
                pass
            # TODO, get first cover or other type
            #if media := self.multimedia_objects[0]:
            #    if media.file_url:
            #        return media.file_url
        return ''

    def get_annotation_map(self, type_name=''):
        result = {}
        for x in self.annotations:
            if type_name == '':
                result[x.annotation_type.name] = x.value
            else:
                result = x.value

        return result

    @staticmethod
    def get_editable_fields(field_types=['date', 'str', 'bool', 'int']):
        int_fields = [
            'parent_id',
        ]
        date_fields = [
            'preparation_date',
            'acquisition_date',
        ]
        str_fields = [
            'accession_number',
            'duplication_number',
            'kind_of_unit',
            'preparation_type',
            #'preservation_text',
            'disposition',
            'acquisition_type',
            'acquisition_source_text',
            'type_status',
            'typified_name',
            'type_reference',
            'type_reference_link',
            'type_note',
            'pub_status',
            'notes',
            'basis_of_record',
        ]
        bool_fields = [
            'type_is_published'
        ]

        fields = []
        for i in field_types:
            if i == 'date':
                fields += date_fields
            if i == 'str':
                fields += str_fields
            if i == 'bool':
                fields += bool_fields
            if i == 'int':
                fields += int_fields
        return fields

    def get_term_text(self, term):
        if record := self.record:
            if term == 'dwc:eventDate':
                if x := record.collect_date:
                    return x.strftime('%Y-%m-%d')
            elif term == 'dwc:verbatimEventDate':
                if x := record.verbatim_collect_date:
                    return x
            elif term == 'dwc:year':
                if record.collect_date:
                    return str(record.collect_date.year)
                elif record.collect_date_year:
                    return str(record.collect_date_year)
            elif term == 'dwc:month':
                if record.collect_date:
                    return str(record.collect_date.month)
                elif record.collect_date_month:
                    return str(record.collect_date_month)
            elif term == 'dwc:day':
                if record.collect_date:
                    return str(record.collect_date.day)
                elif record.collect_date_day:
                    return str(record.collect_date_day)
            elif term == 'dwc:recordedBy':
                if x := record.collector:
                    return x.display_name
            elif term == 'ndb:collect_date':
                if x := record.collect_date:
                    return x.strftime('%Y-%m-%d')
                elif record.collect_date_year:
                    parts = [str(record.collect_date_year)]
                    if record.collect_date_month:
                        parts.append(f'{record.collect_date_month:02d}')
                        if record.collect_date_day:
                            parts.append(f'{record.collect_date_day:02d}')
                    return '-'.join(parts)

        return ''

    def get_data(self):
        # Build catalog_number using frontend.specimens.url template (same logic as get_link)
        catalog_number = self.accession_number or ''
        site = self.record.collection.site if self.record and self.record.collection else None
        url_template = site.get_settings('frontend.specimens.url') if site else None
        if url_template:
            org_code = ''
            if self.collection and self.collection.organization:
                org_code = self.collection.organization.code or ''
            catalog_number = url_template.format(
                org_code=org_code,
                accession_number=self.accession_number or '',
                unit_id=self.id,
                ark='',
            )

        data = {
            'catalog_number': catalog_number,
            'catalog_number_verbose': catalog_number,
            'institution_code': self.record.collection.site.name.upper(),
            'link': self.get_link(),
            'guid': self.guid or '',
            'ark_id': '',
            'assertions': [],
            'annotations': [],
        }
        if guid := self.guid:
            ark_parts = guid.split('ark:/')
            data['ark_id'] = f'ark:/{ark_parts[1]}'

        if self.cover_image_id:
            image_url = self.get_cover_image()
            # TODO, custom size rules
            data.update({
                'image_url_s': image_url.replace('-m.jpg', '-s.jpg'),
                'image_url_m': image_url,
                'image_url_l': image_url.replace('-m.jpg', '-l.jpg'),
                'image_url_x': image_url.replace('-m.jpg', '-x.jpg'),
                'image_url_o': image_url.replace('-m.jpg', '-o.jpg')
            })

        assertions = []
        assertion_type_list = AssertionType.query.filter(AssertionType.target=='unit', AssertionType.collection_id==self.collection_id).order_by('sort').all()
        for i in assertion_type_list:
            val = ''
            if a := self.get_assertion(i.name):
                val = a.value
                if a.option_id:
                    opt = session.get(AssertionTypeOption, a.option_id)
                    val = f'{opt.value} ({opt.description})'

            assertions.append([i.label, val])

        data['assertions'] = assertions

        annotations = []
        annotation_type_list = AnnotationType.query.filter(AnnotationType.target=='unit', AnnotationType.collection_id==self.collection_id).order_by('sort').all()
        for i in annotation_type_list:
            val = ''
            if a := self.get_annotation(i.name):
                val = a.value
                # annotation has no option
                #if a.option_id:
                #    opt = session.get(AnnotationTypeOption, a.option_id)
                #    val = f'{opt.value} ({opt.description})'

            annotations.append([i.label, val])
        data['annotations'] = annotations

        # Multimedia objects
        images = []
        for mo in self.multimedia_objects:
            img = {
                'file_url': mo.file_url or '',
                'thumbnail_url': mo.thumbnail_url or mo.file_url or '',
                'creator': mo.creator_text or (mo.creator.display_name if mo.creator else ''),
                'date': mo.date_created.strftime('%Y-%m-%d') if mo.date_created else '',
                'note': mo.note or '',
                'title': mo.title or '',
            }
            # Generate size variants
            if mo.file_url:
                img['url_s'] = mo.file_url.replace('-m.jpg', '-s.jpg')
                img['url_m'] = mo.file_url
                img['url_l'] = mo.file_url.replace('-m.jpg', '-l.jpg')
                img['url_x'] = mo.file_url.replace('-m.jpg', '-x.jpg')
                img['url_o'] = mo.file_url.replace('-m.jpg', '-o.jpg')
            images.append(img)
        data['images'] = images

        # Unit details
        data['kind_of_unit'] = self.KIND_OF_UNIT_MAP.get(self.kind_of_unit, self.kind_of_unit) if self.kind_of_unit else ''

        # Preparation & Acquisition
        data['preparation_date'] = self.preparation_date.strftime('%Y-%m-%d') if self.preparation_date else ''
        data['acquisition_type'] = self.acquisition_type or ''
        data['acquisition_date'] = self.acquisition_date.strftime('%Y-%m-%d') if self.acquisition_date else ''
        data['acquired_from'] = self.acquired_from_person.display_name if self.acquired_from else ''
        data['acquisition_source_text'] = self.acquisition_source_text or ''
        data['preservation_text'] = self.preservation_text or ''

        # Type status
        data['type_status'] = self.type_status or ''
        data['typified_name'] = self.typified_name or ''
        data['type_reference'] = self.type_reference or ''
        data['type_reference_link'] = self.type_reference_link or ''
        data['type_note'] = self.type_note or ''

        # Legal
        data['legal_statement'] = self.legal_statement.license if self.legal_statement else ''

        return data

    def get_verbatim(self, user_id, source_type, section_type, field='text'):
        if uv_exist := UnitVerbatim.query.filter(
                UnitVerbatim.unit_id==self.id,
                UnitVerbatim.user_id==user_id,
                UnitVerbatim.source_type==source_type,
                UnitVerbatim.section_type==UnitVerbatim.section_type).first():
            if field:
                return getattr(uv_exist, field)
            else:
                return uv_exist

    def __str__(self):
        collector = ''
        record_number = ''
        taxon = '--'
        if self.record and self.record.collector:
            collector = self.record.collector.sorting_name

        if self.record:
            record_number = f'{collector} | {self.record.field_number}::{self.duplication_number}'
            taxon = self.record.proxy_taxon_scientific_name

        return f'<Unit #{self.id} {record_number} | {taxon}>'


class PersonGroup(Base, TimestampMixin):
    __tablename__ = 'person_group'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))

    people = relationship('Person', secondary=person_group_map, back_populates='groups')

    def __repr__(self):
        return '<PersonGroup(id="{}", name="{}")>'.format(self.id, self.name)


class Person(Base, TimestampMixin):
    '''
    full_name => original name
    '''
    __tablename__ = 'person'

    id = Column(Integer, primary_key=True)
    full_name = Column(String(500)) # abcd: FullName
    full_name_en = Column(String(500))
    atomized_name = Column(JSONB)
    # prefix: von | Lord
    # suffix: jun. | III
    # other_name (IPNI)
    given_name = Column(String(500))
    inherited_name = Column(String(500))
    given_name_en = Column(String(500))
    inherited_name_en = Column(String(500))
    preferred_name = Column(String(500))
    sorting_name = Column(String(500))
    abbreviated_name = Column(String(500))

    created_by = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    created_via = Column(String(500))
    #organization_name = Column(String(500))
    data = Column(JSONB) # org_abbr
    is_collector = Column(Boolean, default=False)
    is_identifier = Column(Boolean, default=False)
    is_agent = Column(Boolean, default=False)
    is_multi = Column(Boolean, default=False)
    source_data = Column(JSONB)
    remark = Column(String(500))
    #organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    #organization = Column(String(500))
    pids = relationship('PersistentIdentifierPerson')

    groups = relationship('PersonGroup', secondary=person_group_map, back_populates='people')

    def __repr__(self):
        return '<Person(id="{}", display_name="{}")>'.format(self.id, self.display_name)


    def get_display_name(self, style=''):
        if style == 'print':
            person = self.full_name_en
            if full_name := self.full_name:
                person = f'{person} ({full_name})'

        else:
            person = self.display_name

        return person

    @property
    def display_name(self):
        name_list = []
        if self.full_name and self.full_name_en:

            if self.given_name_en and self.inherited_name_en:
                return f'{self.inherited_name_en}, {self.given_name_en} ({self.full_name})'
            else:
                return f'{self.full_name_en} ({self.full_name})'
        else:
            if x := self.full_name:
                return x

            elif x := self.full_name_en:
                return x
        return ''

    def to_dict(self, with_meta=False):
        data = {
            'id': self.id,
            'display_name': self.display_name,
            'full_name': self.full_name,
            'given_name': self.given_name,
            'inherited_name': self.inherited_name,
            'given_name_en': self.given_name_en,
            'inherited_name_en': self.inherited_name_en,
            'preferred_name': self.preferred_name,
            'full_name_en': self.full_name_en,
            'abbreviated_name': self.abbreviated_name,
            'sorting_name': self.sorting_name,
            'is_collector': self.is_collector,
            'is_identifier': self.is_identifier,
        }

        if with_meta is True:
            #set_locale()
            data['meta'] = {
                'term': 'collector', # TODO
                'label': gettext('採集者'),
                'display': self.display_name,
            }
        return data


class Transaction(Base, TimestampMixin):
    __tablename__ = 'transaction'

    EXCHANGE_TYPE_CHOICES = (
        ('0', '無'),
        ('1', 'Exchange to (交換出去)'),
        ('2', 'Exchange from (交換來的)'),
        ('3', 'From (贈送來的)'),
        ('4' ,'To (贈送給)'),
    )

    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL')) # TODO: remove
    transaction_type = Column(String(500)) #  (DiversityWorkbench) e.g. gift in or out, exchange in or out, purchase in or out
    transaction_from = Column(String(500))
    transaction_to = Column(String(500))
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    #organization_text = Column(String(500))
    date = Column(Date) # (DiversityWorkbench: BeginDate)
    date_text = Column(String(500))
    agreed_end_date = Column(Date) # borrow
    actual_end_date = Column(Date) # borrow prolongation, or gifted from actual get specimen

    organization = relationship('Organization')

    def get_type_display(self):
        if key := self.transaction_type:
            if item := find_options(key, self.EXCHANGE_TYPE_CHOICES):
                return item[0][1]
        return ''

    def to_dict(self):
        display_type = list(filter(lambda x: str(self.transaction_type) == x[0], self.EXCHANGE_TYPE_CHOICES))
        date = ''
        if self.date:
            date = self.date.strftime('%Y-%m-%d')
        elif self.date_text:
            date = self.date_text

        return {
            'id': self.id,
            'title': self.title or '',
            'transaction_type': self.transaction_type,
            'display_transaction_type': display_type[0][1] if len(display_type) else '',
            'organization_id': self.organization_id,
            'date': date,
        }


class TransactionUnit(Base, TimestampMixin):
    __tablename__ = 'transaction_unit'
    id = Column(Integer, primary_key=True)
    transaction_id = Column(ForeignKey('transaction.id', ondelete='SET NULL'))
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL'))
    data = Column(JSONB)

    transaction = relationship('Transaction')

class Project(Base, TimestampMixin):
    __tablename__ = 'project'

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    # organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    collection_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'), nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
        }


class RecordGroup(Base, TimestampMixin):
    __tablename__ = 'record_group'

    GROUP_CATEGORY_OPTIONS = (
        ('project', '計畫'),
        ('exhibition', '展覽'),
        ('sampling', '採樣紀錄'),
        ('literature', '文獻'),
        ('batch-import', '批次匯入'),
        ('issue', '有問題'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    name_en = Column(String(500))
    category = Column(String(500))
    collection_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'), nullable=True)
    #is_admin = Column(Boolean, default=False)

    records = relationship('Record', secondary='record_group_map', back_populates='record_groups', overlaps='record_group_maps')
    record_maps = relationship('RecordGroupMap', back_populates='record_group', overlaps='record_groups,records')
    collection = relationship('Collection')

class RecordGroupMap(Base, TimestampMixin):
    __tablename__ = 'record_group_map'
    record_id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    group_id = Column(Integer, ForeignKey('record_group.id'), primary_key=True)

    record = relationship('Record', back_populates='record_group_maps', overlaps='record_groups,records')
    record_group = relationship('RecordGroup', back_populates='record_maps', overlaps='record_groups,records')


class CollectionTaxonMap(Base):
    """Maps a collection to a taxon tree branch.

    Each row means this collection uses a specific branch (rooted at taxon_id)
    from a taxon tree. A collection can have multiple branches, e.g. both
    Plantae and Fungi from the same TaiCOL backbone.
    """
    __tablename__ = 'collection_taxon_map'

    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey('collection.id', ondelete='CASCADE'), nullable=False, index=True)
    taxon_tree_id = Column(Integer, ForeignKey('taxon_tree.id', ondelete='CASCADE'), nullable=False)
    taxon_id = Column(Integer, ForeignKey('taxon.id', ondelete='CASCADE'), nullable=True)

    collection = relationship('Collection', back_populates='taxon_maps')
    taxon_tree = relationship('TaxonTree')
    taxon = relationship('Taxon')


class VolunteerTask(Base, TimestampMixin):
    """
    Volunteer task assignment for specimen transcription.
    Links volunteers (users) to units (specimens) for data entry.
    """
    __tablename__ = 'volunteer_task'

    STATUS_OPTIONS = (
        ('assigned', 'Assigned'),
        ('completed', 'Completed'),
    )

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('unit.id', ondelete='CASCADE'), nullable=False, unique=True, index=True)
    volunteer_id = Column(Integer, ForeignKey('user.id', ondelete='CASCADE'), nullable=False, index=True)
    assigned_by_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    status = Column(String(20), nullable=False, default='assigned', index=True)
    assigned_date = Column(DateTime, nullable=False, default=get_time)
    completed_date = Column(DateTime, nullable=True)

    # Relationships
    unit = relationship('Unit', backref='volunteer_task')
    volunteer = relationship('User', foreign_keys=[volunteer_id], backref='assigned_tasks')
    assigned_by = relationship('User', foreign_keys=[assigned_by_id])

    def to_dict(self):
        """Serialize task for API responses"""
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'volunteer_id': self.volunteer_id,
            'volunteer_name': self.volunteer.username if self.volunteer else None,
            'assigned_by_id': self.assigned_by_id,
            'assigned_by_name': self.assigned_by.username if self.assigned_by else None,
            'status': self.status,
            'assigned_date': self.assigned_date.isoformat() if self.assigned_date else None,
            'completed_date': self.completed_date.isoformat() if self.completed_date else None,
            'catalog_number': self.unit.accession_number if self.unit else None,
        }

    def mark_completed(self):
        """Mark task as completed with timestamp"""
        self.status = 'completed'
        self.completed_date = get_time()

    @staticmethod
    def get_volunteer_progress(volunteer_id):
        """Get completion statistics for a volunteer"""
        from sqlalchemy import func
        total = session.query(func.count(VolunteerTask.id))\
            .filter(VolunteerTask.volunteer_id == volunteer_id)\
            .scalar()
        completed = session.query(func.count(VolunteerTask.id))\
            .filter(VolunteerTask.volunteer_id == volunteer_id,
                   VolunteerTask.status == 'completed')\
            .scalar()
        return {
            'total': total or 0,
            'completed': completed or 0,
            'remaining': (total or 0) - (completed or 0),
            'percentage': round((completed or 0) / (total or 1) * 100, 1) if total and total > 0 else 0
        }


class LegalStatement(Base):
    __tablename__ = 'legal_statement'

    id = Column(Integer, primary_key=True)
    license = Column(String(500))


class MultimediaObjectContext(Base):
    __tablename__ = 'multimedia_object_context'

    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    description = Column(Text)


class MultimediaObjectType(Base):
    __tablename__ = 'multimedia_object_type'

    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    description = Column(Text)


class MultimediaObjectPhysicalFormat(Base):
    __tablename__ = 'multimedia_object_physical_format'

    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    description = Column(Text)


class MultimediaObject(Base, TimestampMixin):
    __tablename__ = 'multimedia_object'

    id = Column(Integer, primary_key=True)
    #collection_id = Column(ForeignKey('collection.id', ondelete='SET NULL'))
    guid = Column(String(500))
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL'))
    unit = relationship('Unit', back_populates='multimedia_objects', foreign_keys=[unit_id])
    record_id = Column(ForeignKey('record.id', ondelete='SET NULL'))
    record = relationship('Record', back_populates='record_multimedia_objects')
    #multimedia_type = Column(String(500), default='StillImage') # http://rs.gbif.org/vocabulary/dcterms/type.xml
    type_id = Column(ForeignKey('multimedia_object_type.id', ondelete='SET NULL'))
    multimedia_type = relationship('MultimediaObjectType')
    physical_format_id = Column(ForeignKey('multimedia_object_physical_format.id', ondelete='SET NULL')) #dwc ext: simple media->source
    physical_format = relationship('MultimediaObjectPhysicalFormat')
    #physical_format = Column(String(500), default='photograph')

    title = Column(String(500))
    #source = Column(String(500))
    creator_text = Column(String(500))
    creator_id = Column(Integer, ForeignKey('person.id')) # who create the multimedia object
    creator = relationship('Person', foreign_keys=[creator_id])
    provider_text = Column(String(500))
    provider_id = Column(Integer, ForeignKey('person.id'))
    provider = relationship('Person', foreign_keys=[provider_id])
    file_url = Column(String(500)) # dwc-ext: simple multimedia: identifier
    thumbnail_url = Column(String(500))
    # product_url
    note = Column(Text)
    source_data = Column(JSONB) # originalFilename, exifData
    date_created = Column(DateTime) # created (photo taken date, created is for data)
    #modified = Column(DateTime) # updated (image modified, not multimedia record self?)
    reference = Column(String(500))
    #context_text = Column(String(500)) # abcd: The context of the object in relation to the specimen or observation. E.g. image of entire specimen, sound recording the observation is based on, image of original valid publication, etc.
    context_id = Column(ForeignKey('multimedia_object_context.id', ondelete='SET NULL')) # annotation?
    context = relationship('MultimediaObjectContext')
    #category_id = Column(ForeignKey('multimedia_object_category.id', ondelete='SET NULL'))
    #category = relationship('MultimediaObjectCategory')

    legal_statement_id = Column(ForeignKey('legal_statement.id', ondelete='SET NULL'))
    rights_holder = Column(String(500))

    annotations = relationship('MultimediaObjectAnnotation')

    def to_dict(self):
        return {
            'id': self.id,
            'file_url': self.file_url,
            'source_data': self.source_data,
        }

class TrackingTag(Base):
    __tablename__ = 'tracking_tag'

    id = Column(Integer, primary_key=True)
    collection_id = Column(Integer, ForeignKey('collection.id'))
    unit_id = Column(Integer, ForeignKey('unit.id', ondelete='SET NULL'), nullable=True)
    tag_type = Column(String(50)) # qrcode, rfid
    label = Column(String(500))
    value = Column(String(500))

    unit = relationship('Unit', back_populates='tracking_tags')

    def to_dict(self):
        return {
            'tag_type': self.tag_type,
            'label': self.label,
            'value': self.value,
        }

class RecordPerson(Base):
    # other collector
    __tablename__ = 'record_person'

    id = Column(Integer, primary_key=True)
    record_id = Column(ForeignKey('record.id', ondelete='SET NULL'))
    person_id = Column(ForeignKey('person.id', ondelete='SET NULL'))
    #role = Column(String(50))  # column exists in table but intentionally unused
    sequence = Column(Integer)
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)

    record = relationship('Record', back_populates='companions')
    person = relationship('Person')
    organization = relationship('Organization')

    def to_dict(self):
        return {
            'id': self.id,
            'person': self.person.to_dict() if self.person else None,
            'sequence': self.sequence,
        }


class AssertionMixin:

    @declared_attr
    def assertion_type_id(self):
        return Column(Integer, ForeignKey('assertion_type.id'))

    @declared_attr
    def assertion_type(self):
        return relationship('AssertionType')

    @declared_attr
    def datetime(self):
        return Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    value = Column(String(500))
    option_id = Column(Integer, ForeignKey('assertion_type_option.id'))


class AssertionType(Base, TimestampMixin):
    __tablename__ = 'assertion_type'

    INPUT_TYPE_OPTIONS = (
        ('input', '單行文字'),
        ('text', '多行文字'),
        ('select', '下拉選單'),
        ('free', '自由下拉'),
        ('checkbox', '勾選'),
    )
    TARGET_OPTIONS = (
        ('record', 'record'),
        ('unit', 'unit'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    label = Column(String(500))
    target = Column(String(50)) # assertionTargetType
    sort = Column(Integer)
    data = Column(JSONB) # group
    input_type = Column(String(50))
    collection_id = Column(Integer, ForeignKey('collection.id', ondelete='SET NULL'), nullable=True)
    collection = relationship('Collection')
    options = relationship('AssertionTypeOption')

    def get_input_type_display(self):
        if self.input_type:
            if item := find_options(self.input_type, self.INPUT_TYPE_OPTIONS):
                return item[0][1]
        return ''

    def get_target_display(self):
        if self.target:
            if item := find_options(self.target, self.TARGET_OPTIONS):
                return item[0][1]
        return ''

    def to_dict(self):
        return {
            'id': self.id,
            'label': self.label,
            'name': self.name,
            'sort': self.sort,
            'target': self.target,
            'input_type': self.input_type,
            'collection_id': self.collection_id,
        }

class AssertionTypeOption(Base, TimestampMixin):
    __tablename__ = 'assertion_type_option'

    id = Column(Integer, primary_key=True)
    value = Column(String(500))
    description = Column(String(500))
    data = Column(JSONB) # source_data
    assertion_type_id = Column(Integer, ForeignKey('assertion_type.id', ondelete='SET NULL'), nullable=True)


    @property
    def display_text(self):
        text = self.value
        if x := self.description:
            text = f'{text} ({x})'
        return text

    def to_dict(self):
        return {
            'id': self.id,
            'value': self.value,
            'data': self.data,
            'type_id': self.assertion_type_id,
            'display_name': f'{self.value} ({self.description})',
        }


class RecordAssertion(Base, AssertionMixin):
    __tablename__ = 'record_assertion'

    id = Column(Integer, primary_key=True)
    record_id = Column(ForeignKey('record.id', ondelete='SET NULL'))


class UnitAssertion(Base, AssertionMixin):
    __tablename__ = 'unit_assertion'

    id = Column(Integer, primary_key=True)
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL'))

class FieldNumber(Base, TimestampMixin):
    __tablename__ = 'other_field_number'

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey('record.id', ondelete='SET NULL'), nullable=True)
    value = Column(String(500)) # dwc: recordNumber
    #record_number2 = Column(String(500)) # for HAST dupNo.
    collector_id = Column(Integer, ForeignKey('person.id'))
    collector = relationship('Person')
    collector_name = Column(String(500), nullable=True) # abbr. collector's name


class PersistentIdentifierMixin:

    key = Column(String(500))
    pid_type = Column(String(500)) # url, url, doi, ark, lsid, barcode


class PersistentIdentifierUnit(Base, PersistentIdentifierMixin):
    __tablename__ = 'pid_unit'

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('unit.id', ondelete='SET NULL'), nullable=True)
    unit = relationship('Unit', viewonly=True)


class PersistentIdentifierPerson(Base, PersistentIdentifierMixin):
    __tablename__ = 'pid_person'

    id = Column(Integer, primary_key=True)
    person_id = Column(Integer, ForeignKey('person.id', ondelete='SET NULL'), nullable=True)

class PersistentIdentifierOrganization(Base, PersistentIdentifierMixin):
    __tablename__ = 'pid_organization'

    id = Column(Integer, primary_key=True)
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)

class PersistentIdentifierNamedArea(Base, PersistentIdentifierMixin):
    __tablename__ = 'pid_named_area'

    id = Column(Integer, primary_key=True)
    named_area_id = Column(Integer, ForeignKey('named_area.id', ondelete='SET NULL'), nullable=True)


class AnnotationMixin:

    @declared_attr
    def annotation_type_id(self):
        return Column(Integer, ForeignKey('annotation_type.id'))

    @declared_attr
    def annotation_type(self):
        return relationship('AnnotationType')

    @declared_attr
    def datetime(self):
        return Column(DateTime, default=datetime.now(), onupdate=datetime.now())

    value = Column(String(500))


class AnnotationType(Base):
    __tablename__ = 'annotation_type'

    INPUT_TYPE_OPTIONS = (
        ('input', '單行文字'),
        ('text', '多行文字'),
        ('select', '下拉選單'),
        ('checkbox', '勾選'),
    )

    TARGET_OPTIONS = (
        ('record', 'record'),
        ('unit', 'unit'),
        ('multimedia_object', 'Multimedia Object'),
    )

    id = Column(Integer, primary_key=True)
    name = Column(String(500))
    label = Column(String(500))
    target = Column(String(50))
    sort = Column(Integer)
    data = Column(JSONB)
    input_type = Column(String(50))
    collection_id = Column(Integer, ForeignKey('collection.id'))
    collection = relationship('Collection')

    def get_input_type_display(self):
        if self.input_type:
            if item := find_options(self.input_type, self.INPUT_TYPE_OPTIONS):
                return item[0][1]
        return ''

    def get_target_display(self):
        if self.target:
            if item := find_options(self.target, self.TARGET_OPTIONS):
                return item[0][1]
        return ''


class RecordAnnotation(Base, AnnotationMixin):
    __tablename__ = 'record_annotation'

    id = Column(Integer, primary_key=True)
    record_id = Column(Integer, ForeignKey('record.id'))

class UnitAnnotation(Base, AnnotationMixin):
    __tablename__ = 'unit_annotation'

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('unit.id'))


class UnitNote(Base, TimestampMixin):
    """
    User notes attached to units.
    Allows multiple users to add personal notes, observations, or corrections to units.
    """
    __tablename__ = 'unit_note'

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('unit.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)
    note = Column(Text, nullable=False)
    note_type = Column(String(50), default='general')  # general, correction, observation, todo, etc.
    is_public = Column(Boolean, default=False)  # Whether note is visible to other users
    resolved = Column(Boolean, default=False)  # For tracking if issue/todo is resolved

    # Relationships
    unit = relationship('Unit', backref=backref('user_notes', cascade='all, delete-orphan'))
    user = relationship('User', backref='unit_notes')

    def __repr__(self):
        return f'<UnitNote unit_id={self.unit_id} user_id={self.user_id}>'

    def to_dict(self):
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'note': self.note,
            'note_type': self.note_type,
            'is_public': self.is_public,
            'resolved': self.resolved,
            'created': self.created.isoformat() if self.created else None,
            'updated': self.updated.isoformat() if self.updated else None,
        }


class UnitVerbatim(Base, TimestampMixin):
    """
    Multiple transcription versions of specimen labels from various sources.

    Stores label text transcribed by humans, OCR systems, or AI models.
    Supports full label or sectional transcription (collector, locality, date, etc.).

    Design: No primary selection - all transcriptions are stored equally.
    Unit.verbatim_label field will be removed in favor of this versioned approach.
    """
    __tablename__ = 'unit_verbatim'

    # Source type constants
    SOURCE_HUMAN = 'human'
    SOURCE_OCR = 'ocr'
    SOURCE_AI = 'ai'
    SOURCE_IMPORTED = 'imported'
    SOURCE_MIGRATED = 'migrated'

    SOURCE_TYPES = [SOURCE_HUMAN, SOURCE_OCR, SOURCE_AI, SOURCE_IMPORTED, SOURCE_MIGRATED]

    # Section type constants
    SECTION_FULL = 'full'
    SECTION_COLLECTOR = 'collector'
    SECTION_LOCALITY = 'locality'
    SECTION_DATE = 'date'
    SECTION_HABITAT = 'habitat'
    SECTION_IDENTIFICATION = 'identification'
    SECTION_ELEVATION = 'elevation'
    SECTION_COORDINATES = 'coordinates'
    SECTION_OTHER = 'other'

    SECTION_TYPES = [
        SECTION_FULL,
        SECTION_COLLECTOR,
        SECTION_LOCALITY,
        SECTION_DATE,
        SECTION_HABITAT,
        SECTION_IDENTIFICATION,
        SECTION_ELEVATION,
        SECTION_COORDINATES,
        SECTION_OTHER,
    ]

    SECTION_TYPES_DISPLAY = {
        'full': {'en': 'Full Label', 'zh': '完整標籤'},
        'collector': {'en': 'Collector', 'zh': '採集者'},
        'locality': {'en': 'Locality', 'zh': '地點'},
        'date': {'en': 'Date', 'zh': '日期'},
        'habitat': {'en': 'Habitat', 'zh': '棲地'},
        'identification': {'en': 'Identification', 'zh': '鑑定'},
        'elevation': {'en': 'Elevation', 'zh': '海拔'},
        'coordinates': {'en': 'Coordinates', 'zh': '座標'},
        'other': {'en': 'Other', 'zh': '其他'},
    }

    # Columns
    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('unit.id', ondelete='CASCADE'), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True, index=True)

    text = Column(Text, nullable=False)
    section_type = Column(String(50), nullable=False, default=SECTION_FULL, index=True)
    source_type = Column(String(20), nullable=False, index=True)

    # Flexible metadata storage
    # For OCR: {provider: 'azure', confidence: 0.95, bounding_boxes: [...], language: 'zh-TW'}
    # For AI: {model: 'gpt-4-vision', prompt: '...', temperature: 0.3, cost_usd: 0.05}
    # For human: {transcription_time_seconds: 120, device: 'mobile', corrections: 3}
    # For imported: {import_batch_id: 'batch_2025_01', source_file: 'legacy.csv'}
    source_data = Column(JSONB)

    # Relationships
    unit = relationship('Unit', backref=backref('verbatim_transcriptions',
                                                cascade='all, delete-orphan',
                                                order_by='desc(UnitVerbatim.created)'))
    user = relationship('User', backref='verbatim_transcriptions')

    def __repr__(self):
        return f'<UnitVerbatim id={self.id} unit_id={self.unit_id} source={self.source_type} section={self.section_type}>'

    def to_dict(self):
        """Serialize to dictionary for API responses."""
        return {
            'id': self.id,
            'unit_id': self.unit_id,
            'user_id': self.user_id,
            'username': self.user.username if self.user else None,
            'text': self.text,
            'section_type': self.section_type,
            'section_label': self.SECTION_TYPES_DISPLAY.get(self.section_type, {}).get('zh', self.section_type),
            'source_type': self.source_type,
            'source_data': self.source_data,
            'created': self.created.isoformat() if self.created else None,
            'updated': self.updated.isoformat() if self.updated else None,
        }

    @classmethod
    def create_transcription(cls, unit_id, text, source_type, user_id=None,
                           section_type=None, source_data=None):
        """
        Factory method to create a new transcription.

        Args:
            unit_id: ID of the unit
            text: Transcribed text
            source_type: One of SOURCE_TYPES ('human', 'ocr', 'ai', 'imported', 'migrated')
            user_id: User who created (optional for automated sources)
            section_type: Which part of label (default: SECTION_FULL)
            source_data: Metadata dict (optional)

        Returns:
            UnitVerbatim instance

        Raises:
            ValueError: If invalid source_type or section_type
        """
        from app.database import session

        if source_type not in cls.SOURCE_TYPES:
            raise ValueError(f'Invalid source_type: {source_type}. Must be one of {cls.SOURCE_TYPES}')

        section = section_type or cls.SECTION_FULL
        if section not in cls.SECTION_TYPES:
            raise ValueError(f'Invalid section_type: {section}. Must be one of {cls.SECTION_TYPES}')

        transcription = cls(
            unit_id=unit_id,
            user_id=user_id,
            text=text,
            source_type=source_type,
            section_type=section,
            source_data=source_data,
        )

        session.add(transcription)
        session.flush()  # Get ID

        return transcription


class MultimediaObjectAnnotation(Base, AnnotationMixin):
    __tablename__ = 'multimedia_object_annotation'

    id = Column(Integer, primary_key=True)
    multimedia_object_id = Column(Integer, ForeignKey('multimedia_object.id'))

# DEPRECATED?
class Annotation(Base, TimestampMixin):
    __tablename__ = 'annotation'

    id = Column(Integer, primary_key=True)
    type_id = Column(Integer, ForeignKey('annotation_type.id'))
    annotation_type = relationship('AnnotationType')
    unit_id = Column(Integer, ForeignKey('unit.id'))
    value = Column(String(500))
    # data = Column(JSONB) # source_data

    annotation_type = relationship('AnnotationType')
