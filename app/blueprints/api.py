import json
import time
import re
import logging
import math
from datetime import datetime

from flask import (
    Blueprint,
    request,
    abort,
    jsonify,
)
from flask.views import MethodView
from sqlalchemy import (
    select,
    func,
    text,
    desc,
    cast,
    between,
    Integer,
    LargeBinary,
    extract,
    or_,
    inspect,
    join,
)
from sqlalchemy.dialects.postgresql import ARRAY

from app.database import session

from app.models.collection import (
    Record,
    Person,
    NamedArea,
    AreaClass,
    Unit,
    Identification,
    Person,
    AssertionTypeOption,
    Collection,
    #LogEntry,
    #get_structed_list,
)
from app.models.taxon import (
    Taxon,
    TaxonRelation,
)
from app.models.site import (
    Favorite,
)

api = Blueprint('api', __name__)

def make_query_response(query):
    start_time = time.time()

    rows = [x.to_dict() for x in query.limit(50).all()]
    end_time = time.time()
    elapsed = end_time - start_time

    result = {
        'data': rows,
        'total': len(rows),
        'query': str(query),
        'elapsed': elapsed,
    }
    # print(result, flush=True)
    return result

def record_filter(stmt, payload):
    filtr = payload['filter']
    if value := filtr.get('collection'):
        if c := Collection.query.filter(Collection.name==value).scalar():
            stmt = stmt.where(Record.collection_id==c.id)
    if accession_number := filtr.get('accession_number'):
        cn_list = [accession_number]

        if accession_number2 := filtr.get('accession_number2'):
            # TODO validate
            cn_int1 = int(accession_number)
            cn_int2 = int(calatog_number2)
            cn_list = [str(x) for x in range(cn_int1, cn_int2+1)]
            if len(cn_list) > 1000:
                cn_list = [] # TODO flash

        stmt = stmt.where(Unit.accession_number.in_(cn_list))
    if value := filtr.get('collector'):
        stmt = stmt.where(Record.collector_id==value[0])
    if value := filtr.get('field_number'):
        if value2 := filtr.get('field_number2'):
            # TODO validate
            int1 = int(value)
            int2 = int(value2)
            fn_list = [str(x) for x in range(int1, int2+1)]
            if len(fn_list) > 1000:
                fn_list = [] # TODO flash

            many_or = or_()
            for x in fn_list:
                many_or = or_(many_or, Record.field_number.ilike(f'{x}%'))
            stmt = stmt.where(many_or)
        else:
            stmt = stmt.where(Record.field_number.ilike('%{}%'.format(value)))
    if value := filtr.get('field_number_range'):
        if '-' in value:
            start, end = value.split('-')
            fn_list = [str(x) for x in range(int(start), int(end)+1)]
            if len(fn_list) > 1000:
                fn_list = [] # TODO flash

            many_or = or_()
            for x in fn_list:
                many_or = or_(many_or, Record.field_number == x)
            stmt = stmt.where(many_or)
        else:
            stmt = stmt.where(Record.field_number.ilike('%{}%'.format(value)))
    if value := filtr.get('collect_date'):
        if value2 := filtr.get('collect_date2'):
            stmt = stmt.where(Record.collect_date>=value, Record.collect_date<=value2)
        else:
            stmt = stmt.where(Record.collect_date==value)
    if value := filtr.get('collect_month'):
        stmt = stmt.where(extract('month', Record.collect_date) == value)
    # if scientific_name := filtr.get('scientific_name'): # TODO variable name
    #     if t := session.get(Taxon, scientific_name[0]):
    #         taxa_ids = [x.id for x in t.get_children()]
    #         stmt = stmt.where(Collection.proxy_taxon_id.in_(taxa_ids))
    # if taxa := filtr.get('species'):
    #     if t := session.get(Taxon, taxa[0]):
    #         taxa_ids = [x.id for x in t.get_children()]
    #         stmt = stmt.where(Collection.proxy_taxon_id.in_(taxa_ids))
    #         query_key_map['taxon'] = t.to_dict()
    # elif taxa := filtr.get('genus'):
    #     if t := session.get(Taxon, taxa[0]):
    #         taxa_ids = [x.id for x in t.get_children()]
    #         stmt = stmt.where(Collection.proxy_taxon_id.in_(taxa_ids))
    #         query_key_map['taxon'] = t.to_dict()
    # elif taxa := filtr.get('family'):
    #     if t := session.get(Taxon, taxa[0]):
    #         taxa_ids = [x.id for x in t.get_children()]
    #         stmt = stmt.where(Collection.proxy_taxon_id.in_(taxa_ids))
    #         query_key_map['taxon'] = t.to_dict()
    elif taxa_ids := filtr.get('taxon'):
        if t := session.get(Taxon, taxa_ids[0]):
            taxa_ids = [x.id for x in t.get_children()]
            stmt = stmt.where(Record.proxy_taxon_id.in_(taxa_ids))
    elif taxa_names := filtr.get('taxon_name'):
        taxa_name = taxa_names[0]
        stmt = stmt.where(Record.proxy_taxon_text.ilike(f'%{taxa_name}%'))

    if value := filtr.get('locality_text'):
        stmt = stmt.where(Record.locality_text.ilike(f'%{value}%'))
    if value := filtr.get(''):
        stmt = stmt.where(Record.named_areas.any(id=value[0]))
    if value := filtr.get('named_area'):
        stmt = stmt.where(Record.named_areas.any(id=value[0]))
    if value := filtr.get('country'):
        stmt = stmt.where(Record.named_areas.any(id=value[0]))
    if value := filtr.get('stateProvince'):
        stmt = stmt.where(Record.named_areas.any(id=value[0]))
        print(stmt, flush=True)
    if value := filtr.get('county'):
        stmt = stmt.where(Record.named_areas.any(id=value[0]))
    if value := filtr.get('locality'):
        stmt = stmt.where(Record.named_areas.any(id=value[0]))
    if value := filtr.get('national_park'):
        stmt = stmt.where(Record.named_areas.any(id=value[0]))
    if value := filtr.get('locality_text'):
        stmt = stmt.where(Record.locality_text.ilike(f'%{value}%'))
    if value := filtr.get('altitude'):
        value2 = filtr.get('altitude2')
        if cond := filtr.get('altitude_condiction'):
            if cond == 'eq':
                stmt = stmt.where(Record.altitude==value)
            elif cond == 'gte':
                stmt = stmt.where(Record.altitude>=value)
            elif cond == 'lte':
                stmt = stmt.where(Record.altitude<=value)
            elif cond == 'between' and value2:
                stmt = stmt.where(Record.altitude>=value, Record.altitude2<=value2)
        else:
            stmt = stmt.where(Record.altitude==value)

    if value := filtr.get('type_status'):
        stmt = stmt.where(Unit.type_status==value)
    if q := filtr.get('q'):
        term, value = q.split(':')
        if term == 'taxon_name':
            stmt = stmt.where(Record.proxy_taxon_scientific_name.ilike(f'%{value}%') | Record.proxy_taxon_common_name.ilike(f'%{value}%'))
        elif term in ['taxon_family_name', 'taxon_genus_name', 'taxon_species_name']:
            rank = term.split('_')[1]
            stmt_taxa = select(Taxon).where(Taxon.rank==rank).where(Taxon.full_scientific_name.ilike(f'%{value}%') | Taxon.common_name.ilike(f'%{value}%'))
            result = session.execute(stmt_taxa)
            ids = []
            for t in result.all():
                ids += [t[0].id] + [x.id for x in t[0].get_children()]

            if len(ids):
                stmt = stmt.where(Record.proxy_taxon_id.in_(ids))
            else:
                stmt = stmt.where(False)
        elif term == 'collector_name':
            #stmt_p = select(Person.id).where(Person.full_name.ilike(f'%{value}%') | Person.full_name_en.ilike(f'%{value}%'))
            stmt_p = select(Person.id).where(Person.sorting_name.ilike(f'%{value}%'))
            result = session.execute(stmt_p)
            ids = []
            for p in result.all():
                ids.append(p[0])
            if len(ids):
                stmt = stmt.where(Record.collector_id.in_(ids))
            else:
                stmt = stmt.where(False)
        elif term == 'field_number':
            stmt = stmt.where(Record.field_number.ilike(f'%{value}%'))
        elif term == 'collect_date':
            stmt = stmt.where(Record.collect_date==value)
        elif term == 'collect_date_month':
            stmt = stmt.where(extract('month', Record.collect_date) == value)
        elif term == 'collect_date_month':
            stmt = stmt.where(extract('month', Record.collect_date) == value)
        elif 'named_areas_' in term:
            na_list = term.split('_')
            na_name = '_'.join(na_list[2:])
            if ac := AreaClass.query.filter(AreaClass.name==na_name).first():
                stmt_na = select(NamedArea.id).where(NamedArea.name.ilike(f'%{value}%') | NamedArea.name_en.ilike(f'%{value}%')).where(NamedArea.area_class==ac)
                result = session.execute(stmt_na)
                many_or = or_()
                ids = [x[0] for x in result.all()]
                if len(ids):
                    for id_ in ids:
                        many_or = or_(many_or, Record.named_areas.any(id=id_))
                        stmt = stmt.where(many_or)
                else:
                    stmt = stmt.where(False)

        elif term == 'altitude':
            if '-' in value:
                alt_range = value.split('-')
                stmt = stmt.where(Record.altitude >= alt_range[0], Record.altitude2 <= alt_range[1] )
            else:
                stmt = stmt.where(Record.altitude == value)
        elif term == 'accession_number':
            stmt = stmt.where(Unit.accession_number.ilike(f'%{value}%'))


    return stmt

