#from functools import wraps
import re
import math
import json
from datetime import datetime

from flask import (
    Blueprint,
    Response,
    request,
    abort,
    render_template,
    redirect,
    url_for,
    jsonify,
    send_from_directory,
    flash,
    current_app,
    g,
)
from flask_babel import (
    gettext,
)
from flask.views import View
from jinja2.exceptions import TemplateNotFound
from werkzeug.security import (
    check_password_hash,
)

from sqlalchemy import (
    select,
    func,
    text,
    desc,
    cast,
    between,
    extract,
    or_,
    join,
    BigInteger,
)
from sqlalchemy.orm import (
    aliased,
)
from flask_login import (
    login_required,
    login_user,
    logout_user,
    current_user,
)
from flask_jwt_extended import (
    jwt_required,
    create_access_token,
    get_jwt_identity,
    set_access_cookies,
    unset_jwt_cookies,
    set_refresh_cookies,
)
from app.models.collection import (
    Collection,
    Record,
    Project,
    Unit,
    Person,
    Transaction,
    Taxon,
    TrackingTag,
    MultimediaObject,
    Identification,
    #collection_person_map,
    RecordGroup,
)
from app.models.gazetter import (
    AreaClass,
    NamedArea,
)
from app.models.site import (
    User,
    UserList,
    UserListCategory,
    Site,
)
from app.database import (
    session,
    db_insp,
    ModelHistory,
)
from app.helpers import (
    get_current_site,
    get_entity,
    inspect_model,
    get_record_values,
    save_record,
)
from app.helpers_query import (
    make_admin_record_query,
    filter_records,
    make_specimen_query,
 )

from app.helpers_data import (
    export_specimen_dwc_csv,
)
from app.helpers_image import (
    upload_image,
    delete_image,
)

from .admin_register import ADMIN_REGISTER_MAP

admin = Blueprint('admin', __name__, static_folder='admin_static', static_url_path='static')

@admin.route('/login', methods=['GET', 'POST'])
def login():
    site = get_current_site(request)
    if not site:
        return abort(404)

    if request.method == 'GET':
        return render_template('admin/login.html', site=site)
    elif request.method == 'POST':
        username = request.json.get('username', '')
        passwd = request.json.get('passwd', '')
        # print(username, passwd, request.json, request.form, flush=True)
        if u := User.query.filter(User.username==username, User.site_id==site.id).first():
            if check_password_hash(u.passwd, passwd):
                login_user(u)

                access_token = create_access_token(identity=u.id)
                #flash('已登入')

                #next_url = flask.request.args.get('next')
                # is_safe_url should check if the url is safe for redirects.
                # See http://flask.pocoo.org/snippets/62/ for an example.
                #if not is_safe_url(next):
                #    return flask.abort(400)

                #return redirect(url_for('admin.index'))
                response = jsonify(access_token=access_token)
                set_access_cookies(response, access_token)
                return response

        #flash('帳號或密碼錯誤')
        #return redirect(url_for('admin.login'))
        return jsonify({'msg': '帳號或密碼錯誤'}), 401


@admin.route('/logout')
def logout():
    logout_user()

    response = jsonify({"msg": "logout successful"})
    unset_jwt_cookies(response)
    #return response
    return redirect(url_for('admin.login'))

#@admin.before_request
#def check_auth():
#    if not current_user.is_authenticated:
#        return abort(401)

@admin.route('/reset_password', methods=('GET', 'POST'))
@login_required
def reset_password():
    if request.method == 'GET':
        return render_template('admin/reset-password.html')
    elif request.method == 'POST':
        passwd1 = request.form.get('password1')
        passwd2 = request.form.get('password2')
        if passwd1 == passwd2:
            current_user.reset_passwd(passwd1)
            flash('已更新使用者密碼')
        return redirect(url_for('admin.index'))

    return abort(404)


@admin.route('/assets/<path:filename>')
def frontend_assets(filename):
    #return send_from_directory('blueprints/admin_static/record-form/admin/assets', filename)
    return send_from_directory('/build/admin-record-form/admin/assets', filename)

