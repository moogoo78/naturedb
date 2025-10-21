import json
from datetime import datetime
import re
import os
import math

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
    or_,
    join,
)
from sqlalchemy.orm import (
    aliased,
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
    Person,
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

@base.route('/search')
def portal_search():
    site_list = Organization.query.filter(Organization.is_site==True).all()

    current_page = int(request.args.get('page', 1))
    q = request.args.get('q', '')

    taxon_family = aliased(Taxon)
    stmt = select(Unit.id, Unit.accession_number, Record.id, Record.collector_id, Record.field_number, Record.collect_date, Record.proxy_taxon_scientific_name, Record.proxy_taxon_common_name, Record.proxy_taxon_id) \
        .join(Unit, Unit.record_id==Record.id) \
        .join(taxon_family, taxon_family.id==Record.proxy_taxon_id, isouter=True) \
    #print(stmt, flush=True)
    if q:
        stmt = select(Unit.id, Unit.accession_number, Record.id, Record.collector_id, Record.field_number, Record.collect_date, Record.proxy_taxon_scientific_name, Record.proxy_taxon_common_name, Record.proxy_taxon_id) \
        .join(Unit, Unit.record_id==Record.id) \
        .join(Person, Record.collector_id==Person.id, isouter=True)

        stmt = stmt.filter(or_(Unit.accession_number.ilike(f'%{q}%'),
                               Record.field_number.ilike(f'%{q}%'),
                               Person.full_name.ilike(f'%{q}%'),
                               Person.full_name_en.ilike(f'%{q}%'),
                               Record.proxy_taxon_scientific_name.ilike(f'%{q}%'),
                               Record.proxy_taxon_common_name.ilike(f'%{q}%'),
                               ))

    # apply collection filter by site
    #stmt = stmt.filter(Record.collection_id.in_(site.collection_ids))
    print(stmt, flush=True)
    base_stmt = stmt
    subquery = base_stmt.subquery()
    count_stmt = select(func.count()).select_from(subquery)
    total = session.execute(count_stmt).scalar()

    # order & limit
    stmt = stmt.order_by(desc(Record.id))
    if current_page > 1:
        stmt = stmt.offset((current_page-1) * 20)
    stmt = stmt.limit(20)

    result = session.execute(stmt)
    rows = result.all()
    last_page = math.ceil(total / 20)
    pagination = {
        'current_page': current_page,
        'last_page': last_page,
        'start_to': min(last_page-1, 3),
        'has_next': True if current_page < last_page else False,
        'has_prev': True if current_page > 1 else False,
    }
    items = []
    for r in rows:
        record = session.get(Record, r[2])
        loc_list = [x.display_name for x in record.named_areas]
        if loc_text := record.locality_text:
            loc_list.append(loc_text)
        collector = ''
        if r[3]:
            collector = record.collector.display_name
        #collector = '{} ({})'.format(r[4], r[5])
        #elif r[4]:
        #    collector = r[4]

        entity_id = f'u{r[0]}' if r[0] else f'r{r[2]}'

        # HACK
        if r[8]:
            taxon_display = ''
            if taxon := session.get(Taxon, r[8]):
                #if family := taxon.get_higher_taxon('family'):
                #    taxon_family = f
                taxon_display = taxon.display_name

            item = {
                'accession_number': r[1] or '',
                'record_id': r[2],
                'field_number': r[4] or '',
                'collector': collector,
                'collect_date': r[5].strftime('%Y-%m-%d') if r[5] else '',
                'scientific_name': taxon_display, # r[6]
                'common_name': '', #r[7],
                'locality': ','.join(loc_list),
                'entity_id': entity_id,
            }
            items.append(item)


    return render_template('portal-search.html', site_list=site_list, items=items, total=total, pagination=pagination)

@base.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
@base.route('/robots.txt')
def robots_txt():
    return send_from_directory(os.path.join(current_app.static_folder), 'robots.txt')


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
        #units = Unit.query.filter(Unit.accession_number!='').order_by(func.random()).limit(4).all()
        units = []
        stmt = select(Unit.id).where(Unit.accession_number!='').order_by(func.random()).limit(4)
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

    if u := Unit.query.filter(Unit.accession_number==cat_num).first():
        return render_template('specimen-image.html', unit=u)
    else:
        first_3 = cat_num[0:3]
        img_url = f'http://brmas-pub.s3-ap-northeast-1.amazonaws.com/hast/{first_3}/S_{cat_num}_s.jpg'
        return render_template('specimen-image.html', image_url=img_url)
'''
