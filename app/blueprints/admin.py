#from functools import wraps
import re
import math

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
)
from sqlalchemy.orm import (
    aliased,
)
from app.models.collection import (
    Collection,
    Record,
    RecordAssertion,
    AssertionType,
    AreaClass,
    NamedArea,
    Project,
    Unit,
    UnitAssertion,
    Identification,
    Person,
    Transaction,
    AnnotationType,
    Annotation,
    Taxon,
    get_entity,
)
from app.models.site import (
    User,
)

from app.database import (
    session,
    db_insp,
    ModelHistory,
    ChangeLog,
)
from app.helpers import (
    get_current_site,
)
from .admin_register import ADMIN_REGISTER_MAP

admin = Blueprint('admin', __name__)

def get_record_all_options(collection_id):
    project_list = Project.query.all()
    atu_list = AssertionType.query.filter(AssertionType.target=='unit', AssertionType.collection_id==collection_id).all()
    atr_list = AssertionType.query.filter(AssertionType.target=='record', AssertionType.collection_id==collection_id).all()
    ac_list = AreaClass.query.filter(AreaClass.collection_id==collection_id).order_by(AreaClass.sort).all()
    tr_list = Transaction.EXCHANGE_TYPE_CHOICES

    return {
        'project': project_list,
        'assertion_type_record': atr_list,
        'assertion_type_unit': atu_list,
        'area_class': ac_list,
        'transaction_type': tr_list,
        'type_status': Unit.TYPE_STATUS_CHOICES,
        'annotation_type': AnnotationType.query.all(),
        'pub_status': Unit.PUB_STATUS_OPTIONS,
    }