@admin.route('/collections/<int:collection_id>/records/<int:record_id>')
@login_required
def modify_collection_record(collection_id, record_id):

    site = get_current_site(request)
    record = Record.query.filter(Record.id==record_id, Record.collection_id.in_(site.collection_ids)).first()
    '''
    if site and record:
        try:
            return render_template(f'sites/{site.name}/admin/record-form-view.html', collection_id=collection_id, record_id=record_id)
        except TemplateNotFound:
            #return send_from_directory('blueprints/admin_static/record-form', 'index.html')
            #return send_from_directory('/build/admin-record-form', 'index.html')
            return render_template('admin/record-form2-view.html', collection_id=collection_id, record_id=record_id)

    return abort(404)
    '''
    return render_template('admin/record-form.html', collection_id=collection_id, record_id=record_id)

@admin.route('/collections/<int:collection_id>/records')
@login_required
def create_collection_record(collection_id):
    site = current_user.site
    # frontend
    #return send_from_directory('blueprints/admin_static/record-form', 'index.html')
    #return send_from_directory('/build/admin-record-form', 'index.html')
    #return send_from_directory('aa', 'index.html')
    #try:
    #    return render_template(f'sites/{site.name}/admin/record-form-view.html', collection_id=collection_id)
    #except TemplateNotFound:
    #    return send_from_directory('/build/admin-record-form', 'index.html')
    return render_template(f'admin/record-form.html', collection_id=collection_id)


@admin.route('/')
@login_required
def index():
    #if not current_user.is_authenticated:
        #return current_app.login_manager.unauthorized()
    #    return redirect(url_for('admin.login'))

    site = current_user.site
    record_query = session.query(
        Collection.label, func.count(Record.collection_id)
    ).select_from(
        Record
    ).join(
        Record.collection
    ).group_by(
        Collection
    ).filter(
        Collection.site_id==site.id
    ).order_by(
        Collection.sort, Collection.id
    )

    unit_query = session.query(
        Collection.label, func.count(Unit.collection_id)
    ).select_from(
        Unit
    ).join(
        Unit.collection
    ).group_by(
        Collection
    ).filter(
        Collection.site_id==site.id
    ).order_by(
        Collection.sort, Collection.id
    )
    accession_number_query = unit_query.filter(Unit.accession_number!='')

    media_query = session.query(
        Collection.label, func.count(Unit.collection_id)
    ).join(
        Unit,
        Unit.collection_id==Collection.id
    ).join(
        MultimediaObject,
        MultimediaObject.unit_id==Unit.id
    ).group_by(
        Collection
    ).filter(
        Collection.site_id==site.id
    ).order_by(
        Collection.sort, Collection.id
    )
    #stmt = select(Collection.label, func.count(Unit.collection_id)).join(MultimediaObject)

    #stats = {
    #    'record_count': Record.query.filter(Record.collection_id.in_(collection_ids)).count(),
    #'record_lack_unit_count': Record.query.join(Unit, full=True).filter(Unit.id==None, Unit.collection_id.in_(collection_ids)).count(),
    #    'unit_count': Unit.query.filter(Unit.collection_id.in_(collection_ids)).count(),
    #    'unit_accession_number_count': Unit.query.filter(Unit.accession_number!='', Unit.collection_id.in_(collection_ids)).count(),
    #}

    record_total = 0
    unit_total = 0
    accession_number_total = 0
    media_total = 0
    datasets = []

    # TODO
    bg_colors = [
        'rgba(255, 99, 132, 0.2)',
        'rgba(255, 159, 64, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgba(153, 102, 255, 0.2)',
        '#c7d5c6',
        '#e1e1e1',
    ];
    collections = Collection.query.filter(Collection.site==site).order_by('sort').all()
    for i, v in enumerate(collections):
        datasets.append({
            'label': v.label,
            'data': [0, 0, 0, 0],
            'borderWidth': 1,
            'backgroundColor': bg_colors[ i % len(bg_colors)],
        })
    for d in record_query.all():
        record_total += d[1]
        for i, v in enumerate(datasets):
            if v.get('label') == d[0]:
                datasets[i]['data'][0] = d[1]

    for d in unit_query.all():
        unit_total += d[1]
        for i, v in enumerate(datasets):
            if v.get('label') == d[0]:
                datasets[i]['data'][1] = d[1]

    for d in accession_number_query.all():
        accession_number_total += d[1]
        for i, v in enumerate(datasets):
            if v.get('label') == d[0]:
                datasets[i]['data'][2] = d[1]

    for d in media_query.all():
        media_total += d[1]
        for i, v in enumerate(datasets):
            if v.get('label') == d[0]:
                datasets[i]['data'][3] = d[1]
    stats = {
        'collection_datasets_json': json.dumps(datasets),
        'record_total': record_total,
        'unit_total': unit_total,
        'media_total': media_total,
        'accession_number_total': accession_number_total,
    }

    created_query = session.query(
        func.date_trunc('month', Record.created),
        func.count(Record.id)
    ).join(
        Collection
    ).group_by(
        text('1')
    ).filter(
        Collection.site_id==site.id,
        Record.created >= '2023-04-01'
    )

    now = datetime.now()
    year = now.year
    recent_months = {}
    for i in range(0, 12):
        m = now.month - i
        if m == 0:
            m = 12
            year -= 1
        elif m < 0:
            m = 12 + m
        recent_months[f'{year}-{m:02}'] = 0

    for i in created_query.all():
        k = i[0].strftime('%Y-%m')
        recent_months[k] = i[1]

    created_data = {
        'label': [],
        'data': [],
    }
    for k, v in recent_months.items():
        created_data['label'].append(k)
        created_data['data'].append(v)

    created_data['label'].reverse()
    created_data['data'].reverse()

    stats['created_chart_json'] = json.dumps({
        'labels': created_data['label'],
        'data': created_data['data'],
    })
    return render_template('admin/dashboard.html', stats=stats)


