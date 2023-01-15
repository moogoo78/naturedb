import csv

from sqlalchemy import (
    create_engine,
    select,
    func,
)

#from app.models import Unit, Collection, Person, FieldNumber, NamedArea, Identification, AreaClass, MeasurementOrFact, Annotation, MeasurementOrFactParameter, Transaction, MeasurementOrFactParameterOption, MeasurementOrFactParameterOptionGroup, Project
#from app.taxon.models import Taxon, TaxonTree, TaxonRelation
from app.models.collection import *
from app.models.site import *
from app.models.taxon import *

from app.database import session

def make_proj(con):
    '''
    rows = con.execute('SELECT * FROM specimen_specimen ORDER BY id')
    for r in rows:
        if hast := r[4].get('hast'):
            if pid := hast.get('projectID'):
                c = Entity.query.filter(Collection.id==r[0]).first()
                #print (c, flush=True)
                if int(pid) > 11:
                    print (r[0], pid, flush=True)
                else:
                    c.project_id = int(pid)
    session.commit()
    '''
    with open('./data/projectName_202102051854.csv') as csvfile:
        spamreader = csv.reader(csvfile)
        next(spamreader)
        for row in spamreader:
            print (row, flush=True)
            p = Project(name=row[1], collection_id=1)
            session.add(p)
        session.commit()

def make_person(con):
    rows = con.execute('SELECT * FROM specimen_person ORDER BY id')
    people = []
    for r in rows:
        #print(r)
        org = ''
        atom_name = {}
        full_name = r[6]
        full_name_en = ''
        abbr_name = r[1]['nameAbbr'] if len(r[1]) else ''
        org_name = r[1]['organAbbr'] if len(r[1]) else ''
        '''
        if len(r[1]) > 0:
            # has source_data
            org = r[1]['organAbbr']
            abbr_name = r[1]['nameAbbr']
            atom_name = {
                'en': {
                    'given_name': r[1]['firstName'],
                    'inherited_name': r[1]['lastName'],
                }
            }
            if name_other := r[1]['nameOther']:
                atom_name['other'] = name_other
        '''
        name_list = []
        if first_name := r[1].get('firstName'):
            name_list.append(first_name)
        if last_name := r[1].get('lastName'):
            name_list.append(last_name)
        full_name_en = ' '.join(name_list)

        p = Person(
            full_name=full_name,
            full_name_en=full_name_en,
            abbreviated_name=abbr_name,
            organization_name=org_name,
            #atomized_name=atom_name,
            source_data=r[1],
            is_collector=r[3],
            is_identifier=r[4]
        )
        session.add(p)
        people.append(p)

    c = session.get(Collection, 1)
    c.people = people
    session.commit()

def make_geospatial(con):

    rows = con.execute('SELECT * FROM specimen_areaclass ORDER BY id')
    counter = 0
    the_map = {
        'province': 'stateProvince',
        'hsien': 'county',
        'town': 'municipality',
    }
    for r in rows:
        counter += 1
        ac = AreaClass(name=the_map[r[1]] if the_map.get(r[1]) else r[1], label=r[2], collection_id=1, sort=counter)
        if counter > 1 and counter <= 4:
            ac.parent_id = counter - 1
        session.add(ac)
    session.commit()

    rows = con.execute('SELECT * FROM specimen_namedarea ORDER BY id')
    for r in rows:
        if r[4] == 1:
            na = NamedArea(id=r[0], name=r[1], name_en=r[5]['country'], area_class_id=r[4], source_data=r[5])
        else:
            na = NamedArea(id=r[0], name=r[1], name_en=r[6], area_class_id=r[4], source_data=r[5])
        session.add(na)
    session.commit()

    # add parent
    children = NamedArea.query.filter(NamedArea.area_class_id>1).all()
    for i in children:
        qna = None
        if i.area_class_id == 2:
            p = i.source_data['countryNo']
            jstr ='{"countryNo":"'+p+'"}'
            qna = NamedArea.query.filter(
                NamedArea.source_data.op('@>')(jstr),
                NamedArea.area_class_id==1
            )
        elif i.area_class_id == 3:
            p = i.source_data['provinceNo']
            jstr ='{"provinceNo":"'+p+'"}'
            qna = NamedArea.query.filter(
                NamedArea.source_data.op('@>')(jstr),
                NamedArea.area_class_id==2
            )
        elif i.area_class_id == 4:
            p = i.source_data['hsienNo']
            jstr ='{"hsienNo":"'+p+'"}'
            qna = NamedArea.query.filter(
                NamedArea.source_data.op('@>')(jstr),
                NamedArea.area_class_id==3
            )
        if qna:
            if na := qna.first():
                i.parent_id = na.id
    session.commit()



