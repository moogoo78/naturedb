import re
from decimal import Decimal

from flask import (
    render_template,
    abort,
    request,
    current_app,
)

from sqlalchemy import(
    inspect,
    desc,
)
from app.database import (
    session,
    ModelHistory,
)
from app.models.site import Site
from app.models.collection import (
    Collection,
    Unit,
    Record,
    Identification,
    RecordNamedAreaMap,
    AssertionType,
    RecordAssertion,
    UnitAssertion,
    UnitAnnotation,
    Project,
    AnnotationType,
    Annotation,
    RecordGroup,
    TrackingTag,
    Transaction,
    Person,
    AreaClass,
)

from app.utils import (
    get_cache,
    set_cache,
)

def set_attribute_values(attr_type, collection_id, obj_id, values):
    changes = {}
    for name, value in values.items():
        a_type = None
        if '-assertion' in attr_type:
            a_type = AssertionType.query.filter(AssertionType.name==name, AssertionType.collection_id==collection_id).one()
        elif '-annotation' in attr_type:
            a_type = AnnotationType.query.filter(AnnotationType.name==name, AnnotationType.collection_id==collection_id).one()

        do = {
            'action': '',
            'new_val': '',
            'option_id': 0,
            'obj': None,
        }
        # determine what to do
        if value:
            if m:= re.match(r'(\[[0-9]+\])?__(.*)__([0-9]*)', value):
                if m[2]:
                    do['new_val'] = m[2]
                if m[3]:
                    do['option_id'] = int(m[3])

                if m[1]:
                    do['action'] = 'DIFF'
                    if attr_type == 'record-assertion':
                        do['obj'] = session.get(RecordAssertion, m[1][1:-1]) # take off [ ]
                    elif attr_type == 'unit-assertion':
                        do['obj'] = session.get(UnitAssertion, m[1][1:-1]) # take off [ ]
                    elif attr_type == 'unit-annotation':
                        do['obj'] = session.get(UnitAnnotation, m[1][1:-1]) # take off [ ]
                else:
                    do['action'] = 'CREATE'

            else: # select2 tags (custom input)
                do['new_val'] = value
                obj = None
                if attr_type == 'record-assertion':
                    obj = RecordAssertion.query.filter(RecordAssertion.record_id==obj_id, RecordAssertion.assertion_type_id==a_type.id).scalar()
                elif attr_type == 'unit-assertion':
                    obj = UnitAssertion.query.filter(UnitAssertion.unit_id==obj_id, UnitAssertion.assertion_type_id==a_type.id).scalar()
                elif attr_type == 'unit-annotation':
                    obj = UnitAnnotation.query.filter(UnitAnnotation.unit_id==obj_id, UnitAnnotation.annotation_type_id==a_type.id).scalar()

                if obj:
                    do['action'] = 'DIFF'
                    do['obj'] = obj
                else:
                    do['action'] = 'CREATE'
        else:
            obj = None
            if attr_type == 'record-assertion':
                obj = RecordAssertion.query.filter(RecordAssertion.record_id==obj_id, RecordAssertion.assertion_type_id==a_type.id).scalar()
            elif attr_type == 'unit-assertion':
                obj = UnitAssertion.query.filter(UnitAssertion.unit_id==obj_id, UnitAssertion.assertion_type_id==a_type.id).scalar()
            elif attr_type == 'unit-annotation':
                obj = UnitAnnotation.query.filter(UnitAnnotation.unit_id==obj_id, UnitAnnotation.annotation_type_id==a_type.id).scalar()
            if obj:
                do['action'] = 'DELETE'
                do['obj'] = obj

        current_app.logger.debug(f'attr: {name}, do: {do}')

        # do it
        if do['action'] == 'DIFF':
            if do['obj'].value != do['new_val']:
                changes[name] = ['UPDATE', do['obj'].value, do['new_val']]
                do['obj'].value = do['new_val']
                if do['option_id']:
                    do['obj'].option_id = do['option_id']

        elif do['action'] == 'CREATE':
            if attr_type == 'record-assertion':
                obj = RecordAssertion(record_id=obj_id, assertion_type_id=a_type.id, value=do['new_val'])
            elif attr_type == 'unit-assertion':
                obj = UnitAssertion(unit_id=obj_id, assertion_type_id=a_type.id, value=do['new_val'])
            elif attr_type == 'unit-annotation':
                obj = UnitAnnotation(unit_id=obj_id, annotation_type_id=a_type.id, value=do['new_val'])

            do['obj'] = obj
            if do['option_id']:
                do['obj'].option_id = do['option_id']

            session.add(do['obj'])
            changes[name] = ['CREATE', do['new_val']]

        elif do['action'] == 'DELETE':
            changes[name] = ['DELETE', do['obj'].value]
            session.delete(do['obj'])

    #current_app.logger.debug(f'changes: {changes}')

    return changes

