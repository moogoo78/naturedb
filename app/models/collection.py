from flask import (
    g,
    url_for,
    request,
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

collection_person_map = Table(
    'collection_person_map',
    Base.metadata,
    Column('collection_id', ForeignKey('collection.id'), primary_key=True),
    Column('person_id', ForeignKey('person.id'), primary_key=True)
)

def find_options(key, options):
    if option := list(filter(lambda x: (x[0] == key), options)):
        return option
    return None


class Collection(Base, TimestampMixin):
    __tablename__ = 'collection'

    id = Column(Integer, primary_key=True)
    name = Column(String(500), unique=True)
    label = Column(String(500))
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    sort = Column(Integer, default=0)

    people = relationship('Person', secondary=collection_person_map, back_populates='collections')
    area_classes = relationship('AreaClass')
    organization = relationship('Organization', back_populates='collections')


#record_named_area_map = Table(
class RecordNamedAreaMap(Base):
    '''
    via:
    - A: convert from legacy system (area_class_id from 1 to 4) 
    '''
    __tablename__ = 'record_named_area_map'
    record_id = Column(Integer, ForeignKey('record.id'), primary_key=True)
    named_area_id = Column(Integer, ForeignKey('named_area.id'), primary_key=True)
    via = Column(String(10))
    record = relationship('Record', back_populates='named_area_maps')
    named_area = relationship('NamedArea', back_populates='record_maps')

class Record(Base, TimestampMixin):
    __tablename__ = 'record'

    id = Column(Integer, primary_key=True)
    collect_date = Column(DateTime) # abcd: Date
    collect_date_text = Column(String(500))
    # abcd: GatheringAgent, DiversityCollectinoModel: CollectionAgent
    collector_id = Column(Integer, ForeignKey('person.id'))
    verbatim_collector = Column(String(500)) # dwc:recordedBy
    field_number = Column(String(500), index=True)
    collector = relationship('Person')
    companions = relationship('RecordPerson') # companion
    companion_text = Column(String(500)) # unformatted value, # HAST:companions
    companion_text_en = Column(String(500))

    # Locality verbatim
    verbatim_locality = Column(String(1000))
    locality_text = Column(String(1000))
    locality_text_en = Column(String(1000))

    altitude = Column(Integer)
    altitude2 = Column(Integer)
    #depth

    # Coordinate
    latitude_decimal = Column(Numeric(precision=9, scale=6))
    longitude_decimal = Column(Numeric(precision=9, scale=6))
    verbatim_latitude = Column(String(50))
    verbatim_longitude = Column(String(50))

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

    #named_area_relations = relationship('CollectionNamedArea')
    #named_areas = relationship('NamedArea', secondary='record_named_area_map', back_populates='record')
    #named_areas = relationship('Record', secondary='record_named_area_map', back_populates='records')
    named_area_maps = relationship('RecordNamedAreaMap', back_populates='record')
    assertions = relationship('RecordAssertion')
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

    def get_named_area_list(self, list_name=''):

        # TODO: list_name from setting
        list_name_map = {
            'default': [7, 8, 9, 5, 6],
            'legacy': [1, 2, 3, 4, 5, 6],
        }

        if list_name == '':
            ret = {}
            for x in list_name_map:
                ret[x] = []
                for m in self.named_area_maps:
                    if m.named_area.area_class_id in list_name_map[x]:
                        ret[x].append(m.named_area)
                ret[x] = sorted(ret[x], key=lambda x: x.area_class.sort)
            return ret
        else:
            if list_name == 'default':
                # TODO taiwan use new, other country use old
                if country := RecordNamedAreaMap.query.filter(
                        RecordNamedAreaMap.record_id==self.id,
                        RecordNamedAreaMap.named_area_id==1311).first():
                    pass
                else:
                    list_name = 'legacy'

            if area_class_ids := list_name_map.get(list_name):
                na_list = []
                for m in self.named_area_maps:
                    if m.named_area.area_class_id in area_class_ids:
                        na_list.append(m.named_area)
                return sorted(na_list, key=lambda x: x.area_class.sort)

    def get_assertion(self, type_name='', part=''):
        if type_name:
            for x in self.assertions:
                if x.assertion_type.name == type_name:
                    return getattr(x, part) if part else x

        return ''

    def get_named_area(self, area_class_name=''):
        if area_class_name:
            for na in self.named_areas:
                if na.area_class.name == area_class_name:
                    return na
        return ''

    @property
    def key(self):
        unit_keys = [x.key for x in self.units]
        if len(unit_keys):
            return ','.join(unit_keys)
        else:
            return '--'

    @property
    def latest_scientific_name_deprecated(self):
        latest_id = self.identifications.order_by(desc(Identification.verification_level)).first()
        if taxon := latest_id.taxon:
            return taxon.full_scientific_name
        return ''

    @property
    def last_identification(self):
        return self.identifications.order_by(desc(Identification.verification_level)).first()

    def to_dict2(self):

        data = {
            'id': self.id,
            'collect_date': self.collect_date.strftime('%Y-%m-%d') if self.collect_date else '',
            'collector_id': self.collector_id,
            'collector': self.collector.to_dict() if self.collector else '',
            'field_number': self.field_number,
            'last_taxon_text': self.last_taxon_text,
            'last_taxon_id': self.last_taxon_id,
            #'named_area_map': self.get_named_area_map(),
        }
        data['units'] = [x.to_dict() for x in self.units]
        return data

    def update_from_json(self, data):
        changes = {}
        collection_log = SAModelLog(self)
        for name, value in data.items():
            # print('--', name, value, flush=True)
            if name == 'biotopes':
                biotope_list = []
                changes['biotopes'] = {}
                for k, v in value.items():
                    # find origin
                    origin = ''
                    for x in self.biotope_measurement_or_facts:
                        if x.parameter.name == k:
                            origin = x.value
                    changes['biotopes'][k] = f'{origin}=>{v}'
                    biotope = MeasurementOrFact(collection_id=self.id, value=v)
                    if p := MeasurementOrFactParameter.query.filter(MeasurementOrFactParameter.name==k).first():
                        biotope.parameter_id = p.id
                    #if o := MeasurementOrFactParameterOption.query.filter(MeasurementOrFactParameter.name==v).first():
                    # 不管 option 了
                    biotope_list.append(biotope)

                self.biotope_measurement_or_facts = biotope_list

            elif name == 'identifications':
                changes['identifications'] = []
                # 全部檢查 (dirtyFields 看不出是那一個 index 改的?)
                for id_ in value:
                    id_obj = None
                    if iid := id_.get('id'):
                        id_obj = session.get(Identification, iid)
                    else:
                        id_obj = Identification(collection_id=self.id)
                        session.add(id_obj)
                        session.commit()

                    id_log = SAModelLog(id_obj)

                    id_obj.date = id_['date'] if id_.get('date') else None
                    id_obj.date_text = id_.get('date_text', '')
                    id_obj.sequence = id_.get('sequence', '')
                    if x := id_.get('taxon'):
                        id_obj.taxon_id = x['id']
                    if x := id_.get('identifier'):
                        id_obj.identifier_id = x['id']

                    changes['identifications'].append(id_log.check())

            elif name == 'units':
                changes['units'] = []
                # 全部檢查 (dirtyFields 看不出是那一個 index 改的?)
                units = []
                for unit in value:
                    if unit_id := unit.get('id'):
                        unit_obj = session.get(Unit, unit_id)
                    else:
                        # TODO: dataset hard-code to HAST
                        unit_obj = Unit(collection_id=self.id, dataset_id=1)
                        session.add(unit_obj)
                        session.commit()

                    unit_log = SAModelLog(unit_obj)
                    unit_obj.accession_number = unit.get('accession_number')
                    unit_obj.preparation_date = unit['preparation_date'] if unit.get('preparation_date') else None

                    mof_list = []
                    # 用 SAModelLog 就可以了
                    for k, v in unit['measurement_or_facts'].items():
                        mof = MeasurementOrFact(unit_id=unit_obj.id, value=v)
                        #mof_log = SAModelChange(mof)
                        if p := MeasurementOrFactParameter.query.filter(MeasurementOrFactParameter.name==k).first():
                            mof.parameter_id = p.id
                        #if o := MeasurementOrFactParameterOption.query.filter(MeasurementOrFactParameter.name==v).first():
                        # 不管 option 了
                        mof_list.append(mof)

                    unit_obj.measurement_or_facts = mof_list
                    units.append(unit_obj)

                    unit_changes = unit_log.check()
                    #unit_changes['measurement_or_facts'] = 
                    changes['units'].append(unit_changes)

            else:
                if name in ['field_number', 'collect_date', 'altitude', 'altitude2', 'longitude_decimal', 'latitude_decimal', 'longitude_text', 'latitude_text', 'locality_text', 'companion_text', 'companion_text_en']:
                    origin = getattr(self, name, '')
                    changes[name] = f'{origin}=>{value}'
                    setattr(self, name, value)
                elif name == 'collector':
                    if value and value.get('id'):
                        self.collector_id = value['id']
                    else:
                        self.collector_id = None

                    origin = getattr(self, name, '')
                    changes[name] = f'{origin}=>{value}'

        #print('log_entries', log_entries, flush=True)
        # collection_changes = collection_log.check() # 不好用, units, identifications... 會混成同一層
        #changes.update(collection_changes)
        # print('col', collection_changes, flush=True)
        # print('cus', changes, flush=True)
        session.commit()

        return changes

    def get_values(self):
        data = {
            'id': self.id,
            'collect_date': self.collect_date.strftime('%Y-%m-%d') if self.collect_date else '',
            'collector': self.collector.to_dict() if self.collector else '',
            'field_number': self.field_number or '',
            'companion_text': self.companion_text or '',
            'companion_text_en': self.companion_text_en or '',
            'altitude': self.altitude or '',
            'altitude2':self.altitude2 or '',
            'longitude_decimal': self.longitude_decimal or '',
            'latitude_decimal': self.latitude_decimal or '',
            'verbatim_longitude': self.verbatim_longitude or '',
            'verbatim_latitude': self.verbatim_latitude or '',
            'locality_text': self.locality_text or '',
            'locality_text_en': self.locality_text_en or '',
            'verbatim_locality': self.verbatim_locality or '',
            'field_note': self.field_note or '',
            'field_note_en': self.field_note_en or '',
            'identifications': [x.to_dict() for x in self.identifications.order_by(Identification.sequence).all()],
            #'proxy_unit_accession_numbers': self.proxy_unit_accession_numbers,
            #'proxy_taxon_text': self.proxy_taxon_text,
            #'proxy_taxon_id': self.proxy_taxon_id,
            #'proxy_taxon': taxon.to_dict() if taxon else None,
            'assertions': {},
            'units': [x.to_dict() for x in self.units],
            'named_areas': {},
        }

        for i in self.assertions:
            data['assertions'][i.assertion_type.name] = i.value

        for x in self.named_area_maps:
            data['named_areas'][x.named_area.area_class.name] = x.named_area.to_dict()

        return data

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

    def get_coordinates(self, type_=''):
        if self.longitude_decimal and self.latitude_decimal:
            if type_ == '' or type_ == 'dd':
                return {
                    'x': self.longitude_decimal,
                    'y': self.latitude_decimal
                }
            elif type_ == 'dms':
                dms_lng = dd2dms(self.longitude_decimal)
                dms_lat = dd2dms(self.latitude_decimal)
                x_label = '{}{}\u00b0{:02d}\'{:02d}"'.format('N' if dms_lng[0] > 0 else 'S', dms_lng[0], dms_lng[1], round(dms_lng[2]))
                y_label = '{}{}\u00b0{}\'{:02d}"'.format('E' if dms_lat[0] > 0 else 'W', dms_lat[0], dms_lat[1], round(dms_lat[2]))
                return {
                    'x': dms_lng,
                    'y': dms_lat,
                    'x_label': x_label,
                    'y_label': y_label,
                    'simple': f'{x_label}, {y_label}'
                }
        else:
            return None

    #def get_named_area_map(self):
        #named_area_map = {f'{x.named_area.area_class.name}': x.named_area.to_dict() for x in self.named_area_relations}
    #    named_area_map = {f'{x.area_class.name}': x.to_dict() for x in self.named_areas}
    #    return get_structed_map(AreaClass.DEFAULT_OPTIONS, named_area_map)

    #def get_named_area_list(self): #TODO
    #    return []
    def get_form_layout(self):
        named_areas = []
        for x in AreaClass.DEFAULT_OPTIONS:
            data = {
                'id': x['id'],
                'label': x['label'],
                'name': x['name'],
                'options': [],
            }
            for na in NamedArea.query.filter(NamedArea.area_class_id==x['id']).order_by('id').all():
                data['options'].append(na.to_dict())

            named_areas.append(data)

        biotopes = []
        for param in MeasurementOrFact.BIOTOPE_OPTIONS:
            data = {
                'id': param['id'],
                'label': param['label'],
                'name':  param['name'],
                'options': []
            }
            for row in MeasurementOrFactParameterOption.query.filter(MeasurementOrFactParameterOption.parameter_id==param['id']).all():
                data['options'].append(row.to_dict())
            biotopes.append(data)

        unit_mofs = []
        for param in MeasurementOrFact.UNIT_OPTIONS:
            data = {
                'id': param['id'],
                'label': param['label'],
                'name':  param['name'],
                'options': []
            }
            for row in MeasurementOrFactParameterOption.query.filter(MeasurementOrFactParameterOption.parameter_id==param['id']).all():
                data['options'].append(row.to_dict())
            unit_mofs.append(data)

        projects = [x.to_dict() for x in Project.query.all()]

        return {
            'biotopes': biotopes,
            'unit_measurement_or_facts': unit_mofs,
            'named_areas': named_areas,
            'projects': projects,
        }

    def get_first_id(self):
        if self.identifications:
            return self.identifications[0]
        else:
            return None

    @property
    def companion_list(self):
        items = []
        if x:= self.companion_text:
            items.append(x)
        if x:= self.companion_text_en:
            items.append(x)
        return items

class Identification(Base, TimestampMixin):

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
            'sequence': self.sequence or '',
        }
        if self.taxon:
            data['taxon'] =  {'id': self.taxon_id, 'text': self.taxon.display_name}
        if self.identifier:
            data['identifier'] = self.identifier.to_dict()

        return data

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

