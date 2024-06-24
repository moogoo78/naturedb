import csv
import math
import time
import sqlite3
import re

from sqlalchemy import (
    select,
    func,
)

from app.database import session
from app.models.collection import (
    Unit,
    Record,
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
        elif self.hand_match_data:
            self.hand_match(name)

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

            print(name)
            print(taxon_zh)

def export_specimen_dwc_csv():

    chunk_size = 100
    base_stmt = make_specimen_query({})

    #stmt = base_stmt.order_by(Unit.id).limit(chunk_size)
    #count_stmt = select(func.count()).select_from(base_stmt.subquery())
    #query = Unit.query.order_by(Unit.id)

    t1 = time.time()
    #total = session.execute(count_stmt).scalar()
    total = Unit.query.count()
    t2 = time.time()

    basic_fields = [
        'id',
        'occurrenceID',
        'eventID',
        #'datasetID',
        #'datasetName',
        'collectionCode',
        'institutionCode',
        'institutionID',
        'catalogNumber',
        'recordNumber',
        'recordedBy',
        'eventDate',
        'verbatimEventDate',
        'country',
        'countryCode',
        'stateProvince',
        'municipality',
        'county',
        'locality',
        'verbatimLocality',
        'decimalLongitude',
        'decimalLatitude',
        'verbatimLongitude',
        'verbatimLatitude',
        'geodeticDatum',
        'lifeStage',
        'scientificName'
        'kingdom',
        'family',
        'vernacularName',
        'taxonRank',
    ]
    #'basisOfRecord',

    # 'habitat',
    #     'coordinateUncertaintyInMeters'
    #     coordinatePrecision
    #     establishmentMeans
    #     'reproductiveCondition'
    #     references: url
    #     dynamicProperties

    all_fields = basic_fields
    org_identifier = 'ih-irn'
    with open('eggs.csv', 'w', newline='') as csvfile:
        spamwriter = csv.DictWriter(csvfile, fieldnames=all_fields)

        #result = session.execute(stmt)
        #for i in result:
        #    print(i)

        is_keep = True
        keep_map = {
            'collectionCode': '',
            'institutionCode': '',
            'institutionID': '',
        }

        for i in range(0, math.ceil(total/chunk_size)):
            #result = session.execute(stmt.limit(chunk_size).offset(i*chunk_size))
            result = Unit.query.order_by(Unit.id).limit(chunk_size).offset(i*chunk_size)
            #print(i*chunk_size, flush=True)
            for u in result.all():
                data = {}
                if is_keep:
                    if i == 0:
                        keep_map['collectionCode'] = u.collection.name
                        keep_map['institutionCode'] = u.collection.organization.code
                        keep_map['institutionID'] = u.collection.organization.get_identifier(org_identifier)

                    data['collectionCode'] = keep_map['collectionCode']
                    data['institutionCode'] = keep_map['institutionCode']
                    data['institutionID'] = keep_map['institutionID']

                data['id'] = u.id
                data['occurrenceID'] = u.id
                data['eventID'] = f'event-{u.id}'
                data['catalogNumber'] = f"{data['collectionCode']}:{u.accession_number}"
                data['recordNumber'] = u.record.field_number or ''

                for term in ['catalogNumber', 'recordedBy', 'eventDate', 'verbatimEventDate']:
                    data[term] = u.get_term_text(f'dwc:{term}')
                location = u.get_location()
                #print(location, flush=True)
                if x := location.get('dwc:country'):
                    data['country'] = x

                #print(un, flush=True)
                spamwriter.writerow(data)
            break


    t3 = time.time()

    print(t3, t2, t1, flush=True)
    print(t3-t2, t2-t1, flush=True)


def import_phase0(data, collection_id):
    r = Record(source_data=data, collection_id=collection_id)
    session.add(r)
    session.commit()

    #u = Unit(collection_id=collection_id, record_id=r.id)
    #session.add(u)
    #session.commit()
