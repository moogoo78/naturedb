#from functools import wraps
import re
import math
import json
from datetime import datetime
from io import BytesIO

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
    send_file,
)
from flask_babel import (
    gettext,
)
from flask.views import View, MethodView
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
    inspect,
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
    TrackingTag,
    MultimediaObject,
    Identification,
    #collection_person_map,
    RecordGroup,
    UnitAnnotation,
    AnnotationType,
    RecordNamedAreaMap,
    UnitNote,
)
from app.models.taxon import (
    Taxon,
    TaxonRelation,
)
from app.models.gazetter import (
    NamedArea,
)
from app.models.site import (
    User,
    UserList,
    UserListCategory,
    Site,
    ArticleCategory,
    Article,
)
from app.database import (
    session,
    db_insp,
    ModelHistory,
)
from app.helpers import (
    get_current_site,
    get_entity,
    get_entity_for_print,
    get_all_admin_options,
    inspect_model,
    #get_record_values,
    put_entity,
    put_entity_raw,
)
from app.helpers_query import (
    make_admin_record_query,
    try_hybrid_name_stmt,
 )

from app.helpers_image import (
    upload_image,
    delete_image,
)
from app.helpers_label import (
    make_print_docx,
)
from app.helpers import (
    get_site_stats,
)
from app.utils import (
    validate_and_format_date,
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
                access_token = create_access_token(identity=str(u.id)) # if not cast to string, will caused http 422 error
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


#@admin.route('/assets/<path:filename>')
#def frontend_assets(filename):
    #return send_from_directory('blueprints/admin_static/record-form/admin/assets', filename)
#    return send_from_directory('/build/admin-record-form/admin/assets', filename)


@admin.route('/')
@login_required
def index():
    #if not current_user.is_authenticated:
        #return current_app.login_manager.unauthorized()
    #    return redirect(url_for('admin.login'))
    site = current_user.site
    stats = get_site_stats(site)
    print(stats)
    stats = {
        'collection_datasets_json': json.dumps(stats['datasets']),
        'record_total': stats['record_total'],
        'unit_total': stats['unit_total'],
        'media_total': stats['media_total'],
        'accession_number_total': stats['accession_number_total'],
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

    # Volunteer contributions - Top 10 users by transcription activity
    from app.database import ModelHistory
    from app.models.site import User

    volunteer_query = session.query(
        User.username,
        func.count(ModelHistory.id).label('edit_count')
    ).join(
        ModelHistory, ModelHistory.user_id == User.id
    ).filter(
        ModelHistory.action.in_(['unit-simple-edit', 'quick-edit']),
        User.site_id == site.id
    ).group_by(
        User.id, User.username
    ).order_by(
        text('edit_count DESC')
    ).limit(10)

    stats['top_contributors'] = [
        {'username': row.username, 'count': row.edit_count}
        for row in volunteer_query.all()
    ]

    return render_template('admin/dashboard.html', stats=stats)


@admin.route('/records/', methods=['GET'])
@login_required
def record_list():
    site = current_user.site
    main_collections = [x for x in site.collections if not x.parent_id]
    main_collections = sorted(main_collections, key=lambda x: x.sort if x.sort else 0)

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
        collections=main_collections,
    )

@admin.route('/records/create')
@login_required
def record_form_create():
    site = current_user.site
    collection_id = request.args.get('collection_id')
    # frontend
    #return send_from_directory('blueprints/admin_static/record-form', 'index.html')
    #return send_from_directory('/build/admin-record-form', 'index.html')
    #return send_from_directory('aa', 'index.html')
    #try:
    #    return render_template(f'sites/{site.name}/admin/record-form-view.html', collection_id=collection_id)
    #except TemplateNotFound:
    #    return send_from_directory('/build/admin-record-form', 'index.html')
    return render_template(f'admin/record-form.html', collection_id=collection_id)

@admin.route('/records/<entity_key>')
@login_required
def record_form(entity_key):
    #site = get_current_site(request)
    site = current_user.site

    record, unit = get_entity(entity_key)
    if record and record.collection_id in site.collection_ids:
        return render_template('admin/record-form.html', collection_id=record.collection_id, record_id=record.id)

    '''
    if site and record:
        try:
            return render_template(f'sites/{site.name}/admin/record-form-view.html', collection_id=collection_id, record_id=record_id)
        except TemplateNotFound:
            #return send_from_directory('blueprints/admin_static/record-form', 'index.html')
            #return send_from_directory('/build/admin-record-form', 'index.html')
            return render_template('admin/record-form2-view.html', collection_id=collection_id, record_id=record_id)
    '''
    return abort(404)

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
        data = get_all_admin_options(collection)
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

@admin.route('/api/validate-record', methods=['POST'])
@jwt_required()
def validate_form_record():
    if request.method == 'POST':
        payload = request.json
        invalids = []

        if collection_id := payload.get('collection_id', ''):
            unit_ids = [x for x in payload['units'] if x]
            for k, v in payload['units'].items():
                # check duplicate
                if catalog_number := v.get('accession_number'):
                    stmt = select(Unit.id).join(Record).where(
                        Record.collection_id==collection_id,
                        Unit.accession_number==catalog_number,
                        Unit.id.not_in(unit_ids)
                    )
                    if exist := session.execute(stmt).first():
                        invalids.append(['accession_number', '館號有重複', catalog_number])
        else:
            invalids['collection_id'] = [collection_id, 'no collection_id']

        results = {'message': 'valid'}
        if len(invalids):
            results.update({
                'data':invalids,
                'message': 'invalid'
            })
    return jsonify(results)

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
        if upload_conf := site.get_settings('admin.uploads'):
            res = delete_image(upload_conf, serv_keys, mo.file_url)
            mo.unit.cover_image_id = None
            session.delete(mo)
            session.commit()
            return jsonify({'message': 'ok'})
        else:
            return jsonify({'error': 'settings admin.uploads not set'})

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
        if upload_conf := site.get_settings('admin.uploads'):
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
        else:
            return jsonify({'message': 'settings admin.uploads not set'})

    return jsonify({'message': 'upload image failed'})


# simple-edit
@admin.route('/api/units/<int:unit_id>/simple-edit', methods=['POST'])
@jwt_required()
def api_unit_simple_edit(unit_id):
    """
    Simple edit endpoint for unit data entry.
    Updates unit and record fields from form data with validation.
    """
    # Get unit or return error
    unit = session.get(Unit, unit_id)
    if not unit:
        return jsonify({
            'message': 'error',
            'content': 'unit not exist'
        }), 404

    payload = request.json
    record = unit.record

    try:
        # Update verbatim text fields
        _update_verbatim_fields(record, payload)

        unit.verbatim_label = payload.get('verbatim_label', '')

        # Validate and update collect_date
        date_error = _update_collect_date(record, payload)
        if date_error:
            return jsonify({
                'message': '日期格式錯誤',
                'content': date_error
            }), 400

        # Validate and update catalog_number (accession_number)
        catalog_error = _update_catalog_number(unit, payload, unit_id)
        if catalog_error:
            return jsonify({
                'message': '發生錯誤',
                'content': catalog_error
            }), 400

        # Update collector
        _update_collector(record, payload)

        # Update identification (taxon_id -> sequence=0)
        _update_identification(record, payload)

        # Update named areas (country, adm1-3)
        _update_named_areas(record, payload)

        # Save user note if provided
        _save_user_note(unit, payload)

        # Auto-complete volunteer task when volunteer saves
        if current_user.role == 'B':  # Volunteer
            from app.models.collection import VolunteerTask
            volunteer_task = session.query(VolunteerTask)\
                .filter(VolunteerTask.unit_id == unit_id,
                       VolunteerTask.volunteer_id == current_user.id,
                       VolunteerTask.status == 'assigned')\
                .first()

            if volunteer_task:
                volunteer_task.mark_completed()
                current_app.logger.info(f'Auto-completed task {volunteer_task.id} for volunteer {current_user.id}')

        # Log the change
        hist = ModelHistory(
            tablename='unit*',
            item_id=unit.id,
            action='unit-simple-edit',
            user_id=current_user.id,
            changes=payload,
        )
        session.add(hist)
        session.commit()

        return jsonify({
            'message': '快速編輯',
            'content': f'unit [{unit.accession_number}] 已存檔'
        })

    except Exception as err:
        session.rollback()
        return jsonify({
            'message': 'error',
            'content': str(err)
        }), 500


def _update_verbatim_fields(record, payload):
    """Update verbatim text fields from payload."""
    record.verbatim_collector = payload.get('verbatim_collector', '')
    record.companion_text = payload.get('companion_text', '')
    record.field_number = payload.get('field_number', '')
    record.verbatim_latitude = payload.get('verbatim_latitude', '')
    record.verbatim_longitude = payload.get('verbatim_longitude', '')
    record.verbatim_collect_date = payload.get('verbatim_collect_date', '')
    record.verbatim_locality = payload.get('verbatim_locality', '')
    record.altitude = int(payload.get('altitude') or 0)
    record.altitude2 = int(payload.get('altitude2') or 0)

def _update_collect_date(record, payload):
    """
    Validate and update collect_date from year/month/day components.
    Returns error message if validation fails, None otherwise.
    """
    year = payload.get('collect_date__year', '')
    month = payload.get('collect_date__month', '')
    day = payload.get('collect_date__day', '')

    # If all components provided, validate and format
    if year and month and day:
        formatted_date, date_error = validate_and_format_date(year, month, day)
        if date_error:
            return date_error
        record.collect_date = formatted_date
        record.collect_date_text = ''
    else:
        # Partial date - store as text
        parts = [p for p in [year, month, day] if p]
        record.collect_date_text = '-'.join(parts) if parts else ''
        record.collect_date = None

    return None


def _update_catalog_number(unit, payload, unit_id):
    """
    Validate and update catalog_number (accession_number).
    Returns error message if duplicate found, None otherwise.
    """
    catalog_number = payload.get('catalog_number', '').strip()
    if not catalog_number:
        return None

    # Check for duplicates in same site's collections
    collection_ids = current_user.site.collection_ids
    existing_unit = Unit.query.filter(
        Unit.id != unit_id,
        Unit.accession_number == catalog_number,
        Unit.collection_id.in_(collection_ids)
    ).first()

    if existing_unit:
        return f'館號:{catalog_number}已存在'

    unit.accession_number = catalog_number
    return None


def _update_collector(record, payload):
    """Update collector from person_id."""
    collector_id = payload.get('collector_id')
    if collector_id:
        # Verify person exists before setting
        if session.get(Person, collector_id):
            record.collector_id = collector_id
        else:
            record.collector_id = None
    else:
        record.collector_id = None


def _update_identification(record, payload):
    """
    Update or create primary identification (sequence=0) from taxon_id.
    Creates an Identification record with sequence=0 for the selected taxon.

    Args:
        record: The Record object to update
        payload: Request payload containing 'taxon_id' key
    """
    taxon_id = payload.get('taxon_id')

    # Find existing Identification with sequence=0
    existing_id = Identification.query.filter(
        Identification.record_id == record.id,
        Identification.sequence == 0
    ).first()

    if taxon_id:
        # Verify taxon exists
        taxon_id = int(taxon_id)
        if not session.get(Taxon, taxon_id):
            return

        if existing_id:
            # Update existing identification
            existing_id.taxon_id = taxon_id
        else:
            # Create new identification with sequence=0
            new_id = Identification(
                record_id=record.id,
                taxon_id=taxon_id,
                sequence=0
            )
            session.add(new_id)
    else:
        # No taxon_id provided - clear or delete existing identification
        if existing_id:
            # Clear taxon_id but keep the identification record
            existing_id.taxon_id = None

    record.update_proxy()


def _update_named_areas(record, payload):
    """
    Update record's named areas (country, adm1-3) from payload.
    Removes existing area mappings and creates new ones for provided areas.

    Args:
        record: The Record object to update
        payload: Request payload containing named_area_* keys
    """
    # Define area_class_ids mapping
    # 7=COUNTRY, 8=ADM1, 9=ADM2, 10=ADM3
    area_mappings = [
        ('named_area_country', 7),
        ('named_area_adm1', 8),
        ('named_area_adm2', 9),
        ('named_area_adm3', 10),
    ]

    # Collect new named_area IDs from payload
    new_named_area_ids = []
    for key, area_class_id in area_mappings:
        if area_id := payload.get(key):
            new_named_area_ids.append((int(area_id), area_class_id))

    # Get existing named_area mappings for standard area classes (7-10)
    existing_maps = {
        m.named_area.area_class_id: m
        for m in record.named_area_maps
        if m.named_area.area_class_id in [7, 8, 9, 10]
    }

    # Remove existing mappings that are being updated
    for area_class_id in [7, 8, 9, 10]:
        if area_class_id in existing_maps:
            session.delete(existing_maps[area_class_id])

    # Add new mappings
    for area_id, area_class_id in new_named_area_ids:
        # Verify named_area exists
        if named_area := session.get(NamedArea, area_id):
            # Double-check area_class_id matches
            if named_area.area_class_id == area_class_id:
                # Get via value from payload, default to 'manual'
                via = payload.get('named_area__via', 'C')
                new_map = RecordNamedAreaMap(
                    record_id=record.id,
                    named_area_id=area_id,
                    via=via
                )
                session.add(new_map)


def _save_user_note(unit, payload):
    """
    Save user note from payload if provided.
    Creates a new UnitNote entry with the note content.

    Args:
        unit: The Unit object to attach note to
        payload: Request payload containing 'user_note' key
    """
    user_note = payload.get('user_note', '').strip()

    # Only create note if content provided
    if not user_note:
        return

    # Determine note type based on content or explicit type
    note_type = payload.get('note_type', 'general')

    # Create new unit note
    note = UnitNote(
        unit_id=unit.id,
        user_id=current_user.id,
        note=user_note,
        note_type=note_type,
        is_public=False,  # Default to private
        resolved=False
    )
    session.add(note)


# quick edit
@admin.route('/api/quick-edit', methods=['POST'])
def api_record_quick_edit():
    payload = request.json
    if item_key := payload.get('item_key'):
        try:
            #print(payload)
            if item_key[0] == 'u':
                unit_id = item_key[1:]
                unit = session.get(Unit, unit_id)
                record = unit.record
                record.verbatim_collector = payload['verbatim_collector']
                record.companion_text = payload['companion_text']
                record.altitude = payload['altitude'] or 0
                record.altitude2 = payload['altitude2'] or 0
                record.verbatim_latitude = payload['verbatim_latitude']
                record.verbatim_longitude = payload['verbatim_longitude']
                if x := payload['collect_date']:
                    record.collect_date = x
                record.verbatim_collect_date = payload['verbatim_collect_date']
                record.verbatim_locality = payload['verbatim_locality']
                record.field_number = payload['field_number']
                if x:= payload['catalog_number']:
                    collection_ids = current_user.site.collection_ids
                    #print(unit_id, x)
                    if exist_unit := Unit.query.filter(Unit.id!=unit_id, Unit.accession_number==x, Unit.collection_id.in_(collection_ids)).first():
                        print(exist_unit)
                        return jsonify({
                            'message': '發生錯誤',
                            'content': f'館號:{x}已存在'
                        })
                unit.accession_number = payload['catalog_number']

                new_source_data = {}
                if x := record.source_data:
                    new_source_data.update(x)
                quick_sci_name = payload['quick__scientific_name']
                quick_verbatim_sci_name = payload['quick__verbatim_scientific_name']
                if quick_sci_name or quick_verbatim_sci_name:
                    if x := record.identifications.order_by(Identification.id).first():
                        first_id = x
                    else:
                        first_id = Identification(record_id=record.id, sequence=0)
                        session.add(first_id)

                    #print(quick_verbatim_sci_name, first_id)
                    first_id.verbatim_identification = quick_verbatim_sci_name
                    session.commit()
                    record.update_proxy()
                    new_source_data['quick__scientific_name'] = quick_sci_name

                new_source_data['quick__other_text_on_label'] = payload['quick__other_text_on_label']
                new_source_data['quick__user_note'] = payload['quick__user_note']
                new_source_data['quick__user_note__uid'] = current_user.id

                # identifications
                if payload['quick__id1_id']:
                    if id1 := record.identifications.filter(Identification.id==payload['quick__id1_id']).first():
                        id1.verbatim_identifier = payload['quick__id1_verbatim_identifier']
                        id1.verbatim_date = payload['quick__id1_verbatim_date']
                        id1.verbatim_identification = payload['quick__id1_verbatim_identification']
                else:
                    if payload['quick__id1_verbatim_identifier'] or \
                       payload['quick__id1_verbatim_date'] or \
                       payload['quick__id1_verbatim_identification']:
                        id1 = Identification(record_id=record.id, sequence=1)
                        if x := payload.get('quick__id1_verbatim_identifier'):
                            id1.verbatim_identifier = x
                        if x := payload.get('quick__id1_verbatim_date'):
                            id1.verbatim_date = x
                        if x := payload.get('quick__id1_verbatim_identification'):
                            id1.verbatim_identification = x
                        session.add(id1)

                if payload['quick__id2_id']:
                    if id2 := record.identifications.filter(Identification.id==payload['quick__id2_id']).first():
                        id2.verbatim_identifier = payload['quick__id2_verbatim_identifier']
                        id2.verbatim_date = payload['quick__id2_verbatim_date']
                        id2.verbatim_identification = payload['quick__id2_verbatim_identification']
                else:
                    if payload['quick__id2_verbatim_identifier'] or \
                       payload['quick__id2_verbatim_date'] or \
                       payload['quick__id2_verbatim_identification']:
                        id2 = Identification(record_id=record.id, sequence=2)
                        if x := payload.get('quick__id2_verbatim_identifier'):
                            id2.verbatim_identifier = x
                        if x := payload.get('quick__id2_verbatim_date'):
                            id2.verbatim_date = x
                        if x := payload.get('quick__id2_verbatim_identification'):
                            id2.verbatim_identification = x
                        session.add(id2)

                if len(new_source_data):
                    record.source_data = new_source_data
                anno = unit.get_annotation('is_ppi_transcribe')
                if not anno:
                    if atype := AnnotationType.query.filter(AnnotationType.name=='is_ppi_transcribe').first():
                        ua = UnitAnnotation(unit_id=unit.id, value='on', annotation_type_id=atype.id)
                        session.add(ua)

                hist = ModelHistory(
                    tablename='record*',
                    item_id=record.id,
                    action = 'quick-edit',
                    user_id=current_user.id,
                    changes=payload,
                )
                session.add(hist)
                session.commit()
                return jsonify({
                    'message': '快速編輯',
                    'content': f'[{item_key}]已存檔'
                })
        except Exception as err:
          return jsonify({
              'message': 'error',
              'content': str(err)
          })

    return jsonify({
        'message': 'error',
        'content': 'item_key error'
    })


@admin.route('/api/searchbar')
@jwt_required()
def api_searchbar():
    q = request.args.get('q', '')
    q = q.strip()
    collection_ids = current_user.site.collection_ids

    if len(q) <= 3:
        # sorting starts from inhereted name in english
        like_cond = f'{q}%'
    else:
        like_cond = f'%{q}%'

    collectors = Person.query.filter(Person.full_name.ilike(like_cond) | Person.full_name_en.ilike(like_cond) | Person.sorting_name.ilike(like_cond)).all()

    # taxa
    taxon_query = Taxon.query
    many_or = or_(Taxon.full_scientific_name.ilike(like_cond), Taxon.common_name.ilike(f'%{q}%'))

    hybrid_name_or = try_hybrid_name_stmt(q, Taxon.full_scientific_name)
    if str(hybrid_name_or): # if not str, will casu Boolean value clause error
        many_or = or_(many_or, hybrid_name_or)
    taxa = taxon_query.filter(many_or).limit(50).all()

    field_number_stmt = select(Record.id, Person, Record.field_number).join(Person).where(Record.field_number.ilike(f'{q}%')).where(Record.collector_id > 0, Record.collection_id.in_(collection_ids)).limit(50)
    field_number_res = session.execute(field_number_stmt).all()

    catalog_number_stmt = select(Unit.record_id, Unit.accession_number).where(Unit.accession_number.ilike(f'{q}%'), Unit.collection_id.in_(collection_ids)).limit(20)
    catalog_number_res = session.execute(catalog_number_stmt).all()

    categories = [{
        'label': gettext('學名'),
        'key': 'taxon',
        'items': [x.to_dict() for x in taxa],
    }, {
        'label': gettext('採集者'),
        'key': 'collector',
        'items': [x.to_dict() for x in collectors],
    }, {
        'label': gettext('採集號'),
        'key': 'field_number',
        'items': [[x[0], x[1].to_dict(), x[2]] for x in field_number_res],
    },  {
        'label': gettext('館號'),
        'key': 'catalog_number',
        'items': [[x[0], x[1]] for x in catalog_number_res],
    }]

    return jsonify(categories)

# @admin.route('/export-data', methods=['GET', 'POST'])
# @login_required
# def export_data():
#     if request.method == 'GET':
#         return render_template('admin/export-data.html')
#     else:
#         export_specimen_dwc_csv()
#         return ''


@admin.route('/print-label')
@login_required
def print_label():
    keys = request.args.get('entities', '')
    cat_id = request.args.get('category_id')
    sort = request.args.get('sort', '')

    download = request.args.get('download', '')
    #query = Collection.query.join(Person).filter(Collection.id.in_(ids.split(','))).order_by(Person.full_name, Collection.field_number)#.all()
    items = []

    if cat_id:
        entities = UserList.query.filter(UserList.category_id==cat_id, UserList.user_id==current_user.id).order_by(UserList.created).all()
        for i in entities:
            if x := get_entity_for_print(i.entity_id):
                items.append(x)

    elif keys:
        key_list = [x for x in keys.split(',') if x]
        items = [get_entity_for_print(key) for key in key_list]

    if sort:
        item_map = {}
        if sort == 'created':
            pass
        if sort == 'field-number':

            for i in items:
                if record:= i['record']:
                    if record.collector_id:
                        collector = record.collector.display_name
                        if collector not in item_map:
                            item_map[collector] = {}
                        n = record.field_number_int or 0
                        item_map[collector][int(n)] = i

            sorted_items_collector = sorted(item_map.items(), key = lambda x: x[0])

            items = []
            for d in sorted_items_collector:
                sorted_data = sorted(d[1].items(), key = lambda x: x[0])
                items += [x[1] for x in sorted_data]

    if download:

        docx = make_print_docx(items)
        buf = BytesIO()
        docx.save(buf)
        buf.seek(0)

        return send_file(
            buf,
            as_attachment=True,
            download_name="output.docx",
            mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document'
        )

    else:
        return render_template('admin/print-label.html', items=items)


@admin.route('/user-list')
@login_required
def user_list():
    #list_cats = current_user.get_user_lists()
    list_cats = {}
    for cat in current_user.user_list_categories:
        list_cats[cat.id] = {
            'items': [],
            'name': cat.name,
        }
        for item in UserList.query.filter(
                UserList.category_id==cat.id,
                UserList.user_id==current_user.id).all():
            item = {
                'id': item.id,
                'entity_key': item.entity_id,
                'entity': get_entity(item.entity_id)
            }
            list_cats[cat.id]['items'].append(item)

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


@admin.route('/api/relation/<rel_type>', methods=['GET', 'POST'])
def relation_resource(rel_type):
    if request.method == 'POST':
        if rel_type == 'taxon':
            payload = request.json
            if taxon := session.get(Taxon, payload['item_id']):
                rels = TaxonRelation.query.filter(TaxonRelation.child_id==taxon.id, TaxonRelation.depth > 0).all() # remove higher taxa relations
                for rel in rels:
                    session.delete(rel)
                    current_app.logger.debug(f'deleted Relation {rel}')

                rank_depth = taxon.rank_depth
                for i in range(rank_depth):
                    rank_name = Taxon.RANK_HIERARCHY[i]
                    tr = TaxonRelation(
                        child_id=taxon.id,
                        parent_id=payload['data'][rank_name]['id'],
                        depth=rank_depth - i
                    )
                    session.add(tr)
                    current_app.logger.debug(f'added Relation {tr}')
                rel = TaxonRelation.query.filter(TaxonRelation.child_id==taxon.id, TaxonRelation.depth == 0).first()
                if not rel:
                    rel_new = TaxonRelation(
                        child_id=taxon.id,
                        parent_id=taxon.id,
                        depth=0
                    )
                    session.add(rel_new)
                    current_app.logger.debug(f'added Relation {rel_new}')

                # reset higher taxon relation
                if rank_depth < len(Taxon.RANK_HIERARCHY):
                    rels = TaxonRelation.query.filter(TaxonRelation.parent_id==taxon.id).all()
                    children_ids = [x.child_id for x in rels]
                    rels2 = TaxonRelation.query.filter(TaxonRelation.child_id.in_(children_ids), TaxonRelation.depth > rank_depth, TaxonRelation.parent_id != taxon.id).all()
                    for rel in rels2:
                        session.delete(rel)
                        current_app.logger.debug(f'reset Relation {rel}')

                session.commit()
                return jsonify({'message': 'ok'})

    elif request.method == 'GET':
        item_id = request.args.get('item_id', '')
        action = request.args.get('action', '')
        form_list = []
        if rel_type == 'taxon':
            if item_id:
                taxon = session.get(Taxon, item_id)
                if not taxon:
                    return jsonify({'message': 'not found'})

                if action == 'get_form_list':
                    rank_depth = taxon.rank_depth
                    for t in taxon.get_parents():
                        form_list.append({
                            'label': t.rank,
                            'name': t.rank,
                            'value': t.id,
                            'options': [{'id': x.id, 'text': x.display_name} for x in t.get_siblings()]
                        })
                    return jsonify({'form_list': form_list})
                elif action == 'get_children':
                    options = []
                    if children := taxon.get_children(1):
                        for x in children:
                            if x: # if delete, this will be None
                                options.append({'id': x.id, 'text': x.display_name})
                    return jsonify ({'message': 'ok', 'options': options})
            else:
                if action == 'get_form_list':
                    for index, rank in enumerate(Taxon.RANK_HIERARCHY[0:-1]):
                        options = []
                        if index == 0:
                            opts = Taxon.query.filter(Taxon.rank == rank).all()
                            for x in opts:
                                options.append({'id': x.id, 'text': x.display_name})

                        form_list.append({
                            'label': rank,
                            'name': rank,
                            'value': '',
                            'options': options,
                        })
                    return jsonify({'form_list': form_list})
    return jsonify ({'message': 'not found'})

@admin.route('/units/<int:unit_id>/simple-entry')
@login_required
def unit_simple_entry(unit_id):
    if unit := session.get(Unit, unit_id):
        collection_ids = current_user.site.collection_ids
        if unit.collection_id in collection_ids:
            # Volunteer access control - must have task assigned
            if current_user.role == 'B':  # Volunteer
                from app.models.collection import VolunteerTask
                task = session.query(VolunteerTask)\
                    .filter(VolunteerTask.unit_id == unit_id,
                           VolunteerTask.volunteer_id == current_user.id)\
                    .first()

                if not task:
                    flash('此標本未分配給您 / This specimen is not assigned to you', 'warning')
                    return redirect(url_for('admin.volunteer_my_tasks'))

            return render_template('admin/unit-simple-entry.html', unit=unit)

    return abort(404)


# ============= VOLUNTEER TASK MANAGEMENT =============

@admin.route('/volunteer-tasks')
@login_required
def volunteer_task_list():
    """
    Admin interface for viewing and managing volunteer task assignments.
    Only accessible to admin users (role='A').
    """
    if current_user.role != 'A':
        flash('僅限管理員訪問 / Access denied: Admin only', 'error')
        return redirect(url_for('admin.index'))

    # Get all volunteers for this site (role='B')
    volunteers = User.query.filter(
        User.site_id == current_user.site_id,
        User.role == 'B',
        User.status == 'P'  # Active users only
    ).order_by(User.username).all()

    return render_template(
        'admin/volunteer-task-list.html',
        volunteers=volunteers
    )


@admin.route('/api/volunteer-tasks', methods=['GET'])
@jwt_required()
def api_volunteer_tasks_list():
    """
    API endpoint to fetch volunteer tasks with filtering.
    Query params:
    - volunteer_id: Filter by volunteer
    - status: Filter by status (assigned/completed)
    - unit_ids: Comma-separated list of unit IDs (for checking existing assignments)
    """
    from app.models.collection import VolunteerTask

    volunteer_id = request.args.get('volunteer_id', type=int)
    status = request.args.get('status')
    unit_ids_str = request.args.get('unit_ids')

    # Base query - filter by site's collections
    query = session.query(VolunteerTask)\
        .join(Unit, VolunteerTask.unit_id == Unit.id)\
        .join(Collection, Unit.collection_id == Collection.id)\
        .filter(Collection.site_id == current_user.site_id)

    # Apply filters
    if volunteer_id:
        query = query.filter(VolunteerTask.volunteer_id == volunteer_id)

    if status:
        query = query.filter(VolunteerTask.status == status)

    if unit_ids_str:
        unit_ids = [int(x) for x in unit_ids_str.split(',')]
        query = query.filter(VolunteerTask.unit_id.in_(unit_ids))

    tasks = query.order_by(desc(VolunteerTask.assigned_date)).all()

    return jsonify({
        'tasks': [task.to_dict() for task in tasks],
        'total': len(tasks)
    })


@admin.route('/api/volunteer-tasks/batch-assign', methods=['POST'])
@jwt_required()
def api_volunteer_tasks_batch_assign():
    """
    Batch assign units to a volunteer.
    Payload: {
        "volunteer_id": int,
        "unit_ids": [int, int, ...]
    }
    Returns: {
        "success": int (count),
        "skipped": int (already assigned),
        "errors": [...]
    }
    """
    from app.models.collection import VolunteerTask

    # Admin only
    if current_user.role != 'A':
        return jsonify({'error': '僅限管理員 / Admin access required'}), 403

    payload = request.json
    volunteer_id = payload.get('volunteer_id')
    unit_ids = payload.get('unit_ids', [])

    if not volunteer_id or not unit_ids:
        return jsonify({'error': '需要 volunteer_id 和 unit_ids / volunteer_id and unit_ids required'}), 400

    # Verify volunteer exists and belongs to same site
    volunteer = session.get(User, volunteer_id)
    if not volunteer or volunteer.site_id != current_user.site_id:
        return jsonify({'error': '無效的志工 / Invalid volunteer'}), 400

    success_count = 0
    skipped_count = 0
    errors = []

    # Get site's collection IDs
    collection_ids = [c.id for c in current_user.site.collections]

    for unit_id in unit_ids:
        try:
            # Check if unit exists and belongs to site's collections
            unit = session.get(Unit, unit_id)
            if not unit or unit.collection_id not in collection_ids:
                errors.append(f'Unit {unit_id}: 未找到或訪問被拒 / not found or access denied')
                continue

            # Check if already assigned
            existing = session.query(VolunteerTask)\
                .filter(VolunteerTask.unit_id == unit_id)\
                .first()

            if existing:
                skipped_count += 1
                continue

            # Create new task
            task = VolunteerTask(
                unit_id=unit_id,
                volunteer_id=volunteer_id,
                assigned_by_id=current_user.id,
                status='assigned'
            )
            session.add(task)
            success_count += 1

        except Exception as e:
            errors.append(f'Unit {unit_id}: {str(e)}')

    try:
        session.commit()

        # Log the batch assignment
        hist = ModelHistory(
            tablename='volunteer_task',
            item_id=f'batch_{volunteer_id}',
            action='batch-assign',
            user_id=current_user.id,
            changes={'volunteer_id': volunteer_id, 'count': success_count}
        )
        session.add(hist)
        session.commit()

        return jsonify({
            'success': success_count,
            'skipped': skipped_count,
            'errors': errors,
            'message': f'成功分配 {success_count} 個任務 / Successfully assigned {success_count} tasks'
        })
    except Exception as e:
        session.rollback()
        return jsonify({'error': str(e)}), 500


@admin.route('/api/volunteer-tasks/<int:task_id>', methods=['DELETE'])
@jwt_required()
def api_volunteer_task_delete(task_id):
    """
    Unassign a task (delete assignment).
    Admin only.
    """
    from app.models.collection import VolunteerTask

    if current_user.role != 'A':
        return jsonify({'error': '僅限管理員 / Admin access required'}), 403

    task = session.get(VolunteerTask, task_id)
    if not task:
        return jsonify({'error': '任務未找到 / Task not found'}), 404

    # Verify task belongs to site's units
    collection_ids = [c.id for c in current_user.site.collections]
    if task.unit.collection_id not in collection_ids:
        return jsonify({'error': '訪問被拒 / Access denied'}), 403

    session.delete(task)
    session.commit()

    return jsonify({'message': '任務已刪除 / Task deleted'}), 200


@admin.route('/api/volunteer-tasks/<int:task_id>/reassign', methods=['PATCH'])
@jwt_required()
def api_volunteer_task_reassign(task_id):
    """
    Reassign a task to different volunteer.
    Payload: {"volunteer_id": int}
    """
    from app.models.collection import VolunteerTask

    if current_user.role != 'A':
        return jsonify({'error': '僅限管理員 / Admin access required'}), 403

    task = session.get(VolunteerTask, task_id)
    if not task:
        return jsonify({'error': '任務未找到 / Task not found'}), 404

    new_volunteer_id = request.json.get('volunteer_id')
    if not new_volunteer_id:
        return jsonify({'error': '需要 volunteer_id / volunteer_id required'}), 400

    # Verify new volunteer
    volunteer = session.get(User, new_volunteer_id)
    if not volunteer or volunteer.site_id != current_user.site_id:
        return jsonify({'error': '無效的志工 / Invalid volunteer'}), 400

    old_volunteer_id = task.volunteer_id
    task.volunteer_id = new_volunteer_id
    task.assigned_by_id = current_user.id
    task.assigned_date = get_time()

    session.commit()

    # Log reassignment
    hist = ModelHistory(
        tablename='volunteer_task',
        item_id=str(task_id),
        action='reassign',
        user_id=current_user.id,
        changes={'from': old_volunteer_id, 'to': new_volunteer_id}
    )
    session.add(hist)
    session.commit()

    return jsonify(task.to_dict())


@admin.route('/my-tasks')
@login_required
def volunteer_my_tasks():
    """
    Volunteer interface showing their assigned tasks.
    Accessible to all authenticated users.
    """
    from app.models.collection import VolunteerTask

    # Get progress stats
    progress = VolunteerTask.get_volunteer_progress(current_user.id)

    return render_template(
        'admin/volunteer-my-tasks.html',
        progress=progress
    )


@admin.route('/api/my-tasks', methods=['GET'])
@jwt_required()
def api_my_tasks_list():
    """
    API to fetch current user's assigned tasks.
    Query params:
    - status: Filter by status (default: 'assigned')
    """
    from app.models.collection import VolunteerTask

    status = request.args.get('status', 'assigned')

    query = session.query(VolunteerTask)\
        .filter(VolunteerTask.volunteer_id == current_user.id)

    if status:
        query = query.filter(VolunteerTask.status == status)

    tasks = query.order_by(VolunteerTask.assigned_date).all()

    # Enrich with unit details
    tasks_data = []
    for task in tasks:
        task_dict = task.to_dict()
        if task.unit:
            task_dict['unit'] = {
                'id': task.unit.id,
                'catalog_number': task.unit.accession_number,
                'image_url': task.unit.get_cover_image('s') if hasattr(task.unit, 'get_cover_image') and task.unit.cover_image_id else None,
                'collection_name': task.unit.collection.label if task.unit.collection else None,
            }
        tasks_data.append(task_dict)

    return jsonify({
        'tasks': tasks_data,
        'total': len(tasks_data)
    })


@admin.route('/api/my-tasks/navigation/<int:unit_id>')
@jwt_required()
def api_my_tasks_navigation(unit_id):
    """
    Get previous/next unit IDs within volunteer's assigned tasks.
    Used for task-bounded navigation.
    """
    from app.models.collection import VolunteerTask

    # Get all assigned task unit IDs for current user, ordered by assigned_date
    task_unit_ids = [t.unit_id for t in session.query(VolunteerTask.unit_id)\
        .filter(VolunteerTask.volunteer_id == current_user.id,
               VolunteerTask.status == 'assigned')\
        .order_by(VolunteerTask.assigned_date)\
        .all()]

    try:
        current_index = task_unit_ids.index(unit_id)
        prev_unit_id = task_unit_ids[current_index - 1] if current_index > 0 else None
        next_unit_id = task_unit_ids[current_index + 1] if current_index < len(task_unit_ids) - 1 else None

        return jsonify({
            'current_index': current_index + 1,
            'total': len(task_unit_ids),
            'prev_unit_id': prev_unit_id,
            'next_unit_id': next_unit_id
        })
    except ValueError:
        return jsonify({'error': '單元不在已分配的任務中 / Unit not in assigned tasks'}), 404


class GridItemAPI(MethodView):
    init_every_request = False

    def __init__(self, register):
        self.register = register
        self.site = session.get(Site, 1) #current_user.site TODO

    def _get_item(self, item_id):
        if item := session.get(self.register['model'], item_id):
            return item
        return abort(404)

    @jwt_required()
    def patch(self, item_id):
        item = self._get_item(item_id)
        #errors = self.validator.validate(item, request.json)
        #if errors:
        #return jsonify({'err': ''}), 400
        current_app.logger.debug(f'grid patch: {request.json}')
        try:
            rel_data = {}
            for k, v in request.json.items():
                key = k
                value = v
                if foreign_models := self.register.get('foreign_models'):
                    if k in foreign_models:
                        key = f'{k}_id'
                else:
                    if field := self.register['fields'].get(k):
                        if type_ := field.get('type'):
                            if type_ == 'date':
                                value = datetime.strptime(v, '%m/%d/%Y').date()
                            if type_ == 'boolean':
                                value = True if v == 'on' else False

                setattr(item, key, value)

                if 'relation__taxon' in k:
                    k_rank = k.replace('relation__taxon_', '')
                    rel_data[k_rank] = value

            if len(rel_data) > 0:
                item.make_relations(rel_data)


            # 另外處理 uncheck => set boolean False
            for field, data in self.register['fields'].items():
                if data.get('type', '') == 'boolean' and \
                   getattr(item, field) == True and \
                   field not in request.json:
                    setattr(item, field, False)

            if changes := inspect_model(item):
                history = ModelHistory(
                    user_id=current_user.id,
                    tablename=item.__tablename__,
                    action='update',
                    item_id=item_id,
                    changes=changes,
                )
                session.add(history)

            session.commit()

            resp = jsonify({
                'message': 'success',
                'verbose':f"patch {self.register['name']} [{item_id}]"
            })
        except Exception as e:
            current_app.logger.error(e)
            resp = jsonify({'message': 'error', 'verbose': str(e)})

        resp.headers.add('Access-Control-Allow-Origin', '*')
        resp.headers.add('Access-Control-Allow-Methods', '*')
        return resp

    @jwt_required()
    def delete(self, item_id):
        item = self._get_item(item_id)
        try:
            # find relations
            item_map = inspect(item.__class__)
            relations = []
            for x in item_map.relationships:
                relations.append(str(x).replace(f'{item.__class__.__name__}.', ''))

            payload = {}
            for field in self.register['fields']:
                if field in relations:
                    payload[f'{field}_id'] = getattr(item, f'{field}_id')
                else:
                    if type_ := self.register['fields'][field].get('type'):
                        if type_ == 'date':
                            if dt := getattr(item, field):
                                payload[field] = dt.strftime('%Y-%m-%d')
                    else:
                        payload[field] = getattr(item, field)

            history = ModelHistory(
                user_id=current_user.id,
                tablename=item.__tablename__,
                action='delete',
                item_id=item_id,
                changes=payload
            )
            session.add(history)

            session.delete(item)

            session.commit()
            resp = jsonify({'message': 'success'})
        except Exception as e:
            current_app.logger.error(e)
            resp = jsonify({'message': 'error', 'verbose': str(e)})

        resp.headers.add('Access-Control-Allow-Origin', '*')
        resp.headers.add('Access-Control-Allow-Methods', '*')
        return resp

class GridListAPI(MethodView):
    init_every_request = False
    def __init__(self, register):
        self.register = register

    @jwt_required()
    def get(self):
        payload = {
            'filter': json.loads(request.args.get('filter')) if request.args.get('filter') else {},
            'sort': json.loads(request.args.get('sort')) if request.args.get('sort') else {},
            'range': json.loads(request.args.get('range')) if request.args.get('range') else [0, 50],
        }

        query = self.register['model'].query

        if q := payload['filter'].get('q'):
            many_or = or_()
            for field in self.register['search_fields']:
                attr = getattr(self.register['model'], field)
                many_or = or_(many_or, attr.ilike(f'%{q}%'))
            query = query.filter(many_or)

        if self.register.get('filter_by', '') == 'site':
            site_id = current_user.site_id
            attr = getattr(self.register['model'], 'site_id')
            query = query.filter(attr==site_id)
        elif self.register.get('filter_by', '') == 'user':
            attr = getattr(self.register['model'], 'user_id')
            query = query.filter(attr==current_user.id)
        elif self.register.get('filter_by', '') == 'site.collections':
            collection_ids = current_user.site.collection_ids
            attr = getattr(self.register['model'], 'collection_id')
            query = query.filter(attr.in_(collection_ids))
        # if collection_id := request.args.get('collection_id'):
        #     if collection_filter := self.register.get('list_collection_filter'):
        #         if related := collection_filter.get('related'):
        #             query = query.select_from(Collection).join(related)
        #             query = query.filter(Collection.id==collection_id)
        #         elif field := collection_filter.get('field'):
        #             query = query.filter(field==int(collection_id))


        reg_name = self.register.get('name')
        if reg_name == 'taxon':
            if rank := payload['filter'].get('rank'):
                query = query.filter(Taxon.rank==rank)
            if parent_id := payload['filter'].get('parent_id'):
                if parent := session.get(Taxon, parent_id):
                    depth = Taxon.RANK_HIERARCHY.index(parent.rank)
                    taxa_ids = [x.id for x in parent.get_children(depth)]
                    query = query.filter(Taxon.id.in_(taxa_ids))

        total = query.count()

        if sort_list := payload.get('sort'):
            for sort in sort_list:
                field = sort.replace('-', '')
                attr = getattr(self.register['model'], field)
                if sort.startswith('-'):
                    query = query.order_by(desc(attr))
                else:
                    query = query.order_by(attr)
        else:
            if self.register.get('order_by'):
                if self.register['order_by'].startswith('-'):
                    query = query.order_by(desc(self.register['order_by'][1:]))
                else:
                    query = query.order_by(self.register['order_by'])

        if reg_name == 'taxon' and len(payload['filter']):
            # taxon, filter no limit
            pass
        else:
            query = query.offset(payload['range'][0]).limit(payload['range'][1])

        current_app.logger.debug(query)
        data = []
        for r in query.all():
            row = {
                'id': r.id,
            }
            for field in self.register['fields']:
                text = getattr(r, field)
                if foreign_models := self.register.get('foreign_models'):
                    if field in foreign_models:
                        model = foreign_models[field]
                        text = getattr(getattr(r, field), model[1]) # display relationship
                        row[f'{field}_id'] = getattr(r, f'{field}_id')

                if type_ := self.register['fields'][field].get('type'):
                    if type_ == 'date':
                        text = text.strftime(self.register['fields'][field]['format'])

                row[field] = text
                # if rules := self.register.get('list_display_rules', {}).get(field):
                #     # TODO
                #     if rules[0] == 'clean':
                #         if rules[1] == 'striptags':
                #             re_clean = re.compile('<.*?>')
                #             row[f'{field}__clean'] = re.sub(re_clean, '', getattr(r, field))
                #         elif rules[1] == 'ymd':
                #             row[f'{field}__clean'] = getattr(r, field).strftime('%Y-%m-%d')

            # add relations
            if reg_name == 'taxon':
                for p in r.get_higher_taxon():
                    row[f'relation__taxon_{p.rank}'] = {
                        'id': p.id,
                        'text': p.display_name
                    }

            data.append(row)

        return jsonify({
            'total': total,
            'data': data
        })

    @jwt_required()
    def post(self):
        payload = request.json
        instance = self.register['model']()
        current_app.logger.debug(f'post {payload}')
        try:
            # remove empty id
            del payload['id']
            if self.register.get('filter_by', '') == 'site':
                payload['site_id'] = current_user.site_id
            elif self.register.get('filter_by', '') == 'user':
                payload['user_id'] = current_user.id

            for k, v in payload.items():
                key = k
                value = v
                if foreign_models := self.register.get('foreign_models'):
                    if k in foreign_models:
                        key = f'{k}_id'
                else:
                    if field := self.register['fields'].get(k):
                        if type_ := field.get('type'):
                            if type_ == 'boolean':
                                value = True if v == 'on' else False

                setattr(instance, key, value)

            session.add(instance)
            session.commit()
            if changes := inspect_model(instance):
                history = ModelHistory(
                    user_id=current_user.id,
                    tablename=item.__tablename__,
                    action='create',
                    item_id=instance.id,
                    changes=changes,
                )
                session.add(history)

            session.commit()
            resp = jsonify({
                'message': 'success',
                'verbose':f"post {self.register['name']} [{instance.id}]"
            })
        except Exception as e:
            current_app.logger.error(e)
            resp = jsonify({'message': 'error', 'verbose': str(e)})

        # TODO
        # if relation_taxon := payload.get('relation__taxon'):
        #     rel_data = {}
        #     values = relation_taxon.split('|')
        #     for v in values:
        #         vlist = v.split(':')
        #         rel_data[vlist[0]] = vlist[1]

        #     instance.make_relations(rel_data)

        resp.headers.add('Access-Control-Allow-Origin', '*')
        resp.headers.add('Access-Control-Allow-Methods', '*')
        return resp


class GridView(View):

    def __init__(self, register):
        self.register = register
        self.template = 'admin/grid-view.html'

    def dispatch_request(self):

        # login_requried
        if not current_user.is_authenticated:
            return redirect('/login')

        fields = self.register['fields']
        if models := self.register.get('foreign_models'):
            for k, v in models.items():
                if filter_by := self.register.get('filter_by'):
                    if filter_by == 'site':
                        attr = getattr(v[0], 'site_id')
                        options = v[0].query.filter(attr==current_user.site_id).all()
                    elif filter_by == 'site.collections':
                        collection_ids = current_user.site.collection_ids
                        attr = getattr(v[0], 'id')
                        options = v[0].query.filter(attr.in_(collection_ids)).all()

                fields[k]['options'] = [ {'id': x.id, 'text': getattr(x, v[1])} for x in options ]

        # for fields can sorted
        if layout := self.register.get('form_layout'):
            form_layout = layout
        else:
            form_layout = [x for x in fields]

        #print(fields)
        grid_info = {
            'name': self.register['name'],
            'label': self.register['label'],
            'resource_name': self.register['resource_name'],
            'fields': fields,
            'list_display': self.register['list_display'],
            'form_layout': form_layout,
            'list_display_rules': self.register.get('list_display_rules', {}),
        }
        if x := self.register.get('search_fields'):
            grid_info['search_fields'] = x
        if x := self.register.get('relations', {}):
            grid_info['relations'] = x

        admin_api_url = request.root_url
        # flask's request in prod env request.base_url will generate 'http' not 'https'
        if current_app.config['WEB_ENV'] != 'dev':
            if admin_api_url[0:5] == 'http:':
                admin_api_url = admin_api_url.replace('http:', 'https:')

        return render_template(self.template, grid_info=grid_info, admin_api_url=admin_api_url)


class RecordItemAPI(MethodView):
    init_every_request = False
    site = None

    def __init__(self, model):
        self.model = model
        #self.validator = generate_validator(model)

    def _get_item(self, id):
        if item := session.get(self.model, id):
            return item
        return abort(404)

    def get(self, id):
        item = self._get_item(id)

        resp = jsonify(item.get_values())
        resp.headers.add('Access-Control-Allow-Origin', '*')
        resp.headers.add('Access-Control-Allow-Methods', '*')
        return resp

    @jwt_required()
    def patch(self, id):
        item = self._get_item(id)
        #errors = self.validator.validate(item, request.json)
        #if errors:
        #return jsonify({'err': ''}), 400

        if uid := get_jwt_identity():
            if isinstance(item, self.model):
                if data_type := current_user.site.get_settings('data-type'):
                    if data_type == 'raw':
                        res = put_entity_raw(item, request.json, item.collection, uid)
                else:
                    res = put_entity(item, request.json, item.collection, uid)
            else:
                res = item.update_from_dict(request.json)

            resp = jsonify(res)
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Methods', '*')
            return resp
        else:
            return 403

        return 400

    @jwt_required()
    def delete(self, id):
        item = self._get_item(id)
        if hasattr(self.model, 'delete_by_instance'):
            self.model.delete_by_instance(session, item)
        else:
            db.session.delete(item)
            db.session.commit()

        return "", 204


class RecordListAPI(MethodView):
    init_every_request = False
    site = None

    def __init__(self, model):
        self.model = model
        #self.validator = generate_validator(model, create=True)
        self.site = session.get(Site, 1) #current_user.site TODO

    @jwt_required()
    def get(self):
        site = self.site

        payload = {
            'filter': json.loads(request.args.get('filter')) if request.args.get('filter') else {},
            'sort': json.loads(request.args.get('sort')) if request.args.get('sort') else {},
            'range': json.loads(request.args.get('range')) if request.args.get('range') else [0, 50],
        }

        if uid := get_jwt_identity():
            ids = current_user.site.collection_ids
            #if user.role: TODO
            auth = {
                'collection_id': ids,
                'role': 'admin',
            }
            mode = ''
            if data_type := current_user.site.get_settings('data-type'):
                if data_type == 'raw':
                    mode = 'raw'

            results = self.model.get_items(payload, auth, mode)
            return jsonify(results)

    @jwt_required()
    def post(self):
        #errors = self.validator.validate(request.json)

        #if errors:
        #    return jsonify(errors), 400

        if uid := get_jwt_identity():
            res, item = self.model.from_dict(request.json, uid)
            resp = jsonify(res)
            resp.headers.add('Access-Control-Allow-Origin', '*')
            resp.headers.add('Access-Control-Allow-Methods', '*')
            return resp
        else:
            return 403

    def options(self):
        res = Response()
        #res.headers['Access-Control-Allow-Origin'] = '*' 不行, 跟before_request重複?
        res.headers['Access-Control-Allow-Headers'] = '*'
        res.headers['X-Content-Type-Options'] = 'GET, POST, OPTIONS, PATCH, DELETE'
        res.headers['Access-Control-Allow-Headers'] = 'Content-Type'
        res.headers.add('Access-Control-Allow-Origin', '*')
        res.headers.add('Access-Control-Allow-Methods', '*')
        return res

'''
def register_api(app, model, res_name):
    app.add_url_rule(
        f'/api/{res_name}/<int:id>',
        view_func=ItemAPI.as_view(f'api-{res_name}-item', model),
        methods=['GET', 'OPTIONS', 'DELETE', 'PATCH'],
    )
    app.add_url_rule(
        f'/api/{res_name}/',
        view_func=ListAPI.as_view(f'api-{res_name}-list', model),
        methods=['GET', 'POST']
    )

register_api(admin, Record, 'records')
'''
admin.add_url_rule(
    f'/api/records/<int:id>',
    view_func=RecordItemAPI.as_view(f'api-record-item', Record),
    methods=['GET', 'OPTIONS', 'DELETE', 'PATCH'],
)
admin.add_url_rule(
    f'/api/records/',
    view_func=RecordListAPI.as_view(f'api-record-list', Record),
    methods=['GET', 'POST']
)
def register_grids(names, data):
    for name in names:
        reg = data[name]
        res_name = reg['resource_name']
        admin.add_url_rule(
            f'/{res_name}',
            view_func=GridView.as_view(f'{name}-list', reg),
            methods=['GET',]
        )
        admin.add_url_rule(
            f'/api/{res_name}/<int:item_id>',
            view_func=GridItemAPI.as_view(f'api-{res_name}-item', reg),
            methods=['GET', 'OPTIONS', 'DELETE', 'PATCH'],
        )
        admin.add_url_rule(
            f'/api/{res_name}/',
            view_func=GridListAPI.as_view(f'api-{res_name}-list', reg),
            methods=['GET', 'POST']
        )

resources = [
    'taxon',
    'person',
    'article',
    'user_list_category',
    'article_category',
    'related_link',
    'related_link_category',
    'collection',
    'record_group',
]
register_grids(resources, ADMIN_REGISTER_MAP)
