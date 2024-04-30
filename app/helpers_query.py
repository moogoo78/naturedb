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
from app.database import session

from app.models.collection import (
    Record,
    Unit,
    Person,
    RecordNamedAreaMap,
)
from app.models.taxon import (
    Taxon,
)
from app.models.gazetter import (
    Country,
    NamedArea,
)

def make_specimen_query(filtr):

    # TODO：
    # 處理異體字: 台/臺
    # basic stmt
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
