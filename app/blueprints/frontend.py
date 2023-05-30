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
from app.models.site import (
    Article,
    Organization,
)
from app.models.collection import (
    Unit,
    Person,
    Collection,
    Record,
)
from app.models.taxon import (
    Taxon,
)

from app.helpers import (
    get_specimen,
    get_or_set_type_specimens,
)

frontend = Blueprint('frontend', __name__, url_prefix='/<locale>')

#@frontend.before_request
#def foo():
#    print('foo', request, flush=True)

@frontend.url_defaults
def put_url_attr(endpoint, values):
    #values.setdefault('locale', g.lang_code)
    print('put', endpoint, values, flush=True)
    if loc := values.get('locale', ''):
        setattr(g, 'locale', loc)
        values.setdefault('locale', loc)


@frontend.url_value_preprocessor
def get_url_attr(endpoint, values):
    print('get', endpoint, values, flush=True)
    if loc := values.get('locale', ''):
        if loc in ['en', 'zh']:
            setattr(g, 'locale', loc)
            values.setdefault('locale', loc)
        else:
            return abort(404)


@frontend.route('/')
def index(locale):
    domain = request.headers['Host']
    #print(domain, locale, flush=True)

    if site := Organization.get_site(domain):
        articles = [x.to_dict() for x in Article.query.filter(Article.organization_id==site.id).order_by(Article.publish_date.desc()).limit(10).all()]
        #units = Unit.query.filter(Unit.accession_number!='').order_by(func.random()).limit(4).all()
        units = []
        stmt = select(Unit.id).where(Unit.accession_number!='', Collection.organization_id==site.id).join(Record).join(Collection).order_by(func.random()).limit(4)

        results = session.execute(stmt)
        for i in results.all():
            u = session.get(Unit, int(i[0]))
            units.append(u)

        return render_template('index.html', articles=articles, units=units, site=site)
    else:
        abort(404)


@frontend.route('/<name>')
def page(locale, name=''):
    domain = request.headers.get('Host', '')
    if site := Organization.get_site(domain):
        #print(site, flush=True)
        if name in ['making-specimen', 'visiting', 'people', 'about']: # TODO page, tempalet mapping
            return render_template(f'page-{name}.html', site=site)
        elif name == 'type-specimens':
            unit_stats = get_or_set_type_specimens()
            return render_template('page-type-specimens.html', unit_stats=unit_stats, site=site)
            return 'ok'

        elif name == 'related-links':
            return render_template('related_links.html', site=site)

    return abort(404)

@frontend.route('/articles/<article_id>')
def article_detail(article_id):
    article = Article.query.get(article_id)
    article.content_html = markdown.markdown(article.content)
    return render_template('article-detail.html', article=article)