def allow_cors_preflight():
    response = make_response()
    response.headers.add("Access-Control-Allow-Origin", "*")
    response.headers.add('Access-Control-Allow-Headers', "*")
    response.headers.add('Access-Control-Allow-Methods', "*")
    return response

def allow_cors(data):
    resp = jsonify(data)
    resp.headers.add('Access-Control-Allow-Origin', '*')
    return resp


@api.route('/collections/<int:collection_id>', methods=['GET', 'PUT', 'DELETE', 'OPTIONS'])
def collection_item(collection_id):
    obj = session.get(Collection, collection_id)
    if not obj:
        return abort(404)

    if request.method == 'GET':
        data = obj.to_dict()
        return allow_cors({
            'data': data,
            'form': obj.get_form_layout()
        })

    elif request.method == 'OPTIONS':
        return allow_cors_preflight()

    elif request.method == 'PUT':
        changes = obj.update_from_json(request.json)
        log = LogEntry(
            model='Collection',
            item_id=collection_id,
            action='update',
            changes=changes)
        session.add(log)
        session.commit()

        return allow_cors(obj.to_dict())
    elif request.method == 'DELETE':
        session.delete(obj)
        session.commit()
        log = LogEntry(
            model='Collection',
            item_id=item.id,
            action='delete')
        session.add(log)
        session.commit()
        return allow_cors({})



