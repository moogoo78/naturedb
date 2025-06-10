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

def put_entity_raw(record, payload, collection, uid, is_new=False):
    #print(payload, flush=True)
    if raw := payload.get('_raw'):
        data = record.source_data.copy()
        diff = {}

        for k, v in data.items():
            if 'extension__' in k:
                pass
            elif k == '__source':
                pass
            elif k == '__namecode':
                pass
            elif k not in raw or v != raw[k]:
                diff[k] = ['UPDATE', f'{k}:{v} -> {raw[k]}']

        data.update(raw)
        record.source_data = data
        session.commit()

        if len(diff):
            hist = ModelHistory(
                tablename='record*',
                item_id=record.id,
                action = 'update',
                user_id=uid,
                changes=diff,
                remarks=payload.get('__changelog__', ''),
            )
            session.add(hist)
            session.commit()

    return {'message': 'ok'}

def put_entity(record, payload, collection, uid, is_new=False):
    related_logs = {}

    identification_payload = payload.pop('identifications', None)
    named_area_payload = payload.pop('named_areas', None)
    unit_payload = payload.pop('units', None)
    assertion_payload = payload.pop('assertions', None)
    record_group_payload = payload.pop('record_groups', None)
    record_payload = payload

    # update record
    record_changes = record.update_from_dict(record_payload)
    record_logs = inspect_model(record)

    if record_group_payload:
        record.record_groups = [session.get(RecordGroup, int(x)) for x in record_group_payload] # TODO: no log
    session.commit() # commit record

    # named areas
    logs = {}
    via = payload.get('named_areas__via', '') #TODO
    pv = record.get_named_area_map()

    updated_keys = []
    for name, selected in named_area_payload.items():
        if selected:
            new_val = int(selected)
            updated_keys.append(name)
            if name in pv:
                if pv[name].named_area_id != new_val:
                    #print('update r-n-a-m', pv[name].named_area_id, new_val, flush=True)
                    logs[name] = ['UPDATE', pv[name].named_area_id, new_val]
                    pv[name].named_area_id = new_val
            else:
                rel = RecordNamedAreaMap(record_id=record.id, named_area_id=new_val, via=via)
                #print('new r-n-a-m', rel, flush=True)
                logs[name] = ['CREATE', name, new_val]
                session.add(rel)

    should_delete = list(set(pv.keys()) - set(updated_keys))
    for key in should_delete:
        logs[name] = ['DELETE', key, pv[key].named_area_id]
        session.delete(pv[key])

    if len(logs):
        related_logs['named_areas'] = logs

    # assertion
    logs = set_attribute_values('record-assertion', collection.id, record.id, assertion_payload)
    if len(logs):
        related_logs['assertions'] = logs

    # identification
    logs = {}
    pv = {}
    update_ids = [int(x['id']) for x in identification_payload if x.get('id')]
    for i in record.identifications.all():
        pv[i.id] = i
        # delete id no exist now
        if i.id not in update_ids:
            logs[i.id] = ['DELETE Identification', i.to_dict()]
            session.delete(i)

    for data in identification_payload:
        iden = None
        iden_changes = None
        if exist_id := data.get('id'):
            iden = pv[int(exist_id)]
            changes = iden.update_from_dict(data)
            if len(changes):
                logs[iden.id] = inspect_model(iden)
        else:
            data['record_id'] = record.id
            iden, iden_changes = Identification.create_from_dict(data)
            create_logs = inspect_model(iden)
            session.add(iden)
            session.commit()

            logs[iden.id] = ['CREATE Identification', create_logs]

    if len(logs):
        related_logs['identifications'] = logs

    # unit
    logs = {}
    pv = {}
    # for check update or delete old values
    update_ids = [int(x['id']) for _, x in unit_payload.items() if x.get('id')]

    for unit in record.units:
        pv[unit.id] = unit
        if unit.id not in update_ids:
            logs[unit.id] = ['DELETE unit', unit.to_dict()]
            session.delete(unit)

    assertion_types = collection.get_options('assertion_types')
    assertion_type_map = {x.name: x for x in assertion_types}
    annotation_types = collection.get_options('annotation_types')
    annotation_type_map = {x.name: x for x in annotation_types}

    for _, data in unit_payload.items():
        unit = None
        unit_changes = None
        unit_assertion_payload = data.pop('assertions')
        unit_annotation_payload = data.pop('annotations')
        create_logs = None
        if exist_id := data.get('id'):
            unit = pv[int(exist_id)]
            changes = unit.update_from_dict(data)
            current_app.logger.debug(f'unit <{unit.id}>changes) {changes}')
            if len(changes):
                logs[unit.id] = inspect_model(unit)
        else:
            data['record_id'] = record.id
            unit, unit_changes = Unit.create_from_dict(data)
            create_logs = inspect_model(unit)
            session.add(unit)
            session.commit()

        # unit assertions & annotations
        ext_logs = {
            'assertions': None,
            'annotations': None,
        }
        if unit_assertion_payload:
            ch = set_attribute_values('unit-assertion', collection.id, unit.id, unit_assertion_payload)
            if ch:
                ext_logs['assertions'] = ch
        if unit_annotation_payload:
            ch = set_attribute_values('unit-annotation', collection.id, unit.id, unit_annotation_payload)
            if ch:
                ext_logs['annotations'] = ch

        if create_logs:
            for k, v in ext_logs.items():
                if v:
                    if unit.id not in logs:
                        logs[unit.id] = {}
                    create_logs.update({k: v})
            logs[unit.id] = ['CREATE unit', create_logs]
        else:
            for k, v in ext_logs.items():
                if v:
                    if unit.id not in logs:
                        logs[unit.id] = {}
                    logs[unit.id].update({k: v})


        # TODO, rfid寫死
        if tag_id := data.get('tracking_tags__rfid'):
            if tag := session.get(TrackingTag, tag_id):
                if not tag.unit_id:
                    tag.unit_id = unit.id

                if exist_tag := TrackingTag.query.filter(TrackingTag.unit_id==unit.id, TrackingTag.tag_type=='rfid').first():
                    exist_tag.unit_id = None

                session.commit() # commit tracking_tags changes

        if len(logs):
            related_logs['units'] = logs

    if raw_data := payload.get('_raw'):
        raw = {}
        for k, v in raw_data.items():
            if k in record.source_data:
                if record.source_data[k] != v:
                    raw[k] = v
            elif v != '':
                raw[k] = v
        #record.source_data.update(raw)
        modify['source_data'] = raw


    record.update_proxy()

    # save changes
    all_logs = record_logs
    if len(related_logs):
        all_logs['__relate__'] = related_logs
    current_app.logger.debug(f'[put_entity] {all_logs}')
    if len(all_logs):
        hist = ModelHistory(
            tablename='record*',
            item_id=record.id,
            action = 'create' if is_new else 'update',
            user_id=uid,
            changes=all_logs,
            remarks=payload.get('__changelog__', ''),

        )
        session.add(hist)
        session.commit()
    return {'message': 'ok'}

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