MOF_PARAM_LIST = [
    ('abundance', 'annotation_abundance_choice_id', 'annotation_abundance_text', (18, 19), '豐富度'),
    ('habitat', 'annotation_habitat_choice_id', 'annotation_habitat_text', (20, 21), '微棲地'),
    ('humidity', 'annotation_humidity_choice_id', 'annotation_humidity_text', (22, 23), '環境濕度'),
    ('light-intensity', 'annotation_light_choice_id', 'annotation_light_text', (24, 25), '環境光度'),
    ('naturalness', 'annotation_naturalness_choice_id', 'annotation_naturalness_text', (26, 27), '自然度'),
    ('topography', 'annotation_topography_choice_id', 'annotation_topography_text', (28, 29),'地形位置'),
    ('veget', 'annotation_veget_choice_id', 'annotation_veget_text', (30, 31),'植群型'),
]
MOF_PARAM_LIST2a = [
    ('plant-h', 'annotation_plant_h', '植株高度'),
    ('sex-char', 'annotation_sex_char', '性狀描述'),
    #('memo', 'annotation_memo'),
    #('memo2', 'annotation_memo2'),
    #('is-greenhouse', 'annotation_category')
]
MOF_PARAM_LIST2 = [
    ('life-form', 'annotation_life_form_choice_id', 'annotation_life_form_text', '生長型'),
    ('flower', 'annotation_flower_choice_id', 'annotation_flower_text', '花'),
    ('fruit', 'annotation_fruit_choice_id', 'annotation_fruit_text', '果'),
    ('flower-color', 'annotation_flower_color_choice_id', 'annotation_flower_color_text', '花色'),
    ('fruit-color', 'annotation_fruit_color_choice_id', 'annotation_fruit_color_text', '果色'),
]

PARAM_MAP = {'abundance': '1', 'habitat': '2', 'humidity': '3', 'light-intensity': '4', 'naturalness': '5', 'topography': '6', 'veget': '7', 'plant-h': '8', 'sex-char': '9', 'life-form': '10', 'flower': '11', 'fruit': '12', 'flower-color': '13', 'fruit-color': '14'}

PARAM_OPT_GROUP_MAP = ['一般型','人工/干擾環境', '闊葉林', '針葉林/混交林', '混合型', '海岸環境', '針闊葉混合林','高山植群', '混合林']

PARAM_MAP2 = {'abundance': '7', 'habitat': '2', 'humidity': '6', 'light-intensity': '5', 'naturalness': '4', 'topography': '3', 'veget': '1', 'plant-h': '9', 'sex-char': '14', 'life-form': '8', 'flower': '10', 'fruit': '12', 'flower-color': '11', 'fruit-color': '13', 'add-char': '15', 'is-greenhouse': '17', 'name-comment': 16}

