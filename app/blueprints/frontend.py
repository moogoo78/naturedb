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
from app.utils import (
    get_cache,
    set_cache,
    get_domain,
)

frontend = Blueprint('frontend', __name__, url_prefix='/<locale>')

#@frontend.before_request
#def foo():
#    print('foo', request, flush=True)


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
                    'specimen_url': u.specimen_url,
                    'accession_number': u.accession_number,
                    'type_status': u.type_status
                })
                units = sorted(units, key=lambda x: (x['family'], x['scientific_name']))
                unit_stats = {'units': units, 'stats': stats}
                set_cache(CACHE_KEY, unit_stats, CACHE_EXPIRE)

    return unit_stats


@frontend.url_defaults
def put_url_attr(endpoint, values):
    #values.setdefault('locale', g.lang_code)
    # print('put', endpoint, values, flush=True)
    if loc := values.get('locale', ''):
        setattr(g, 'locale', loc)
        values.setdefault('locale', loc)


@frontend.url_value_preprocessor
def get_url_attr(endpoint, values):
    # print('get', endpoint, values, flush=True)
    if loc := values.get('locale', ''):
        if loc in ['en', 'zh']:
            setattr(g, 'locale', loc)
            values.setdefault('locale', loc)
        else:
            return abort(404)


@frontend.route('/')
def index(locale):
    domain = get_domain(request)
    #print(domain, locale, flush=True)

    if site := Organization.get_site(domain):
        if site.id == 1:
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
            return render_template('index-other.html', site=site)
    else:
        abort(404)


@frontend.route('/<name>')
def page(locale, name=''):
    domain = get_domain(request)
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
def article_detail(locale, article_id):
    article = Article.query.get(article_id)
    article.content_html = markdown.markdown(article.content)
    return render_template('article-detail.html', article=article)


@frontend.route('/specimens/<entity_key>')
def specimen_detail(locale, entity_key):
    org = session.get(Organization, 1)
    if entity := Unit.get_specimen(entity_key):
        return render_template('specimen-detail.html', entity=entity, site=org)
    else:
        return abort(404)

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

@frontend.route('/data')
def data_explore(locale):
    options = {
        'type_status': Unit.TYPE_STATUS_CHOICES,
    }
    org = session.get(Organization, 1)
    return render_template('data-explore.html', options=options, site=org)
