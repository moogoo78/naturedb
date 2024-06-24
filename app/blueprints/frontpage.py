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
from jinja2.exceptions import TemplateNotFound
from sqlalchemy import (
    desc,
    func,
    select,
)
import markdown

from app.database import session

from app.models.site import (
    Article,
    Site,
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
)
from app.helpers_query import (
    make_specimen_query,
)
from app.config import Config

#frontend = Blueprint('frontend', __name__, url_prefix='/<lang_code>')
frontpage = Blueprint('frontpage', __name__)

DEFAULT_LANG_CODE = Config.DEFAULT_LANG_CODE

@frontpage.url_defaults
def add_language_code(endpoint, values):
    #print('add code', endpoint, values, flush=True)
    if 'lang_code' in values or not 'lang_code' in g:
        return
    #else:
    #    values.setdefault('lang_code', g.lang_code)

    #if app.url_map.is_endpoint_expecting(endpoint, 'lang_code'):
    #    values['lang_code'] = g.lang_code
    #print('expect', current_app.url_map.is_endpoint_expecting(endpoint, 'lang_code'), flush=True)


@frontpage.url_value_preprocessor
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


@frontpage.route('/', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>')
def index(lang_code):
    #current_app.logger.debug(f'{g.site.name}, {lang_code}')
    try:
        return render_template(f'sites/{g.site.name}/index.html')
    except TemplateNotFound:
        return render_template('index.html')


@frontpage.route('/news', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/news')
def news(lang_code):
    #articles = [x.to_dict() for x in Article.query.filter(Article.site_id==g.site.id).order_by(Article.publish_date.desc()).limit(10).all()]
    articles = [x.to_dict() for x in Article.query.order_by(Article.publish_date.desc()).limit(10).all()]

    try:
        return render_template(f'sites/{g.site.name}/news.html', articles=articles)
    except TemplateNotFound:
        return render_template('news.html', articles=articles)


@frontpage.route('/pages/<path:name>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/pages/<path:name>')
def page(lang_code, name=''):
    if g.site.data:
        if name in g.site.data.get('pages'):
            page_name = name.replace('/', '_')
            try:
                return render_template(f'sites/{g.site.name}/page-{page_name}.html')
            except TemplateNotFound:
                return 'template not found'
    return 'page'


@frontpage.route('/articles/<article_id>', defaults={'lang_code': DEFAULT_LANG_CODE})
def article_detail(lang_code, article_id):
    article = Article.query.get(article_id)
    article.content_html = markdown.markdown(article.content)

    try:
        return render_template(f'sites/{g.site.name}/article-detail.html', article=article)
    except TemplateNotFound:
        return render_template('article-detail.html', article=article)


@frontpage.route('/specimens/SpecimenDetailC.aspx', defaults={'lang_code': DEFAULT_LANG_CODE})
def specimen_detail_legacy(lang_code):
    if key := request.args.get('specimenOrderNum'):
        entity = Unit.get_specimen(f'HAST:{int(key)}')
        return render_template('specimen-detail.html', entity=entity)
    return abort(404)
 
@frontpage.route('/collections/<path:record_key>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/collections/<path:record_key>')
@frontpage.route('/specimens/<path:record_key>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/specimens/<path:record_key>')
#@frontpage.route('/specimens/<record_key>')
def specimen_detail(record_key, lang_code):
    entity = None
    # TODO: 判斷domain
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
        try:
            return render_template(f'sites/{g.site.name}/specimen-detail.html', entity=entity)
        except TemplateNotFound:
            return render_template('specimen-detail.html', entity=entity)

    return abort(404)


@frontpage.route('/records/<int:record_id>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/records/<int:record_id>')
def record_detail(record_id, lang_code):
    entity = None
    # TODO: 判斷domain
    try:
        id_ = int(record_id)
        entity = session.get(Record, id_)
    except ValueError:
        pass

    if entity:
        try:
            return render_template(f'sites/{g.site.name}/specimen-detail.html', entity=entity)
        except TemplateNotFound:
            return render_template('specimen-detail.html', entity=entity)

    return abort(404)


@frontpage.route('/species/<int:taxon_id>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/species/<int:taxon_id>')
def species_detail(taxon_id, lang_code):
    if species := session.get(Taxon, taxon_id):
        stmt = make_specimen_query({'taxon_id': taxon_id})
        result = session.execute(stmt)
        items = []
        for row in result.all():
            items.append(row)

        try:
            return render_template(f'sites/{g.site.name}/species-detail.html', species=species, items=items)
        except TemplateNotFound:
            return render_template('species-detail.html', species=species, items=items)
    else:
        return abort(404)

@frontpage.route('/taxa', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/taxa')
def taxa_index(lang_code):
    taxa = Taxon.query.filter(Taxon.rank=='family').order_by(Taxon.full_scientific_name).all()

    try:
        return render_template(f'sites/{g.site.name}/taxa-index.html', taxa=taxa)
    except TemplateNotFound:
        return render_template('taxa-index.html', taxa=taxa)

@frontpage.route('/specimen-image/<entity_key>')
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

@frontpage.route('/data', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/data')
def data_search(lang_code):
    #print(mimetypes.knownfiles, flush=True)

    try:
        return render_template(f'sites/{g.site.name}/data-search.html')
    except TemplateNotFound:
        return render_template('data-search.html')