def make_assertion_type_option(con):
    rows = con.execute(f"SELECT * FROM specimen_annotation")
    for row in rows:
        pid = PARAM_MAP[row[2]]
        group_name = ''
        if row[2] == 'veget':
            group_name = row[4].get('typeC')
        # print (pid, group_name, row, flush=True)
        opt = AssertionTypeOption(value=row[1], assertion_type_id=int(PARAM_MAP2[row[2]]), data=row[4], description=row[3], )
        session.add(opt)
        session.commit()
    return {}

def make_record(con):
    '''
    collection_id = r[0] (hast_21.specimen_specimen.id)
    '''
    #LIMIT = ' LIMIT 500'
    LIMIT = ''
    rows = con.execute(f'SELECT * FROM specimen_specimen ORDER BY id{LIMIT}')
    for r in rows:
        #print(r)
        cid = r[0]
        field_number = r[2].replace('::', '') if r[2] else ''

        col = Record(
            id=cid,
            collect_date=r[32],
            collector_id=r[6],
            field_number=field_number,
            companion_text=r[14],
            companion_text_en=r[15],
            locality_text=r[5],
            locality_text_en=r[13],
            altitude=r[11],
            altitude2=r[12],
            latitude_decimal=r[9],
            longitude_decimal=r[10],
            field_note=r[16],
            field_note_en=r[17],
            source_data=r[4],
            collection_id=1,
        )

        if hast := r[4].get('hast'):
            if pid := hast.get('projectID'):
                if int(pid) > 11:
                    print (r[0], pid, flush=True)
                else:
                    col.project_id = int(pid)

        if r[39] or r[41] or r[42] or r[43]:
            col.latitude_text = "{}{}°{}'{}\"".format(r[39], r[41], r[42], r[43])
        if r[40] or r[44] or r[45] or r[46]:
            col.longitude_text = "{}{}°{}'{}\"".format(r[40], r[44], r[45], r[46])
        session.add(col)


        # FieldNumber
        #fn = FieldNumber(
        #    collection_id=cid,
        #    value=field_number,
        #    collector_id=r[6])
        #session.add(fn)

        # NamedArea
        na_list = [r[33], r[37], r[34], r[38], r[36], r[35]]
        for na in na_list:
            #print(na, flush=True)
            if na:
                naObj = NamedArea.query.get(na)
                if naObj:
                    col.named_areas.append(naObj)
                else:
                    print(na, 'not found', flush=True)

        # Identification
        rows2 = con.execute(f"SELECT i.*, t.full_scientific_name FROM specimen_identification AS i LEFT JOIN taxon_taxon AS t ON t.id = i.taxon_id  WHERE specimen_id ={r[0]} ORDER BY verification_level")

        id_list = [x for x in rows2]
        if len(id_list) > 0:
            last_id = id_list[-1]
            common_name = ''
            if tx := Taxon.query.get(last_id[7]):
                if cname := tx.common_name:
                    common_name = cname
            col.proxy_taxon_scientific_name = last_id[10]
            col.proxy_taxon_common_name = common_name
            col.proxy_taxon_id = last_id[7]

        for r2 in id_list:
            iden = Identification(
                record_id=cid,
                identifier_id=r2[2],
                date=r2[1],
                date_text=r2[9],
                taxon_id=r2[7],
                #verification_level=r2[8],
                sequence=r2[8],
                created=r2[4],
                updated=r2[3],
                source_data=r2[6],
            )
            session.add(iden)
        session.commit()

        # MeasurementOrFact1
        # for param in MOF_PARAM_LIST:
        #     #print(p[0], r[p[2]])
        #     if x := r[param[2]]:
        #         mof = MeasurementOrFact(
        #             collection_id=cid,
        #             #parameter=param[0],
        #             #text=x,
        #             parameter_id=PARAM_MAP[param[0]],
        #             value=x,
        #         )
        #         session.add(mof)
        # session.commit()
        for param in MOF_PARAM_LIST:
            #print(p[0], r[p[2]])
            if x := r[param[2]]:
                ea = RecordAssertion(
                    record_id=cid,
                    value=x,
                    assertion_type_id=PARAM_MAP2[param[0]]
                )
                session.add(ea)
        session.commit()

        an_list = []
        rows3 = con.execute(f"SELECT * FROM specimen_accession WHERE specimen_id ={r[0]}  ORDER BY id")
        for r3 in rows3:
            acc_num = ''
            acc_num2 = ''
            if an := r3[1]:
                acc_num = an
            if an2 := r3[2]:
                acc_num2 = an2

            an_list.append(acc_num)
            # Unit
            u = Unit(
                record_id=cid,
                catalog_number=acc_num,
                duplication_number=acc_num2,
                acquisition_source_text=r[47],
                kind_of_unit='HS',
                preparation_date=r3[22],
                preparation_type='S',
                source_data=r[4],
                created=r3[5],
                updated=r3[4],
                collection_id=1,
            )
            session.add(u)
            session.commit()

            # MeasurementOrFact2
            for param in MOF_PARAM_LIST2:
                if x := r3[param[2]]:
                    # mof = MeasurementOrFact(
                    #     unit_id=u.id,
                    #     #parameter=param[0],
                    #     parameter_id=PARAM_MAP[param[0]],
                    #     value=x,
                    # )
                    # session.add(mof)
                    ua = UnitAssertion(value=x, unit_id=u.id, assertion_type_id=PARAM_MAP2[param[0]])
                    session.add(ua)

            # MeasurementOrFact2a
            for param in MOF_PARAM_LIST2a:
                if x := r3[param[1]]:
                    # mof = MeasurementOrFact(
                    #     unit_id=u.id,
                    #     #parameter=param[0],
                    #     parameter_id=PARAM_MAP[param[0]],
                    #     value=x,
                    # )
                    # session.add(mof)
                    ua2 = UnitAssertion(value=x, unit_id=u.id, assertion_type_id=PARAM_MAP2[param[0]])
                    session.add(ua2)

            if x := r3['annotation_memo']:
                ua = UnitAssertion(value=x, unit_id=u.id, assertion_type_id=PARAM_MAP2['add-char'])
                session.add(ua)

            if x := r3['annotation_category']:
                ua = UnitAssertion(value=x, unit_id=u.id, assertion_type_id=PARAM_MAP2['is-greenhouse'])
            session.add(ua)
            '''
            a = Annotation(
                unit_id=u.id,
                category='add-char',
                text=r3['annotation_memo'],
                #memo='converted from legacy',
            )
            session.add(a)
            a = Annotation(
                unit_id=u.id,
                category='name-comment',
                text=r3['annotation_memo2'],
                #memo='converted from legacy',
            )
            session.add(a)
            a = Annotation(
                unit_id=u.id,
                category='is-greenhouse',
                text=r3['annotation_category'],
                #memo='converted from legacy',
            )
            session.add(a)
            '''
            #a = Annotation(
            #    unit_id=u.id,
            #    category='plant_h',
            #    text=r3['annotation_plant_h'],
            #    memo='converted from legacy',
            #)
            #session.add(a)
            #a = Annotation(
            #    unit_id=u.id,
            #    category='sex_char',
            #    text=r3['annotation_sex_char'],
            #    memo='converted from legacy',
            #)
            #session.add(a)
            #a = Annotation(
            #    unit_id=u.id,
            #    category='exchange_dept',
            #    text=r3['annotation_exchange_dept'],
            #    memo='converted from legacy',
            #)
            #session.add(a)
            #a = Annotation(
            #    unit_id=u.id,
            #    category='exchange_id',
            #    text=r3['annotation_exchange_type'],
            #    memo='converted from legacy',
            #)
            #session.add(a)
            if r3['annotation_exchange_type'] or r3['annotation_exchange_dept']:
                tr = Transaction(
                    unit_id=u.id,
                    transaction_type=r3['annotation_exchange_type'],
                    organization_text=r3['annotation_exchange_dept'],
                )
                session.add(tr)

        #col.proxy_unit_accession_numbers = '|'.join(an_list)
        # save unit
        session.commit()


