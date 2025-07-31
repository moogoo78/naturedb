import json
import time
import re
import logging
import math
from datetime import datetime

from flask import (
    Blueprint,
    request,
    Response,
    abort,
    jsonify,
    redirect,
    url_for,
    current_app,
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
    BigInteger,
    LargeBinary,
    extract,
    or_,
    inspect,
    join,
)
from sqlalchemy.dialects.postgresql import ARRAY
from geoalchemy2.functions import (
    ST_Point,
    ST_SetSRID,
    ST_Within,
)

from app.database import session
from app.models.site import (
    User,
    Site,
)
from app.models.collection import (
    Record,
    Person,
    Unit,
    Identification,
    Person,
    AssertionTypeOption,
    AssertionType,
    Collection,
    MultimediaObject,
)
from app.models.gazetter import (
    NamedArea,
    AreaClass,
    Country,
)
from app.models.taxon import (
    Taxon,
    TaxonRelation,
)

from app.helpers_query import (
    make_specimen_query,
)

api = Blueprint('api', __name__)

def make_query_response(query):
    start_time = time.time()

    rows = [x.to_dict() for x in query.all()]
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

@api.after_request
def after_request(resp):
    # make cors
    resp.headers.add('Access-Control-Allow-Origin', '*')
    resp.headers.add('Access-Control-Allow-Methods', '*')
    return resp

def get_searchbar():
    q = request.args.get('q')

    categories = {
        'taxa': [],
        #'named_area': [],
        'collectors': [],
        #'accession_number': [],
        #'field_number': [],
    }

    category_limit = 10
    if len(q) <= 3:
        # sorting starts from inhereted name in english
        rows = Person.query.filter(Person.full_name.ilike(f'{q}%') | Person.full_name_en.ilike(f'{q}%') | Person.sorting_name.ilike(f'{q}%')).limit(category_limit).all()
    else:
        rows = Person.query.filter(Person.full_name.ilike(f'%{q}%') | Person.full_name_en.ilike(f'%{q}%') | Person.sorting_name.ilike(f'{q}%')).limit(5).all()

    for r in rows:
        categories['collectors'].append(r.to_dict())

    rows = Taxon.query.filter(Taxon.full_scientific_name.ilike(f'{q}%') | Taxon.common_name.ilike(f'%{q}%')).limit(category_limit).all()
    for r in rows:
        categories['taxa'].append(r.to_dict())

    #rows = NamedArea.query.filter(NamedArea.name.ilike(f'{q}%') | NamedArea.name_en.ilike(f'%{q}%')).limit(5).all()
    #for r in rows:
    #    categories['named_area'].append(r.to_dict())

    if q.isascii():
        rows = Record.query.filter(Record.field_number.ilike(f'%{q}%')).limit(category_limit).all()
        for r in rows:
            #categories['field_number'].append(r.gathering())
            #TODO
            pass

        rows = Unit.query.filter(Unit.accession_number.ilike(f'{q}%')).limit(category_limit).all()
        for r in rows:
            #categories['accession_number'].append(r.label_info)
            pass

    return jsonify(categories)


