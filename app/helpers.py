from decimal import Decimal

from flask import (
    render_template,
    abort,
    request,
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
)
from app.utils import (
    get_cache,
    set_cache,
)

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
        }
    if record.project_id:
        data['project'] = record.project_id
    for i in record.get_editable_fields(['date']):
        if x := getattr(record, i):
            data[i] = x.strftime('%Y-%m-%d')
    for i in record.get_editable_fields(['int', 'str', 'decimal']):
        x = getattr(record, i)
        data[i] = x or ''

    for i in record.assertions:
        data['assertions'][i.assertion_type.name] = i.value

    for x in record.named_area_maps:
        if x.named_area.area_class_id in [5, 6] or x.named_area.area_class_id >= 7:
            data['named_areas'][x.named_area.area_class.name] = x.named_area.to_dict()

    data['named_areas__legacy'] = [x.to_dict() for x in record.get_named_area_list('legacy')]

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