@api.route('/searchbar', methods=['GET'])
def get_searchbar():
    '''for searchbar
    '''
    q = request.args.get('q')
    data = []
    if q.isdigit():
        # Field Number (with Collector)
        rows = Record.query.filter(Record.field_number.ilike(f'{q}%')).limit(10).all()
        for r in rows:
            item = {
                'field_number': r.field_number or '',
                'collector': r.collector.to_dict(with_meta=True) if r.collector else {},
            }
            item['meta'] = {
                'term': 'field_number_with_collector',
                'label': '採集號',
                'display': '{} {}'.format(r.collector.display_name if r.collector else '', r.field_number),
                'seperate': {
                    'field_number': {
                        'term': 'field_number',
                        'label': '採集號',
                        'display': r.field_number,
                    },
                },
            }
            data.append(item)

        # calalogNumber
        rows = Unit.query.filter(Unit.accession_number.ilike(f'{q}%')).limit(10).all()
        for r in rows:
            #unit = r.to_dict()
            unit = {
                'value': r.accession_number or '',
            }
            unit['meta'] = {
                'term': 'accession_number',
                'label': '館號',
                'display': r.accession_number
            }
            data.append(unit)
    elif '-' in q:
        # TODO
        m = re.search(r'([0-9]+)-([0-9]+)', q)
        if m:
            data.append({
                'field_number_range': q,
                'term': 'field_number_range',
            })
    else:
        # Collector
        rows = Person.query.filter(Person.full_name.ilike(f'%{q}%') | Person.full_name_en.ilike(f'%{q}%')).limit(10).all()
        for r in rows:
            collector = r.to_dict(with_meta=True)
            data.append(collector)

        # Taxon
        rows = Taxon.query.filter(Taxon.full_scientific_name.ilike(f'{q}%') | Taxon.common_name.ilike(f'%{q}%')).limit(10).all()
        for r in rows:
            taxon = r.to_dict(with_meta=True)
            data.append(taxon)

        # Location
        rows = NamedArea.query.filter(NamedArea.name.ilike(f'{q}%') | NamedArea.name_en.ilike(f'%{q}%')).limit(10).all()
        for r in rows:
            loc = r.to_dict(with_meta=True)
            data.append(loc)

    resp = jsonify({
        'data': data,
    })
    resp.headers.add('Access-Control-Allow-Origin', '*')
    resp.headers.add('Access-Control-Allow-Methods', '*')
    return resp


