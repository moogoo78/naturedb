import csv
import math
import time
import sqlite3
import re
from tempfile import NamedTemporaryFile
from datetime import datetime
from pathlib import Path

from sqlalchemy import (
    select,
    func,
    desc,
)
from flask import (
    current_app,
)
from app.database import session
from app.models.collection import (
    Unit,
    Record,
    RecordGroupMap,
    Identification,
)
from app.models.gazetter import (
    Country,
)
from app.models.taxon import (
    Taxon
)
from app.helpers_query import (
     make_specimen_query,
)

class MiniMatch(object):

    cur = None
    values = []
    hand_match_data = None

    def __init__(self, db_path):
        self.db_path = db_path
        con = sqlite3.connect("names.sqlite3")
        self.cur = con.cursor()


    def exec_query(self, sql):
        rows = []
        res = self.cur.execute(sql)
        for row in res.fetchall():
            data = {}
            if fields := self.values:
                for i,field in enumerate(fields):
                    data[field] = row[i]
                rows.append(data)
            #rows.append(row)

        return rows

    def select(self, *args):
        self.values = args

    def match(self, name, limit):
        '''
        sql = """SELECT bm25(taicol_fts, 0, 10), t.name_id, t.simple_name\
        FROM taicol t INNER JOIN taicol_fts s ON s.name_id = t.name_id\
        WHERE taicol_fts match '{{simple_name}}: {name}' LIMIT {limit}""".format(name=name, limit=limit);
        '''
        fields = ', '.join([f'"{x}"'for x in self.values])
        sql = f'SELECT {fields} from taicol where simple_name like \'%{name}%\''
        results = self.exec_query(sql)

        if len(results) > 0:
            return results[0] # first one
        #elif self.hand_match_data:
        #    return self.hand_match(name)

    def set_hand_match_data(self, data):
        self.hand_match_data = data

    def hand_match(self, name):
        # global names resolver copy and paste rank
        if ranks := self.hand_match_data.get(name):
            taxon = {}
            for i in ranks.split('>>'):
                for k in ['kingdom', 'phylum', 'class', 'order', 'family', 'genus']:
                    if f'({k})' in i:
                        taxon[f'{k}_name'] = i.replace(f'({k})', '').strip()

            taxon_zh = {}
            for k, v in taxon.items():
                taxon_zh[k] = v
                if res := self.match(v, 1):
                    if cname := res.get('common_name_c'):
                        taxon_zh[f'{k}_zh'] = cname

            #print(name)
            #print(taxon_zh)
            return taxon_zh

