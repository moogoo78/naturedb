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
    NamedArea,
)
from app.models.taxon import (
    Taxon,
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
    if taxa_id := filtr.get('taxon_id'):
        if t := session.get(Taxon, taxa_id):
            taxa_ids = [x.id for x in t.get_children()]
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
            stmt = stmt.where(Record.field_number.ilike('%{}%'.format(value)))
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
    if value := filtr.get('named_area_id'):
        stmt = stmt.where(Record.named_areas.any(id=value))
    if value := filtr.get('country'):
        stmt = stmt.where(Record.named_areas.any(id=value).where(NamedArea.area_class_id==1))
    if value := filtr.get('locality_text'):
        stmt = stmt.where(Record.locality_text.ilike(f'%{value}%'))

    if value := filtr.get('altitude'):
        if '--' in value:
            vs = value.split('--')
            value1 = vs[0]
            value2 = vs[1]
        else:
            value1 = value

        if cond := filtr.get('altitude_condiction'):
            if cond == 'eq':
                stmt = stmt.where(Record.altitude==value1)
            elif cond == 'gte':
                stmt = stmt.where(Record.altitude>=value1)
            elif cond == 'lte':
                stmt = stmt.where(Record.altitude<=value1)
            elif cond == 'between' and value2:
                stmt = stmt.where(Record.altitude>=value1, Record.altitude2<=value2)
        else:
            stmt = stmt.where(Record.altitude==value1)

    # specimens
    if accession_number := filtr.get('accession_number'):
        if accession_number2 := filtr.get('accession_number2'):
            stmt = stmt.where(cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)>=int(value), cast(Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g'), BigInteger)<=int(value2), Unit.accession_number.regexp_replace('[^0-9]+', '', flags='g') != '')
        else:
            stmt = stmt.where(Unit.accession_number == accession_number)

    if value := filtr.get('type_status'):
        stmt = stmt.where(Unit.type_status==value)

    return stmt