@api.route('/explore', methods=['GET'])
def get_explore():
    view = request.args.get('view', '')
    # group by collection
    #stmt = select(Collection, func.array_agg(Unit.id), func.array_agg(Unit.accession_number)).select_from(Unit).join(Collection, full=True).group_by(Collection.id) #where(Unit.id>40, Unit.id<50)
    # TODO: full outer join cause slow
    #stmt = select(Collection, func.array_agg(Unit.id), func.array_agg(Unit.accession_number)).select_from(Collection).join(Unit).group_by(Collection.id)

    # cast(func.nullif(Collection.field_number, 0), Integer)
    #unit_collection_join = join(Unit, Collection, Unit.collection_id==Collection.id)
    #collection_person_join = join(Collection, Person, Collection.collector_id==Person.id)
    #orig stmt = select(Unit.id, Unit.accession_number, Collection, Person.full_name).join(Collection, Collection.id==Unit.collection_id).join(Person, Collection.collector_id==Person.id)
    stmt = select(Unit, Record) \
    .join(Unit, Unit.record_id==Record.id) \
    .join(Person, Record.collector_id==Person.id)

    stmt = stmt.where(Unit.pub_status=='P')

    # 不要顯示沒有館號 (unit) 的資料
    # .join(Unit, Unit.record_id==Record.id, isouter=True) \


    #res = session.execute(stmt)
    #.select_from(cp_join)
    #print(f'!!default stmt: \n{stmt}\n-----------------', flush=True)
    total = request.args.get('total', None)

    payload = {
        'filter': json.loads(request.args.get('filter')) if request.args.get('filter') else {},
        'sort': json.loads(request.args.get('sort')) if request.args.get('sort') else {},
        'range': json.loads(request.args.get('range')) if request.args.get('range') else [0, 20],
    }
    # query_key_map = {}
    # print(payload, flush=True)
    stmt = record_filter(stmt, payload)
    # logging.debug(stmt)

    base_stmt = stmt
    # print(payload['filter'], flush=True)
    # sort
    if view == 'checklist':
        stmt = stmt.order_by(Record.proxy_taxon_scientific_name)
    elif view != 'map':
        if sort := payload['sort']:
            if 'collect_date' in sort:
                if sort['collect_date'] == 'desc':
                    stmt = stmt.order_by(desc(Record.collect_date))
                else:
                    stmt = stmt.order_by(Record.collect_date)
            elif 'field_number' in sort:
                if sort['field_number'] == 'desc':
                    stmt = stmt.order_by(Person.full_name, desc(cast(Record.field_number, LargeBinary)))
                else:
                    stmt = stmt.order_by(Person.full_name, cast(Record.field_number, LargeBinary))
            elif 'accession_number' in sort:
                stmt = stmt.order_by(Unit.accession_number)
            #elif 'taxon' in sort:
            #    stmt = stmt.order_by(Collection.proxy_taxon_scientific_name)
            #elif 'created' in sort:
            #    stmt = stmt.order_by(Collection.created)
        else:
            # default order
            stmt = stmt.order_by(Person.full_name, cast(Record.field_number, LargeBinary)) # TODO ulitilize Person.sorting_name
        #print(stmt, flush=True)

    # limit & offset
    if view != 'checklist':
        start = int(payload['range'][0])
        end = int(payload['range'][1])
        limit = min((end-start), 1000) # TODO: max query range
        stmt = stmt.limit(limit)
        if start > 0:
            stmt = stmt.offset(start)

    # group by
    #if view == 'checklist':
    #    stmt = stmt.group_by(Collection.proxy_taxon_id)

    # =======
    # results
    # =======
    begin_time = time.time()
    result = session.execute(stmt)
    elapsed = time.time() - begin_time

    # -----------
    # count total
    # -----------
    elapsed_count = None
    if total is None:
        begin_time = time.time()
        subquery = base_stmt.subquery()
        count_stmt = select(func.count()).select_from(subquery)
        total = session.execute(count_stmt).scalar()
        elapsed_count = time.time() - begin_time

    # --------------
    # result mapping
    # --------------
    data = []
    begin_time = time.time()
    elapsed_mapping = None

    rank_list = [{}, {}, {}] # family, genus, species
    rank_map = {'family': 0, 'genus': 1, 'species': 2}
    is_truncated = False
    TRUNCATE_LIMIT = 2000
    if view == 'checklist' and total > TRUNCATE_LIMIT: #  TODO
        is_truncated = True

    rows = result.all()
    if is_truncated is True:
        rows = rows[0:TRUNCATE_LIMIT] # TODO

    for r in rows:
        unit = r[0]
        if record := r[1]:
            t = None
            if taxon_id := record.proxy_taxon_id:
                t = session.get(Taxon, taxon_id)

            if view == 'map':
                if record.longitude_decimal and record.latitude_decimal:
                    data.append({
                        'accession_number': unit.accession_number if unit else '',
                        'collector': record.collector.to_dict() if record.collector else '',
                        'field_number': record.field_number,
                        'collect_date': record.collect_date.strftime('%Y-%m-%d') if record.collect_date else '',
                        'taxon': f'{record.proxy_taxon_scientific_name} ({record.proxy_taxon_common_name})',
                        'longitude_decimal': record.longitude_decimal,
                        'latitude_decimal': record.latitude_decimal,
                    })
            elif view == 'checklist':
                if record.proxy_taxon_id:
                    # taxon = session.get(Taxon, record.proxy_taxon_id)
                    # parents = taxon.get_parents()
                    tr_list = TaxonRelation.query.filter(TaxonRelation.child_id==record.proxy_taxon_id).order_by(TaxonRelation.depth).all()
                    tlist = [r.parent for r in tr_list]
                    for index, t in enumerate(tlist):
                        map_idx = rank_map[t.rank]
                        parent_id = 0
                        if index < len(tlist) - 1:
                            parent_id = tlist[index+1].id
                        if t.id not in rank_list[map_idx]:
                            rank_list[map_idx][t.id] = {
                                'obj': t.to_dict(),
                                'parent_id': parent_id,
                                'count': 1,
                                'children': [],
                            }
                        else:
                            rank_list[map_idx][t.id]['count'] += 1
            else:
                image_url = ''
                try:
                    accession_number_int = int(unit.accession_number)
                    instance_id = f'{accession_number_int:06}'
                    first_3 = instance_id[0:3]
                    image_url = f'https://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{instance_id}_s.jpg'
                except:
                    pass

                data.append({
                    'unit_id': unit.id if unit else '',
                    'collection_id': record.id,
                    'record_key': f'u{unit.id}' if unit else f'c{record.id}',
                    # 'accession_number': unit.accession_number if unit else '',
                    'accession_number': unit.accession_number if unit else '',
                    'image_url': image_url,
                    'field_number': record.field_number,
                    'collector': record.collector.to_dict() if record.collector else '',
                    'collect_date': record.collect_date.strftime('%Y-%m-%d') if record.collect_date else '',
                    'taxon_text': f'{record.proxy_taxon_scientific_name} ({record.proxy_taxon_common_name})',
                    'taxon': t.to_dict() if t else {},
                    'named_areas': [x.to_dict() for x in record.named_areas],
                    'locality_text': record.locality_text,
                    'altitude': record.altitude,
                    'altitude2': record.altitude2,
                    'longitude_decimal': record.longitude_decimal,
                    'latitude_decimal': record.latitude_decimal,
                    'type_status': unit.type_status if unit and unit.type_status else '',
                })

    elapsed_mapping = time.time() - begin_time

    # update data while view = checklist
    if view == 'checklist':
        flat_list = []
        tree = {'id':0, 'children':[]}
        taxon_list = {
            0: tree,
        }
        # sort
        for rank_dict in rank_list:
            for _, node in rank_dict.items():
                flat_list.append(node)

        # make tree
        for x in flat_list:
            taxon_list[x['obj']['id']] = x
            taxon_list[x['parent_id']]['children'].append(taxon_list[x['obj']['id']])

        data = tree['children']

    resp = jsonify({
        'data': data,
        # 'key_map': query_key_map,
        'is_truncated': is_truncated,
        'total': total,
        'elapsed': elapsed,
        'elapsed_count': elapsed_count,
        'elapsed_mapping': elapsed_mapping,
        'debug': {
            'query': str(stmt),
            'payload': payload,
        }
    })
    resp.headers.add('Access-Control-Allow-Origin', '*')
    resp.headers.add('Access-Control-Allow-Methods', '*')
    return resp


