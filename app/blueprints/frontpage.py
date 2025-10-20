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
from app.helpers import (
    get_current_site,
    get_site_stats,
    get_specimen,
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

    if request and request.headers:
        if host := request.headers.get('Host'):
            # go to portal
            if host == current_app.config['PORTAL_HOST']:
                if request.path == '/':
                    g.site = '__PORTAL__'
                else:
                    return abort(404)
        elif site := get_current_site(request):
            g.site = site
    else:
        return abort(404)

@frontpage.route('/', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>')
def index(lang_code):
    #current_app.logger.debug(f'{g.site.name}, {lang_code}')
    if g.site == '__PORTAL__':
        return render_template('landing.html')
    else:
        stats = get_site_stats(g.site)
        features = Unit.query.filter(Unit.accession_number!='', Unit.collection_id.in_(g.site.collection_ids), Unit.pub_status=='P').order_by(func.random()).limit(4).all()
        news = Article.query.filter(Article.site_id==g.site.id).order_by(desc(Article.publish_date)).limit(4).all()

        if hasattr(g, 'site'):
            try:
                return render_template(
                    f'sites/{g.site.name}/index.html',
                    features=features,
                    news=news,
                    stats=stats,
                )
            except TemplateNotFound:
                return render_template(
                    'index.html',
                    features=features,
                    news=news,
                    stats=stats,
                )



        else:
            return 'index'

@frontpage.route('/ping', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/ping')
def ping(lang_code):
    return 'pong'

@frontpage.route('/news', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/news')
def news(lang_code):
    articles  = Article.query.filter(Article.site_id==g.site.id).order_by(desc(Article.publish_date)).limit(20).all()
    try:
        return render_template(f'sites/{g.site.name}/news.html', articles=articles)
    except TemplateNotFound:
        return render_template('news.html', articles=articles)

@frontpage.route('/about', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/about')
def about(lang_code):
    try:
        return render_template(f'sites/{g.site.name}/about.html')
    except TemplateNotFound:
        return render_template('about.html')

@frontpage.route('/pages/<path:name>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/pages/<path:name>')
def page(lang_code, name=''):
    page_settings = g.site.get_settings('pages')
    if page_settings:
        if name in page_settings:
            page_name = name.replace('/', '_')
            try:
                return render_template(f'sites/{g.site.name}/page-{page_name}.html')
            except TemplateNotFound:
                return 'template not found'
    return 'page'


@frontpage.route('/articles/<article_id>', defaults={'lang_code': DEFAULT_LANG_CODE})
def article_detail(lang_code, article_id):
    article = Article.query.get(article_id)
    article.content_html = markdown.markdown(article.content, extensions=['attr_list'])

    try:
        return render_template(f'sites/{g.site.name}/article-detail.html', article=article)
    except TemplateNotFound:
        return render_template('article-detail.html', article=article)


@frontpage.route('/specimens/SpecimenDetailC.aspx', defaults={'lang_code': DEFAULT_LANG_CODE})
def specimen_detail_legacy(lang_code):
    # TODO: move to nginx conf
    if key := request.args.get('specimenOrderNum'):
        entity = Unit.get_specimen(f'HAST:{int(key)}')
        try:
            return render_template(f'sites/{g.site.name}/specimen-detail.html', entity=entity)
        except TemplateNotFound:
            return render_template('specimen-detail.html', entity=entity)

    return abort(404)

#@frontpage.route('/collections/<path:record_key>', defaults={'lang_code': DEFAULT_LANG_CODE})
#@frontpage.route('/<lang_code>/collections/<path:record_key>')
@frontpage.route('/specimens/<path:record_key>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/specimens/<path:record_key>')
def specimen_detail(record_key, lang_code):
    data = get_specimen(record_key, g.site.collection_ids)
    print(data)
    try:
        return render_template(f'sites/{g.site.name}/specimen-detail.html', data=data)
    except TemplateNotFound:
        return render_template('specimen-detail.html', data=data)

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
    options = {
        'type_status': [],
        'family': [],
        'collections': [{'value': x.id, 'text': x.label} for x in g.site.collections],
    }
    options['type_status'] = [{'value': x[0], 'text': x[1].upper()} for x in Unit.TYPE_STATUS_OPTIONS]
    family_list = Taxon.query.filter(Taxon.rank=='family').all()

    for x in family_list:
        d = x.to_dict()
        options['family'].append({'value': d['id'], 'text': d['display_name']})

    api_url = request.root_url
    # flask's request in prod env request.base_url will generate 'http' not 'https'
    if current_app.config['WEB_ENV'] != 'dev':
        if api_url[0:5] == 'http:':
            api_url = api_url.replace('http:', 'https:')
    try:
        return render_template(f'sites/{g.site.name}/data-search.html', options=options, SEARCH_API_URL=api_url)
    except TemplateNotFound:
        return render_template('data-search.html', options=options, SEARCH_API_URL=api_url)

@frontpage.route('/test-entity/<key>', defaults={'lang_code': DEFAULT_LANG_CODE})
@frontpage.route('/<lang_code>/test-entity/<key>')
def test_entity(lang_code, key):
    data = {
        'record_id': 0,
        'unit_id': 0,
        'catalog_number': 0,
    }
    if 'ark:' in key:
        pass
    elif ':' in key:
        klist = key.split(':')
        stmt = (
            select(Collection.id)
            .select_from(Site)
            .join(Collection)
            .where(Site.name == klist[0].lower())
        )
        collection_ids = session.execute(stmt).all()
        stmt2 = (
            select(Record, Unit)
            .join(Unit)
            .where(Unit.accession_number==klist[1])
        )
        entities = session.execute(stmt2).first()
        data.update({
            'record_id': entities[0].id,
            'unit_id': entities[1].id,
            'info': entities[0].get_info(),
            'catalog_number': klist[1],
        })

    return jsonify(data)