@admin.route('/records/', methods=['GET'])
@login_required
def record_list():
    site = current_user.site

    record_groups = {}
    record_group_list = RecordGroup.query.filter(RecordGroup.collection_id.in_(site.collection_ids))
    for i in record_group_list:
        if i.category not in record_groups:
            record_groups[i.category] = {
                'items': [],
                'label': [x[1] for x in RecordGroup.GROUP_CATEGORY_OPTIONS if x[0] == i.category][0],
            }
        record_groups[i.category]['items'].append(i)

    return render_template(
        'admin/record-list.html',
        record_groups=record_groups,
    )


def get_all_options(collection):
    record_group_list = RecordGroup.query.filter(RecordGroup.collection_id==collection.id)
    record_groups = [{'id': x.id, 'text': x.name, 'category': x.category} for x in record_group_list]

    data = {
        'project_list': [],
        'person_list': [],
        'record_groups': record_groups,
        'assertion_type_unit_list': [],
        'assertion_type_record_list': [],
        'annotation_type_unit_list': [],
        'annotation_type_multimedia_object_list': [],
        'unit_basis_of_record': [[x, x] for x in Unit.BASIS_OF_RECORD_OPTIONS],
        'transaction_type': Transaction.EXCHANGE_TYPE_CHOICES,
        'unit_pub_status': Unit.PUB_STATUS_OPTIONS,
        'unit_disposition': [[x, x] for x in Unit.DISPOSITION_OPTIONS],
        'unit_preparation_type': [[k, v] for k, v in Unit.PREPARATION_TYPE_MAP.items()],
        'unit_kind_of_unit': [[k, v] for k, v in Unit.KIND_OF_UNIT_MAP.items()],
        'unit_acquisition_type': Unit.ACQUISITION_TYPE_OPTIONS,
        'unit_type_status': Unit.TYPE_STATUS_OPTIONS,
        'collection': {
            'name': collection.name,
            'label': collection.label,
        },
        '_record_fields': Record.get_editable_fields(),
        '_identification_fields': Identification.get_editable_fields(),
        '_unit_fields': Unit.get_editable_fields(),
        #'current_user': current_user.id
    }

    people = Person.query.all()
    for i in people:
        data['person_list'].append({
            'id': i.id,
            'full_name': i.full_name,
            'full_name_en': i.full_name_en,
            'is_collector': i.is_collector,
            'is_identifier': i.is_identifier,
            'display_name': i.display_name,
        })

    a_types = collection.get_options('assertion_types')
    for i in a_types:
        tmp = {
            'id': i.id,
            'label': i.label,
            'name': i.name,
            'sort': i.sort,
            'input_type': i.input_type,
        }
        if i.input_type in ['select', 'free']:
            tmp['options'] = [{
                'id': x.id,
                'value': x.value,
                'description': x.description,
                'display_name': x.display_text,
            } for x in i.options]
        data[f'assertion_type_{i.target}_list'].append(tmp)

    a_types = collection.get_options('annotation_types')
    for i in a_types:
        tmp = {
            'id': i.id,
            'label': i.label,
            'name': i.name,
            'sort': i.sort,
            'input_type': i.input_type,
        }
        if i.input_type == 'select':
            tmp['options'] = i.data['options']

        data[f'annotation_type_{i.target}_list'].append(tmp)

    data['named_areas'] = {}

    ac_list = []
    query = AreaClass.query.filter(AreaClass.collection_id==collection.id)
    if collection.id == 1: # FIXME, still keep old data mapping
        ac_list = AreaClass.query.filter(AreaClass.id > 4, AreaClass.id < 7).all()

    ac = session.get(AreaClass, 7) # default
    data['named_areas'][ac.name] = {
        'label': ac.label,
        'options': [x.to_dict() for x in ac.named_area]
    }
    for ac in ac_list:
        data['named_areas'][ac.name] = {
            'label': ac.label,
            'options': [x.to_dict() for x in ac.named_area]
        }

    # phase 1
    site = get_current_site(request)
    if phase := site.data.get('phase'):
        if phase == 1:
            data['_phase1'] = {
                'form': site.data['admin']['form'][str(collection.id)],
                'fields': site.data.get('fields', []),
            }

    return data