@api.route('/collections', methods=['GET', 'POST', 'OPTIONS'])
def collection():
    if request.method == 'GET':
        # group by collection
        #stmt = select(Collection, func.array_agg(Unit.id), func.array_agg(Unit.accession_number)).select_from(Unit).join(Collection, full=True).group_by(Collection.id) #where(Unit.id>40, Unit.id<50)
        # TODO: full outer join cause slow
        #stmt = select(Collection, func.array_agg(Unit.id), func.array_agg(Unit.accession_number)).select_from(Collection).join(Unit).group_by(Collection.id)

        # stmt = select(Collection)
        stmt = select(Unit.id, Unit.accession_number, Collection, Person.full_name) \
            .join(Unit, Unit.collection_id==Collection.id, isouter=True) \
            .join(Person, Collection.collector_id==Person.id)

        total = request.args.get('total', None)
        payload = {
            'filter': json.loads(request.args.get('filter')) if request.args.get('filter') else {},
            'sort': json.loads(request.args.get('sort')) if request.args.get('sort') else {},
            'range': json.loads(request.args.get('range')) if request.args.get('range') else [0, 20],
        }

        base_stmt = record_filter(stmt, payload)

        # =======
        # results
        # =======
        begin_time = time.time()
        result = session.execute(stmt)
        elapsed = time.time() - begin_time

        # -----------
        # count total
        # -----------
        elapsed_count = None
        if total is None:
            begin_time = time.time()
            subquery = base_stmt.subquery()
            count_stmt = select(func.count()).select_from(subquery)
            total = session.execute(count_stmt).scalar()
            elapsed_count = time.time() - begin_time

        # --------------
        # result mapping
        # --------------
        data = []
        begin_time = time.time()
        elapsed_mapping = None

        rows = result.all()
        for r in rows:
            if c := r[2]:
                units = []
                for u in c.units:
                    unit = {
                        'id': u.id,
                        'accession_number': u.accession_number,
                    }
                    image_url = ''
                    # TODO
                    try:
                        accession_number_int = int(u.accession_number)
                        instance_id = f'{accession_number_int:06}'
                        first_3 = instance_id[0:3]
                        image_url = f'https://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{instance_id}_s.jpg'
                    except:
                        pass

                    if image_url:
                        unit['image_url'] = image_url

                    units.append(unit)

                data.append({
                    'id': c.id,
                    'field_number': c.field_number,
                    'collector': c.collector.to_dict() if c.collector else '',
                    'collect_date': c.collect_date.strftime('%Y-%m-%d') if c.collect_date else '',
                    'taxon': c.proxy_taxon_text,
                    'units': units,
                    'named_areas': [x.to_dict() for x in c.named_areas],
                })
            else:
                print(r, flush=True)
        elapsed_mapping = time.time() - begin_time

        resp = jsonify({
            'data': data,
            'total': total,
            'elapsed': elapsed,
            'elapsed_count': elapsed_count,
            'elapsed_mapping': elapsed_mapping,
            'debug': {
                'query': str(stmt),
                'payload': payload,
            }
        })
        resp.headers.add('Access-Control-Allow-Origin', '*')
        resp.headers.add('Access-Control-Allow-Methods', '*')
        return resp

    elif request.method == 'OPTIONS':
        return allow_cors_preflight()

    elif request.method == 'POST':
        collection = Collection()
        changes = collection.update_from_json(request.json)
        session.add(collection)
        session.commit()
        log = LogEntry(
            model='Collection',
            item_id=collection.id,
            action='insert',
            changes=changes)
        session.add(log)
        session.commit()

        return allow_cors(collection.to_dict())