#@api.route('/search', methods=['GET'])
def get_search():
    view = request.args.get('VIEW', '')
    download = request.args.get('download', '')
    total = request.args.get('total', None)
    #print(download, '---') TODO
    payload = {
        'filter': json.loads(request.args.get('filter')) if request.args.get('filter') else {},
        'sort': json.loads(request.args.get('sort')) if request.args.get('sort') else {},
        'range': json.loads(request.args.get('range')) if request.args.get('range') else [0, 20],
    }

    useCustomFields = False

    stmt = make_specimen_query(payload['filter'])

    # strict collection
    available_collection_ids = []
    site_collection_ids = []
    if host := request.headers.get('Host'):
        site = Site.find_by_host(host)
        site_collection_ids = [x.id for x in site.collections]

    if filter_collection_id := payload['filter'].get('collection_id'):
        if isinstance(filter_collection_id, list):
            available_collection_ids = list(set(site_collection_ids) & set(filter_collection_id))
        elif int(filter_collection_id) in site_collection_ids:
            available_collection_ids = [filter_collection_id]
    else:
        available_collection_ids = site_collection_ids

    #stmt = stmt.where(Unit.collection_id.in_(available_collection_ids))
    stmt = stmt.where(Record.collection_id.in_(available_collection_ids))
    current_app.logger.debug(stmt)

    if sd := payload['filter'].get('customFields'):
        useCustomFields = True
        if sd.get('annotate'):
            if count_fields := sd['annotate'].get('values'):
                fields = [Record.source_data[x] for x in count_fields]
                stmt = stmt.group_by(*fields)

        if sd.get('count'):
            subquery = stmt.subquery()
            stmt = select(func.count()).select_from(subquery)
            data = session.execute(stmt).scalar()
        else:
            result= session.execute(stmt)
            data = [list(x) for x in result]

        if sd.get('annotate') or sd.get('count'):
            return jsonify({'data': data, 'debug_stmt': str(stmt)})

    base_stmt = stmt

    ## sort
    if len(payload['sort']):
        for sort in payload['sort']:
            if sort in ['field_number', '-field_number']:
                if sort == '-field_number':
                    stmt = stmt.order_by(Person.sorting_name, desc(Record.field_number_int))
                else:
                    stmt = stmt.order_by(Person.sorting_name, Record.field_number_int)
            elif sort in ['accession_number', '-accession_number']:
                if sort == '-accession_number':
                    stmt = stmt.order_by(desc(func.length(Unit.accession_number)), desc(Unit.accession_number))
                else:
                    stmt = stmt.order_by(func.length(Unit.accession_number), Unit.accession_number)
            elif sort in ['collector', '-collector']:
                # same as field_number
                if sort == '-collector':
                    stmt = stmt.order_by(Person.sorting_name, desc(Record.field_number_int))
                else:
                    stmt = stmt.order_by(Person.sorting_name, Record.field_number_int)
            else:
                if sort[0] == '-':
                    stmt = stmt.order_by(desc(sort[1:]))
                else:
                    stmt = stmt.order_by(sort)
    else:
        stmt = stmt.order_by(desc(Unit.id))

    ## range
    start = int(payload['range'][0])
    end = int(payload['range'][1])

    if view == 'map':
        end = 2000 # TODO

    if start == 0 and end == -1:
        pass # no limit
    else:
        limit = min((end-start), 2000) # TODO: max query range
        stmt = stmt.limit(limit)
        if start > 0:
            stmt = stmt.offset(start)


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

        if payload['filter'].get('count'):
            return jsonify({'count': total})

        elapsed_count = time.time() - begin_time

    # --------------
    # result mapping
    # --------------
    data = []
    begin_time = time.time()
    elapsed_mapping = None

    rows = result.all()
    for r in rows:
        unit = r[0]
        if record := r[1]:
            t = None
            if taxon_id := record.proxy_taxon_id:
                t = session.get(Taxon, taxon_id)

            image_url = ''
            try:
                #accession_number_int = int(unit.accession_number)
                #instance_id = f'{accession_number_int:06}'
                #first_3 = instance_id[0:3]
                #image_url = f'https://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{instance_id}_s.jpg'
                image_url = unit.get_cover_image()
            except:
                pass

            taxon_text = record.proxy_taxon_scientific_name
            if record.proxy_taxon_common_name:
                taxon_text = f'{record.proxy_taxon_scientific_name} ({record.proxy_taxon_common_name})'

            named_areas = []
            for k, v in record.get_named_area_map().items():
                named_areas.append(v.named_area.to_dict())

            if not view or view == 'table':
                d = {
                    'unit_id': unit.id if unit else '',
                    'record_id': record.id,
                    'record_key': f'u{unit.id}' if unit else f'c{record.id}',
                    # 'accession_number': unit.accession_number if unit else '',
                    'accession_number': unit.accession_number if unit else '',
                    'image_url': image_url,
                    'field_number': record.field_number,
                    'collector': record.collector.to_dict() if record.collector else '',
                    'collect_date': record.collect_date.strftime('%Y-%m-%d') if record.collect_date else '',
                    'taxon': t.to_dict() if t else {},
                    'named_areas': named_areas,
                    'locality_text': record.locality_text,
                    'altitude': record.altitude,
                    'altitude2': record.altitude2,
                    'longitude_decimal': record.longitude_decimal,
                    'latitude_decimal': record.latitude_decimal,
                    'type_status': unit.type_status if unit and (unit.type_status and unit.pub_status=='P' and unit.type_is_published is True) else '',

                }

                d['link'] = unit.get_link()

                if useCustomFields:
                    d['source_data'] = record.source_data

                data.append(d)

            elif view == 'map':
                if record.longitude_decimal and record.latitude_decimal:
                    data.append({
                        'accession_number': unit.accession_number if unit else '',
                        'image_url': image_url,
                        'field_number': record.field_number,
                        'collector': record.collector.to_dict() if record.collector else '',
                        'collect_date': record.collect_date.strftime('%Y-%m-%d') if record.collect_date else '',
                        'taxon_text': taxon_text,
                        'longitude_decimal': record.longitude_decimal,
                        'latitude_decimal': record.latitude_decimal,
                    })

    elapsed_mapping = time.time() - begin_time

    resp = jsonify({
        'data': data,
        #'is_truncated': is_truncated,
        #'filter_tokens': filter_tokens,
        'total': total,
        'elapsed': elapsed,
        'debug': {
            'query': str(stmt),
            'elapsed_count': elapsed_count,
            'elapsed_mapping': elapsed_mapping,
            #'payload': payload,
        }
    })

    return resp