def make_taxon(con):
    rows_init = con.execute(f"SELECT * FROM taxon_taxon")
    rows = [x for x in rows_init]
    tree = TaxonTree(name='HAST-legacy')
    session.add(tree)
    session.commit()
    #tree = TaxonTree.query.filter(TaxonTree.id==1).first()

    for r in rows:
        sn = Taxon(
            id=r[0],
            rank=r[1],
            full_scientific_name=r[2],
            common_name=r[6],
            source_data=r[8],
            tree_id=tree.id,
        )
        session.add(sn)
    session.commit()

    # relation
    ## self
    for r in rows:
        tr = TaxonRelation(
            parent_id=r[0],
            child_id=r[0],
            depth=0,
        )
        session.add(tr)
    session.commit()

    for r in rows:
        if r[1] == 'species' and r[8]:
            #print(type(r[8]), r[8].get('genusE'), flush=True)
            if gen := r[8].get('genusE'):
                t_g = Taxon.query.filter(Taxon.rank=='genus', Taxon.full_scientific_name==gen).first()
                if t_g:
                    tr = TaxonRelation(
                        parent_id=t_g.id,
                        child_id=r[0],
                        depth=1,
                    )
                    session.add(tr)
            if fam := r[8].get('familyE'):
                t_f = Taxon.query.filter(Taxon.rank=='family', Taxon.full_scientific_name==fam).first()
                if t_f:
                    tr = TaxonRelation(
                        parent_id=t_f.id,
                        child_id=r[0],
                        depth=2,
                    )
                    session.add(tr)
        if r[1] == 'genus' and r[8]:
            if fam := r[8].get('familyE'):
                t_f = Taxon.query.filter(Taxon.rank=='family', Taxon.full_scientific_name==fam).first()
                if t_f:
                    tr = TaxonRelation(
                        parent_id=t_f.id,
                        child_id=r[0],
                        depth=1,
                    )
                    session.add(tr)
    session.commit()