@api.route('/people/<int:id>', methods=['GET'])
def get_person_detail(id):
    obj = session.get(Person, id)
    return jsonify(obj.to_dict(with_meta=True))

@api.route('/people', methods=['GET'])
def get_person_list():
    #query = Person.query.select_from(Collection).join(Collection.people)
    query = Person.query.select_from(Collection)
    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        collector_id = None
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
            # query = query.filter(Person.full_name.ilike(like_key) | Person.atomized_name['en']['given_name'].astext.ilike(like_key) | Person.atomized_name['en']['inherited_name'].astext.ilike(like_key))
            #query = query.filter(Person.full_name.ilike(like_key) | Person.full_name_en.ilike(like_key))
            query = query.filter(Person.sorting_name.ilike(like_key))
        if is_collector := filter_dict.get('is_collector', ''):
            query = query.filter(Person.is_collector==True)
        if is_identifier := filter_dict.get('is_identifier', ''):
            query = query.filter(Person.is_identifier==True)

        #if x := filter_dict.get('collector_id', ''):
        #    collector_id = x
        if x := filter_dict.get('id', ''):
            query = query.filter(Person.id.in_(x))
        if collection_id := filter_dict.get('collection_id', ''):
            query = query.filter(Collection.id==collection_id)
    #print(query, flush=True)
    return jsonify(make_query_response(query))

@api.route('/taxa/<int:id>', methods=['GET'])
def get_taxa(id):
    obj = session.get(Taxon, id)
    return jsonify(obj.to_dict(with_meta=True))

@api.route('/named_areas/<int:id>', methods=['GET'])
def get_named_area_detail(id):
    obj = session.get(NamedArea, id)
    return jsonify(obj.to_dict(with_meta=True))

@api.route('/named_areas', methods=['GET'])
def get_named_area_list():
    query = NamedArea.query

    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
            query = query.filter(NamedArea.name.ilike(like_key) | NamedArea.name_en.ilike(like_key))
        if ids := filter_dict.get('id', ''):
            query = query.filter(NamedArea.id.in_(ids))
        if area_class_id := filter_dict.get('area_class_id', ''):
            query = query.filter(NamedArea.area_class_id==area_class_id)
        if parent_id := filter_dict.get('parent_id'):
            query = query.filter(NamedArea.parent_id==parent_id)

    return jsonify(make_query_response(query))

@api.route('/assertion_type_options', methods=['GET'])
def get_assertion_type_option_list():
    query = AssertionTypeOption.query

    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
            query = query.filter(AssertionTypeOption.value.ilike(like_key))
        #if ids := filter_dict.get('id', ''):
        #    query = query.filter(AssertionTypeOption.id.in_(ids))
        if type_id := filter_dict.get('type_id', ''):
            query = query.filter(AssertionTypeOption.assertion_type_id==type_id)

    return jsonify(make_query_response(query))

