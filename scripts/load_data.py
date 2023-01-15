import csv
import json
import re
import urllib.request
from urllib.parse import quote


from app.models import Taxon, Collection, Unit, Annotation, Identification
from app.database import session

def lookup_nomenmatch(sci_name, source):
    print(f'lookup: {sci_name}')
    url = 'http://match.taibif.tw/api.php?names={}&format=json'.format(quote(sci_name))

    with urllib.request.urlopen(url) as response:
        resp = response.read()
        #print(type(resp), json.loads(resp))
        payload = json.loads(resp)

        if res := payload['results']:
            data = res[0][0]

            source_map = { v: i for i, v in enumerate(data['source']) }

            source_id = source_map.get('taicol', '')
            return {
                'raw': res,
                'score': data['score'],
                'matched_name': data['matched'],
                'taicol_namecode': data['namecode'][source_id] if source_id else '',
                'taicol_accepted_namecode': data['accepted_namecode'][source_id] if source_id else '',
                'kingdom': data['kingdom'][source_id] if source_id else '',
                'phylum': data['phylum'][source_id] if source_id else '',
                'class': data['class'][source_id] if source_id else '',
                'order': data['order'][source_id] if source_id else '',
                'family': data['family'][source_id] if source_id else '',
            }

class HierarchyData(object):
    layer_list = []
    data = {}

    def __init__(self, layer_list):
        self.layer_list = layer_list
        self.data = {
            'layer': 'root',
            'children': {}
        }


    def append_child(self, children, value, layer):
        if value not in children:
            children[value] = {
                'layer': layer,
                'children': {}
            }
        return children

    def append_data(self, stacked, old):
        tmp = old if old else self.data
        for i, k in enumerate(self.layer_list):
            val = stacked[i]
            #print(i, k, tmp, self.data)
            if val not in tmp['children']:
                tmp['children'][val] = {
                    'layer': k,
                    'children': {}
                }

            tmp = tmp['children'][val]

        #print(self.data)
        return self.data

def import_csv(conf):
    with open(conf['source'], newline='') as csvfile:
        spamreader = csv.reader(csvfile)

        if conf['is_skip_header']:
            next(spamreader, None)

        taxa = HierarchyData(conf['rank_list'])

        for row in spamreader:
            collection = Collection()
            session.add(collection)
            if not conf['is_dry_run']:
                session.commit()
            unit = Unit(collection_id=collection.id, dataset_id=conf['dataset_id'])
            session.add(unit)

            rank_map = {f'{x}': '' for x in conf['rank_list']}
            rank_map['taicol_order'] = ''
            rank_map['taicol_family'] = ''
            #rank_map['taicol_genus'] = ''
            rank_map['taicol_species'] = ''

            if not conf['is_dry_run']:
                session.commit()

            for i, v in enumerate(row):
                tmp = None
                col = conf['columns'][i]
                if col['resource'] == 'taxon':
                    if col['rank'] == 'species':
                        rank_map['species'] = v
                        rank_map['genus'] = v.split(' ')[0] if v else ''
                        #x = lookup_nomenmatch(v, 'taicol')
                        #if x:
                        #    rank_map['taicol_order'] = x['order']
                        #    rank_map['taicol_family'] = x['family']
                        #    rank_map['taicol_species'] = x['matched_name']
                    else:
                        rank = col['rank']
                        if v not in rank_map[rank]:
                            val = v.strip()
                            m = re.search(r'[a-zA-Z]+', val) # ignore chinese
                            rank_map[rank] = m.group(0) if m else val
                elif col['resource'] == 'locality_text':
                    collection.locality_text = v
                elif col['resource'] == 'annotation':
                    anno = Annotation(unit_id=unit.id, category=col['category'], text=v)
                elif col['resource'] == 'unit.accession_number':
                    unit.accession_number = v
            #print(i, rank_map)
            #for rank in conf['rank_list']:
            # stupid way
            '''
            r4 = rank_map[conf['rank_list'][0]]
            if r4 not in tree_map:
                tree_map[r4] = {}
            r5 = rank_map[conf['rank_list'][1]]
            if r5 not in tree_map[r4]:
                tree_map[r4][r5] = {}
            r6 = rank_map[conf['rank_list'][2]]
            if r6 not in tree_map[r4][r5]:
                tree_map[r4][r5][r6] = {}
            r7 = rank_map[conf['rank_list'][3]]
            if r7 not in tree_map[r4][zr5][r6]:
                tree_map[r4][r5][r6][r7] = ''
            '''
            #print(taxa.data, taxa.layer)
            tmp = taxa.append_data([rank_map.get(x, '') for x in conf['rank_list']], tmp)

            if not conf['is_dry_run']:
                session.commit()

        print('!!last', taxa.data)
        #from 