@admin.route('/api/records/', methods=['GET'])
@jwt_required()
def api_get_record_list():
    site = current_user.site
    payload = {
        'filter': json.loads(request.args.get('filter')) if request.args.get('filter') else {},
        'sort': json.loads(request.args.get('sort')) if request.args.get('sort') else {},
        'range': json.loads(request.args.get('range')) if request.args.get('range') else [0, 50],
    }

    stmt = filter_records(payload['filter'], auth={'collection_ids': site.collection_ids})
    #current_app.logger.debug(f'fetch_records) {stmt}')

    base_stmt = stmt
    subquery = base_stmt.subquery()
    count_stmt = select(func.count()).select_from(subquery)
    total = session.execute(count_stmt).scalar()

    #print(stmt, flush=True)
    # order & limit
    if len(payload['filter']) > 0:
        #stmt = stmt.order_by(cast(Record.field_number.regexp_replace('[^0-9]+', 0, flags='g'), BigInteger))
        stmt = stmt.order_by(Record.field_number)
    else:
        stmt = stmt.order_by(desc(Record.id))

    stmt = stmt.limit(payload['range'][1] - payload['range'][0])
    if payload['range'][0] > 0:
        stmt = stmt.offset(payload['range'][0])

    result = session.execute(stmt)

    resp = {
        'data': [],
        'total': total,
    }

    for r in result.all():
        #print(r, flush=True)
        item = {}
        record = session.get(Record, r[2])
        loc_list = [x.named_area.display_name for x in record.named_area_maps]
        if loc_text := record.locality_text:
            loc_list.append(loc_text)

        entity_id = f'u{r[0]}' if r[0] else f'r{r[2]}'

        image_url = ''
        if r[0]:
            if unit := session.get(Unit, r[0]):
                image_url = unit.get_cover_image('s')

        collector = ''
        if r[3]:
            collector = record.collector.display_name

        mod_time = ''
        created = r[9] if len(r) >= 10 else ''
        #updated = r[10] if len(r) > 11 else ''
        if created:
            mod_time = created.strftime('%Y-%m-%d')
        #if updated:
        #    mod_time = mod_time + '/' + updated.strftime('%Y-%m-%d')

        if last_history := ModelHistory.query.filter(ModelHistory.tablename=='record*', ModelHistory.item_id==str(record.id)).order_by(desc(ModelHistory.created)).first():
            mod_time = f'{mod_time} ({last_history.user.username})'

        taxon = r[6] or ''
        if r[7]:
            taxon = f'{taxon} ({r[7]})'

        item.update({
            'record_id': r[2],
            'collector': collector,
            'field_number': r[4] or '',
            'catalog_number': r[1] or '',
            'collect_date': r[5].strftime('%Y-%m-%d') if r[5] else '',
            'locality': ','.join(loc_list),
            'taxon': taxon,
            'image_url': image_url,
            'entity_id': entity_id,
            'mod_time': mod_time,
            'collection_id': record.collection_id,
        })
        resp['data'].append(item)

    return jsonify(resp)

@admin.route('/export-data', methods=['GET', 'POST'])
@login_required
def export_data():
    if request.method == 'GET':
        return render_template('admin/export-data.html')
    else:
        export_specimen_dwc_csv()
        return ''