class Unit(Base, TimestampMixin):
    '''mixed abcd: SpecimenUnit/ObservationUnit (phycal state-specific subtypes of the unit reocrd)
    BotanicalGardenUnit/HerbariumUnit/ZoologicalUnit/PaleontologicalUnit
    '''
    KIND_OF_UNIT_MAP = {'HS': 'Herbarium Sheet'}

    TYPE_STATUS_CHOICES = (
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
    #last_editor = Column(String(500))
    #owner
    #identifications = relationship('Identification', back_populates='unit')
    kind_of_unit = Column(String(500)) # herbarium sheet (HS), leaf, muscle, leg, blood, ..., ref: https://arctos.database.museum/info/ctDocumentation.cfm?table=ctspecimen_part_name#whole_organism

    # assemblages
    # associations
    # sequences

    assertions = relationship('UnitAssertion')
    #planting_date
    #propagation

    # abcd: SpecimenUnit
    accession_number = Column(String(500), index=True)
    #accession_uri = Column(String(500)) ark?
    #accession_catalogue = Column(String(500))
    # accession_date
    duplication_number = Column(String(500)) # extend accession_number
    #abcd:preparations
    preparation_type = Column(String(500)) #specimens (S), tissues, DNA
    preparation_date = Column(Date)
    preservation_text = Column(String(500))
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

    specimen_marks = relationship('SpecimenMark')
    collection = relationship('Collection')
    record = relationship('Record', overlaps='units') # TODO warning
    assertions = relationship('UnitAssertion')
    transactions = relationship('Transaction')
    annotations = relationship('Annotation')
    propagations = relationship('Propagation')
    # abcd: Disposition (in collection/missing...)

    # observation
    source_data = Column(JSONB)
    information_withheld = Column(Text)

    pub_status = Column(String(10), default='P')

    multimedia_objects = relationship('MultimediaObject')
    legal_statement_id = Column(ForeignKey('legal_statement.id', ondelete='SET NULL'))

    @property
    def ark(self):
        for x in self.pids:
            if x.pid_type == 'ark':
                return x.key
        return None

    @staticmethod
    def get_specimen(entity_key):
        org_code, accession_number = entity_key.split(':')
        stmt = select(Collection.id) \
            .join(Organization) \
            .where(Organization.code==org_code)

        result = session.execute(stmt)
        collection_ids = [x[0] for x in result.all()]
        if entity := Unit.query.filter(Unit.accession_number==accession_number, Unit.collection_id.in_(collection_ids)).first():
            return entity
        return None

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

    def get_specimen_url(self, namespace=''):
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
    def to_dict(self, mode='with-collection'):
        data = {
            'id': self.id,
            'key': self.key,
            'accession_number': self.accession_number or '',
            'duplication_number': self.duplication_number or '',
            #'collection_id': self.collection_id,
            'kind_of_unit': self.kind_of_unit or '',
            'preparation_type': self.preparation_type or '',
            'preparation_date': self.preparation_date.strftime('%Y-%m-%d') if self.preparation_date else '',
            #'measurement_or_facts': mofs,
            'assertions': self.get_assertions(),
            'image_url': self.get_image(),
            'transactions': [x.to_dict() for x in self.transactions],
            #'dataset': self.dataset.to_dict(), # too man
        }
        #if mode == 'with-collection':
        #    data['collection'] = self.collection.to_dict(include_units=False)

        return data

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

    def get_image(self, thumbnail='_s'):
        if self.collection_id == 1:
            #if self.multimedia_objects:
            #    accession_number_int = int(self.accession_number)
            #    id_ = f'{accession_number_int:06}'
            #    thumbnail = thumbnail.replace('_', '-')
            #    return f'https://pid.biodiv.tw/ark:/18474/v6cc0ts6j/S_{id_}{thumbnail}.jpg'
            try:
                accession_number_int = int(self.accession_number)
                instance_id = f'{accession_number_int:06}'
                first_3 = instance_id[0:3]
                image_url = f'https://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{instance_id}{thumbnail}.jpg'
                return image_url
            except:
                pass
            # TODO, get first cover or other type
            #if media := self.multimedia_objects[0]:
            #    if media.file_url:
            #        return media.file_url
        return ''

    def get_assertions(self, type_name=''):
        result = {}
        for a in self.assertions:
            if type_name == '':
                result[a.assertion_type.name] = {
                    'type_id': a.assertion_type_id,
                    'type_name': a.assertion_type.name,
                    'type_label': a.assertion_type.label,
                    'value': a.value
                }
            else:
                result = {
                    'type_id': a.assertion_type_id,
                    'type_name': a.assertion_type.name,
                    'type_label': a.assertion_type.label,
                    'value': a.value
                }
        return result

    def get_annotation_map(self, type_name=''):
        result = {}
        for x in self.annotations:
            if type_name == '':
                result[x.annotation_type.name] = x.value
            else:
                result = x.value

        return result

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


class Person(Base, TimestampMixin):
    '''
    full_name => original name
    atomized_name => by language (en, ...), contains: given_name, inherited_name
    '''
    __tablename__ = 'person'

    id = Column(Integer, primary_key=True)
    full_name = Column(String(500)) # abcd: FullName
    full_name_en = Column(String(500))
    atomized_name = Column(JSONB)
    # prefix: von | Lord
    # inherited_name
    # given_names(list): given name + middle name
    # given_name(str)
    # suffix: jun. | III
    # preferred_names: nickname
    # other name (IPNI)
    sorting_name = Column(String(500))
    abbreviated_name = Column(String(500))
    sorting_name = Column(String(500))

    #organization_name = Column(String(500))
    data = Column(JSONB) # org_abbr
    is_collector = Column(Boolean, default=False)
    is_identifier = Column(Boolean, default=False)
    is_agent = Column(Boolean, default=False)
    is_multi = Column(Boolean, default=False)
    source_data = Column(JSONB)
    #organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)
    #organization = Column(String(500))
    pids = relationship('PersistentIdentifierPerson')

    collections = relationship('Collection', secondary=collection_person_map, back_populates='people')

    def __repr__(self):
        return '<Person(id="{}", display_name="{}")>'.format(self.id, self.display_name)

    # @property
    # def english_name(self):
    #     if self.atomized_name and len(self.atomized_name):
    #         if en_name := self.atomized_name.get('en', ''):
    #             return '{} {}'.format(en_name['inherited_name'], en_name['given_name'])
    #     return ''

    @property
    def display_name(self):
        name_list = []
        if self.full_name and self.full_name_en:

            if self.atomized_name and self.atomized_name.get('given_name_en'):
                name2 = self.atomized_name.get('given_name_en')
                name1 = self.atomized_name.get('inherited_name_en')
                return f'{name1}, {name2} ({self.full_name})'
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
            'atomized_name': self.atomized_name,
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
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL'))
    transaction_type = Column(String(500)) #  (DiversityWorkbench) e.g. gift in or out, exchange in or out, purchase in or out
    title = Column(String(500))
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
        return {
            'title': self.title,
            'transaction_type': self.transaction_type,
            'display_transaction_type': display_type[0][1] if len(display_type) else '',
            # 'organization_id': self.organization_id,
            'organization_text': self.organization_text,
        }


class TransactionUnit(Base, TimestampMixin):
    __tablename__ = 'transaction_unit'
    id = Column(Integer, primary_key=True)
    transaction_id = Column(ForeignKey('transaction.id', ondelete='SET NULL'))
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL'))
    data = Column(JSONB)

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
    unit_id = Column(ForeignKey('unit.id', ondelete='SET NULL'))
    unit = relationship('Unit', back_populates='multimedia_objects')
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
    source_data = Column(JSONB)
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


class SpecimenMark(Base):
    __tablename__ = 'unit_mark'

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('unit.id', ondelete='SET NULL'), nullable=True)
    mark_type = Column(String(50)) # qrcode, rfid
    mark_text = Column(String(500))
    mark_author = Column(Integer, ForeignKey('person.id'))