#@api.route('/people/<int:id>', methods=['GET'])
def get_person_detail(id):
    obj = session.get(Person, id)
    return jsonify(obj.to_dict(with_meta=True))

#@api.route('/people', methods=['GET'])
def get_person_list():
    #query = Person.query.select_from(Collection).join(Collection)
    query = Person.query
    #print(query, flush=True)
    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        collector_id = None
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
            # query = query.filter(Person.full_name.ilike(like_key) | Person.atomized_name['en']['given_name'].astext.ilike(like_key) | Person.atomized_name['en']['inherited_name'].astext.ilike(like_key))
            query = query.filter(Person.full_name.ilike(like_key) | Person.full_name_en.ilike(like_key))
            #query = query.filter(Person.sorting_name.ilike(like_key))
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

    if sort_str := request.args.get('sort'):
        sort_dict = json.loads(sort_str)
        for i in sort_dict:
            if 'sorting_name' in i:
                if i['sorting_name'] == 'desc':
                    query = query.order_by(desc('sorting_name'))
                else:
                    query = query.order_by('sorting_name')

    #print(query, flush=True)
    return jsonify(make_query_response(query))


#@api.route('/named_areas/<int:id>', methods=['GET'])
def get_named_area_detail(id):
    if obj := session.get(NamedArea, id):
        na = obj.to_dict()
        if request.args.get('options'):
            na['higher_area_classes'] = [{
                'id': x.id,
                'name': x.name,
                'area_class_id': x.area_class_id,
                'area_class_name': x.area_class.name,
            } for x in obj.get_parents()]

            # parent options
            na['options'] = {}
            # ignore highest
            for i, value in enumerate(na['higher_area_classes']):
                na_list = NamedArea.query.filter(NamedArea.parent_id==value['id']).all()
                if i < len(na['higher_area_classes']) - 1:
                    opt_idx = na['higher_area_classes'][i+1]['area_class_id']
                    na['options'][str(opt_idx)] = [{'id': x.id, 'display_name': x.display_name} for x in na_list]

            na['options'][str(obj.area_class_id)] = [{'id': x.id, 'display_name': x.display_name} for x in NamedArea.query.filter(NamedArea.parent_id==obj.parent_id).all()]
            na['options'][str(obj.area_class_id+1)] = [{'id': x.id, 'display_name': x.display_name} for x in NamedArea.query.filter(NamedArea.parent_id==obj.id).all()]
        if request.args.get('parents'):
            na['higher_area_classes'] = [{
                'id': x.id,
                'name': x.name,
                'name_en': x.name_en,
                'display_text': x.display_text,
                'area_class_id': x.area_class_id,
                'area_class_name': x.area_class.name,
            } for x in obj.get_parents()]
    return jsonify(na)


#@api.route('/named_areas', methods=['GET'])
def get_named_area_list():
    query = NamedArea.query.join(AreaClass)
    named_area_ids = []
    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
            query = query.filter(NamedArea.name.ilike(like_key) | NamedArea.name_en.ilike(like_key))
        if value := filter_dict.get('continent', ''):
            named_area_ids += Country.get_named_area_ids_from_continent(value.capitalize())
        if ids := filter_dict.get('id', ''):
            named_area_ids += ids
        if x := filter_dict.get('area_class_id', ''):
            if isinstance(x, list):
                query = query.filter(NamedArea.area_class_id.in_(x))
            else:
                query = query.filter(NamedArea.area_class_id==x)
        if parent_id := filter_dict.get('parent_id'):
            query = query.filter(NamedArea.parent_id==parent_id)
        if within := filter_dict.get('within'):
            set_srid = 4326
            if srid := within.get('srid'):
                set_srid = srid
                if point := within.get('point'):
                    if len(point) == 2:
                        query = query.filter(func.ST_Within(
                            func.ST_SetSRID(func.ST_Point(point[0], point[1]), set_srid),
                            NamedArea.geom_mpoly
                        ))
        if len(named_area_ids) > 0:
            query = query.filter(NamedArea.id.in_(named_area_ids))

        query = query.order_by(AreaClass.sort, NamedArea.name_en)
    else:
        query = query.filter(NamedArea.id==0)

    if x := request.args.get('range'):
        args_range = json.loads(x)
        query = query.offset(args_range[0]).limit(args_range[1])

    return jsonify(make_query_response(query))