def export_specimens(site, collection_ids, fmt):
    limit = 1000
    dwc_settings = site.get_settings('dwc')
    if fmt == 'dwc':
        auth = {}
        if collection_ids:
            auth = {
                'collection_id': collection_ids.split(',')
            }
        stmt = make_specimen_query({}, auth)
        base_stmt = stmt
        subquery = base_stmt.subquery()
        count_stmt = select(func.count()).select_from(subquery)
        total = session.execute(count_stmt).scalar()

        occurrence_fieldnames = [
            'occurrenceID',
            'basisOfRecord',
            'catalogNumber',
            'decimalLongitude',
            'decimalLatitude',
            'minimumElevationInMeters',
            'maximumElevationInMeters',
            'geodeticDatum',
            'country',
            'countryCode',
            'stateProvince',
            'county',
            'municipality',
            'locality',
            'verbatimLocality',
            'habitat',
            'lifeStage',
            'recordedBy',
            'recordNumber',
            'eventDate',
            'verbatimEventDate',
            'scientificName',
            'vernacularName',
            'taxonRank',
            'kingdom',
            'phylum',
            'class',
            'order',
            'family',
            'genus',
            'associatedMedia',
            'license',
            'rightsHolder',
            'institutionCode',
            'ownerInstitutionCode',
            'modified',
            'references'
        ]
        ext_fieldnames = {
            'measurement_or_facts': ['occurrenceID', 'measurementID', 'measurementType', 'measurementValue', 'measurementDeterminedDate'],
            'identification_history': ['occurrenceID', 'identificationID', 'verbatimIdentification', 'identifiedBy', 'dateIdentified', 'identificationRemarks', 'scientificName', 'taxonRank', 'vernacularName']
        }

        now = datetime.now().strftime('%y%m%d_%H%M%S')
        tmp_dir = Path('/', 'uploads', f'{site.name}-dwc-{now}')
        tmp_dir.mkdir()
        core_csv = open(Path(tmp_dir, 'occurrence.txt'), 'w', newline='')
        core_writer = csv.DictWriter(core_csv, fieldnames=occurrence_fieldnames, delimiter='\t')
        core_writer.writeheader()

        ext_writers = {}
        ext_csvs = []
        for ext in dwc_settings['extensions']:
            ext_csv = open(Path(tmp_dir, f'{ext}.txt'), 'w', newline='')
            ext_csvs.append(ext_csv)
            ext_writers[ext] = csv.DictWriter(ext_csv, fieldnames=ext_fieldnames[ext], delimiter='\t')
            ext_writers[ext].writeheader()

        stmt = stmt.order_by(Unit.id)
        for page in range(0, math.ceil(total/limit)):
            stmt = stmt.limit(limit).offset(page*limit)
            result = session.execute(stmt)
            rows = result.all()
            print(f'processing export_dwc: {page*limit}-{(page+1)*limit} / {total}')
            for r in rows:
                data = get_darwin_core(r[0], 'all', dwc_settings) # unit only
                core_writer.writerow(data['occurrence'])
                for ext in dwc_settings['extensions']:
                    for i in data[ext]:
                        ext_writers[ext].writerow(i)

        core_csv.close()
        for ext_csv in ext_csvs:
            ext_csv.close()

def import_raw(data, collection_id, record_group_id):
    r = Record(source_data=data, collection_id=collection_id)
    session.add(r)
    session.commit()

    m = RecordGroupMap(record_id=r.id, group_id=record_group_id)
    session.add(m)
    session.commit()

    u = Unit(collection_id=collection_id, record_id=r.id)
    session.add(u)
    session.commit()