@api.route('/taxa', methods=['GET'])
def get_taxon_list():
    query = Taxon.query
    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
            query = query.filter(Taxon.full_scientific_name.ilike(like_key) | Taxon.common_name.ilike(like_key))
        if ids := filter_dict.get('id', ''):
            query = query.filter(Taxon.id.in_(ids))
        if rank := filter_dict.get('rank'):
            query = query.filter(Taxon.rank==rank)
        if pid := filter_dict.get('parent_id'):
            if parent := session.get(Taxon, pid):
                depth = Taxon.RANK_HIERARCHY.index(parent.rank)
                taxa_ids = [x.id for x in parent.get_children(depth)]
                query = query.filter(Taxon.id.in_(taxa_ids))

    return jsonify(make_query_response(query))


@api.route('/favorites', methods=['GET', 'POST'])
def favorite():
    if request.method == 'GET':
        pass
    elif request.method == 'POST':
        data = request.json
        action = ''
        if fav := Favorite.query.filter(Favorite.user_id == data['uid'], Favorite.record == data['entity_id']).scalar():
            action = 'remove'
            session.delete(fav)
            session.commit()
        else:
            fav = Favorite(user_id=data['uid'], record=data['entity_id'])
            session.add(fav)
            action = 'add'

        session.commit()

        return jsonify({'action': action, 'entity_id': data['entity_id']})

    return abort(404)