@admin.route('/api/collections/<int:collection_id>/tracking-tags')
def api_get_collection_tracking_tags(collection_id):
    filter_str = request.args.get('filter')
    filter_dict = json.loads(filter_str)
    q = filter_dict['q']
    tag_type = filter_dict['tag_type']
    if collection := session.get(Collection, collection_id):
        query = TrackingTag.query.filter(TrackingTag.collection_id==collection_id, TrackingTag.tag_type==tag_type, TrackingTag.value.ilike(f'{q}%'))
        data = []
        for tag in query.all():
            label = tag.label
            if tag.unit_id:
                label = f'{label} (u{tag.unit_id})'
            data.append({
                'id': tag.id,
                'label': label,
                'value': tag.value
            })
        resp = jsonify(data)

        resp.headers.add('Access-Control-Allow-Origin', '*')
        resp.headers.add('Access-Control-Allow-Methods', '*')
        return resp

@admin.route('/api/collections/<int:collection_id>/options')
@jwt_required()
def api_get_collection_options(collection_id):
    if collection := session.get(Collection, collection_id):
        data = get_all_options(collection)
        if uid := get_jwt_identity():
            if user := session.get(User, uid):
                data['current_user'] = {
                    'uid': uid,
                    'uname': user.username,
                }

                #return jsonify(data)
                resp = jsonify(data)
                resp.headers.add('Access-Control-Allow-Origin', '*')
                resp.headers.add('Access-Control-Allow-Methods', '*')
                return resp

    return abort(404)

@admin.route('/api/collections/<int:collection_id>/records/<int:record_id>', methods=['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'])
@jwt_required()
def api_modify_admin_record(collection_id, record_id):
    if request.method == 'GET':
        if record := session.get(Record, record_id):
            if record.collection_id != collection_id:
                return abort(404)

            resp = jsonify(get_record_values(record))
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Methods', '*')
            return resp

        return abort(404)

    elif request.method == 'OPTIONS':
        res = Response()
        #res.headers['Access-Control-Allow-Origin'] = '*' 不行, 跟before_request重複?
        res.headers['Access-Control-Allow-Headers'] = '*'
        res.headers['X-Content-Type-Options'] = 'GET, POST, OPTIONS, PUT, DELETE'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        res.headers.add('Access-Control-Allow-Origin', '*')
        res.headers.add('Access-Control-Allow-Methods', '*')
        return res
    elif request.method == 'POST':
        if record := session.get(Record, record_id):
            if col := session.get(Collection, collection_id):
                current_uid = None # TODO dirty HACK
                if uid := get_jwt_identity():
                    current_uid = uid
                else:
                    current_uid = 1

                save_record(record, request.json, col, current_uid)

            resp = jsonify({'message': 'ok'})
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Methods', '*')
            return resp

    elif request.method == 'DELETE':
        if record := session.get(Record, record_id):
            #session.delete(record)
            #session.commit()
            resp = jsonify({'message': 'ok'})
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Methods', '*')
            return resp

    return abort(404)


@admin.route('/api/collections/<int:collection_id>/records', methods=['POST', 'OPTIONS'])
@jwt_required()
def api_create_admin_record(collection_id):
    if request.method == 'OPTIONS':
        res = Response()
        #res.headers['Access-Control-Allow-Origin'] = '*' 不行, 跟before_request重複?
        res.headers['Access-Control-Allow-Headers'] = '*'
        res.headers['X-Content-Type-Options'] = 'GET, POST, OPTIONS, PUT, DELETE'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        res.headers.add('Access-Control-Allow-Origin', '*')
        res.headers.add('Access-Control-Allow-Methods', '*')
        return res
    elif request.method == 'POST':
        if col := session.get(Collection, collection_id):
            current_uid = None # TODO dirty HACK
            if uid := get_jwt_identity():
                current_uid = uid
            else:
                current_uid = 1

            record, is_new = save_record(None, request.json, col, uid)

        if is_new:
            uid = request.json.get('uid')
            resp = jsonify({
                'message': 'ok',
                'next_url': url_for('admin.modify_collection_record', collection_id=record.collection_id, record_id=record.id),
                'is_new': True,
            })
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Methods', '*')
            return resp
        else:
            resp = jsonify({'message': 'ok'})
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Methods', '*')
            return resp

@admin.route('/api/units/<int:unit_id>/media/<int:media_id>', methods=['POST'])
def api_post_unit_media_action(unit_id, media_id):
    action = request.args.get('action')
    if mo := session.get(MultimediaObject, media_id):
        if action == 'set-cover':
            mo.unit.cover_image_id = media_id
            session.commit()
            return jsonify({'message': 'ok', 'action': action})
        else:
            return jsonify({'error': 'no action'})
    else:
        return jsonify({'error': 'media_id not found'})

