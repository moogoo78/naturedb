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


@frontend.route('/specimens/<path:record_key>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontend.route('/<lang_code>/specimens/<path:record_key>')
#@frontend.route('/specimens/<record_key>')
def specimen_detail(record_key, lang_code):
    entity = None

    if 'ark:/' in record_key:
        #ark:<naan>/<key>
        naan, identifier = record_key.replace('ark:/', '').split('/')
        if ark_naan := ArkNaan.query.filter(naan==naan).first():
            key = f'ark:/{naan}/{identifier}'
            if unit := Unit.query.filter(Unit.guid==f'https://n2t.net/{key}').first():
                entity = unit
    elif ':' in record_key:
        entity = Unit.get_specimen(record_key)
    try:
        id_ = int(record_key)
        entity = session.get(Unit, id_)
    except ValueError:
        pass

    if entity:
        return render_template('specimen-detail.html', entity=entity)

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