def make_param(con):
    for i in MOF_PARAM_LIST:
        p = MeasurementOrFactParameter(dataset_id=1, name=i[0], label=i[4])
        session.add(p)
    for i in MOF_PARAM_LIST2a:
        p = MeasurementOrFactParameter(dataset_id=1, name=i[0], label=i[2])
        session.add(p)
    for i in MOF_PARAM_LIST2:
        p = MeasurementOrFactParameter(dataset_id=1, name=i[0], label=i[3])
        session.add(p)
    session.commit()

def make_other_csv():
    # import related link

    import csv
    with open('./data/2021相關網站連結更新.csv', newline='') as csvfile:
        spamreader = csv.reader(csvfile)
        cat = None
        for row in spamreader:
            if row[0] == '' and row[1] == '':
                # empty
                pass
            else:
                c1 = row[0].strip()
                c2 = row[1].strip()
                c3 = row[2].strip()
                if c1[0] == '#' or c1[1] == '#': # has strange character
                    label = c1[1:]
                    if c1[1] == '#':
                        label = c1[2:]
                    cat = RelatedLinkCategory(name=row[1], label=label, organization_id=1)
                    session.add(cat)
                    session.commit()
                else:
                    rl = RelatedLink(title=c1, url=c2, note=c3, category_id=cat.id, organization_id=1)
                    print(c1, c2, c3, flush=True)
                    session.add(rl)
                    session.commit()


    # import type 
    TMAP = {
        '1': 'holotype',
        '2': 'isotype',
        '3': 'paratype',
    }

    with open('./data/vwTypeDetail_202211150941.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row['typeSpecimenOrderNum'],row['typeCateID'], , flush=True)
            an = row['typeSpecimenOrderNum']
            if u := Unit.query.filter(Unit.catalog_number==an).first():
                u.type_status = TMAP[row['typeCateID']]
                u.typified_name = row['verSpeciesE']
                u.type_reference = row['reference']
                u.type_reference_link = row['literaryLink']
                u.type_note = row['typeNote']
                session.commit()

    # import news (article)
    with open('./data/newsCenter_202210051010.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row['typeSpecimenOrderNum'],row['typeCateID'], , flush=True)
            a = Article(
                subject=row['newsSubject'],
                content=row['newsContent'],
                organization_id=1,
                category_id=row['newsTypeID'],
                publish_date=row['newsDate'],
                data=row,
            )
            session.add(a)
            session.commit()

def make_images(con):
    # import images
    count = 0
    with open('./data/images_202205181803.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            #print(row, flush=True)
            if sn := row['SN']:
                r = con.execute(f"SELECT a.accession_number FROM specimen_accession AS a LEFT JOIN specimen_specimen AS s ON s.id=a.specimen_id WHERE s.source_id='{sn}'")
                if x:= r.first():
                    if u := Unit.query.filter(Unit.catalog_number==x[0]).first():

                        file_url = ''
                        if 'P_' in row['imageCode']:
                            file_url = f'https://brmas-hast.s3.ap-northeast-1.amazonaws.com/Album/imageStringFileName/${row["imageCode"]}.jpg'
                        else:
                            sn_full = f'{int(row["imageCode"]):07}'
                            sn_pre = sn_full[:3]
                            sn_mid = sn_full[3:4]

                        mmo = MultimediaObject(unit_id=u.id, source_data=row, provider=row['providerID'], file_url=f'https://brmas-hast.s3.ap-northeast-1.amazonaws.com/Album/image{sn_pre}/{sn_mid}/{sn_full}.jpg')
                        print(count, row['imageCode'], flush=True)
                        count += 1
                        session.add(mmo)
                        session.commit()


def append_name_comment():
    with open('./data/vwAcHastDetail_202212092059.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            # print(row, flush=True)
            if x := row.get('nameComment'):
                print(row['SN'], x, flush=True)
                ea = RecordAssertion(record_id=row['SN'], value=x, assertion_type_id=16)
                session.add(ea)
        session.commit()

def conv_hast21(key):
    '''
    independ: person, geo,taxon, assertion_type

    make_proj
    '''
    engine2 = create_engine('postgresql+psycopg2://postgres:example@postgres:5432/hast21', convert_unicode=True)
    with engine2.connect() as con:

        if key == 'person':
            make_person(con)
        elif key == 'geo':
            make_geospatial(con)
        elif key == 'taxon':
            make_taxon(con)
        elif key == 'record':
            make_record(con)
        elif key == 'assertion_type_option':
            make_assertion_type_option(con)
        elif key == 'proj':
            make_proj(con)
        elif key == 'other-csv':
            make_other_csv()
        elif key == 'img':
            make_images(con)
        elif key == 'name-comment':
            append_name_comment()

def process_text(process_list, text_list):
    if len(text_list) == 0:
        return ''

    result = ''
    for process, args in process_list.items():
        if process == 'join':  # concatenate text part
            result = args.get('char', ',').join(text_list)
        elif process == 'one' and args is True:
            result = text_list[0]

        if process == 'capitalize' and args is True:
            result = result.capitalize()
        if process == 'end':
            result = f"{result}{args['char']}"

    return result

def get_entity(key):
    unit = None
    record = None
    entity = {
        'type': 'unit',
        'record': None,
        'unit': None,
    }

    entity_type = key[0]
    item_id = key[1:]
    if entity_type == 'u':
        unit = session.get(Unit, item_id)
        entity.update({
            'unit': unit,
            'record': unit.record,
        })
    elif entity_type == 'r':
        record = session.get(Record, key[1:])
        entity.update({
            'type': 'record',
            'record': session.get(Record, key[1:]),
        })
    '''
    ppp = [
        [
            ['veget', ['cap', 'end']],
            ['topography', ['cap', 'end']]
        ], ['join'],
        [
            [['life-form', 'plant-h'], ['join', 'cap']],
            [['fruit', 'fruit-color', 'flower', 'flower-color', 'sex-char'], ['join']]
        ], ['join']
    ]
    '''
    # generate label text
    # ordered dict after python 3.6
    hast_label_policy = {
        'biotope1a': {
            'label': '1a',
            'parameter_list': ['veget'],
            'process_list': {
                'one': True,
                'capitalize': True,
                'end': {
                    'char': '.'
                }
            }
        },
        'biotope1b': {
            'label': '1b',
            'parameter_list': ['topography'],
            'process_list': {
                'one': True,
                'capitalize': True,
                'end': {
                    'char': '.'
                }
            }
        },
        'mof1': {
            'label': '2a',
            'parameter_list': ['life-form', 'plant-h'],
            'process_list': {
                'join': {
                    'char': ', '
                },
                'capitalize': True,
                #'end': {
                #    'char': '.'
                #},
            }
        },
        'mof2': {
            'label': '2b',
            'parameter_list': ['fruit', 'fruit-color', 'flower', 'flower-color', 'sex-char'],
            'process_list': {
                'join': {
                    'char': ', '
                },
                #'end': {
                #    'char': '.'
                #}
            },
        },
        'biotope2': {
            'label': '3',
            'parameter_list': ['habitat', 'light-intensity', 'humidity', 'abundance'],
            'process_list': {
                'join': {
                    'char': ', '
                },
                'capitalize': True,
                'end': {
                    'char': '.'
                }
            }
        }
    }
    hast_label_format = ['biotope1a+biotope1b', 'mof1+mof2', 'biotope2']
    annotations = {}
    assertion_map = {}
    hast_label_output = {
        '1st': {
            'parameter_list': ['biotope1a', 'biotope1b'],
            'process_list': {
                'join': {
                    'char': ' ',
                },
            }
        },
        '2nd': {
            'parameter_list': ['mof1', 'mof2'],
            'process_list': {
                'join': {
                    'char': '; ',
                },
                'end': {
                    'char': '.',
                }
            }
        },
        '3rd': {
            'parameter_list': ['biotope2',],
            'process_list': {
                'join': {
                    'one': True,
                },
            }
        }
    }
    record_assertions = entity['record'].assertions
    for a in record_assertions:
        assertion_map[a.assertion_type.name] = a.value

    if entity['type'] == 'unit':
        unit_assertions = entity['unit'].assertions
        for a in unit_assertions:
            assertion_map[a.assertion_type.name] = a.value

    text_map = {}
    for name, policy in hast_label_policy.items():
        text_map[name] = process_text(
            policy['process_list'],
            [assertion_map[x] for x in policy['parameter_list'] if assertion_map.get(x, '')])

    for name2, policy2 in hast_label_output.items():
        p = process_text(
            policy2['process_list'],
            [text_map[x] for x in policy2['parameter_list'] if text_map.get(x, '')]
        )
        annotations[name2] = p

    entity.update({
        'annotation_list': annotations,
    })

    return entity


def import_checklist():
    nlist = '''Reinboldiella warburgii (Heydrich) Yoshida et Mikami
    Augophyllum kentingii Lin, Fredericq et Hommersand
    Gracilaria huangii Lin & de Clerck
    Martensia lewisiae Lin, Hommersand & Fredericq
    Martensia formosana Lin, Hommersand & Fredericq
    Gracilaria huangii Lin & de Clerck
    Dichotomaria hommersandii S.-L. Liu et S.-M. Lin
    Actinotrichia taiwanica S. L. Liu et W. L. Wang
    Actinotrichia fragilis (Forsskal) Børgesen
    Actinotrichia robusta Itono
    Gelidiophycus hongkonensis S.-M. Lin & L.-C. Liu'''

    count = 0
    #cnames = list(map(lambda x: '{} {}'.format(x.split(' ')[0], x.split(' ')[1]), nlist.split('\n')))
    higher_rank_list = ['kingdom', 'phylum', 'class', 'order', 'family', 'genus']
    name = './data/TaiwanSpecies20221102_UTF8.csv'
    import csv
    def nonull(s):
        if s == 'NULL':
            return ''
        else:
            return s

    rank = {
    }

    with open(name, 'r') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            '''
            parents = []
            for rank in higher_rank_list:
                if t := Taxon.query.filter(Taxon.full_scientific_name==row[rank], Taxon.rank==rank, Taxon.tree_id==2).first():
                    parents.append(t.id)
                else:
                    t = Taxon(full_scientific_name=row[rank], rank=rank, tree_id=2)
                    #tr = TaxonRelation(depth=0, parent_id=t.id, child_id=)
                    session.add(t)
                    session.commit()
                    parents.append(t.id)
            '''
            # get full name
            fname_list = []
            if x := nonull(row['genus']):
                fname_list.append(x)
            if x := nonull(row['species']):
                fname_list.append(x)
            if nonull(row['author2']):
                if x := nonull(row['author']):
                    fname_list.append(x)
            if x := nonull(row['infraspecies_marker']):
                if y := nonull(row['infraspecies']):
                    fname_list.append(x)
                else:
                    fname_list.append(f'[{x}]')
            if x := nonull(row['infraspecies']):
                fname_list.append(x)
            if x := nonull(row['infraspecies2_marker']):
                fname_list.append(x)
            if x := nonull(row['infraspecies2']):
                fname_list.append(x)
            if x := nonull(row['author2']):
                fname_list.append(x)
            elif x:= nonull(row['author']):
                fname_list.append(x)

            t = Taxon(
                canonical_name=nonull(row['name']),
                rank='species',
                first_epithet=nonull(row['species']),
                author=nonull(row['author']),
                common_name=nonull(row['common_name_c']),
                source_data=row,
                is_accepted=True if nonull(row['is_accepted_name']) == '1' else False,
                provider_id=1,
                provider_source_id=nonull(row['name_code']),
                full_scientific_name=' '.join(fname_list),
            )

            if nonull(row['author']) and nonull(row['author2']) and row['kingdom'] == 'Plantae':
                print(row, flush=True)
                break
            #if row['genus'] == 'Pyropia' and row['species'] == 'acanthophora':
            #if nonull(row['infraspecies2_marker']): # good example
            # author2 122976
            # if nonull(row['name_code'] == '420365'):
            #         print(row, flush=True)
            #         print(fname_list, flush=True)
            #     break

            #if row['phylum'] == 'Rhodophyta' and row['is_accepted_name'] == '1':
            #    print(row, flush=True)
            #    break
            #    count += 1
            #break

            #session.add(t)
            #session.commit()

            '''
            tr = TaxonRelation(parent_id=t.id, child_id=t.id, depth=0)
            session.add(tr)
            for index, pid in enumerate(parents):
                depth = len(parents) - index
                TaxonRelation.query.filter(TaxonRelation.parent_id==pid, ).first()
                tr = TaxonRelation(parent_id=pid, child_id=t.id, depth=len(parents)-index)
                tr = TaxonRelation(parent_id=pid, child_id=t.id, depth=len(parents)-index)
            session.commit()
            '''
        print(count)

def get_specimen(entity_key):
    org_code, catalog_number = entity_key.split(':')
    stmt = select(Collection.id) \
        .join(Organization) \
        .where(Organization.code==org_code)

    result = session.execute(stmt)
    collection_ids = [x[0] for x in result.all()]
    if entity := Unit.query.filter(Unit.catalog_number==catalog_number, Unit.collection_id.in_(collection_ids)).first():
        return entity
    return None