@api.route('/occurrence', methods=['GET'])
def occurrence():
    # required
    startCreated = request.args.get('startCreated', '')
    endCreated = request.args.get('endCreated', '')
    startModified = request.args.get('startModified', '')
    endModified = request.args.get('endModified', '')
    selfProduced = request.args.get('selfProduced', '')
    limit = request.args.get('limit', 300)
    offset = request.args.get('offset', 0)

    limit = int(limit)
    offset = int(offset)

    # optional
    collectionId= request.args.get('collectionId')
    occurrenceId= request.args.get('occurrenceId')

    stmt = select(
        Unit.id,
        Unit.accession_number,
        Unit.type_status,
        Unit.created,
        Unit.updated,
        Record.field_number,
        Record.collect_date,
        Person.full_name,
        Person.full_name_en,
        Record.longitude_decimal,
        Record.latitude_decimal,
        Record,
        Record.locality_text,
        Record.locality_text_en,
        Unit.kind_of_unit,
        Collection.label,
        Taxon.full_scientific_name,
        Taxon.common_name,
        Taxon.rank,
        #func.string_agg(NamedArea.name, ', ')
    ) \
    .join(Record, Unit.record_id==Record.id) \
    .join(Person, Record.collector_id==Person.id) \
    .join(Collection, Record.collection_id==Collection.id) \
    .join(Taxon, Record.proxy_taxon_id==Taxon.id)
    #.join(NamedArea, Record.named_areas) \
    #.group_by(Unit.id, Record.id, Person.id, Collection.id, Taxon.id)

    # join named_area cause slow query

    #print(stmt, flush=True)
    #stmt2 = select(Unit.id, Record.id, Record.field_number, func.string_agg(NamedArea.name, ' | ')).join(NamedArea, Record.named_areas).group_by(Unit.id, Record.id).limit(20)
    #print(stmt2, flush=True)
    #r2 = session.execute(stmt2)
    #print(r2.all(), flush=True)

    try:
        if startCreated:
            dt = datetime.strptime(startCreated, '%Y%m%d')
            stmt = stmt.where(Unit.created >= dt)
        if endCreated:
            dt = datetime.strptime(endCreated, '%Y%m%d')
            stmt = stmt.where(Unit.created <= dt)
        if startModified:
            dt = datetime.strptime(startModified, '%Y%m%d')
            stmt = stmt.where(Unit.updated >= dt)
        if endModified:
            dt = datetime.strptime(endModified, '%Y%m%d')
            stmt = stmt.where(Unit.updated <= dt)
    except:
        return abort(400)

    # count total
    subquery = stmt.subquery()
    count_stmt = select(func.count()).select_from(subquery)
    total = session.execute(count_stmt).scalar()

    stmt = stmt.order_by(desc(Unit.created)).limit(limit).offset(offset)
    #print(stmt, flush=True)
    results = session.execute(stmt)

    rows = []
    for r in results.all():
        #print(r[19], flush=True)

        collector = ''
        if r[7] and r[8]:
            collector = f'{r[8]} ({r[7]})'
        elif r[7] and not r[8]:
            collector = r[7]
        elif r[8] and not r[7]:
            collector = r[8]

        na_list = []
        if record := r[11]:
            if named_areas := record.get_sorted_named_area_list():
                na_list = [x.display_name for x in named_areas]
        if x:= record.locality_text:
            na_list.append(x)
        if x:= record.locality_text_en:
            na_list.append(x)

        kind_of_unit = ''
        if x := Unit.KIND_OF_UNIT_MAP.get(r[14]):
            kind_of_unit = x

        row = {
            'occurrenceID': r[0],
            'collectionID': r[1],
            'scientificName': r[16] or '',
            'isPreferredName': r[17] or '',
            'taxonRank': r[18] or '',
            'typeStatus': r[2] or '',
            'eventDate': r[6].strftime('%Y%m%d') if r[6] else '',
            'verbatimCoordinateSystem':'DecimalDegrees',
            'verbatimSRS': 'EPSG:4326',
            #'coordinateUncertaintyInMeters': '',
            'dataGeneralizations': False,
            #'coordinatePrecision':
            'locality': ', '.join(na_list),
            'organismQuantity': 1,
            'organismQuantityType': '份',
	    'recordedBy': collector,
            'recordNumber':r[5] or '',
            #'taxonID': '',
            #'scientificNameID''
            'preservation': kind_of_unit,
            'datasetName': r[15],
            'resourceContacts': '鍾國芳、劉翠雅',
            'references': f'{request.scheme}:/{request.host}/specimens/{r[15]}:{r[1]}' if r[1] else '',
            'license': 'CC BY NC 4.0+', #'https://creativecommons.org/licenses/by-nc/4.0/legalcode',
            'mediaLicense': 'CC BY NC 4.0+', #'https://creativecommons.org/licenses/by-nc/4.0/legalcode',
            #'sensitiveCategory':
            'created': r[3].strftime('%Y%m%d'), #unit.created.strftime('%Y%m%d') if unit.created else '',
            'modified': r[4].strftime('%Y%m%d'), #unit.updated.strftime('%Y%m%d') if unit.updated else '',
        }
        if r[9]:
            row['verbatimLongitude'] = float(r[9])
        if r[10]:
            row['verbatimLatitude'] = float(r[10])

        '''
        unit = session.get(Unit, r[0])

        row = {
            'occurrenceID': r[0],
            'collectionID': unit.accession_number or '',
            'scientificName': '',
            'isPreferredName': '',
            'taxonRank': '',
            'typeStatus': unit.type_status or '',
            'eventDate': '',
            'verbatimLongitude': '',
            'verbatimLatitude': '',
            'verbatimCoordinateSystem':'DecimalDegrees',
            'verbatimSRS': 'EPSG:4326',
            #'coordinateUncertaintyInMeters': '',
            'dataGeneralizations': False,
            #'coordinatePrecision':
            'locality': '',
            'organismQuantity': 1,
            'organismQuantityType': '份',
	    'recordedBy': '',
            'recordNumber':'',
            #'taxonID': '',
            #'scientificNameID''
            'preservation': unit.display_kind_of_unit(),
            'datasetName': '',
            'resourceContacts': '鍾國芳、劉翠雅',
            'references': f'{request.scheme}:/{request.host}{unit.specimen_url}',
            'license': 'CC BY NC 4.0+', #'https://creativecommons.org/licenses/by-nc/4.0/legalcode',
            'mediaLicense': 'CC BY NC 4.0+', #'https://creativecommons.org/licenses/by-nc/4.0/legalcode',
            #'sensitiveCategory':
            'created': unit.created.strftime('%Y%m%d') if unit.created else '',
            'modified': unit.updated.strftime('%Y%m%d') if unit.updated else '',
        }

        if x := unit.get_image('_m'):
            row['associatedMedia'] = x

        if record := unit.record:
            if collect_date := record.collect_date:
                row['eventDate'] = collect_date.strftime('%Y%m%d')
            row['recordNumber'] = record.field_number
            row['datasetName'] = record.collection.label

            if x := record.longitude_decimal:
                row['verbatimLongitude'] = float(x)
            if x := record.latitude_decimal:
                row['verbatimLatitude'] = float(x)

            if collector := record.collector:
                row['recordedBy'] = collector.display_name

            if named_areas := record.get_sorted_named_area_list():
                na_list = [x.display_name for x in named_areas]
                if x:= record.locality_text:
                    na_list.append(x)
                if x:= record.locality_text_en:
                    na_list.append(x)
                row['locality'] = ', '.join(na_list)

            if last_id := record.last_identification:
                if taxon := last_id.taxon:
                    row['scientificName'] = taxon.full_scientific_name
                    row['isPreferredName'] = taxon.common_name
                    row['taxonRank'] = taxon.rank
        '''
        rows.append(row)


    results = {
        'data': rows,
        'messages': [
            '經緯度可能會有誤差，也有可能不一定是 WGS84',
            '授權需確認',
            'resourceContacts 需確認',
        ],
        'meta': {
            'total': total,
        }
    }

    # pagination
    if offset < total:
        num_pages = math.ceil(total / limit)
        page = math.floor( offset / limit ) + 1
    else:
        num_pages = 0
        page = 0

    results['meta']['pagination'] = {
        'num_pages': num_pages,
        'page': page,
        'num_per_page': limit,
    }

    return jsonify(results)