@admin.route('/api/units/<int:unit_id>/media/<int:media_id>', methods=['DELETE'])
def api_delete_unit_media(unit_id, media_id):
    if mo := session.get(MultimediaObject, media_id):
        site = get_current_site(request)
        serv_keys = site.get_service_keys()
        upload_conf = site.data['admin']['uploads']
        res = delete_image(upload_conf, serv_keys, mo.file_url)
        mo.unit.cover_image_id = None
        session.delete(mo)
        session.commit()
        return jsonify({'message': 'ok'})

    return jsonify({'error': 'media_id not found'})


# upload unit media
@admin.route('/api/units/<int:unit_id>/media', methods=['POST'])
def api_post_unit_media(unit_id):
    unit = session.get(Unit, unit_id)

    if not unit:
        return jsonify({'message': 'no unit'})

    if 'file' not in request.files:
        return jsonify({'message': 'no file'})

    if f := request.files['file']:
        site = get_current_site(request)
        serv_keys = site.get_service_keys()
        upload_conf = site.data['admin']['uploads']
        res = upload_image(upload_conf, serv_keys, f, f'u{unit.id}')
        if res['error'] == '' and res['message'] == 'ok':
            sd = {'originalFilename': f.filename}
            if exif := res.get('exif'):
                sd['exifData'] = exif
            mo = MultimediaObject(type_id=1, unit_id=unit.id, source_data=sd, file_url=res['file_url'])
            session.add(mo)
            session.commit()
            unit.cover_image_id = mo.id
            session.commit()
            return jsonify({'message': 'ok'})
        else:
            return jsonify(res)

    return jsonify({'message': 'upload image failed'})

@admin.route('/api/searchbar')
@jwt_required()
def api_searchbar():
    q = request.args.get('q', '')

    if len(q) <= 3:
        # sorting starts from inhereted name in english
        like_cond = f'{q}%'
    else:
        like_cond = f'%{q}%'

    collectors = Person.query.filter(Person.full_name.ilike(like_cond) | Person.full_name_en.ilike(like_cond) | Person.sorting_name.ilike(like_cond)).all()
    taxa = Taxon.query.filter(Taxon.full_scientific_name.ilike(like_cond) | Taxon.common_name.ilike(f'%{q}%')).limit(50).all()

    field_number_stmt = select(Record.id, Person, Record.field_number).join(Person).where(Record.field_number.ilike(f'{q}%')).where(Record.collector_id > 0).limit(50)
    field_number_res = session.execute(field_number_stmt).all()

    catalog_number_stmt = select(Unit.record_id, Unit.accession_number).where(Unit.accession_number.ilike(f'{q}%')).limit(20)
    catalog_number_res = session.execute(catalog_number_stmt).all()

    categories = [{
        'label': gettext('採集者'),
        'key': 'collector',
        'items': [x.to_dict() for x in collectors],
    }, {
        'label': gettext('採集號'),
        'key': 'field_number',
        'items': [[x[0], x[1].to_dict(), x[2]] for x in field_number_res],
    }, {
        'label': gettext('學名'),
        'key': 'taxon',
        'items': [x.to_dict() for x in taxa],
    }, {
        'label': gettext('館號'),
        'key': 'catalog_number',
        'items': [[x[0], x[1]] for x in catalog_number_res],
    }]

    return jsonify(categories)

@admin.route('/print-label')
@login_required
def print_label():
    keys = request.args.get('entities', '')
    cat_id = request.args.get('category_id')
    sort = request.args.get('sort', '')
    #query = Collection.query.join(Person).filter(Collection.id.in_(ids.split(','))).order_by(Person.full_name, Collection.field_number)#.all()
    items = []

    if cat_id:
        items = [get_entity(x.entity_id) for x in UserList.query.filter(UserList.category_id==cat_id, UserList.user_id==current_user.id).order_by(UserList.created).all()]

    elif keys:
        key_list = [x for x in keys.split(',') if x]
        items = [get_entity(key) for key in key_list]

    if sort:
        item_map = {}

        if sort == 'created':
            pass
        if sort == 'field-number':
            for i in items:
                item_map[i['record'].get_record_number()] = i

            sorted_items = sorted(item_map.items(), key = lambda x: x[0])
            items = [x[1] for x in sorted_items]


    return render_template('admin/print-label.html', items=items)


@admin.route('/user-list')
@login_required
def user_list():
    list_cats = current_user.get_user_lists()
    for cat_id in list_cats:
        for item in list_cats[cat_id]['items']:
            item['entity'] = get_entity(item['entity_id'])

    return render_template('admin/user-list.html', user_list_categories=list_cats)