def save_record(record, data, is_create=False):
    # check column type in table
    #table = db_insp.get_columns(Entity.__tablename__)
    #for c in table:
    #    print(c['name'], c['type'], flush=True)
    #print(columns_table, '-----------',flush=True)

    #print(data, flush=True)

    if is_create is True:
        session.add(record)
        session.commit()

    record_change_log = ChangeLog(record)

    # many to many fields
    m2m = {
        'named_areas': [],
        'record_assertions': [],
    }
    # one to many
    o2m = {
        'identifications': {},
        'units':{},
    }

    for name, value in data.items():
        if name in ['field_number', 'collect_date', 'collect_date_text','companion_text', 'companion_text_en', 'locality_text', 'verbatim_locality', 'latitude_decimal', 'longitude_decimal', 'verbatim_latitude', 'verbatim_longitude', 'altitude', 'altitude2','field_note', 'field_note_en', 'project_id', 'collection_id']:
            # validation
            is_valid = True

            # timestamp
            if name == 'collect_date' and value == '':
                is_valid = False

            # number
            if name in ['altitude', 'altitude2', 'latitude_decimal', 'longitude_decimal'] and value == '':
                is_valid = False

            if name in ['project_id']:
                # let it NULL
                if value == '':
                    value = None

            if is_valid is True:
                setattr(record, name, value)

        elif name in ['collector__hidden_value'] and value:
            name_key = name.replace('__hidden_value', '_id')
            setattr(record, name_key, value)

        elif match := re.search(r'^(named_areas|record_assertions)__(.+)__hidden_value', name):
            # print(match, match.group(1), match.group(2), value,flush=True)
            if value:
                name_class = match.group(1)
                name_part = match.group(2)
                m2m[name_class].append((name_part, value))

        elif match := re.search(r'^(identifications|units)__(NEW-[0-9]+|[0-9]+)__(.+)', name):
            # not accept only "__NEW__" => hidden template
            name_class = match.group(1)
            num = match.group(2)
            name_part = match.group(3)
            #print(name_class, num, name_part, value, flush=True)
            if num not in o2m[name_class]:
                o2m[name_class][num] = {}
            o2m[name_class][num][name_part] = value

            if name_class == 'units' and 'assertion' in name_part:
                # print(name_part, flush=True)
                assertion_part = name_part.replace('assertion__', '')
                if 'assertion' not in o2m[name_class][num]:
                    o2m[name_class][num]['assertion'] = {}
                if assertion_part not in o2m[name_class][num]['assertion']:
                    o2m[name_class][num]['assertion'][assertion_part] = {}
                o2m[name_class][num]['assertion'][assertion_part] = value

            if name_class == 'units' and 'annotation' in name_part:
                annotation_part = name_part.replace('annotation__', '')
                if 'annotation' not in o2m[name_class][num]:
                    o2m[name_class][num]['annotation'] = {}
                if annotation_part not in o2m[name_class][num]['annotation']:
                    o2m[name_class][num]['annotation'][annotation_part] = {}
                o2m[name_class][num]['annotation'][annotation_part] = value

    named_areas = []
    # print(m2m, flush=True)
    for i in m2m['named_areas']:
        # only need id
        if obj := session.get(NamedArea, int(i[1])):
            named_areas.append(obj)

    assertions = []
    for i in m2m['record_assertions']:
        type_id = int(i[0])
        val = i[1]
        if ea := RecordAssertion.query.filter(
                RecordAssertion.record_id==record.id,
                RecordAssertion.assertion_type_id==type_id).first():
            ea.value = val
        else:
            ea = RecordAssertion(record_id=record.id, assertion_type_id=type_id, value=val)
            session.add(ea)

        if ea:
            assertions.append(ea)

    #print(o2m, flush=True)
    updated_identifications = []
    for k, v in o2m['identifications'].items():
        date = v.get('date')
        date_text = v.get('date_text')
        identifier_id = v.get('identifier__hidden_value')
        taxon_id = v.get('taxon__hidden_value')
        sequence = v.get('sequence')
        if 'NEW-' in k:
            id_ = Identification(
                record_id=record.id,
            )
            session.add(id_)
        else:
            id_ = session.get(Identification, int(k))

        id_.date = date or None
        id_.date_text = date_text or None
        id_.identifier_id = identifier_id or None
        id_.taxon_id = taxon_id or None
        id_.sequence = int(sequence) if sequence else 0
        updated_identifications.append(id_)

    updated_units = []
    for k, v in o2m['units'].items():
        preparation_date = v.get('preparation_date')

        if 'NEW-' in k:
            unit = Unit(
                record_id=record.id,
            )
            session.add(unit)
        else:
            unit = session.get(Unit, int(k))

        unit_assertions = []
        if assertion := v.get('assertion'):
            for ak, val in assertion.items():
                if '__hidden_value' not in ak:
                    type_id = int(ak)
                    if ua := UnitAssertion.query.filter(
                            UnitAssertion.unit_id==unit.id,
                            UnitAssertion.assertion_type_id==type_id).first():
                        ua.value = val
                        unit_assertions.append(ua)
                    else:
                        if val:
                            ua = UnitAssertion(unit_id=unit.id, assertion_type_id=type_id, value=val)
                            session.add(ua)
                            unit_assertions.append(ua)

        unit_annotations = []
        # print(v, flush=True)
        if annotation := v.get('annotation'):
            for ak, val in annotation.items():
                type_id = int(ak)
                if anno := Annotation.query.filter(
                        Annotation.unit_id==unit.id,
                        Annotation.type_id==type_id).first():
                    anno.value = val
                    unit_annotations.append(anno)
                else:
                    anno = Annotation(unit_id=unit.id, type_id=type_id, value=val)
                    session.add(anno)
                    unit_annotations.append(anno)

        unit.assertions = unit_assertions
        unit.annotations = unit_annotations
        unit.accession_number = v.get('accession_number')
        unit.pub_status = v.get('pub_status')
        unit.preparation_date = preparation_date or None
        unit.type_is_published = True if v.get('type_is_published') else False
        unit.type_status = v.get('type_status', '')
        unit.typified_name = v.get('typified_name', '')
        unit.type_reference = v.get('type_reference', '')
        unit.type_reference_link = v.get('type_reference_link', '')
        unit.acquisition_type = v.get('acquisition_type')
        if x := v.get('acquisition_date'):
            unit.acquisition_date = x
        unit.acquisition_source_text = v.get('acquisition_source_text', '')


        updated_units.append(unit)

    record.named_areas = named_areas
    record.assertions = assertions
    record.identifications = updated_identifications
    record.units = updated_units

    changes = record_change_log.get_changes()

    session.commit()

    history = ModelHistory(
        user_id=current_user.id,
        tablename=record.__tablename__,
        action='update',
        item_id=record.id,
        changes=changes,
    )
    session.add(history)
    session.commit()

    return record

@admin.route('/static/<path:filename>')
@login_required
def static_file(filename):
    return send_from_directory('static_admin', filename)



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
@login_required
def index():
    site = current_user.organization
    collection_ids = site.collection_ids
    stats = {
        'record_count': Record.query.filter(Record.collection_id.in_(collection_ids)).count(),
        'record_lack_unit_count': Record.query.join(Unit, full=True).filter(Unit.id==None, Unit.collection_id.in_(collection_ids)).count(),
        'unit_count': Unit.query.filter(Unit.collection_id.in_(collection_ids)).count(),
        'unit_accession_number_count': Unit.query.filter(Unit.accession_number!='', Unit.collection_id.in_(collection_ids)).count(),
    }
    return render_template('admin/dashboard.html', stats=stats)


