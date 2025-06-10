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

    if sd := filtr.get('customFields'):
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
            for field in sd['fields']:
                many_or = or_(many_or, Record.source_data[field].astext.ilike(f'%{q}%'))
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
            # DEPRECATED
            vs = value.split('--')
            value1 = vs[0]
            value2 = vs[1]
            stmt = stmt.where(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Record.field_number.regexp_replace('[^0-9]+', '', flags='g') != '')
            #print(stmt, '---', flush=True)
        else:
            #stmt = stmt.where(Record.field_number==value)
            #stmt = stmt.where(cast(Record.field_number.regexp_replace('[^0-9]+', '', flags='g'), Integer)==value)
            if value2 := filtr.get('field_number2'):
                stmt = stmt.where(Record.field_number_int >= value, Record.field_number_int <= value2)
            else:
                stmt = stmt.where(Record.field_number_int == value)

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
                if value2 := filtr.get('collect_date2'):
                    stmt = stmt.where(Record.collect_date >= value, Record.collect_date <= value2)
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
    if value := filtr.get('catalog_number'):
        if value2 := filtr.get('catalog_number2'):
            stmt = stmt.where(
                cast(
                    Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value),
                cast(
                    Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2),
                Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g') != '')
            #range_list = list(range(int(value), int(value2)+1))
            #print(range_list, flush=True)
            #many_or = or_()
            #for i in range_list:
            #    many_or = or_(many_or, Unit.accession_number.ilike(f'{i}%'))

            #stmt = stmt.where(many_or)
        else:
            stmt = stmt.where(Unit.accession_number == value)

        # if '--' in value:
        #     value1, value2 = value.split('--')
        #     stmt = stmt.where(cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value1), cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g') != '')
        # else:
        #     stmt = stmt.where(Unit.accession_number==value)

    if value := filtr.get('type_status'):
        stmt = stmt.where(Unit.type_status.ilike(f'%{value}%'))

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

def make_items_stmt(payload, auth={}, mode=''):
    stmt_select = select(
        Record.id,
        #Record.collection_id,
        #Record.collector_id,
        #Record.field_number,
        #Record.collect_date,
        Unit.id,
        Record.proxy_taxon_scientific_name,
        Record.proxy_taxon_common_name,
        Record.proxy_taxon_id,
        #Unit.accession_number,
        #Unit.created,
        #Unit.updated,
    )

    taxon_family = aliased(Taxon)
    stmt = stmt_select\
        .join(Unit, Unit.record_id==Record.id, isouter=True) \
        .join(taxon_family, taxon_family.id==Record.proxy_taxon_id, isouter=True) \
        .join(Person, Record.collector_id==Person.id, isouter=True)
    #print(stmt, flush=True)

    if len(auth):
        if ids := auth.get('collection_id'):
            stmt = stmt.where(Record.collection_id.in_(ids))
        if role := auth.get('role'):
            if role != 'admin':
                stmt = stmt.where(Unit.pub_status=='P')
                stmt = stmt.where(Unit.accession_number!='') # 有 unit, 但沒有館號

    filtr = payload['filter']
    if collection_id := filtr.get('collection_id'):
        stmt = stmt.where(Record.collector_id==collection_id)
    if record_group_id := filtr.get('record_group_id'):
        stmt = stmt.join(RecordGroupMap).where(RecordGroupMap.group_id==record_group_id)

    if q := filtr.get('q'):
        # 整理, 集合
        q_group = {}
        for val in q:
            if ':' in val:
                k, v = val.split(':')
                if k not in q_group:
                    q_group[k] = []
                q_group[k].append(v)
            elif '--' in val:
                if len(val.split('--')) == 2:
                    q_group['cont_field_number'] = val.split('--') # 只有一組AND
            else:
                if 'fts' not in q_group:
                    q_group['fts'] = []
                val = val.replace('%20', ' ')
                q_group['fts'].append(val)

        #print(q, q_group, '----', flush=True)

        # 同term用OR, 不同用AND
        for k, vlist in q_group.items():
            if k == 'collector_id':
                stmt = stmt.where(Record.collector_id.in_(vlist))
            elif k == 'taxon_id':
                taxon_ids = []
                many_or = or_()
                for v in vlist:
                    if t := session.get(Taxon, v):
                        taxon_ids += [x.id for x in t.get_children()]
                        many_or = or_(many_or, Record.proxy_taxon_id.in_(taxon_ids))
                stmt = stmt.where(many_or)
            elif k == 'record_id':
                record_ids = [v for v in vlist]
                stmt = stmt.where(Record.id.in_(record_ids))
            elif k == 'cont_field_number':
                stmt = stmt.where(Record.field_number_int >= vlist[0], Record.field_number_int <= vlist[1])
            elif k == 'fts':
                many_or = or_()
                if mode == 'raw':
                    fields = [
                        'phylum_name',
                        'phylum_name_zh',
                        'class_name',
                        'class_name_zh',
                        'order_name',
                        'order_name_zh',
                        'family_name',
                        'family_name_zh',
                        'genus_name',
                        'genus_name_zh',
                        'species_name',
                        'species_name_zh',
                        'voucher_id',
                        'unit_id',
                        'note',
                        'document_id',
                        'collector',
                        'collector_zh',
                    ] # TODO: TAIBOL0211
                    for field in fields:
                        many_or = or_(many_or, Record.source_data[field].astext.ilike(f'%{val}%'))
                else:
                    for v in vlist:
                        hybrid_name_or = try_hybrid_name_stmt(v, Record.proxy_taxon_scientific_name)
                        if str(hybrid_name_or): # if not str, will casu Boolean value clause error
                            many_or = or_(many_or, hybrid_name_or)

                        many_or = or_(
                            many_or,
                            Unit.accession_number.ilike(f'{v}'),
                            Record.field_number.ilike(f'{v}'),
                            Person.full_name.ilike(f'%{v}%'),
                            Person.full_name_en.ilike(f'%{v}%'),
                            Record.proxy_taxon_scientific_name.ilike(f'%{v}%'),
                            Record.proxy_taxon_common_name.ilike(f'%{v}%')
                        )

                # both custom fields and normal filter many_or
                stmt = stmt.where(many_or)

    # find total
    base_stmt = stmt
    subquery = base_stmt.subquery()
    count_stmt = select(func.count()).select_from(subquery)
    total = session.execute(count_stmt).scalar()

    # order & limit
    if len(payload['filter']) > 0:
        stmt = stmt.order_by(Record.field_number_int)
    else:
        stmt = stmt.order_by(desc(Record.id))

    stmt = stmt.limit(payload['range'][1] - payload['range'][0])
    if payload['range'][0] > 0:
        stmt = stmt.offset(payload['range'][0])

    return stmt, total

def try_hybrid_name_stmt(q, field):

    def possible_x_multiplication(term: str) -> str:
        return [
            re.sub(r'(?<=\w)\s*x\s*(?=\w)', '×', term, flags=re.IGNORECASE),
            re.sub(r'(?<=\w)\s*x\s*(?=\w)', ' ×', term, flags=re.IGNORECASE),
            re.sub(r'(?<=\w)\s*x\s*(?=\w)', ' × ', term, flags=re.IGNORECASE),
            re.sub(r'(?<=\w)\s*x\s*(?=\w)', ' ×', term, flags=re.IGNORECASE)
        ]
    extra_try = []
    many_or = or_()
    # try taxon hybrid name
    if m := re.search(r'(?<=\w)\s*[xX]\s*(?=\w)', q):
        extra_try = possible_x_multiplication(q)
        print(extra_try, flush=True)
        for x in extra_try:
            many_or = or_(many_or, field.ilike(f'{x}%'))
        return many_or

    return None