def save_record(record, payload, collection, uid):
    is_debug = False

    #uid = payload.get('uid')
    is_new_record = False
    if not record:
        record = Record(collection_id=collection.id)
        session.add(record)
        session.commit()
        is_new_record = True

    relate_changes = {}
    modify = make_editable_values(record, payload)

    if collector_id := payload.get('collector_id'):
        try:
            cid = int(collector_id)
            record.collector_id = cid
        except:
            pass
    else:
        record.collector_id = None

    if value := payload.get('record_groups'):
        #groups_orig = [x.group_id for x in record.group_maps]
        groups_new = []
        for x in value:
            record_group = session.get(RecordGroup, int(x))
            groups_new.append(record_group)
        record.record_groups = groups_new

    if value := payload.get('named_areas'):
        changes = {}
        via = payload.get('named_areas__via', '')
        pv = record.get_named_area_map()
        #print(pv, value, flush=True)

        updated_keys = []
        for name, selected in value.items():
            #print(name, selected, flush=True)
            if selected:
                new_val = int(selected)
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

    if values := payload.get('assertions'):
        changes = set_attribute_values('record-assertion', collection.id, record.id, values)
        if len(changes):
            relate_changes['assertions'] = changes

    if value := payload.get('identifications'):
        changes = {}
        pv = {}
        update_ids = [int(x['id']) for x in value if x.get('id')]
        for i in record.identifications.all():
            pv[i.id] = i
            # delete id no exist now
            if i.id not in update_ids:
                changes[i.id] = ['DELETE Identification', i.to_dict()]
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
            #print('iden: ', i2, flush=True)
            if x := i2.get('identifier_id'):
                i2['identifier_id'] = x
                iden.update({'identifier_id': x})
            if x := i2.get('taxon_id'):
                i2['taxon_id'] = x
                iden.update({'taxon_id': x})

            iden_modify = make_editable_values(iden, i)
            #print('iden_mod:', iden_modify, flush=True)
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
        update_ids = [int(x['id']) for _, x in value.items() if x.get('id')]

        for unit in record.units:
            pv[unit.id] = unit
            if unit.id not in update_ids:
                session.delete(unit)

        assertion_types = collection.get_options('assertion_types')
        assertion_type_map = {x.name: x for x in assertion_types}
        annotation_types = collection.get_options('annotation_types')
        annotation_type_map = {x.name: x for x in annotation_types}

        for _, i in value.items():
            unit = None
            if exist_id := i.get('id'):
                unit = pv[int(exist_id)]
            else:
                unit = Unit(record_id=record.id)
                session.add(unit)
                session.commit()

            #print('unit item:', i, flush=True)
            unit_modify = make_editable_values(unit, i)
            if len(unit_modify):
                unit.update(unit_modify)
                unit_changes = inspect_model(unit)
                changes[unit.id] = {}
                if len(unit_changes):
                    changes[unit.id] = unit_changes

                if assertions := i.get('assertions'):
                    ch = set_attribute_values('unit-assertion', collection.id, unit.id, assertions)
                    changes[unit.id]['assertions'] = ch
                if annotations := i.get('annotations'):
                    ch = set_attribute_values('unit-annotation', collection.id, unit.id, annotations)
                    changes[unit.id]['annotations'] = ch

            # TODO, rfid寫死
            if tag_id := i.get('tracking_tags__rfid'):
                if tag := session.get(TrackingTag, tag_id):
                    if not tag.unit_id:
                        tag.unit_id = unit.id

                    if exist_tag := TrackingTag.query.filter(TrackingTag.unit_id==unit.id, TrackingTag.tag_type=='rfid').first():
                        exist_tag.unit_id = None

                    session.commit() # commit tracking_tags changes

            if len(changes):
                relate_changes['units'] = changes


    if phase1_raw := payload.get('_phase1'):
        #record.source_data.update(phase1_raw)
        raw = {}
        for k, v in phase1_raw.items():
            if k in record.source_data:
                if record.source_data[k] != v:
                    raw[k] = v
            elif v != '':
                raw[k] = v
        #record.source_data.update(raw)
        modify['source_data'] = raw
        #changes['_phase1']
    if len(modify):
        record.update(modify)
        #print(modify, flush=True)
        changes = inspect_model(record)

        if is_debug:
            print('modify:', modify, flush=True)
            print('record:', changes, flush=True)

    if (len(modify) and len(changes)) or \
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

    record.update_proxy()

    return record, is_new_record