@admin.route('/api/user-list', methods=['POST'])
@login_required
def post_user_list():
    if request.method != 'POST':
        return abort(404)

    if entity_id_list := request.json.get('entity_id'):
        msg_list = []
        for entity_id in entity_id_list:
            if ul := UserList.query.filter(
                    UserList.entity_id==entity_id,
                    UserList.user_id==request.json.get('uid'),
                    UserList.category_id==request.json.get('category_id')).first():
                msg_list.append(entity_id)
                #return jsonify({'message': '已加過', 'entity_id': entity_id, 'code': 'already'})
            else:
                ul = UserList(
                    entity_id=entity_id,
                    user_id=request.json.get('uid'),
                    category_id=request.json.get('category_id'))
                session.add(ul)
                session.commit()
                msg_list.append(entity_id)
                #return jsonify({'message': '已加入使用者清單', 'entity_id': entity_id, 'code': 'added'})
        return jsonify({'message': '已加入使用者清單', 'content': ','.join(msg_list), 'code': 'added'})

    if query := request.json.get('query'):
        payload = {}
        for i in query.split('&'):
            k, v = i.split('=')
            payload[k] = v

        stmt = make_admin_record_query(payload)
        result = session.execute(stmt)
        entity_ids = []
        for r in result:
            if r[0]:
                entity_ids.append(f'u{r[0]}')
            elif r[2]:
                entity_ids.append(f'r{r[2]}')


        category_id = request.json.get('category_id')
        uid = request.json.get('uid')
        for entity_id in entity_ids:
            if ul := UserList.query.filter(
                    UserList.entity_id==entity_id,
                    UserList.user_id==uid,
                    UserList.category_id==category_id).first():
                pass
            else:
                ul = UserList(
                    entity_id=entity_id,
                    user_id=uid,
                    category_id=category_id)
                session.add(ul)

        session.commit()

        #print(request.json, query, payload, stmt, entity_ids,flush=True)

        return jsonify({'message': '已將搜尋結果全部加入使用者清單', 'code': 'all added'})
#@admin.route('/api/user-lists/<int:user_list_id>', methods=['DELETE',])
@admin.route('/api/user-lists/<int:user_list_id>')
@login_required
def delete_user_list(user_list_id):
    #print(request.method, flush=True)
    if ul := session.get(UserList, user_list_id):
        session.delete(ul)
        session.commit()
    return jsonify({'message': 'ok'})

class ListView(View):
    def __init__(self, register):
        self.register = register
        self.template = 'admin/list-view.html'

    def dispatch_request(self):

        # login_requried
        if not current_user.is_authenticated:
            return redirect('/login')

        if query := self.register.get('list_query'):
            query = query
        else:
            query = self.register['model'].query

        if filter_by := self.register.get('filter_by'):
            if filter_by == 'organization':
                query = query.filter(self.register['model'].site_id==current_user.site_id)
            elif filter_by == 'collection':
                collection_ids = [x.id for x in site.collections]
                query = query.filter(self.register['model'].collection_id.in_(collection_ids))

        #print(query, flush=True)
        if list_filter := self.register.get('list_filter'):
           if q := request.args.get('q'):
                many_or = or_()
                for x in list_filter:
                    attr = getattr(self.register['model'], x)
                    many_or = or_(many_or, attr.ilike(f'{q}%'))
                query = query.filter(many_or)

        if collection_id := request.args.get('collection_id'):
            if collection_filter := self.register.get('list_collection_filter'):
                if related := collection_filter.get('related'):
                    query = query.select_from(Collection).join(related)
                    query = query.filter(Collection.id==collection_id)
                elif field := collection_filter.get('field'):
                    query = query.filter(field==int(collection_id))


        total = query.count()
        items = query.limit(50).all()

        return render_template(self.template, items=items, register=self.register, total=total)