class RecordPerson(Base):
    # other collector
    __tablename__ = 'record_person'

    id = Column(Integer, primary_key=True)
    record_id = Column(ForeignKey('record.id', ondelete='SET NULL'))
    #gathering = relationship('gathering')
    person_id = Column(ForeignKey('person.id', ondelete='SET NULL'))
    role = Column(String(50))
    sequence = Column(Integer)
    organization_id = Column(Integer, ForeignKey('organization.id', ondelete='SET NULL'), nullable=True)


class AssertionMixin:

    @declared_attr
    def assertion_type_id(self):
        return Column(Integer, ForeignKey('assertion_type.id'))

    @declared_attr
    def assertion_type(self):
        return relationship('AssertionType')

    value = Column(String(500))


class AssertionType(Base, TimestampMixin):
    __tablename__ = 'assertion_type'

    INPUT_TYPE_OPTIONS = (
        ('input', '單行文字'),
        ('text', '多行文字'),
        ('select', '下拉選單'),
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
        #('record', 'record'),
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


class UnitAnnotation(Base, AnnotationMixin):
    __tablename__ = 'unit_annotation'

    id = Column(Integer, primary_key=True)
    unit_id = Column(Integer, ForeignKey('unit.id'))

class MultimediaObjectAnnotation(Base, AnnotationMixin):
    __tablename__ = 'multimedia_object_annotation'

    id = Column(Integer, primary_key=True)
    multimedia_object_id = Column(Integer, ForeignKey('multimedia_object.id'))

class Annotation(Base, TimestampMixin):
    __tablename__ = 'annotation'

    id = Column(Integer, primary_key=True)
    type_id = Column(Integer, ForeignKey('annotation_type.id'))
    annotation_type = relationship('AnnotationType')
    unit_id = Column(Integer, ForeignKey('unit.id'))
    value = Column(String(500))
    # data = Column(JSONB) # source_data

    annotation_type = relationship('AnnotationType')
