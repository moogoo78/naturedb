import json
import os
import time
import re
import logging
import math
from datetime import datetime

import requests as http_requests

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
    case,
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
    CollectionTaxonMap,
    MultimediaObject,
    UnitVerbatim,
)
from flask_login import login_required, current_user
from app.services.ai import (
    extract_label,
    BackendError,
    BackendUnavailable,
    BackendTimeout,
    NoCoverImage,
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
from app.exporters.tbia import (
    fetch_named_areas_by_record,
    fetch_cover_image_urls,
    fetch_taxon_ancestors,
)
from app.exporters.scribe import shape_specimens_page

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

@api.before_request
def handle_preflight():
    if request.method == 'OPTIONS':
        origin = request.headers.get('Origin', '')
        allowed_origins = current_app.config.get('CORS_ORIGINS', [])
        resp = Response()
        if origin in allowed_origins:
            resp.headers['Access-Control-Allow-Origin'] = origin
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        return resp

@api.after_request
def after_request(resp):
    origin = request.headers.get('Origin', '')
    allowed_origins = current_app.config.get('CORS_ORIGINS', [])
    if origin in allowed_origins:
        resp.headers['Access-Control-Allow-Origin'] = origin
        resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        resp.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    return resp

def get_searchbar():
    q = request.args.get('q')

    categories = {
        'taxa': [],
        #'named_area': [],
        'collectors': [],
        #'catalog_number': [],
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

        rows = Unit.query.filter(Unit.catalog_number.ilike(f'{q}%')).limit(category_limit).all()
        for r in rows:
            #categories['catalog_number'].append(r.label_info)
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

    auth = {
        'collection_id': [],
        'role': '',
        'area-class-id': [],
    }
    custom_area_class_ids = []
    if host := request.headers.get('Host'):
        if site := Site.find_by_host(host):
            custom_area_class_ids = [x.id for x in site.get_custom_area_classes()]
            auth['collection_id'] = site.collection_ids
            #auth['area-class-id'] = site. TODO
            if filter_collection_id := payload['filter'].get('collection_id'):
                if isinstance(filter_collection_id, list):
                    auth['collection_id'] = list(set(site.collection_ids) & set(filter_collection_id))
                elif int(filter_collection_id) in auth['collection_id']:
                    pass
                else:
                    abort(401)
        else:
            return abort(401)

    stmt = make_specimen_query(payload['filter'], auth)

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
            elif sort in ['catalog_number', '-catalog_number']:
                if sort == '-catalog_number':
                    stmt = stmt.order_by(desc(func.length(Unit.catalog_number)), desc(Unit.catalog_number))
                else:
                    stmt = stmt.order_by(func.length(Unit.catalog_number), Unit.catalog_number)
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
                #catalog_number_int = int(unit.catalog_number)
                #instance_id = f'{catalog_number_int:06}'
                #first_3 = instance_id[0:3]
                #image_url = f'https://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{instance_id}_s.jpg'
                image_url = unit.get_cover_image()
            except:
                pass

            taxon_text = record.proxy_taxon_scientific_name
            if record.proxy_taxon_common_name:
                taxon_text = f'{record.proxy_taxon_scientific_name} ({record.proxy_taxon_common_name})'

            named_areas = []

            for k, v in record.get_named_area_map(custom_area_class_ids).items():
                named_areas.append(v.named_area.to_dict())

            d = {
                'unit_id': unit.id if unit else '',
                'record_id': record.id,
                'record_key': f'u{unit.id}' if unit else f'c{record.id}',
                # 'catalog_number': unit.catalog_number if unit else '',
                'catalog_number': unit.catalog_number if unit else '',
                'image_url': image_url,
                'field_number': record.field_number,
                'collector': record.collector.to_dict() if record.collector else '',
                'collector_text': record.verbatim_collector or '',
                'collect_date': record.collect_date.strftime('%Y-%m-%d') if record.collect_date else '',
                'taxon': t.to_dict() if t else {},
                'taxon_text': taxon_text,
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
    # If collection_id provided, proxy to the institution's API that owns this collection
    if collection_id := request.args.get('collection_id', type=int):
        collection = session.get(Collection, collection_id)
        if not collection or not collection.site_id:
            return jsonify({'error': 'Site not found for collection'}), 404
        site = session.get(Site, collection.site_id)
        if not site or not site.host:
            return jsonify({'error': f'No host configured for site of collection {collection_id}'}), 404

        portal_host = os.environ.get('PORTAL_HOST')
        if portal_host:
            subdomain = site.host.split('.')[0]
            base = portal_host.removeprefix('www.')
            institution_host = f"{subdomain}.{base}"
            port = base.split(':')[1] if ':' in base else '80'
            # In Docker local dev, call loopback with Host header — DNS won't resolve subdomains inside the container
            taxon_url = f"http://127.0.0.1:{port}/api/v1/taxa"
            headers = {'Host': institution_host}
        else:
            taxon_url = f"https://{site.host}/api/v1/taxa"
            headers = {}

        try:
            resp = http_requests.get(taxon_url, headers=headers, timeout=10)
            resp.raise_for_status()
            return jsonify(resp.json())
        except http_requests.RequestException as e:
            current_app.logger.error(f'Taxon proxy failed: GET {taxon_url} (Host: {headers.get("Host", "")}) → {e}')
            return jsonify({'error': f'Failed to fetch taxa from {taxon_url}: {e}'}), 502

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
        if collection_id := filter_dict.get('collection_id'):
            maps = CollectionTaxonMap.query.filter(
                CollectionTaxonMap.collection_id == int(collection_id)
            ).all()
            if maps:
                tree_ids = list({m.taxon_tree_id for m in maps})
                query = query.filter(Taxon.tree_id.in_(tree_ids))
        if tree_id := filter_dict.get('tree_id'):
            query = query.filter(Taxon.tree_id == int(tree_id))

    if sort_str := request.args.get('sort'):
        sort_list = json.loads(sort_str)
        for i in sort_list:
            if isinstance(i, dict):
                if 'full_scientific_name' in i:
                    if i['full_scientific_name'] == 'desc':
                        query = query.order_by(desc('full_scientific_name'))
                    else:
                        query = query.order_by('full_scientific_name')
            elif isinstance(i, str):
                field = i.lstrip('-')
                if field == 'full_scientific_name':
                    if i.startswith('-'):
                        query = query.order_by(desc('full_scientific_name'))
                    else:
                        query = query.order_by('full_scientific_name')
    else:
        rank_order = case(
            (Taxon.rank == 'family', 0),
            (Taxon.rank == 'genus', 1),
            (Taxon.rank == 'species', 2),
            else_=3,
        )
        query = query.order_by(rank_order, Taxon.full_scientific_name)

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
    """only for HAST to TBIA"""
    # required
    startCreated = request.args.get('startCreated', '')
    endCreated = request.args.get('endCreated', '')
    startModified = request.args.get('startModified', '')
    endModified = request.args.get('endModified', '')
    selfProduced = request.args.get('selfProduced', '')
    limit = int(request.args.get('limit', 300))
    offset = int(request.args.get('offset', 0))

    # optional
    collectionId = request.args.get('collectionId')
    occurrenceId = request.args.get('occurrenceId')

    base_conditions = [
        Unit.pub_status == 'P',
        Unit.catalog_number != '',
        Unit.collection_id == 1,  # HAST only
    ]

    try:
        if startCreated:
            base_conditions.append(Unit.created >= datetime.strptime(startCreated, '%Y%m%d'))
        if endCreated:
            base_conditions.append(Unit.created <= datetime.strptime(endCreated, '%Y%m%d'))
        if startModified:
            base_conditions.append(Unit.updated >= datetime.strptime(startModified, '%Y%m%d'))
        if endModified:
            base_conditions.append(Unit.updated <= datetime.strptime(endModified, '%Y%m%d'))
    except ValueError:
        return abort(400)

    # Slim count: no joins, since all filters live on Unit.
    total = session.execute(
        select(func.count()).select_from(Unit).where(*base_conditions)
    ).scalar()

    custom_area_class_ids = []
    if host := request.headers.get('Host'):
        if site := Site.find_by_host(host):
            custom_area_class_ids = [x.id for x in site.get_custom_area_classes()]

    # Main page query: scalar columns only (no Record entity → no lazy loads).
    stmt = (
        select(
            Unit.id,                          # 0
            Unit.catalog_number,              # 1
            Unit.type_status,                 # 2
            Unit.created,                     # 3
            Unit.updated,                     # 4
            Record.field_number,              # 5
            Record.collect_date,              # 6
            Person.full_name,                 # 7
            Person.full_name_en,              # 8
            Record.longitude_decimal,         # 9
            Record.latitude_decimal,          # 10
            Record.id,                        # 11
            Record.locality_text,             # 12
            Record.locality_text_en,          # 13
            Unit.kind_of_unit,                # 14
            Collection.label,                 # 15
            Taxon.full_scientific_name,       # 16
            Taxon.common_name,                # 17
            Taxon.rank,                       # 18
            Unit.guid,                        # 19
            Unit.cover_image_id,              # 20
            Record.proxy_taxon_id,            # 21
        )
        .join(Record, Unit.record_id == Record.id)
        .join(Person, Record.collector_id == Person.id, isouter=True)
        .join(Taxon, Record.proxy_taxon_id == Taxon.id, isouter=True)
        .join(Collection, Unit.collection_id == Collection.id)
        .where(*base_conditions)
        .order_by(desc(Unit.created))
        .limit(limit)
        .offset(offset)
    )

    page = session.execute(stmt).all()

    # Batch-fetch what used to be per-row lazy loads.
    record_ids = [r[11] for r in page if r[11]]
    cover_image_ids = [r[20] for r in page if r[20]]
    taxon_ids = [r[21] for r in page if r[21]]

    named_areas = fetch_named_areas_by_record(record_ids, custom_area_class_ids)
    cover_image_urls = fetch_cover_image_urls(cover_image_ids)
    taxon_ancestors = fetch_taxon_ancestors(taxon_ids)

    rows = []
    for r in page:
        collector = ''
        if r[7] and r[8]:
            collector = f'{r[8]} ({r[7]})'
        elif r[7]:
            collector = r[7]
        elif r[8]:
            collector = r[8]

        na_list = list(named_areas.get(r[11], []))
        if r[12]:
            na_list.append(r[12])
        if r[13]:
            na_list.append(r[13])

        kind_of_unit = Unit.KIND_OF_UNIT_MAP.get(r[14], '') or ''

        row = {
            'occurrenceID': r[0],
            'collectionID': r[1],
            'scientificName': r[16] or '',
            'isPreferredName': r[17] or '',
            'taxonRank': r[18] or '',
            'typeStatus': r[2] or '',
            'eventDate': r[6].strftime('%Y%m%d') if r[6] else '',
            'verbatimCoordinateSystem': 'DecimalDegrees',
            'verbatimSRS': 'EPSG:4326',
            'dataGeneralizations': False,
            'locality': ', '.join(na_list),
            'organismQuantity': 1,
            'organismQuantityType': '份',
            'recordedBy': collector,
            'recordNumber': r[5] or '',
            'preservation': kind_of_unit,
            'datasetName': '中央研究院生物多樣性中心植物標本館 (HAST)', # TODO:為了TBIA網頁呈現, 先寫死
            'resourceContacts': '鍾國芳、劉翠雅',
            'references': r[19] or '',
            'license': 'CC BY NC 4.0+',
            'mediaLicense': 'CC BY NC 4.0+',
            'created': r[3].strftime('%Y%m%d') if r[3] else '',
            'modified': r[4].strftime('%Y%m%d') if r[4] else '',
        }

        if file_url := cover_image_urls.get(r[20]):
            row['associatedMedia'] = file_url.replace('-m.jpg', '-l.jpg')
        else:
            row['associatedMedia'] = ''

        if r[9]:
            row['verbatimLongitude'] = float(r[9])
        if r[10]:
            row['verbatimLatitude'] = float(r[10])

        row['kingdom'] = 'Plantae'
        for rank, display_text in taxon_ancestors.get(r[21], []):
            row[rank] = display_text

        rows.append(row)


    results = {
        'data': rows,
        'messages': [], #'經緯度可能會有誤差，也有可能不一定是 WGS84',
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

@api.route('/scribe/collections')
def scribe_collections():
    """Institution + collection facet for the Nature-Scribe explorer rail."""
    label_map = current_app.config['SCRIBE_COLLECTION_LABELS']
    if not label_map:
        return jsonify({'items': [], 'total': 0})

    stmt = (
        select(
            Collection.id,
            func.count(Unit.id).label('unit_count'),
        )
        .join(Unit, Unit.collection_id == Collection.id, isouter=True)
        .where(Collection.id.in_(label_map.keys()))
        .group_by(Collection.id)
    )
    rows = session.execute(stmt).all()
    items = [
        {'id': cid, 'label': label_map[cid], 'count': count}
        for cid, count in rows
    ]
    items.sort(key=lambda x: (-x['count'], x['id']))

    institution = (request.args.get('institution') or '').upper().strip()
    if institution:
        items = [i for i in items if i['label'].upper() == institution or i['label'].upper().startswith(f'{institution}:')]

    return jsonify({'items': items, 'total': len(items)})


@api.route('/scribe/specimens')
def scribe_specimens():
    """Paginated specimen card rows for the Nature-Scribe explorer grid."""
    label_map = current_app.config['SCRIBE_COLLECTION_LABELS']

    try:
        page = max(1, int(request.args.get('page', 1)))
    except (TypeError, ValueError):
        page = 1
    try:
        per_page = int(request.args.get('per_page', 50))
    except (TypeError, ValueError):
        per_page = 60
    per_page = max(1, min(per_page, 100))

    collection_id = request.args.get('collection_id', type=int)
    institution = (request.args.get('institution') or '').upper().strip()
    q = (request.args.get('q') or '').strip()
    sort = request.args.get('sort', 'recent')

    stmt = (
        select(Unit, Record)
        .join(Record, Unit.record_id == Record.id)
        .where(Unit.collection_id.in_(label_map.keys()))
    )
    if institution:
        inst_ids = [
            cid for cid, label in label_map.items()
            if label.upper() == institution or label.upper().startswith(f'{institution}:')
        ]
        if not inst_ids:
            return jsonify({'items': [], 'total': 0, 'page': page, 'per_page': per_page})
        stmt = stmt.where(Unit.collection_id.in_(inst_ids))
    if collection_id is not None:
        stmt = stmt.where(Unit.collection_id == collection_id)
    if q:
        like = f'%{q}%'
        stmt = stmt.where(or_(
            Record.proxy_taxon_scientific_name.ilike(like),
            Record.proxy_taxon_common_name.ilike(like),
            Record.locality_text.ilike(like),
            Record.verbatim_locality.ilike(like),
            Record.verbatim_collector.ilike(like),
        ))

    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = session.execute(count_stmt).scalar_one()

    if sort == 'catalog':
        stmt = stmt.order_by(Unit.catalog_number.asc())
    else:
        stmt = stmt.order_by(Unit.id.desc())

    stmt = stmt.offset((page - 1) * per_page).limit(per_page)
    rows = session.execute(stmt).all()
    items = shape_specimens_page(rows, collection_label_map=label_map)

    return jsonify({
        'items': items,
        'page': page,
        'per_page': per_page,
        'total': total,
    })


@api.route('/scribe/units/<int:unit_id>/annotations', methods=['POST'])
def save_unit_annotations(unit_id):
    """Save annotation data for a unit (specimen)."""
    from app.models.collection import Unit, Record, Identification

    unit = session.get(Unit, unit_id)
    if not unit:
        return jsonify({'error': 'Unit not found'}), 404

    record = unit.record
    if not record:
        return jsonify({'error': 'Record not found'}), 404

    data = request.get_json() or {}

    # Map form fields to Record model attributes
    field_map = {
        'collector_id': 'collector_id',
        'collector_name': None,  # derived from collector, skip
        'verbatim_collector': 'verbatim_collector',
        'companion_text': 'companion_text',
        'field_number': 'field_number',
        'verbatim_collect_date': 'verbatim_collect_date',
        'collect_date_year': 'collect_date_year',
        'collect_date_month': 'collect_date_month',
        'collect_date_day': 'collect_date_day',
        'locality_text': 'locality_text',
        'verbatim_locality': 'verbatim_locality',
        'longitude_decimal': 'longitude_decimal',
        'latitude_decimal': 'latitude_decimal',
        'country_id': None,  # named_area, handle separately
        'adm1_id': None,  # named_area, handle separately
        'adm2_id': None,  # named_area, handle separately
        'adm3_id': None,  # named_area, handle separately
        'altitude': 'altitude',
        'altitude2': 'altitude2',
        'identifications': None,  # list, handle separately
    }

    # Update Record fields
    for key, attr in field_map.items():
        if attr and key in data and data[key] is not None:
            try:
                setattr(record, attr, data[key])
            except Exception as e:
                return jsonify({'error': f'Failed to set {attr}: {str(e)}'}), 400

    # Handle identifications: edit existing rows by id, insert new ones with sequence = max+1
    idents_payload = data.get('identifications') or []
    if idents_payload:
        existing_max_seq = max(
            (i.sequence or 0 for i in record.identifications),
            default=-1,
        )
        ident_writable = (
            'identifier_id', 'verbatim_identifier',
            'taxon_id', 'verbatim_identification',
            'date_text', 'verbatim_date', 'note',
        )
        for entry in idents_payload:
            ident_id = entry.get('id')
            if ident_id:
                ident = session.get(Identification, ident_id)
                if not ident or ident.record_id != record.id:
                    continue
            else:
                existing_max_seq += 1
                ident = Identification(record_id=record.id, sequence=existing_max_seq)
                session.add(ident)
            for f in ident_writable:
                if f in entry:
                    val = entry[f]
                    setattr(ident, f, val if val not in ('', None) else None)

    try:
        session.commit()
        return jsonify({
            'status': 'success',
            'message': 'Annotations saved',
            'unit_id': unit_id,
        })
    except Exception as e:
        session.rollback()
        return jsonify({'error': f'Database error: {str(e)}'}), 500


# === AI label extraction =====================================================
# Per-user, hourly in-memory rate limiter for un-cached calls.
# Keyed by (user_id, hour_bucket); not persistent across worker restarts —
# good enough for v1 with a small fleet, swap for redis when we scale.
_AI_LABEL_BUCKETS = {}


def _ai_rate_limit_check(user_id):
    limit = current_app.config.get('AI_LABEL_RATE_PER_HOUR', 60)
    bucket = (user_id, int(time.time() // 3600))
    used = _AI_LABEL_BUCKETS.get(bucket, 0)
    if used >= limit:
        # Seconds until the next bucket starts
        retry_after = 3600 - (int(time.time()) % 3600)
        return False, retry_after
    return True, None


def _ai_rate_limit_consume(user_id):
    bucket = (user_id, int(time.time() // 3600))
    _AI_LABEL_BUCKETS[bucket] = _AI_LABEL_BUCKETS.get(bucket, 0) + 1


@api.route('/scribe/units/<int:unit_id>/ai/label', methods=['POST'])
@login_required
def ai_label_extract(unit_id):
    """Run AI label extraction on the unit's cover image."""
    if not current_app.config.get('FEATURE_AI_LABEL', False):
        return jsonify({'error': 'feature disabled', 'code': 'feature_off'}), 404

    unit = session.get(Unit, unit_id)
    if not unit:
        return jsonify({'error': 'unit not found', 'code': 'not_found'}), 404

    body = request.get_json(silent=True) or {}
    backend = body.get('backend') or current_app.config.get('AI_LABEL_DEFAULT_BACKEND', 'remote')
    image_size = body.get('image_size') or '2048'
    force = bool(body.get('force', False))

    if backend not in ('api', 'remote'):
        return jsonify({'error': f'unsupported backend: {backend!r}', 'code': 'bad_backend'}), 400
    if image_size not in ('1024', '2048', '4096'):
        return jsonify({'error': f'invalid image_size: {image_size!r}', 'code': 'bad_size'}), 400

    user_id = getattr(current_user, 'id', None)

    # Rate limit (skipped on cache hit — we re-check after the call returns)
    ok, retry_after = _ai_rate_limit_check(user_id)
    if not ok and force:
        # Force always counts against the limit
        return jsonify({
            'error': 'rate limit exceeded',
            'code': 'rate_limit',
            'retry_after': retry_after,
        }), 429

    try:
        result = extract_label(
            unit,
            backend=backend,
            image_size=image_size,
            force=force,
            user_id=user_id,
        )
    except NoCoverImage:
        return jsonify({'error': 'unit has no cover image', 'code': 'no_image'}), 422
    except BackendUnavailable as e:
        return jsonify({'error': str(e), 'code': 'remote_down', 'backend': backend}), 503
    except BackendTimeout as e:
        return jsonify({'error': str(e), 'code': 'remote_timeout', 'backend': backend}), 504
    except BackendError as e:
        return jsonify({'error': str(e), 'code': 'backend_error', 'backend': backend}), 502
    except ValueError as e:
        return jsonify({'error': str(e), 'code': 'bad_request'}), 400
    except Exception as e:
        session.rollback()
        current_app.logger.exception('AI label extraction failed')
        return jsonify({'error': f'unexpected: {e}', 'code': 'internal'}), 500

    # Re-check rate limit before consuming: a cache hit should be free
    if not result.cached:
        ok, retry_after = _ai_rate_limit_check(user_id)
        if not ok:
            session.rollback()
            return jsonify({
                'error': 'rate limit exceeded',
                'code': 'rate_limit',
                'retry_after': retry_after,
            }), 429
        _ai_rate_limit_consume(user_id)

    try:
        session.commit()
    except Exception as e:
        session.rollback()
        current_app.logger.exception('AI extraction commit failed')
        return jsonify({'error': f'database error: {e}', 'code': 'db_error'}), 500

    return jsonify({
        'text': result.text,
        'model': result.model,
        'backend': result.backend,
        'ms': result.ms,
        'prompt_version': result.prompt_version,
        'image_size': result.image_size,
        'cached': result.cached,
    })


@api.route('/scribe/ai/health', methods=['GET'])
def ai_label_health():
    """Health check for the remote-control worker (no auth required)."""
    if not current_app.config.get('FEATURE_AI_LABEL', False):
        return jsonify({'feature': False, 'remote_available': False})

    sock_path = current_app.config.get('AI_LABEL_REMOTE_SOCKET')
    remote_available = False
    if sock_path and os.path.exists(sock_path):
        import socket as _socket
        try:
            s = _socket.socket(_socket.AF_UNIX, _socket.SOCK_STREAM)
            s.settimeout(0.5)
            s.connect(sock_path)
            s.close()
            remote_available = True
        except OSError:
            remote_available = False

    return jsonify({
        'feature': True,
        'remote_available': remote_available,
        'default_backend': current_app.config.get('AI_LABEL_DEFAULT_BACKEND', 'remote'),
    })


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
