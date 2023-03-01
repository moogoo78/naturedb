import json
from datetime import datetime
import re

from flask import (
    Blueprint,
    request,
    render_template,
    jsonify,
    abort,
    g,
)
from sqlalchemy import (
    desc,
    func,
    select,
)
from babel.support import Translations
from flask_babel import (
    get_locale,
)
from app.database import session
#from app.models import Dataset, Collection
# from app.models import (
#     Article,
#     Collection,
#     Person,
#     Unit,
#     Identification,
#     MeasurementOrFactParameterOption,
#     MeasurementOrFact,
#     Dataset,
#     MultimediaObject,
#     Organization,
# )
from app.models.site import (
    Article,
    Organization,
)
from app.models.collection import (
    Unit,
    Person,
    Collection,
)
from app.models.taxon import (
    Taxon,
)

from app.helpers import (
    conv_hast21,
    import_checklist,
    get_specimen,
    import_algae,
)

main = Blueprint('main', __name__)


@main.route('/conv-hast21')
def conv_hast21_view():
    key = request.args.get('key')
    start = datetime.now()
    conv_hast21(key)
    end = datetime.now()
    return jsonify({
        'start': start,
        'end': end,
        'dur': (end-start).total_seconds(),
        'key': key,
    })

B_NAME = '''
Begonia acutis
Begonia arachnoidea
Begonia asteropyrifolia
Begonia aurantiflora
Begonia auritistipula
Begonia austroguangxiensis
Begonia babeana
Begonia bamaensis
Begonia bellii
Begonia biflora
Begonia bonii var. remotisetulosa
Begonia bretschneideriana
Begonia calciphila
Begonia catbensis
Begonia cavaleriei
Begonia cavaleriei var. cavaleriei
Begonia cavaleriei var. pinfaensis
Begonia chongzuoensis
Begonia circularis
Begonia cirrosa
Begonia crispula later homonym
Begonia crystallina
Begonia curvicarpa
Begonia cylindrica
Begonia daxinensis
Begonia debaoensis
Begonia erectocarpa
Begonia esquirolii
Begonia fangii
Begonia ferox
Begonia filiformis
Begonia fimbribracteata
Begonia floribunda later homonym
Begonia gigaphylla
Begonia guangdongensis
Begonia guangxiensis
Begonia guixiensis
Begonia gulongshanensis
Begonia huangii
Begonia jingxiensis
Begonia kui
Begonia langsonensis
Begonia lanternaria
Begonia larvata
Begonia leipingensis
Begonia leprosa
Begonia liuyanii
Begonia locii
Begonia longa
Begonia longgangensis
Begonia longiornithophylla
Begonia longistyla
Begonia lui
Begonia luochengensis
Begonia luzhaiensis
Begonia macrorhiza orth. var.
Begonia masoniana
Begonia masoniana nom. nud.
Begonia masoniana var. maculata
Begonia masoniana var. masoniana
Begonia melanobullata
Begonia minissima
Begonia mollissima
Begonia montaniformis
Begonia morsei
Begonia morsei var. morsei
Begonia morsei var. myriotricha
Begonia nahangensis
Begonia ningmingensis
Begonia ningmingensis var. bella
Begonia ningmingensis var. ningmingensis
Begonia obliquifolia
Begonia obsolescens
Begonia ornithophylla
Begonia pengii
Begonia phuthoensis
Begonia picturata
Begonia platycarpa
Begonia porteri
Begonia porteri var. macrorhiza
Begonia porteri var. porteri
Begonia pseudodaxinensis
Begonia pseudodryadis
Begonia pseudodryadis var. bitepala
Begonia pseudoleprosa
Begonia pulvinifera
Begonia remusatifolia
Begonia retinervia
Begonia rhynchocarpa
Begonia rhytidophylla
Begonia rugosula
Begonia scabrifolia
Begonia semicava nom. nud.
Begonia semiparietalis
Begonia setulosopeltata
Begonia sinofloribunda
Begonia sonlaensis
Begonia subcoriacea
Begonia ufoides
Begonia umbraculifolia
Begonia umbraculifolia var. flocculosa
Begonia umbraculifolia var. umbraculifolia
Begonia variegata
Begonia variifolia
Begonia wangii
Begonia yishanensis
Begonia yizhouensis
Begonia zhangii
Begonia zhengyiana
Begonia zhuoyuniae
Begonia ×breviscapa'''

@main.route('/admin/biotope_options')
def get_measurement_or_fact_option_list():
    biotope_list = ['veget', 'topography', 'habitat', 'naturalness', 'light-intensity', 'humidity', 'abundance']
    data = {x: {'name':x, 'label': '', 'options': []} for x in biotope_list}
    rows = MeasurementOrFactParameterOption.query.all()
    for row in rows:
        key = row.parameter.name
        if key in biotope_list:
            if data[key]['label'] == '':
                data[key]['label'] = row.parameter.label
            data[key]['options'].append((row.id, row.value, row.value_en))

    ret = [data[x] for x in biotope_list]
    resp = jsonify(ret)
    resp.headers.add('Access-Control-Allow-Origin', '*')
    resp.headers.add('Access-Control-Allow-Methods', '*')
    '''
    rows = MeasurementOrFact.query.all()
    for i in rows:
        if x := MeasurementOrFactParameterOption.query.filter(MeasurementOrFactParameterOption.value_en==i.value_en).first():
            i.option_id = x.id
    session.commit()
    resp = {}
    '''
    return resp