@admin.route('/records/', methods=['GET'])
@login_required
def record_list():
    site = current_user.organization

    current_page = int(request.args.get('page', 1))
    q = request.args.get('q', '')

    #stmt = select(Unit.id, Unit.accession_number, Entity.id, Entity.field_number, Person.full_name, Person.full_name_en, Entity.collect_date, Entity.proxy_taxon_scientific_name, Entity.proxy_taxon_common_name) \
    #.join(Unit, Unit.entity_id==Entity.id, isouter=True) \
    #.join(Person, Entity.collector_id==Person.id, isouter=True)
    taxon_family = aliased(Taxon)
    stmt = select(
        Unit.id,
        Unit.accession_number,
        Record.id,
        Record.collector_id,
        Record.field_number,
        Record.collect_date,
        Record.proxy_taxon_scientific_name,
        Record.proxy_taxon_common_name,
        Record.proxy_taxon_id) \
        .join(Unit, Unit.record_id==Record.id, isouter=True) \
        .join(taxon_family, taxon_family.id==Record.proxy_taxon_id, isouter=True) \
    #print(stmt, flush=True)
    if q:
        stmt = select(Unit.id, Unit.accession_number, Record.id, Record.collector_id, Record.field_number, Record.collect_date, Record.proxy_taxon_scientific_name, Record.proxy_taxon_common_name, Record.proxy_taxon_id) \
        .join(Unit, Unit.record_id==Record.id, isouter=True) \
        .join(Person, Record.collector_id==Person.id, isouter=True)
        #.join(TaxonRelation, TaxonRelation.depth==1, TaxonRelation.child_id==Record.proxy_taxon_id)

    #.join(Unit, Unit.entity_id==Entity.id, isouter=True) \
    #.join(Person, Entity.collector_id==Person.id, isouter=True)
        stmt = stmt.filter(or_(Unit.accession_number.ilike(f'%{q}%'),
                               Record.field_number.ilike(f'%{q}%'),
                               Person.full_name.ilike(f'%{q}%'),
                               Person.full_name_en.ilike(f'%{q}%'),
                               Record.proxy_taxon_scientific_name.ilike(f'%{q}%'),
                               Record.proxy_taxon_common_name.ilike(f'%{q}%'),
                               ))


    # apply collection filter by site
    stmt = stmt.filter(Record.collection_id.in_(site.collection_ids))

    # print(stmt, flush=True)
    base_stmt = stmt
    subquery = base_stmt.subquery()
    count_stmt = select(func.count()).select_from(subquery)
    total = session.execute(count_stmt).scalar()

    # order & limit
    stmt = stmt.order_by(desc(Record.id))
    if current_page > 1:
        stmt = stmt.offset((current_page-1) * 20)
    stmt = stmt.limit(20)

    result = session.execute(stmt)
    rows = result.all()
    # print(stmt, '==', flush=True)
    last_page = math.ceil(total / 20)
    pagination = {
        'current_page': current_page,
        'last_page': last_page,
        'start_to': min(last_page-1, 3),
        'has_next': True if current_page < last_page else False,
        'has_prev': True if current_page > 1 else False,
    }
    items = []
    fav_list = [x.record for x in current_user.favorites]
    for r in rows:
        record = session.get(Record, r[2])
        loc_list = [x.display_name for x in record.named_areas]
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
        else:
            print()

        item = {
            'accession_number': r[1] or '',
            'record_id': r[2],
            'field_number': r[4] or '',
            'collector': collector,
            'collect_date': r[5].strftime('%Y-%m-%d') if r[5] else '',
            'scientific_name': taxon_display, # r[6]
            'common_name': '', #r[7],
            'locality': ','.join(loc_list),
            'entity_id': entity_id,
            'is_fav': True if entity_id in fav_list else False,
        }
        items.append(item)

    return render_template(
        'admin/record-list-view.html',
        items=items,
        total=total,
        pagination=pagination)


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
    items = [get_entity(x.record) for x in current_user.favorites]
    return render_template('admin/print-label.html', items=items)


@admin.route('/fav-list')
def fav_list():
    items = [get_entity(x.record) for x in current_user.favorites]
    return render_template('admin/fav-list.html', items=items)

@admin.route('/delete-favorites', methods=['DELETE'])
def delete_favorites():
    for i in current_user.favorites:
        session.delete(i)
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

        items = query.all()

        return render_template(self.template, items=items, register=self.register)


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
                if self.register['filter_by'] == 'organization':
                    self.item = self.register['model'](organization_id=current_user.organization_id)
                else:
                    self.item = self.register['model']()
                session.add(self.item)

            change_log = ChangeLog(self.item)

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

            history = ModelHistory(
                user_id=current_user.id,
                tablename=self.item.__tablename__,
                action='create' if self.is_create else 'update',
                item_id=self.item.id,
                changes=change_log.get_changes(),
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