def get_entity_for_print(entity_id):
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
        if unit := session.get(Unit, item_id):
            for a in unit.record.assertions:
                assertion_map[a.assertion_type.name] = a.value
            for a in unit.assertions:
                assertion_map[a.assertion_type.name] = a.value

            entity.update({
                'unit': unit,
                'record': unit.record,
            })
        else:
            return None

    elif entity_type == 'r':
        if record := session.get(Record, entity_id[1:]):
            for a in record.assertions:
                assertion_map[a.assertion_type.name] = a.value

            entity.update({
                'type': 'record',
                'record': record,
            })
        else:
            return None

    if site := get_current_site(request):
        if rules := site.get_settings('assertionDisplayRules'):
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
        'identifications': [x.to_dict() for x in record.identifications.order_by(desc(Identification.sequence)).all()],
        #'proxy_unit_accession_numbers': record.proxy_unit_accession_numbers,
        #'proxy_taxon_text': record.proxy_taxon_text,
        #'proxy_taxon_id': record.proxy_taxon_id,
        #'proxy_taxon': taxon.to_dict() if taxon else None,
        'assertions': {},
        'units': [x.to_dict() for x in Unit.query.filter(Unit.record_id==record.id).order_by(desc(Unit.id))],
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
        'created': x.created.strftime('%Y-%m-%d %H:%M:%S') if x.created else '',
        'user': {
            'username': x.user.username if x.user else '',
            'uid': x.user_id,
        },
        'remarks': x.remarks,
    } for x in histories]

    if data_type := record.collection.site.get_settings('data-type'):
        if data_type == 'raw':
            data['raw_data'] = record.source_data

    return data


def update_editable(obj, data):
    modify = {}
    # print(data, flush=True)
    for k, v in data.items():
        key = k
        value = '__N/A__'
        if k in obj.get_editable_fields(['str']):
            v1 = getattr(obj, k) or ''
            v2 = str(v) or ''
            if v1 != v2:
                value = v2
        elif k in obj.get_editable_fields(['decimal']):
            v1 = getattr(obj, k) or None
            v2 = Decimal(v) if v else None
            if v1 != v2:
                value = v2
        elif k in obj.get_editable_fields(['int']):
            v1 = getattr(obj, k) or 0
            v2 = int(v) if v else 0
            if v1 != v2:
                value = v2
        elif k in obj.get_editable_fields(['date']):
            v1 = getattr(obj, k)
            v1 = v1.strftime('%Y-%m-%d') if v1 else None
            v2 = v or None
            if v1 != v2:
                value = v2
        if value != '__N/A__':
            modify[k] = value
            setattr(obj, value)
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


def get_entity(entity_key):
    entity_type = entity_key[0]
    entity_id = entity_key[1:]

    unit = None
    record = None
    if entity_type == 'u':
        unit = session.get(Unit, entity_id)
        if unit:
            record = unit.record
    elif entity_type == 'r':
        record = session.get(Record, entity_id)

    return record, unit

def get_all_admin_options(collection):
    record_group_list = RecordGroup.query.filter(RecordGroup.collection_id==collection.id)
    record_groups = [{'id': x.id, 'text': x.name, 'category': x.category} for x in record_group_list]
    sub_collections = Collection.query.filter(Collection.parent_id==collection.id).all()
    #print(sub_collections, flush=True) # TODO
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
        '_record_fields': Record.get_editable_fields(['date', 'int', 'str', 'decimal']),
        '_identification_fields': Identification.get_editable_fields(['date', 'int', 'str']),
        '_unit_fields': Unit.get_editable_fields(),
        'sub_collection_attributes': {},
    }

    if x := collection.site.get_settings(f'admin.record-form.collection.{collection.name}.default'):
        data['collection']['defaults'] = x

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

    # raw data-type
    site = get_current_site(request)
    if settings := site.get_settings():
        if data_type := settings.get('data-type'):
            if data_type == 'raw':
                data['_raw'] = {
                    'form': settings[f'admin.record-form.collection.{collection.name}.field-layout'],
                    'fields': settings.get('fields', []),
                }

    return data