def get_or_set_type_specimens(collection_ids):
    CACHE_KEY = 'type-stat'
    CACHE_EXPIRE = 86400 # 1 day: 60 * 60 * 24
    unit_stats = None

    if x := get_cache(CACHE_KEY):
        unit_stats = x
    else:
        rows = Unit.query.filter(Unit.type_status != '', Unit.pub_status=='P', Unit.type_is_published==True, Unit.collection_id.in_(collection_ids)).all()
        stats = { x[0]: 0 for x in Unit.TYPE_STATUS_OPTIONS }
        units = []
        for u in rows:
            if u.type_status and u.type_status in stats:
                stats[u.type_status] += 1

                # prevent lazy loading
                units.append({
                    'family': u.record.taxon_family.full_scientific_name if u.record.taxon_family else '',
                    'scientific_name': u.record.proxy_taxon_scientific_name,
                    'common_name': u.record.proxy_taxon_common_name,
                    'type_reference_link': u.type_reference_link,
                    'type_reference': u.type_reference,
                    'specimen_url': u.get_specimen_url('local.ark'),
                    'accession_number': u.accession_number,
                    'type_status': u.type_status
                })
                units = sorted(units, key=lambda x: (x['family'], x['scientific_name']))
                unit_stats = {'units': units, 'stats': stats}
                set_cache(CACHE_KEY, unit_stats, CACHE_EXPIRE)

    return unit_stats

def get_current_site(request):
    if request and request.headers:
        if host := request.headers.get('Host'):
            if site := Site.find_by_host(host):
                return site
    return None

def get_assertion_display(rules, assertion_map):
    results = []
    if rules['_v'] == '0.1':
        for rule in rules['rules']:
            sentences = []

            for idx, text in enumerate(rule['context']):
                if isinstance(text, str) and assertion_map.get(text):
                    sentences.append(assertion_map[text])
                elif isinstance(text, list):
                    parts = []
                    for t in text:
                        if val := assertion_map.get(t):
                            parts.append(val)

                    if effect := rule.get('effect'):
                        sn = str(idx + 1)
                        if sn in effect:
                            if concat2 := effect[sn].get('concat'):
                                if parts:
                                    sentence = concat2.join(parts)
                                    sentences.append(sentence)


            if concat := rule.get('concat'):
                result = concat.join(sentences)

            if result:
                if cap := rule.get('cap'):
                    result = result.capitalize()
                if end := rule.get('end'):
                    # if already has end, ignore action
                    if result[-1] != end:
                        result = f'{result}{end}'

            if result:
                results.append(result)
        # end of v0.1

    return results

def get_entity(entity_id):
    unit = None
    record = None
    entity = {
        'type': 'unit',
        'record': None,
        'unit': None,
        'entity_id': entity_id,
        'assertionDisplay': []
    }

    entity_type = entity_id[0]
    item_id = entity_id[1:]

    assertion_map = {}
    if entity_type == 'u':
        unit = session.get(Unit, item_id)

        for a in unit.record.assertions:
            assertion_map[a.assertion_type.name] = a.value
        for a in unit.assertions:
            assertion_map[a.assertion_type.name] = a.value

        entity.update({
            'unit': unit,
            'record': unit.record,
        })
    elif entity_type == 'r':
        record = session.get(Record, entity_id[1:])

        for a in record.assertions:
            assertion_map[a.assertion_type.name] = a.value

        entity.update({
            'type': 'record',
            'record': session.get(Record, entity_id[1:]),
        })

    if site := get_current_site(request):
        if site.data:
            if rules := site.data.get('assertionDisplayRules'):
                #print(entity, assertion_map, flush=True)
                alist = get_assertion_display(rules, assertion_map)
                entity.update({
                    'assertion_display_list': alist,
                })
    return entity