class FormView(View):
    '''
    - has item_id: GET, POST
    - create: GET, POST
    '''
    def __init__(self, register, is_create=False):
        # self.template = f"{model.__tablename__}/detail.html"
        self.template = 'admin/form-view.html'
        self.register = register
        self.is_create = is_create
        self.item = None

    def _get_item(self, item_id):
        return self.register['model'].query.get(item_id)

    def dispatch_request(self, item_id):
        # login_requried
        if not current_user.is_authenticated:
            return redirect('/login')

        if self.is_create is not True:
            self.item = self._get_item(item_id)

            if not self.item:
                return abort(404)

        if request.method == 'GET':
            if self.is_create is not True and item_id:
                return render_template(
                    self.template,
                    item=self.item,
                    register=self.register,
                    action_url=url_for(f'admin.{self.register["name"]}-form', item_id=item_id)
                )
            else:
                return render_template(
                    self.template,
                    register=self.register,
                    action_url=url_for(f'admin.{self.register["name"]}-create')
                )
        elif request.method == 'POST':
            # create new instance
            if self.is_create is True:
                if 'filter_by' in self.register:
                    if self.register['filter_by'] == 'site':
                        self.item = self.register['model'](site_id=current_user.site_id)
                    else:
                        self.item = self.register['model']()
                else:
                    self.item = self.register['model']()

                session.add(self.item)

            #change_log = ChangeLog(self.item)

            m2m_collections = []
            for key, value in request.form.items():
                # print(key, value, flush=True)
                if key[:19] == '__m2m__collection__':
                    collection = session.get(Collection, int(key[19:]))
                    m2m_collections.append(collection)
                elif key[:8] == '__bool__':
                    bool_value = True if value == '1' else False
                    setattr(self.item, key[8:], bool_value)
                elif hasattr(self.item, key):
                    m = re.match(r'.+(_id)$', key)
                    if m:
                        setattr(self.item, key, None if value == '' else value)
                    else:
                        setattr(self.item, key, value)

            if len(m2m_collections) > 0:
                self.item.collections = m2m_collections
            else:
                self.item.collections = []

            changes = inspect_model(self.item)
            history = ModelHistory(
                user_id=current_user.id,
                tablename=self.item.__tablename__,
                action='create' if self.is_create else 'update',
                item_id=self.item.id,
                changes=changes,
            )
            session.add(history)

            session.commit()

            if self.is_create:
                history.item_id = self.item.id
                session.commit()

            flash(f'已儲存: {self.item}', 'success')
            return redirect(url_for(f'admin.{self.register["name"]}-list'))

        elif request.method == 'DELETE':
            history = ModelHistory(
                user_id=current_user.id,
                tablename=self.item.__tablename__,
                action='delete',
                item_id=item_id,
            )
            session.add(history)

            session.delete(self.item)
            session.commit()
            next_url = url_for(f'admin.{self.register["name"]}-list')
            return jsonify({'next_url': next_url})



# common url rule
for name, reg in ADMIN_REGISTER_MAP.items():
    res_name = reg['resource_name']
    admin.add_url_rule(
        f'/{res_name}/',
        view_func=ListView.as_view(f'{name}-list', reg),
    )
    admin.add_url_rule(
        f'/{res_name}/<int:item_id>',
        view_func=FormView.as_view(f'{name}-form', reg),
        methods=['GET', 'POST', 'DELETE']
    )
    admin.add_url_rule(
        f'/{res_name}/create',
        defaults={'item_id': None},
        view_func=FormView.as_view(f'{name}-create', reg, is_create=True),
        methods=['GET', 'POST']
    )

'''
## TEMPLATE ##

# articles
admin.add_url_rule(
    '/articles/',
    view_func=ListView.as_view('article-list', Article),
)
admin.add_url_rule(
    '/articles/<int:item_id>',
    view_func=FormView.as_view('article-form', Article),
    methods=['GET', 'POST', 'DELETE']
)
admin.add_url_rule(
    '/article/create',
    defaults={'item_id': None},
    view_func=FormView.as_view('article-create', Article, is_create=True),
    methods=['GET', 'POST']
)
'''



# @admin.app_template_filter()
# def get_value(item, key):
#     if '.' in key:
#         tmp = item
#         for k in key.split('.'):
#             tmp = getattr(tmp, k)
#         return tmp
#     else:
#         return getattr(item, key)
#     return item


# def check_res(f):
#     #def decorator(f):
#     @wraps(f)
#     def decorated_function(*args, **kwargs):
#         #print (request.path, flush=True)
#         m = re.match(r'/admin/(.+)(/.*)', request.path)
#         if m:
#             res = m.group(1)
#             if res in RESOURCE_MAP:
#                 result = f(*args, **kwargs)
#                 return result
#         return abort(404)
#     return decorated_function
#return decorator

# @admin.app_template_filter()
# def get_display(item):
#     if isinstance(item, str):
#         return item
#     else:
#         print(item.name,dir(item), flush=True)
#     return ''
