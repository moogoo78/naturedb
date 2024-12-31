import re

from sqlalchemy import (
    select,
    func,
    text,
    desc,
    cast,
    between,
    Integer,
    BigInteger,
    LargeBinary,
    extract,
    or_,
    inspect,
    join,
)
from sqlalchemy.orm import (
    aliased,
)
from app.database import session

from app.models.collection import (
    Record,
    Unit,
    Person,
    RecordNamedAreaMap,
    RecordGroup,
    RecordGroupMap,
)
from app.models.taxon import (
    Taxon,
)
from app.models.gazetter import (
    Country,
    NamedArea,
)

def make_specimen_query(filtr):
    '''
    filter data
    '''
    # TODO：
    # 處理異體字: 台/臺
    # basic stmt

    if sd := filtr.get('sourceData'):
        if sd.get('annotate'):
            fields = []
            if count_fields := sd['annotate'].get('values'):
                fields = [Record.source_data[x] for x in count_fields]

            if sd['annotate'].get('aggregate'):
                stmt = select(
                    func.count("*"),
                    *fields,
                )
            else:
                stmt = select(
                    *fields,
                )

        else:
            stmt = select(Unit, Record)

        stmt = stmt.join(Unit, Unit.record_id==Record.id) # prevent cartesian product

        if q := sd.get('q', ''):
            many_or = or_()
            for field in sd['qFields']:
                many_or = or_(many_or, or_(Record.source_data[field].astext.ilike(f'%{q}%')))
            stmt = stmt.where(many_or)

        if ft := sd.get('filters'):
            for k, v in ft.items():
                if v == '__NOT_NULL__':
                    stmt = stmt.where(
                        Record.source_data[k].astext != ''
                    )
                else:
                    stmt = stmt.where(
                        Record.source_data[k].astext == v
                    )

        return stmt

    stmt = select(Unit, Record) \
        .join(Unit, Unit.record_id==Record.id) \
        .join(Person, Record.collector_id==Person.id, isouter=True)

    stmt = stmt.where(Unit.pub_status=='P')
    stmt = stmt.where(Unit.accession_number!='') # 有 unit, 但沒有館號

    # filter
    if q := filtr.get('q'):
        stmt = stmt.where(or_(Unit.accession_number.ilike(f'%{q}%'),
                              Record.field_number.ilike(f'%{q}%'),
                              Person.full_name.ilike(f'%{q}%'),
                              Person.full_name_en.ilike(f'%{q}%'),
                              Record.proxy_taxon_scientific_name.ilike(f'%{q}%'),
                              Record.proxy_taxon_common_name.ilike(f'%{q}%'),
                              ))
    if taxon_id := filtr.get('taxon_id'):
        taxa_ids = []
        if isinstance(taxon_id, list):
            for x in taxon_id:
                if t := session.get(Taxon, x):
                    taxa_ids += [x.id for x in t.get_children()]
        else:
            if t := session.get(Taxon, taxon_id):
                taxa_ids = [x.id for x in t.get_children()]

        # filter with child taxa
        stmt = stmt.where(Record.proxy_taxon_id.in_(taxa_ids))

    if taxon_name := filtr.get('taxon_name'):
        stmt = stmt.where(Record.proxy_taxon_scientific_name.ilike(f'%{taxon_name}%') | Record.proxy_taxon_common_name.ilike(f'%{taxon_name}%'))
    if value := filtr.get('collector_id'):
        stmt = stmt.where(Record.collector_id==value)
    #if value := filtr.get('collector_name'):
    #    stmt = stmt.where(Person.full_name.ilike(f'{value}%'))
    if value := filtr.get('field_number'):
        if '--' in value:
            vs = value.split('--')
            value1 = vs[0]
            value2 = vs[1]
            stmt = stmt.where(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Record.field_number.regexp_replace('[^0-9]+', '', flags='g') != '')
            print(stmt, '---', flush=True)
        else:
            stmt = stmt.where(Record.field_number==value)
            #stmt = stmt.where(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), Integer)==value)

    if value := filtr.get('collect_date'):
        if '--' in value:
            vs = value.split('--')
            value1 = vs[0]
            value2 = vs[1]
            stmt = stmt.where(Record.collect_date>=value1, Record.collect_date<=value2)
        else:
            if m := re.search(r'([0-9]{4})-([0-9]{4})', value):
                stmt = stmt.where(Record.collect_date >= f'{m.group(1)}-01-01').where(Record.collect_date <= f'{m.group(2)}-01-01')
            else:
                stmt = stmt.where(Record.collect_date==value)
    if value := filtr.get('collect_month'):
        stmt = stmt.where(extract('month', Record.collect_date) == value)

    # locality
    if value := filtr.get('continent'):
        ids = Country.get_named_area_ids_from_continent(value.capitalize())
        exists_stmt = (
            select(RecordNamedAreaMap).
            where(Record.id==RecordNamedAreaMap.record_id, RecordNamedAreaMap.named_area_id.in_(ids)).exists()
        )
        stmt = stmt.where(exists_stmt)
    if value := filtr.get('named_area_id'):
        if isinstance(value, list):
            or_list = []
            for x in value:
                or_list.append(Record.named_area_maps.any(named_area_id=x))
            stmt = stmt.where(or_(*or_list))
        else:
            stmt = stmt.where(Record.named_area_maps.any(named_area_id=value))
    if value := filtr.get('country'):
        if filtr.get('named_area_id'):
            # if has named_area_id, country filter cause 0 results
            pass
        else:
            stmt = stmt.where(Record.named_area_maps.any(named_area_id=value))
    if value := filtr.get('locality_text'):
        stmt = stmt.where(Record.locality_text.ilike(f'%{value}%'))

    if value := filtr.get('altitude'):
        if '--' in value:
            vs = value.split('--')
            value1 = vs[0]
            value2 = vs[1]

            if value1 and value2:
                stmt = stmt.where(Record.altitude>=value1, Record.altitude2<=value2)
            elif value1 and not value2:
                stmt = stmt.where(Record.altitude>=value1)
            elif not value1 and value2:
                stmt = stmt.where(Record.altitude<=value2)
        else:
            stmt = stmt.where(Record.altitude==value)

    # specimens
    if value := filtr.get('accession_number'):
        # if value2 := filtr.get('accession_number2'):
        #     stmt = stmt.where(cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value), cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g') != '')
        # else:
        #     stmt = stmt.where(Unit.accession_number == accession_number)
        if '--' in value:
            value1, value2 = value.split('--')
            stmt = stmt.where(cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g') != '')
        else:
            stmt = stmt.where(Unit.accession_number==value)

    if value := filtr.get('type_status'):
        stmt = stmt.where(Unit.type_status.ilike(f'%{value}%'))

    #print(stmt, flush=True)
    return stmt

def make_admin_record_query(payload):
    qlist = []
    if qstr := payload.get('q'):
        qlist = qstr.split(' ')

    collectors = payload.get('collectors')
    taxa = payload.get('taxa')
    collection_id = payload.get('collection_id')
    record_group_id = payload.get('record_group_id')

    stmt_select = select(
        Unit.id,
        Unit.accession_number,
        Record.id,
        Record.collector_id,
        Record.field_number,
        Record.collect_date,
        Record.proxy_taxon_scientific_name,
        Record.proxy_taxon_common_name,
        Record.proxy_taxon_id,
        Unit.created,
        Unit.updated,
        Record.collection_id)

    taxon_family = aliased(Taxon)
    stmt = stmt_select\
    .join(Unit, Unit.record_id==Record.id, isouter=True) \
    .join(taxon_family, taxon_family.id==Record.proxy_taxon_id, isouter=True) \
    #print(stmt, flush=True)

    many_or = or_()
    for q in qlist:
        if q:
            if q.isdigit():
                #stmt = stmt.filter(
                #    or_(Unit.accession_number==q,
                #        Record.field_number==q,
                #        ))
                many_or = or_(many_or, or_(
                    Unit.accession_number==q,
                    Record.field_number==q,
                ))
            elif '--' in q:
                value1, value2 = q.split('--')
                #stmt = stmt.where(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Record.field_number.regexp_replace('[^0-9]+', '', flags='g') != '')
                many_or = or_(many_or, or_(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Record.field_number.regexp_replace('[^0-9]+', '', flags='g') != ''))
            else:
                # stmt = stmt.filter(
                #     or_(Unit.accession_number.ilike(f'{q}'),
                #         Record.field_number.ilike(f'{q}'),
                #         Person.full_name.ilike(f'{q}%'),
                #         Person.full_name_en.ilike(f'{q}%'),
                #         Record.proxy_taxon_scientific_name.ilike(f'{q}%'),
                #         Record.proxy_taxon_common_name.ilike(f'{q}%'),
                #         ))
                many_or = or_(many_or, or_(
                    Unit.accession_number.ilike(f'{q}'),
                    Record.field_number.ilike(f'{q}'),
                    Person.full_name.ilike(f'{q}%'),
                    Person.full_name_en.ilike(f'{q}%'),
                    Record.proxy_taxon_scientific_name.ilike(f'{q}%'),
                    Record.proxy_taxon_common_name.ilike(f'{q}%'),
                ))

    stmt = stmt.filter(many_or)
    if collectors:
        collector_list = collectors.split(',')
        stmt = stmt.filter(Record.collector_id.in_(collector_list))

    if taxa:
        taxon_list = taxa.split(',')
        taxa_ids = []
        for tid in taxon_list:
            if t := session.get(Taxon, tid):
                taxa_ids += [x.id for x in t.get_children()]

        stmt = stmt.filter(Record.proxy_taxon_id.in_(taxa_ids))

    if collection_id:
        stmt = stmt.filter(Record.collection_id==collection_id)
    if record_group_id:
        stmt = stmt.filter(RecordGroup.id==record_group_id)
    #print(stmt)
    return stmt

def filter_records(filtr, auth=None):

    stmt_select = select(
        Unit.id,
        Unit.accession_number,
        Record.id,
        Record.collector_id,
        Record.field_number,
        Record.collect_date,
        Record.proxy_taxon_scientific_name,
        Record.proxy_taxon_common_name,
        Record.proxy_taxon_id,
        Unit.created,
        Unit.updated,
        Record.collection_id)

    taxon_family = aliased(Taxon)
    stmt = stmt_select\
    .join(Unit, Unit.record_id==Record.id, isouter=True) \
    .join(taxon_family, taxon_family.id==Record.proxy_taxon_id, isouter=True) \
    #print(stmt, flush=True)

    for key, values in filtr.items():
        if key == 'collection_id':
            if int_v := int(values):
                stmt = stmt.where(Record.collection_id==int_v)
        elif key == 'record_group_id':
            stmt = stmt.join(RecordGroupMap).where(RecordGroupMap.group_id==values)

        elif key == 'q':
            many_or = or_()
            for val in values:
                if ':' in val:
                    k, v = val.split(':')
                    if k == 'collector_id':
                        many_or = or_(many_or, or_(Record.collector_id==v))
                    if k == 'taxon_id':
                        many_or = or_(many_or, or_(Record.proxy_taxon_id==v))
                    if k == 'record_id':
                        many_or = or_(many_or, or_(Record.id==v))
                elif '--' in val:
                    value1, value2 = val.split('--')
                    many_or = or_(many_or, or_(
                        cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1),
                        cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Record.field_number.regexp_replace('[^0-9]+', '', flags='g') != ''))


            stmt = stmt.filter(many_or)
    '''

    for q in qlist:
        if q:
            if q.isdigit():
                #stmt = stmt.filter(
                #    or_(Unit.accession_number==q,
                #        Record.field_number==q,
                #        ))
                many_or = or_(many_or, or_(
                    Unit.accession_number==q,
                    Record.field_number==q,
                ))
            elif '--' in q:
                value1, value2 = q.split('--')
                #stmt = stmt.where(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Record.field_number.regexp_replace('[^0-9]+', '', flags='g') != '')
                many_or = or_(many_or, or_(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Record.field_number.regexp_replace('[^0-9]+', '', flags='g') != ''))
            else:
                # stmt = stmt.filter(
                #     or_(Unit.accession_number.ilike(f'{q}'),
                #         Record.field_number.ilike(f'{q}'),
                #         Person.full_name.ilike(f'{q}%'),
                #         Person.full_name_en.ilike(f'{q}%'),
                #         Record.proxy_taxon_scientific_name.ilike(f'{q}%'),
                #         Record.proxy_taxon_common_name.ilike(f'{q}%'),
                #         ))
                many_or = or_(many_or, or_(
                    Unit.accession_number.ilike(f'{q}'),
                    Record.field_number.ilike(f'{q}'),
                    Person.full_name.ilike(f'{q}%'),
                    Person.full_name_en.ilike(f'{q}%'),
                    Record.proxy_taxon_scientific_name.ilike(f'{q}%'),
                    Record.proxy_taxon_common_name.ilike(f'{q}%'),
                ))

    stmt = stmt.filter(many_or)
    if collectors:
        collector_list = collectors.split(',')
        stmt = stmt.filter(Record.collector_id.in_(collector_list))

    if taxa:
        taxon_list = taxa.split(',')
        taxa_ids = []
        for tid in taxon_list:
            if t := session.get(Taxon, tid):
                taxa_ids += [x.id for x in t.get_children()]

        stmt = stmt.filter(Record.proxy_taxon_id.in_(taxa_ids))

    if collection_id:
        stmt = stmt.filter(Record.collection_id==collection_id)
    if record_group_id:
        stmt = stmt.filter(RecordGroup.id==record_group_id)
    #print(stmt)
    '''
    if auth:
        if 'collection_ids' in auth:
            stmt = stmt.filter(Record.collection_id.in_(auth['collection_ids']))
    return stmt