def get_darwin_core(unit, type_='simple', settings={}):
    site = unit.record.collection.site
    data = {}
    measurement_or_facts = []
    simple_multimedia = []
    identification_history = []

    record = unit.record
    # Class:Record-level
    data['modified'] = unit.updated.replace(microsecond=0).isoformat()
    data['references'] = f'https://{site.host}/specimens/{site.name.upper()}:{unit.accession_number}'
    # terms['accessRights'] = '' 網頁說明
    # TODO GRSciColl
    # institutionID
    # collectionID
    # datasetID
    # collectionCode
    #data['datasetName'] = 
    # dataGeneralizations = 'Coordinates generalized from original GPS coordinates to the nearest half degree grid cell.'

    data['basisOfRecord'] = unit.basis_of_record
    data['occurrenceID'] = unit.guid
    data['catalogNumber'] = unit.accession_number

    # Class:Location
    if  x:= record.longitude_decimal:
        data['decimalLongitude'] = str(float(x))
    if x := record.latitude_decimal:
        data['decimalLatitude'] = str(float(x))
    if x:= record.verbatim_locality:
        data['verbatimLocality'] = x
    if x:= record.altitude:
        data['minimumElevationInMeters'] = str(x)
    if x:= record.altitude2:
        data['maximumElevationInMeters'] = str(x)
    # coordinateUncertaintyInMeters
    data['geodeticDatum'] = record.geodetic_datum or 'not recorded'

    custom_area_class_ids = [x.id for x in site.get_custom_area_classes()]
    named_area_map = record.get_named_area_map(custom_area_class_ids)
    if x := named_area_map.get('COUNTRY'):
        data['country'] = x.named_area.name_en
        if code := x.named_area.code:
            if country := Country.query.filter(Country.iso3==code).scalar():
                data['countryCode'] = country.iso3166_1

    if data.get('countryCode', '') == 'TW':
        # no stateProvince
        if x := named_area_map.get('ADM1'):
            data['county'] = x.named_area.name_en # City/County
        if x := named_area_map.get('ADM2'):
            data['municipality'] = x.named_area.name_en # Township/District
        #if x := record.get_named_area('ADM3'): # 為了空stateProvince放棄村里
        #    data['municipality'] = x.display_text
    else:
        if x := named_area_map.get('ADM1'):
            data['stateProvince'] = x.named_area.display_text
        if x := named_area_map.get('ADM2'):
            data['county'] = x.named_area.display_text
        if x := named_area_map.get('ADM3'):
            data['municipality'] = x.named_area.display_text

        locality_list = []
        for k, v in named_area_map.items():
            if k not in ['COUNTRY', 'ADM1', 'ADM2', 'ADM3']:
                locality_list.append(v.named_area.display_name)

        if x := record.locality_text:
            if '\n' in x:
                print(data['occurrenceID'], x, '1')
                current_app.logger.info(f"{data['occurrenceID']} has content with \r: ${x} => remove it")
                x = x.replace('\n', '')
            locality_list.append(x)
        if x := record.locality_text_en:
            if '\n' in x:
                current_app.logger.info(f"{data['occurrenceID']} has content with \r: ${x} => remove it")
                x = x.replace('\n', '')
            locality_list.append(x)

        if len(locality_list) > 0:
            data['locality'] = '|'.join(locality_list)

    # island
    # continent

    # Class:Occurrence
    if x := record.collector:
        data['recordedBy'] = x.display_name
    elif x := record.verbatim_collector:
        data['recordedBy'] = x

    if x := record.field_number:
        data['recordNumber'] = x
    #establishmentMeans

    #georeferenceVerificationStatus
    #associatedMedia
    #occurrenceRemarks
    # Class:Event
    if x := record.collect_date:
        data['eventDate'] = x.strftime('%Y-%m-%d')
    if x := record.verbatim_collect_date:
        data['verbatimEventDate'] = x

    # reproductiveCondition
    # fieldNotes

    # Taxon
    if tid := record.proxy_taxon_id:
        if taxon := session.get(Taxon, tid):
            data['scientificName'] = taxon.full_scientific_name
            data['taxonRank'] = taxon.rank
            if x := taxon.common_name:
                data['vernacularName'] = x
            for ancestor in taxon.get_parents():
                if rank := ancestor.rank:
                    data[rank] = ancestor.full_scientific_name.capitalize()

    # MeasurementOrFact
    ao_map = {}
    if len(settings) > 0:
        ao_map = settings.get('assertionOccurrenceMap', {})

    for a in record.assertions + unit.assertions:
        v = a.value
        v = v.replace('\n', '')
        v = v.replace('\r', '')
        if len(ao_map) == 0 or a.assertion_type.name not in ao_map:
            mof = {
                'occurrenceID': data['occurrenceID'],
                'measurementID': a.id,
                'measurementType': a.assertion_type.label,
                'measurementValue': v,
            }
            if a.datetime:
                mof['measurementDeterminedDate'] = a.datetime.replace(microsecond=0).isoformat()

            measurement_or_facts.append(mof)
        else:
            data[ao_map[a.assertion_type.name]] = v


    # identificationHistory
    for i in unit.record.identifications.order_by(desc(Identification.sequence)):
        id_ = {
            'occurrenceID': data['occurrenceID'],
            'identificationID': i.id,
        }
        if x := i.verbatim_identification:
            id_['verbatimIdentification'] = x
        if x := i.identifier:
            id_['identifiedBy'] = x.display_name
        if x := i.date:
            id_['dateIdentified'] = x.strftime('%Y-%m-%d')
        if x := i.note:
            id_['identificationRemarks'] = x
        if t := i.taxon:
            id_['scientificName'] = t.full_scientific_name
            id_['taxonRank'] = t.rank
            if x := t.common_name:
                id_['vernacularName'] = x

        identification_history.append(id_)


    # TODO simple multimedia
    if x:= unit.cover_image:
        data['associatedMedia'] = x.file_url

    if a := settings.get('apply'):
        data.update(a)

    return {
        'occurrence': data,
        'measurement_or_facts': measurement_or_facts,
        'simple_multimedia': simple_multimedia,
        'identification_history': identification_history,
    }