def get_record_values(record):
    data = {
        'id': record.id,
        #'collect_date': record.collect_date.strftime('%Y-%m-%d') if record.collect_date else '',
        'collector': record.collector.to_dict() if record.collector else '',
        'identifications': [x.to_dict() for x in record.identifications.order_by(Identification.sequence).all()],
        #'proxy_unit_accession_numbers': record.proxy_unit_accession_numbers,
        #'proxy_taxon_text': record.proxy_taxon_text,
        #'proxy_taxon_id': record.proxy_taxon_id,
        #'proxy_taxon': taxon.to_dict() if taxon else None,
        'assertions': {},
        'units': [x.to_dict() for x in record.units],
        'named_areas': {},
        'groups': [],
        'source_data': record.source_data,
        }
    #if record.project_id:
    #    data['project'] = record.project_id
    collection_id = record.collection_id
    for i in record.record_groups:
        if i.collection_id == collection_id:
            data['groups'].append({
                'id': i.id,
                'name': i.name,
                'category': i.category,
            })

    for i in record.get_editable_fields(['date']):
        if x := getattr(record, i):
            data[i] = x.strftime('%Y-%m-%d')
    for i in record.get_editable_fields(['int', 'str', 'decimal']):
        x = getattr(record, i)
        data[i] = x or ''

    for i in record.assertions:
        data['assertions'][i.assertion_type.name] = {
            'id': i.id,
            'value': i.value,
            'option_id': i.option_id,
        }

    for x in record.named_area_maps:
        if x.named_area.area_class_id not in [1, 2, 3, 4]: #FIXME
            data['named_areas'][x.named_area.area_class.name] = x.named_area.to_dict()

    #data['named_areas__legacy'] = [x.to_dict() for x in record.get_named_area_list('legacy')]

    histories = ModelHistory.query.filter(ModelHistory.tablename=='record*', ModelHistory.item_id==str(record.id)).order_by(desc(ModelHistory.created)).all()
    data['__histories__'] = [{
        'id': x.id,
        'changes': x.changes,
        'action': x.action,
        'created': x.created.strftime('%Y-%m-%d %H:%M:%S'),
        'user': {
            'username': x.user.username,
            'uid': x.user_id,
        }
    } for x in histories]

    if site_data := record.collection.site.data:
        if phase := record.collection.site.data.get('phase'):
            if phase == 1:
                data['raw_data'] = record.source_data
    return data

def make_editable_values(model, data):
    modify = {}
    for k, v in data.items():
        if k in model.get_editable_fields(['str']):
            modify[k] = v
        elif k in model.get_editable_fields(['decimal']):
            decimal_val = None
            if v != '':
                decimal_val = Decimal(v)
            modify[k] = decimal_val
        elif k in model.get_editable_fields(['int']):
            int_val = None
            if v != '':
                int_val = int(v)
            modify[k] = int_val
        elif k in model.get_editable_fields(['date']):
            date_val = None
            if v != '':
                # TODO: sanity date str
                date_val = v
            modify[k] = date_val

    return modify


def inspect_model(model):
    '''via: https://stackoverflow.com/a/56351576/644070
    '''
    changes = {}
    state = inspect(model)
    for attr in state.attrs:
        hist = state.get_history(attr.key, True)
        # print(hist, flush=True)
        if not hist.has_changes():
            continue

        old_value = hist.deleted[0] if hist.deleted else None
        new_value = hist.added[0] if hist.added else None
        #self.changes[attr.key] = [old_value, new_value]
        changes[attr.key] = f'{old_value}=>{new_value}'

    return changes

def update_record_proxy_taxon(record):
    print(record.identifications, flush=True)


def get_item(item_key):
    item_type = item_key[0]
    item_id = item_key[1:]

    unit = None
    record = None
    if item_type == 'u':
        unit = session.get(Unit, item_id)
        if unit:
            record = unit.record
    elif item_type == 'r':
        record = session.get(Record, item_id)

    return record, unit

def get_all_admin_options(collection):
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
