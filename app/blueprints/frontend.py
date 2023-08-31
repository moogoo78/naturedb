import re

from flask import (
    Blueprint,
    request,
    render_template,
    jsonify,
    abort,
    g,
    redirect,
    url_for,
    current_app,
)
from sqlalchemy import (
    desc,
    func,
    select,
)
import markdown

from app.database import session

from app.models.site import (
    Article,
    Organization,
)
from app.models.collection import (
    Unit,
    Person,
    Collection,
    Record,
    PersistentIdentifierUnit,
)
from app.models.taxon import (
    Taxon,
)
from app.models.pid import (
    Ark,
    ArkNaan,
)
from app.helpers import (
    get_current_site,
    get_or_set_type_specimens,
)
from app.config import Config

#frontend = Blueprint('frontend', __name__, url_prefix='/<lang_code>')
frontend = Blueprint('frontend', __name__)

DEFAULT_LANG_CODE = Config.DEFAULT_LANG_CODE

@frontend.route('/foo', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontend.route('/<lang_code>/foo')
def foo(lang_code):
    from app.models.collection import PersistentIdentifierUnit
    #a = Ark(naan=12345, identifier='pid.biodiv.tw/ark:/12345/b2')
    #http://myrepo.example.org/ark:/12345/bcd987
    #print(a, flush=True)
    #session.add(a)
    #session.commit()
    #u = Unit.query.get(1)
    #print(u.ark, flush=True)
    #uquery = Unit.query.filter(Collection.organization_id==41).limit(20)
    #stmt = select(Unit.pids, Unit.collection_id).filter(Collection.organization_id==41).limit(20)

    #print(stmt, flush=True)
    #results = session.execute(stmt)
    #for i in results.all():
    #    print(i, flush=True)
    #naan = 18474
    #for u in uquery.all():
    #    a = Ark(naan=18474, identifier=f'/ark:/{08474}/b2')
    #    print(u, flush=True)


    #org = session.get(Organization, 1)
    #print(org, flush=True)
    #org.data = a
    #session.commit()

    f = open('data/ark-150000.txt')
    d = f.read()
    a = d.split(',')
    x = Unit.query.all()
    for i, k in enumerate(x):
        #print(k.collection_id, a[i], flush=True)
        id_ = ''

        if k.collection_id == 5:
            id_ = f'h7{a[i]}'
        else:
            id_ = f'b2{a[i]}'

        key = f'https://hast.biodiv.tw/ark:18474/{id_}'
        #ark = Ark(naan=18474, identifier=, )
        punit = PersistentIdentifierUnit(unit_id=k.id, pid_type='ark', key=key)
        session.add(punit)
    session.commit()

    print(len(x), flush=True)
    return 'foo'

@frontend.url_defaults
def add_language_code(endpoint, values):
    #print('add code', endpoint, values, flush=True)
    if 'lang_code' in values or not 'lang_code' in g:
        return
    #else:
    #    values.setdefault('lang_code', g.lang_code)

    #if app.url_map.is_endpoint_expecting(endpoint, 'lang_code'):
    #    values['lang_code'] = g.lang_code
    #print('expect', current_app.url_map.is_endpoint_expecting(endpoint, 'lang_code'), flush=True)


@frontend.url_value_preprocessor
def pull_lang_code(endpoint, values):
    #print('pull code', endpoint, values, request.path, flush=True)
    lang_code = values.get('lang_code')
    if not lang_code:
        lang_code = request.accept_languages.best_match(['zh', 'en'])

    if lang_code not in current_app.config['LANG_CODES']:
        return abort(404)

    values.setdefault('lang_code', lang_code)
    g.lang_code = lang_code

    #domain = request.headers.get('Host', '')
    if site := get_current_site(request):
        g.site = site


@frontend.route('/news', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontend.route('/<lang_code>/news')
def news(lang_code):
    site = g.site
    if site.id == 1:
        articles = [x.to_dict() for x in Article.query.filter(Article.organization_id==site.id).order_by(Article.publish_date.desc()).limit(10).all()]
        #units = Unit.query.filter(Unit.accession_number!='').order_by(func.random()).limit(4).all()
        units = []
        stmt = select(Unit.id).where(Unit.accession_number!='', Collection.organization_id==site.id).join(Record).join(Collection).order_by(func.random()).limit(4)

        results = session.execute(stmt)
        for i in results.all():
            u = session.get(Unit, int(i[0]))
            units.append(u)
        return render_template('index.html', articles=articles, units=units)
    else:
        return render_template('index-other.html')


@frontend.route('/page/<name>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontend.route('/<lang_code>/page/<name>')
def page(lang_code, name=''):
    if name in ['making-specimen', 'visiting', 'people', 'about']: # TODO page, tempalet mapping
        return render_template(f'page-{name}.html')

    elif name == 'type-specimens':
        unit_stats = get_or_set_type_specimens()
        return render_template('page-type-specimens.html', unit_stats=unit_stats)
    elif name == 'related-links':
        return render_template('related_links.html')

    return 'page'


@frontend.route('/articles/<article_id>', defaults={'lang_code': DEFAULT_LANG_CODE})
def article_detail(lang_code, article_id):
    article = Article.query.get(article_id)
    article.content_html = markdown.markdown(article.content)
    return render_template('article-detail.html', article=article)



@frontend.route('/specimens/<entity_key>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontend.route('/<lang_code>/specimens/<entity_key>')
#@frontend.route('/specimens/<entity_key>')
def specimen_detail(entity_key, lang_code):
    if entity := Unit.get_specimen(entity_key):
        return render_template('specimen-detail.html', entity=entity)

    return abort(404)


@frontend.route('/ark:<naan>/<key>', defaults={'lang_code': DEFAULT_LANG_CODE})
def specimen_ark(naan, key, lang_code):
    if ark_naan := ArkNaan.query.filter(naan==naan).first():
        #print(naan, key, lang_code, flush=True)
        key = f'https://hast.biodiv.tw/ark:{naan}/{key}'
        if pid_unit := PersistentIdentifierUnit.query.filter(
                PersistentIdentifierUnit.key==key).first():
            return render_template('specimen-detail.html', entity=pid_unit.unit)
    return abort(404)

@frontend.route('/specimen-image/<entity_key>')
def specimen_image(locale, entity_key):
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

@frontend.route('/data', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontend.route('/<lang_code>/data')
def data_explore(lang_code):
    options = {
        'type_status': Unit.TYPE_STATUS_CHOICES,
    }
    return render_template('data-explore.html', options=options)