#@api.route('/taxa/<int:id>', methods=['GET'])
def get_taxon_detail(id):
    if obj := session.get(Taxon, id):
        taxon = obj.to_dict()
        if request.args.get('options'):
            taxon['higher_classification'] = []
            taxon['ranks'] = {}
            for t in obj.get_parents():
                taxon['higher_classification'].append({
                    'id': t.id, 'rank': t.rank
                })

                # frontend prefetched highest rank options
                #if rank_index = Taxon.RANK_HIERARCHY.index(x['rank']) > 0:
                entities = TaxonRelation.query.filter(TaxonRelation.parent_id==t.id, TaxonRelation.depth==1).all()
                taxon['ranks'][Taxon.RANK_HIERARCHY[t.rank_depth + 1]] = [
                    {'id': x.child.id, 'display_name': x.child.display_name} for x in entities]

            if obj.rank_depth < len(Taxon.RANK_HIERARCHY) - 1:
                #  not the last rank, should append child rank options
                entities = TaxonRelation.query.filter(TaxonRelation.parent_id==obj.id, TaxonRelation.depth==1).all()
                taxon['ranks'][Taxon.RANK_HIERARCHY[obj.rank_depth + 1]] = [
                    {'id': x.child.id, 'display_name': x.child.display_name} for x in entities]

        return jsonify(taxon)
    else:
        abort(404)

#@api.route('/taxa', methods=['GET'])
def get_taxon_list():
    query = Taxon.query
    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) <= 2 else f'%{keyword}%'
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

    if sort_str := request.args.get('sort'):
        sort_dict = json.loads(sort_str)
        for i in sort_dict:
            if 'full_scientific_name' in i:
                if i['full_scientific_name'] == 'desc':
                    query = query.order_by(desc('full_scientific_name'))
                else:
                    query = query.order_by('full_scientific_name')

    if range_str := request.args.get('range'):
        range_dict = json.loads(range_str)
        if range_dict[0] != -1 and range_dict[1] != -1:
            query = query.slice(range_dict[0], range_dict[1])
    else:
        query = query.slice(0, 50)

    return jsonify(make_query_response(query))

def get_area_class_list():
    query = AreaClass.query.order_by('sort')
    query = query.filter(AreaClass.id > 4) # HACK
    if filter_str := request.args.get('filter', ''):
        filter_dict = json.loads(filter_str)
        if keyword := filter_dict.get('q', ''):
            like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
            query = query.filter(AreaClass.label.ilike(like_key))
        if ids := filter_dict.get('id', ''):
            query = query.filter(AreaClass.id.in_(ids))
        if parent_id := filter_dict.get('parent_id'):
            query = query.filter(AreaClass.parent_id==parent_id)

    return jsonify(make_query_response(query))

def get_area_class_detail(id):
    if obj := session.get(AreaClass, id):
        return jsonify(obj.to_dict())
    else:
        return redirect(404)

# def get_assertion_type_option_list():
#     query = AssertionTypeOption.query

#     if filter_str := request.args.get('filter', ''):
#         filter_dict = json.loads(filter_str)
#         if keyword := filter_dict.get('q', ''):
#             like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
#             query = query.filter(AssertionTypeOption.value.ilike(like_key))
#         #if ids := filter_dict.get('id', ''):
#         #    query = query.filter(AssertionTypeOption.id.in_(ids))
#         if type_id := filter_dict.get('type_id', ''):
#             query = query.filter(AssertionTypeOption.assertion_type_id==type_id)

#     return jsonify(make_query_response(query))

# def get_assertion_type_list():
#     query = AssertionType.query

