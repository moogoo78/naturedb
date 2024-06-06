#from functools import wraps
import re
import math
import json
from datetime import datetime

from flask import (
    Blueprint,
    request,
    abort,
    render_template,
    redirect,
    url_for,
    jsonify,
    send_from_directory,
    flash,
    current_app,
)
from flask.views import View
from flask_login import (
    login_required,
    current_user,
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
from app.models.collection import (
    Collection,
    Record,
    RecordAssertion,
    RecordNamedAreaMap,
    AssertionType,
    Project,
    Unit,
    UnitAssertion,
    UnitAnnotation,
    Identification,
    Person,
    Transaction,
    AnnotationType,
    Annotation,
    Taxon,
    MultimediaObject,
    collection_person_map,
)
from app.models.gazetter import (
    AreaClass,
    NamedArea,
)
from app.models.site import (
    User,
    UserList,
    UserListCategory,
)
from app.database import (
    session,
    db_insp,
    ModelHistory,
)
from app.helpers import (
    get_current_site,
    get_entity,
    make_editable_values,
    inspect_model,
)
from app.helpers_query import (
    make_admin_record_query,
)

from .admin_register import ADMIN_REGISTER_MAP

admin = Blueprint('admin', __name__, static_folder='admin_static', static_url_path='static')


@admin.before_request
def check_auth():
    if not current_user.is_authenticated:
        return abort(401)

def save_record(record, payload, collection):
    #print(record, payload, flush=True)
    is_debug = False

    uid = payload.get('uid')
    is_new_record = False
    if not record:
        record = Record(collection_id=collection.id)
        session.add(record)
        session.commit()
        is_new_record = True

    relate_changes = {}
    modify = make_editable_values(record, payload)

    if project_id := payload.get('project_id'):
        record.project_id = project_id
    else:
        record.project_id = None
    if collector_id := payload.get('collector_id'):
        record.collector_id = collector_id
    else:
        record.collector_id = None

    if value := payload.get('named_areas'):
        changes = {}
        via = payload.get('named_areas__via', '')
        pv = record.get_named_area_map()
        #print(pv, value, flush=True)

        updated_keys = []
        for name, selected in value.items():
            if selected:
                new_val = int(selected['value'])
                updated_keys.append(name)
                if name in pv:
                    if pv[name].named_area_id != new_val:
                        #print('update r-n-a-m', pv[name].named_area_id, new_val, flush=True)
                        pv[name].named_area_id = new_val
                        changes[name] = ['UPDATE', pv[name].named_area_id, new_val]
                else:
                    rel = RecordNamedAreaMap(record_id=record.id, named_area_id=new_val, via=via)
                    #print('new r-n-a-m', rel, flush=True)
                    changes[name] = ['CREATE', name, new_val]
                    session.add(rel)

        should_delete = list(set(pv.keys()) - set(updated_keys))
        for key in should_delete:
            changes[name] = ['DELETE', key, pv[key].named_area_id]
            session.delete(pv[key])

        if len(changes):
            relate_changes['named_areas'] = changes

    if value := payload.get('assertions'):
        changes = {}
        pv = {}
        for m in record.assertions:
            pv[m.assertion_type.name] = m

        updated_keys = []
        ## TODO only consider select type
        for name, val in value.items():
            if val:
                updated_keys.append(name)
                new_val = str(val)
                if name in pv:
                    if pv[name].value != new_val:
                        changes[name] = ['UPDATE', pv[name].value, new_val]
                        pv[name].value = new_val
 
                else:
                    if a_type := AssertionType.query.filter(AssertionType.name==name).first():
                        new_ra = RecordAssertion(record_id=record.id, assertion_type_id=a_type.id, value=new_val)
                        changes[name] = ['CREATE', name, new_val]
                        session.add(new_ra)

        should_delete = list(set(pv.keys()) - set(updated_keys))
        for key in should_delete:
            changes[key] = ['DELETE', key, pv[key].value]
            session.delete(pv[key])

        if len(changes):
            relate_changes['assertions'] = changes

    if value := payload.get('identifications'):
        changes = {}
        pv = {}
        update_ids = [x['id'] for x in value if x.get('id')]
        for i in record.identifications.all():
            pv[i.id] = i
            # delete id no exist now
            if i.id not in update_ids:
                #changes[i.id] = ['DELETE Identification', i.to_dict()]
                session.delete(i)

        for i in value:
            iden = None
            if exist_id := i.get('id'):
                iden = pv[int(exist_id)]
            else:
                iden = Identification(
                    record_id=record.id,
                )
                session.add(iden)
                session.commit()

            i2 = dict(i)
            if x := i2.get('identifier_id'):
                i2['identifier_id'] = x
            if x := i2.get('taxon_id'):
                i2['taxon_id'] = x

            iden_modify = make_editable_values(iden, i)
            if len(iden_modify):
                iden.update(iden_modify)
                iden_changes = inspect_model(iden)
                if len(iden_changes):
                    changes[iden.id] = iden_changes

        if len(changes):
            relate_changes['identifications'] = changes

    if value := payload.get('units'):
        changes = {}
        pv = {}
        # for check update or delete old values
        update_ids = [x['id'] for x in value if x.get('id')]

        for unit in record.units:
            pv[unit.id] = unit
            if unit.id not in update_ids:
                session.delete(unit)

        assertion_types = collection.get_options('assertion_types')
        assertion_type_map = {x.name: x for x in assertion_types}
        annotation_types = collection.get_options('annotation_types')
        annotation_type_map = {x.name: x for x in annotation_types}

        for i in value:
            unit = None
            if exist_id := i.get('id'):
                unit = pv[int(exist_id)]
            else:
                unit = Unit(record_id=record.id)
                session.add(unit)
                session.commit()

            unit_modify = make_editable_values(unit, i)
            if len(unit_modify):
                unit.update(unit_modify)
                unit_changes = inspect_model(unit)
                if len(unit_changes):
                    changes[unit.id] = unit_changes

                if assertions := i.get('assertions'):
                    changes_assertions = {}
                    pv_assertions = {}
                    for x in unit.assertions:
                        pv_assertions[x.assertion_type.name] = x

                    for k, v in assertions.items():
                        if k in pv_assertions:
                            if v:
                                if v != pv_assertions[k].value:
                                    # update
                                    pure_value = str(v)
                                    if assertion_type_map[k].input_type == 'select':
                                        if isinstance(v, dict):
                                            pure_value = v.get('value')
                                    elif assertion_type_map[k].input_type == 'checkbox':
                                        if isinstance(v, bool):
                                            if v is True:
                                                pure_value = '__checked__'
                                            else:
                                                session.delete(pv_assertions[k])
                                                changes_assertions[k] = ['DELETE', k]

                                    if pv_assertions[k].value != pure_value:
                                        pv_assertions[k].value = pure_value
                                        #print('update', k, pure_value, flush=True)
                                        changes_assertions[k] = ['UPDATE', k, pv_assertions[k].value, pure_value]
                            else:
                                # delete
                                session.delete(pv_assertions[k])
                                #print('delete', k, flush=True)
                                changes_assertions[k] = ['DELETE', k, pv_assertions[k].value]
                        else:
                            # new
                            if v:
                                a = UnitAssertion(unit_id=unit.id, assertion_type_id=assertion_type_map[k].id, value=v)
                                session.add(a)
                                #print('insert', k, flush=True)
                                changes_assertions[k] = ['CREATE', k, v]
                    if len(changes_assertions):
                        if unit.id not in changes:
                            changes[unit.id] = {}
                        changes[unit.id]['assertions'] = changes_assertions

                if annotations := i.get('annotations'):
                    changes_annotations = {}
                    pv_annotations = {}
                    for x in unit.annotations:
                        pv_annotations[x.annotation_type.name] = x

                    for k, v in annotations.items():
                        if k in pv_annotations:
                            if v:
                                if v != pv_annotations[k].value:
                                    # update
                                    pure_value = v
                                    if annotation_type_map[k].input_type == 'select':
                                        if isinstance(v, dict):
                                            pure_value = v.get('value')

                                    elif annotation_type_map[k].input_type == 'checkbox':
                                        if isinstance(v, bool):
                                            if v is True:
                                                pure_value = '__checked__'
                                            else:
                                                session.delete(pv_annotations[k])
                                                changes_annotations[k] = ['DELETE', k]

                                    pv_annotations[k].value = pure_value
                                    pv_annotations[k].datetime = datetime.now()
                                    #print('update', k, pure_value, flush=True)
                                    changes_annotations[k] = ['UPDATE', k, pv_annotations[k].value, pure_value]
                            else:
                                # delete
                                session.delete(pv_annotations[k])
                                #print('delete', k, flush=True)
                                changes_annotations[k] = ['DELETE', k, pv_annotations[k].value]
                        else:
                            # new
                            if v:
                                a = UnitAnnotation(unit_id=unit.id, annotation_type_id=annotation_type_map[k].id, value=v, datetime=datetime.now())
                                session.add(a)
                                #print('insert', k, flush=True)
                                changes_annotations[k] = ['CREATE', k, v]
                    if len(changes_annotations):
                        if unit.id not in changes:
                            changes[unit.id] = {}
                        changes[unit.id]['annotations'] = changes_annotations

            if len(changes):
                relate_changes['units'] = changes

    if len(modify):
        record.update(modify)
        #print(modify, flush=True)
        changes = inspect_model(record)

        if is_debug:
            print('modify:', modify, flush=True)
            print('record:', changes, flush=True)

    if len(changes) or \
       relate_changes.get('assertions') or \
       relate_changes.get('identifications') or \
       relate_changes.get('named_areas') or \
       relate_changes.get('units'):
        if len(relate_changes):
            changes['__relate__'] = relate_changes
        hist = ModelHistory(
            tablename='record*',
            item_id=record.id,
            action='update',
            user_id=uid,
            changes=changes)
        if is_new_record:
            hist.action = 'create'
        else:
            hist.action = 'update'

        session.add(hist)

    session.commit()

    return record, is_new_record

@admin.route('/assets/<path:filename>')
def frontend_assets(filename):
    #return send_from_directory('blueprints/admin_static/record-form/admin/assets', filename)
    return send_from_directory('/build/admin-record-form/admin/assets', filename)

@admin.route('/collections/<int:collection_id>/records/<int:record_id>')
def modify_frontend_collection_record(collection_id, record_id):
    if record := session.get(Record, record_id):
        #return send_from_directory('blueprints/admin_static/record-form', 'index.html')
        return send_from_directory('/build/admin-record-form', 'index.html')
    else:
        return abort(404)

@admin.route('/collections/<int:collection_id>/records')
def create_frontend_collection_record(collection_id):
    #return send_from_directory('blueprints/admin_static/record-form', 'index.html')
    return send_from_directory('/build/admin_static/record-form', 'index.html')

@admin.route('/static_build/<path:filename>')
def static_build(filename):
    return send_from_directory('/build', filename)

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

@admin.route('/')
#@login_required
def index():
    if not current_user.is_authenticated:
        #return current_app.login_manager.unauthorized()
        return redirect(url_for('base.login'))

    site = current_user.organization
    collection_ids = site.collection_ids

    record_query = session.query(
        Collection.label, func.count(Record.collection_id)
    ).select_from(
        Record
    ).join(
        Record.collection
    ).group_by(
        Collection
    ).filter(
        Collection.organization_id==site.id
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
        Collection.organization_id==site.id
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
        Collection.organization_id==site.id
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

    bg_colors = [
        'rgba(255, 99, 132, 0.2)',
        'rgba(255, 159, 64, 0.2)',
        'rgba(54, 162, 235, 0.2)',
        'rgba(153, 102, 255, 0.2)',
    ];
    for i, v in enumerate(record_query.all()):
        record_total += v[1]
        datasets.append({
            'label': v[0],
            'data': [v[1]],
            'borderWidth': 1,
            'backgroundColor': bg_colors[i],
        })
    for i, v in enumerate(unit_query.all()):
        unit_total += v[1]
        datasets[i]['data'].append(v[1])
    for i, v in enumerate(accession_number_query.all()):
        accession_number_total += v[1]
        datasets[i]['data'].append(v[1])
    for i, v in enumerate(media_query.all()):
        media_total += v[1]
        datasets[i]['data'].append(v[1])
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
        Collection.organization_id==site.id,
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
    site = current_user.organization

    current_page = int(request.args.get('page', 1))
    q = request.args.get('q', '')
    collectors = request.args.get('collectors', '')
    taxa = request.args.get('taxa', '')

    #stmt = select(Unit.id, Unit.accession_number, Entity.id, Entity.field_number, Person.full_name, Person.full_name_en, Entity.collect_date, Entity.proxy_taxon_scientific_name, Entity.proxy_taxon_common_name) \
    #.join(Unit, Unit.entity_id==Entity.id, isouter=True) \
    #.join(Person, Entity.collector_id==Person.id, isouter=True)

    stmt = make_admin_record_query(dict(request.args))

    # apply collection filter by site
    stmt = stmt.filter(Record.collection_id.in_(site.collection_ids))

    # print(stmt, flush=True)
    base_stmt = stmt
    subquery = base_stmt.subquery()
    count_stmt = select(func.count()).select_from(subquery)
    total = session.execute(count_stmt).scalar()
    per_page = 50 #TODO

    # order & limit
    #stmt = stmt.order_by(desc(Record.id))
    stmt = stmt.order_by(Record.field_number)
    if current_page > 1:
        stmt = stmt.offset((current_page-1) * per_page)
    stmt = stmt.limit(per_page)

    result = session.execute(stmt)
    rows = result.all()
    # print(stmt, '==', flush=True)
    last_page = math.ceil(total / per_page)
    qs_list = []
    if q:
        qs_list.append(f'q={q}')
    if collectors:
        qs_list.append(f'collectors={collectors}')

    qs_str = ''
    if len(qs_list):
        qs_str = '&'.join(qs_list)

    pagination = {
        'current_page': current_page,
        'last_page': last_page,
        'start_to': min(last_page-1, 3),
        'has_next': True if current_page < last_page else False,
        'has_prev': True if current_page > 1 else False,
        'query_string': qs_str,
    }
    items = []
    #fav_list = [x.record for x in current_user.favorites]
    for r in rows:
        record = session.get(Record, r[2])
        loc_list = [x.named_area.display_name for x in record.named_area_maps]
        if loc_text := record.locality_text:
            loc_list.append(loc_text)
        collector = ''
        if r[3]:
            collector = record.collector.display_name
        #collector = '{} ({})'.format(r[4], r[5])
        #elif r[4]:
        #    collector = r[4]

        entity_id = f'u{r[0]}' if r[0] else f'r{r[2]}'

        # HACK
        taxon_display = ''
        if r[8]:
            if taxon := session.get(Taxon, r[8]):
                #if family := taxon.get_higher_taxon('family'):
                #    taxon_family = f
                taxon_display = taxon.display_name

        created = r[9] if len(r) >= 10 else ''
        updated = r[10] if len(r) > 11 else ''
        mod_time = ''
        if created:
            mod_time = created.strftime('%Y-%m-%d')
        if updated:
            mod_time = mod_time + '/' + updated.strftime('%Y-%m-%d')

        # TODO uid
        cat_lists= UserList.query.filter(UserList.user_id==current_user.id, UserList.entity_id==entity_id).all()

        #print(r, flush=True)
        item = {
            'collection_id': r[11],
            'accession_number': r[1] or '',
            'record_id': r[2],
            'field_number': r[4] or '',
            'collector': collector,
            'collect_date': r[5].strftime('%Y-%m-%d') if r[5] else '',
            'scientific_name': taxon_display, # r[6]
            'common_name': '', #r[7],
            'locality': ','.join(loc_list),
            'entity_id': entity_id,
            'category_lists': [{'category_id': x.category_id, 'text': x.category.name} for x in cat_lists],
            'mod_time': mod_time,
        }
        items.append(item)

    plist = Person.query.filter(Person.is_collector==True).all()
    collector_list = [{
        'id': x.id,
        'full_name': x.full_name,
        'full_name_en': x.full_name_en,
        'display_name': x.display_name,
    } for x in plist]
    return render_template(
        'admin/record-list-view.html',
        items=items,
        total=total,
        pagination=pagination,
        collector_list=collector_list,
    )


@admin.route('/<collection_name>/records/create', methods=['GET', 'POST'])
@login_required
def record_create(collection_name):
    site = current_user.organization
    if collection := Collection.query.filter(Collection.id.in_(site.collection_ids), Collection.name==collection_name).one():
        if request.method == 'GET':
            x =  get_record_all_options(collection.id)
            return render_template(
                'admin/record-form-view.html',
                all_options=get_record_all_options(collection.id),
                collection=collection,
            )

        elif request.method == 'POST':
            record = save_record(Record(collection_id=collection.id), request.form, True)

            flash(f'已儲存: <採集記錄與標本>: {record.id}', 'success')
            submit_val = request.form.get('submit', '')
            if submit_val == 'save-list':
                return redirect(url_for('admin.record_list'))
            elif submit_val == 'save-edit':
                return redirect(url_for('admin.record_form', record_id=record.id))

    else:
        return abort(404)

# @admin.route('/api/records/<int:item_id>', methods=['POST'])
# def api_record_post(item_id):
#     print(item_id, request.get_json(), flush=True)
#     return jsonify({'message': 'ok'})

@admin.route('/records/<int:record_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def record_form(record_id):
    if record := session.get(Record, record_id):
        if request.method == 'GET':
            return render_template(
                'admin/record-form-view.html',
                record=record,
                all_options=get_record_all_options(record.collection_id),
            )
        elif request.method == 'POST':
            record = save_record(record, request.form)

            submit_val = request.form.get('submit', '')
            flash(f'已儲存: <採集記錄與標本>: {record.id}', 'success')
            if submit_val == 'save-list':
                return redirect(url_for('admin.record_list'))
            elif submit_val == 'save-edit':
                return redirect(url_for('admin.record_form', record_id=record.id))
        elif request.method == 'DELETE':
            history = ModelHistory(
                user_id=current_user.id,
                tablename=record.__tablename__,
                action='delete',
                item_id=record_id,
            )
            session.add(history)
            session.commit()
            return jsonify({'message': 'ok', 'next_url': url_for('admin.record_list')})

    return abort(404)


def get_all_options(collection):
    data = {
        'project_list': [],
        'person_list': [],
        'assertion_type_unit_list': [],
        'assertion_type_record_list': [],
        'annotation_type_unit_list': [],
        'annotation_type_multimedia_object_list': [],
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
        #'current_user': current_user.id
    }
    projects = Project.query.filter(Project.collection_id==collection.id).all()
    for i in projects:
        data['project_list'].append({
            'id': i.id,
            'name': i.name
        })

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
    for ac in AreaClass.query.filter(AreaClass.collection_id==collection.id, AreaClass.id > 4).all():
        data['named_areas'][ac.name] = {
            'label': ac.label,
            'options': [x.to_dict() for x in ac.named_area]
        }
        ac = session.get(AreaClass, 7)
        data['named_areas']['country'] = {
            'label': ac.label,
            'options': [x.to_dict() for x in ac.named_area]
        }
    return data

# auth error
# @admin.route('/api/collections/<int:collection_id>/options')
# def api_get_collection_options(collection_id):
#     if collection := session.get(Collection, collection_id):
#             data = get_all_options(collection)
#             return jsonify(data)

#     return abort(404)


@admin.route('/api/units/<int:item_id>', methods=['DELETE'])
def api_unit_delete(item_id):
    return jsonify({'message': 'ok',})


@admin.route('/api/identifications/<int:item_id>', methods=['DELETE'])
def api_identification_delete(item_id):
    return jsonify({'message': 'ok', 'next_url': url_for('admin.')})


@admin.route('/print-label')
def print_label():
    #keys = request.args.get('entities', '')
    #query = Collection.query.join(Person).filter(Collection.id.in_(ids.split(','))).order_by(Person.full_name, Collection.field_number)#.all()
    #key_list = keys.split(',')
    #print(key_list, flush=True)
    #items = [get_entity(key) for key in key_list]
    if cat_id := request.args.get('category_id'):
        items = [get_entity(x.entity_id) for x in UserList.query.filter(UserList.category_id==cat_id, UserList.user_id==current_user.id).all()]
    return render_template('admin/print-label.html', items=items)


@admin.route('/user-list')
def user_list():
    list_cats = current_user.get_user_lists()
    for cat_id in list_cats:
        for item in list_cats[cat_id]['items']:
            item['entity'] = get_entity(item['entity_id'])

    return render_template('admin/user-list.html', user_list_categories=list_cats)


@admin.route('/api/user-list', methods=['POST'])
def post_user_list():
    if request.method != 'POST':
        return abort(404)

    if entity_id := request.json.get('entity_id'):
        if ul := UserList.query.filter(
                UserList.entity_id==entity_id,
                UserList.user_id==request.json.get('uid'),
                UserList.category_id==request.json.get('category_id')).first():
            return jsonify({'message': '已加過', 'entity_id': entity_id, 'code': 'already'})
        else:
            ul = UserList(
                entity_id=entity_id,
                user_id=request.json.get('uid'),
                category_id=request.json.get('category_id'))
            session.add(ul)
            session.commit()

        return jsonify({'message': '已加入使用者清單', 'entity_id': entity_id, 'code': 'added'})

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

        print(request.json, query, payload, stmt, entity_ids,flush=True)

        return jsonify({'message': '已將搜尋結果全部加入使用者清單', 'code': 'all added'})
#@admin.route('/api/user-lists/<int:user_list_id>', methods=['DELETE',])
@admin.route('/api/user-lists/<int:user_list_id>')
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
                query = query.filter(self.register['model'].organization_id==current_user.organization_id)
            elif filter_by == 'collection':
                query = query.filter(self.register['model'].collection_id.in_(current_user.organization.collection_ids))

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
                    if self.register['filter_by'] == 'organization':
                        self.item = self.register['model'](organization_id=current_user.organization_id)
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
