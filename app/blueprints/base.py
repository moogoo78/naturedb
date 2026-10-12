import json
from datetime import datetime
import re
import os

from flask import (
    Blueprint,
    request,
    render_template,
    jsonify,
    abort,
    g,
    current_app,
    send_from_directory,
    flash,
    redirect,
    url_for,
)
from sqlalchemy import (
    select,
    func,
    text,
    desc,
    cast,
    between,
    extract,
    join,
)

from app.models.site import (
    Organization,
    User,
)
from app.models.collection import (
    Collection,
    Record,
    RecordAssertion,
    AssertionType,
    AreaClass,
    Unit,
    UnitAssertion,
    Identification,
    Taxon,
)
from app.models.gazetter import (
    NamedArea,
)
from app.models.taxon import (
    Taxon,
)
from app.helpers import (
    get_current_site,
)

from app.database import (
    session,
)

base = Blueprint('base', __name__)


@base.route('/portals')
def portal_list():
    #site_list = Organization.query.filter(Organization.is_site==True).all()
    return render_template('portal-list.html', site_list=[])

@base.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
@base.route('/robots.txt')
def robots_txt():
    from app.models.site import Site
    site = Site.query.filter(Site.host == request.host).first()
    if site:
        site_dir = os.path.join(current_app.static_folder, 'sites', site.name)
        if os.path.exists(os.path.join(site_dir, 'robots.txt')):
            return send_from_directory(site_dir, 'robots.txt')
    return send_from_directory(current_app.static_folder, 'robots.txt')


@base.route('/assets/<path:filename>')
def assets(filename):
    #return send_from_directory('/build/data-search', filename)
    return send_from_directory('/app/static/assets/data-search', filename)


'''
@main.route('/zh')
@main.route('/en')
@main.route('/')
def index():
    # print(subdomain, flush=True)
    g.lang_code = 'zh'
    domain = request.headers['Host']
    print(domain, flush=True)
    if site := Organization.get_site(domain):
        articles = [x.to_dict() for x in Article.query.order_by(Article.publish_date.desc()).limit(10).all()]
        #units = Unit.query.filter(Unit.catalog_number!='').order_by(func.random()).limit(4).all()
        units = []
        stmt = select(Unit.id).where(Unit.catalog_number!='').order_by(func.random()).limit(4)
        results = session.execute(stmt)
        for i in results.all():
            u = session.get(Unit, int(i[0]))
            units.append(u)

        return render_template('index.html', articles=articles, units=units, site=site)
    else:
        return render_template('cover.html')
'''
'''
@main.route('/<lang>/data')
@main.route('/data')
def data_explore(lang=''):
    if lang in ['en', 'zh']:
        setattr(g, 'LOCALE', lang)

    options = {
        'type_status': Unit.TYPE_STATUS_CHOICES,
    }
    org = session.get(Organization, 1)
    return render_template('data-explore.html', options=options, organization=org)


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

    if u := Unit.query.filter(Unit.catalog_number==cat_num).first():
        return render_template('specimen-image.html', unit=u)
    else:
        first_3 = cat_num[0:3]
        img_url = f'http://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{cat_num}_s.jpg'
        return render_template('specimen-image.html', image_url=img_url)
'''