#     if filter_str := request.args.get('filter', ''):
#         filter_dict = json.loads(filter_str)
#         if x := filter_dict.get('collection', ''):
#             query = query.filter(AssertionType.collection_id==x)
#         if x := filter_dict.get('target', ''):
#             query = query.filter(AssertionType.target==x)
#         if keyword := filter_dict.get('q', ''):
#             like_key = f'{keyword}%' if len(keyword) == 1 else f'%{keyword}%'
#             query = query.filter(AssertionType.label.ilike(like_key))

#     return jsonify(make_query_response(query))

def get_record_parts(record_id, part):
    if record := session.get(Record, record_id):
        ret = {}
        if part == 'named-areas':
            named_areas = record.get_named_area_list('default')
            ret['default'] = [x.to_dict() for x in named_areas]
            #for name, lst in all_list.items():
            #    ret[name] = [x.to_dict() for x in lst]
            return jsonify(ret)

    return jsonify({})


#@api.route('/occurrence', methods=['GET'])
def get_occurrence():
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
        Unit.guid,
        Unit.cover_image_id,
        #func.string_agg(NamedArea.name, ', ')
    ) \
    .join(Record, Unit.record_id==Record.id) \
    .join(Person, Record.collector_id==Person.id, isouter=True) \
    .join(Taxon, Record.proxy_taxon_id==Taxon.id, isouter=True) \
    .join(Collection, Unit.collection_id==Collection.id)
    #.join(NamedArea, Record.named_areas) \
    #.group_by(Unit.id, Record.id, Person.id, Collection.id, Taxon.id)

    stmt = stmt.where(Unit.pub_status=='P')
    stmt = stmt.where(Unit.accession_number!='') # 有 unit, 但沒有館號
    stmt = stmt.where(Collection.id==1) # only get HAST default

    # join named_area cause slow query

    #print('[TBIA]', stmt, flush=True)
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
            #if named_areas := record.get_named_area_list('default'):
            for k, v in record.get_named_area_map().items():
                na_list.append(v.named_area.to_dict()['display_name'])

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
            'datasetName': '中央研究院生物多樣性中心動物標本館 (HAST)', # TODO:為了TBIA網頁呈現, 先寫死
            'resourceContacts': '鍾國芳、劉翠雅',
            #'references': f'https://{request.host}/specimens/{r[15]}:{r[1]}' if r[1] else '',
            'references': r[19] or '',
            'license': 'CC BY NC 4.0+', #'https://creativecommons.org/licenses/by-nc/4.0/legalcode',
            'mediaLicense': 'CC BY NC 4.0+', #'https://creativecommons.org/licenses/by-nc/4.0/legalcode',
            #'sensitiveCategory':
            'created': r[3].strftime('%Y%m%d'), #unit.created.strftime('%Y%m%d') if unit.created else '',
            'modified': r[4].strftime('%Y%m%d'), #unit.updated.strftime('%Y%m%d') if unit.updated else '',
        }
        if r[20]:
            unit = session.get(Unit, r[0])
            if unit.cover_image_id:
                row['associatedMedia'] = unit.cover_image.file_url.replace('-m.jpg', '-l.jpg')
        else:
            row['associatedMedia'] = ''

        if r[9]:
            row['verbatimLongitude'] = float(r[9])
        if r[10]:
            row['verbatimLatitude'] = float(r[10])

        rows.append(row)


    results = {
        'data': rows,
        'messages': [
            '經緯度可能會有誤差，也有可能不一定是 WGS84',
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

def get_taxonomy_children():

    if filtr := request.args.get('filter'):
        filter_data = json.loads(filtr)
        ranks = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']

        rank_index = -1
        taxon_name = ''
        taxon_key = ''
        if raw := filter_data.get('raw'):
            for k, v in raw.items():
                if ranks.index(k) > rank_index:
                    rank_index = ranks.index(k)
                    taxon_name = v[1]
                    taxon_key = v[0]

            stmt = select(Record.source_data[f'{ranks[rank_index+1]}_name'])
            stmt_zh = select(Record.source_data[f'{ranks[rank_index+1]}_name_zh'])

            if collection_id := filter_data.get('collection_id'):
                stmt = stmt.where(Record.collection_id.in_(collection_id))
                stmt_zh = stmt_zh.where(Record.collection_id.in_(collection_id))

            for k, v in raw.items():
                stmt = stmt.where(Record.source_data[v[0]].astext == v[1])

            stmt = stmt.group_by(Record.source_data[f'{ranks[rank_index+1]}_name'])
            result = session.execute(stmt).all()
            data = []
            for x in result:
                # find common name
                stmt_zhx = stmt_zh.where(
                    Record.source_data[f'{ranks[rank_index+1]}_name'].astext == x[0],
                    Record.source_data[f'{ranks[rank_index+1]}_name_zh'].astext != ''
                )
                y = session.execute(stmt_zhx.limit(1)).scalar()
                data.append([x[0], y])

            return jsonify({
                'status': 'success',
                'parent': taxon_name,
                'rank': ranks[rank_index+1],
                'data': data
            })

    return jsonify({
        'status': 'error',
        'message': 'no filter'
    })

def get_taxonomy_stats():
    if filtr := request.args.get('filter'):
        ranks = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus', 'species']

        filter_data = json.loads(filtr)
        stmt = select(func.count('*'))

        if collection_id := filter_data.get('collection_id'):
            stmt = stmt.where(Record.collection_id.in_(collection_id))

        rank_index = -1
        taxon_name = ''
        taxon_key = ''
        if raw := filter_data.get('raw'):
            for k, v in raw.items():
                stmt = stmt.where(Record.source_data[v[0]].astext == v[1])
                if ranks.index(k) > rank_index:
                    rank_index = ranks.index(k)
                    taxon_name = v[1]
                    taxon_key = v[0]

        if rank_index >= 0:
            #stmt_base = stmt
            data = {}
            total = 0
            for i in range(rank_index + 1, len(ranks)):
                stmt = stmt.group_by(Record.source_data[f'{ranks[i]}_name']) # TODO: define foo_name
                result = session.execute(stmt).all()
                data[ranks[i]] = len(result)
                if ranks[i] == 'species':
                    for x in result:
                        total += x[0]

            return jsonify({
                'status': 'success',
                'name': taxon_name,
                'rank': ranks[rank_index],
                'data': data,
                'total': total,
            })

    return jsonify({
        'status': 'error',
        'message': 'no filter'
    })

# API url maps
api.add_url_rule('/searchbar', 'get-searchbar', get_searchbar, ('GET'))
api.add_url_rule('/search', 'get-search', get_search, ('GET'))
api.add_url_rule('/people', 'get-person-list', get_person_list, ('GET'))
api.add_url_rule('/people/<int:id>', 'get-person-detail', get_person_detail, ('GET'))
api.add_url_rule('/taxa', 'get-taxa-list', get_taxon_list, ('GET'))
api.add_url_rule('/taxa/<int:id>', 'get-taxa-detail', get_taxon_detail, ('GET'))
#api.add_url_rule('/assertion-type-options', 'get-assertion-type-option-list', get_assertion_type_option_list, ('GET'))
#api.add_url_rule('/assertion-types', 'get-assertion-type-list', get_assertion_type_list, ('GET'))
api.add_url_rule('/taxonomy/stats', 'get-taxonomy-stats', get_taxonomy_stats, ('GET'))
api.add_url_rule('/taxonomy/children', 'get-taxonomy-children', get_taxonomy_children, ('GET'))

#gazetter
api.add_url_rule('/named-areas', 'get-named-area-list', get_named_area_list, ('GET'))
api.add_url_rule('/named-areas/<int:id>', 'get-named-area-detail', get_named_area_detail, ('GET'))
api.add_url_rule('/area-classes', 'get-area-class-list', get_area_class_list, ('GET'))
api.add_url_rule('/area-classes/<int:id>', 'get-area-class-detail', get_area_class_detail, ('GET'))

api.add_url_rule('/record/<int:record_id>/<part>', 'get-record-parts', get_record_parts, ('GET'))
api.add_url_rule('/occurrence', 'get-occurrence', get_occurrence) # for TBIA

@api.route('/collections/<int:collection_id>/raw')
def get_collection_raw_list(collection_id):
    #print(collection_id, flush=True)
    if c := session.get(Collection, collection_id):
        rows = Record.query.filter(Record.collection_id==collection_id).limit(10).all()
        print(rows, flush=True)
        return jsonify({'result': 'ok'})
    return jsonify({'foo', 'bar'})


@api.route('/collections/<int:collection_id>/records/<int:record_id>/raw')
def get_collection_raw_detail(collection_id, record_id):
    #print(collection_id, flush=True)
    if c := session.get(Collection, collection_id):
        #rows = Record.query.filter(Record.collection_id==collection_id).limit(10).all()
        if r := session.get(Record, record_id):
            return jsonify({'raw': r.source_data})

    return jsonify({'foo', 'bar'})