@main.route('/foo')
def foo():
    #import_checklist()
    import_algae()
    return jsonify({})

def find_coel():
    from sqlalchemy import create_engine
    engine2 = create_engine('postgresql+psycopg2://postgres:example@postgres:5432/hast21_0107', convert_unicode=True)
    with engine2.connect() as con:
        rows = con.execute('''
        SELECT s.id, u.accession_number, CONCAT(p.first_name, p.last_name), REPLACE(field_number, '::', '') AS field_number, u.accession_number2, t.full_scientific_name FROM specimen_specimen s
        LEFT JOIN (
          SELECT specimen_id, MAX(verification_level) mv FROM specimen_identification GROUP BY specimen_id
        ) j
        JOIN specimen_identification i ON i.specimen_id = j.specimen_id AND j.mv = i.verification_level
        ON i.specimen_id = s.id
        LEFT JOIN taxon_taxon t ON t.id = i.taxon_id
        LEFT JOIN specimen_accession u ON u.specimen_id = s.id
        LEFT JOIN specimen_person p ON p.id = s.collector_id
        WHERE t.parent_id = 2544;
        ''')
        return rows

def get_image(hast_id, short_name):
    import urllib.request
    from pathlib import Path

    hast_id = int(hast_id)
    hast_id = f'{hast_id:06}'

    short_name = short_name.replace(' ', '_')
    p = Path(f'dist/{short_name}')
    if not p.exists():
        p.mkdir()

    first_3 = hast_id[0:3]
    fname = f'S_{hast_id}_l.jpg'
    imgURL = f'http://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/{fname}'
    try:
        print('downloading...', imgURL, flush=True)
        urllib.request.urlretrieve(imgURL, f'dist/{short_name}/{fname}')
        return True
    except:
        return False


@main.route('/bego')
def bego():
    #get_image(142908)
    coel_names = B_NAME.split('\n')
    rows = find_coel()
    counter = 0
    names = []
    res_1 = 0
    res_m = 0
    res_0 = 0
    res_image = 0
    out_rows = []
    out = open('out.csv', 'w')

    for i in rows:

        counter += 1
        #print (i)
        name = i[5]
        hast_id = i[1]

        has_image = 'N'

        c = 0
        cname = name.split(' ')[1]
        if cname == 'Sect.':
            print(cname)
            #print(i)

        if f'Begonia {cname}' in coel_names:
            c += 1

        if c == 0:
            res_0 += 1
        elif c == 1:
            res_1 += 1
            short_name = [x for x in coel_names if x == f'Begonia {cname}'][0]
            if i[1]:
                is_ok = get_image(hast_id, short_name)
                #print(hast_id, is_ok, short_name)

                if is_ok:
                    res_image += 1
                    has_image = 'Y'
        else:
            res_m += 1

        out_rows = [str(i[0]), str(i[1]) if i[1] else '', i[2], i[3], i[4] if i[4] else '', i[5], has_image, '\n']
        #print(out_rows)
        out.write(','.join(out_rows))

    print(res_0, res_1, res_m, res_image)
    print(counter, flush=True)
    out.close()

    return ('foo-bego')

@main.route('/zh')
@main.route('/en')
@main.route('/')
def index():
    articles = [x.to_dict() for x in Article.query.order_by(Article.publish_date.desc()).limit(10).all()]
    #units = Unit.query.filter(Unit.accession_number!='').order_by(func.random()).limit(4).all()
    units = []
    stmt = select(Unit.id).where(Unit.accession_number!='').order_by(func.random()).limit(4)
    results = session.execute(stmt)
    for i in results.all():
        u = session.get(Unit, int(i[0]))
        units.append(u)

    return render_template('index.html', articles=articles, units=units)

@main.route('/data')
def data_explore():
    options = {
        'type_status': Unit.TYPE_STATUS_CHOICES,
    }
    org = session.get(Organization, 1)
    return render_template('data-explore.html', options=options, organization=org)

@main.route('/robots.txt')
def robots_txt():
    return render_template('robots.txt')

@main.route('/specimens/<entity_key>')
def specimen_detail(entity_key):
    if entity := get_specimen(entity_key):
        return render_template('specimen-detail.html', entity=entity)
    else:
        return abort(404)

    return abort(404)


@main.route('/specimen-image/<entity_key>')
def specimen_image(entity_key):
    keys = entity_key.split(':')
    cat_num = keys[1]
    # delete leading 0
    m = re.search(r'(^0+)(.+)', keys[1])
    if m:
        cat_num = m.group(2)

    if u := Unit.query.filter(Unit.accession_number==cat_num).first():
        return render_template('specimen-image.html', unit=u)
    else:
        first_3 = cat_num[0:3]
        img_url = f'http://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{cat_num}_s.jpg'
        return render_template('specimen-image.html', image_url=img_url)
