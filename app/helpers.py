from flask import (
    render_template,
    abort,
)

from app.models.site import Organization
from app.models.collection import (
    Collection,
    Unit
)
from app.utils import (
    get_cache,
    set_cache,
)

def get_or_set_type_specimens():
    CACHE_KEY = 'type-stat'
    CACHE_EXPIRE = 86400 # 1 day: 60 * 60 * 24
    unit_stats = None
    if x := get_cache(CACHE_KEY):
        unit_stats = x
    else:
        rows = Unit.query.filter(Unit.type_status != '', Unit.pub_status=='P', Unit.type_is_published==True).all()
        stats = { x[0]: 0 for x in Unit.TYPE_STATUS_CHOICES }
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
        if domain := request.headers.get('Host'):
            if site := Organization.get_site(domain):
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
