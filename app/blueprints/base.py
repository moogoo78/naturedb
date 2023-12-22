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
from flask_login import (
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import (
    check_password_hash,
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
    NamedArea,
    Unit,
    UnitAssertion,
    Identification,
    Person,
    Taxon,
)
from app.models.taxon import (
    Taxon,
)
from app.helpers import (
    get_current_site,
)
from app.utils import (
    get_domain,
)
from app.database import (
    session,
)

base = Blueprint('base', __name__)


@base.route('/foo')
def foo():
    import csv

    from app.database import session
    from app.models.collection import Unit, Record, Person, MultimediaObject, MultimediaObjectAnnotation, MultimediaObjectAnnotation

    stats = {'r': 0, 'no': 0, 'no-sn': 0}
    counter = 0
    with open('images_202312201920.csv', newline='') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            counter += 1
            if sn := row.get('SN'):
                if code := row.get('imageCode'):
                    if record := Record.query.filter(Record.source_data['hast']['SN'].astext == sn).first():
                        stats['r'] += 1
                        code_int = int(code) # P_D_BEGO000001A
                        image_id = f'{code_int:07}'
                        first_3 = image_id[:3]
                        folder = image_id[3:4]
                        file_url = f'https://brmas-media.s3.ap-northeast-1.amazonaws.com/hast/species-image/Album/image{first_3}/{folder}/{image_id}.jpg'
                        thumb_url = f'https://brmas-media.s3.ap-northeast-1.amazonaws.com/hast/species-image/thumb/thumb{first_3}/{folder}/{image_id}.jpg'
                        catalog_numbers = [f'HAST:{x.accession_number}' for x in record.units if x.accession_number]
                        title = ','.join(catalog_numbers)
                        story = row.get('creationOperator', '')

                        if x:= row.get('dataReviser'):
                            story = f'{story}, reviser: {x}'

                        format = ''
                        if format_id := row.get('sourceID'):
                            format_id = int(format_id)
                            format = MultimediaObject.PSYSICAL_FORMAT_OPTIONS[format_id-1][0]

                        mo_type= ''
                        if cat_id := row.get('categoryID'):
                            cat_id = int(cat_id)
                            mo_type = MultimediaObject.TYPE_OPTIONS[cat_id-1][0]


                        mo = MultimediaObject(
                            record_id=record.id,
                            title=title,
                            file_url=file_url,
                            thumbnail_url=thumb_url,
                            source_data=row,
                            source='legacy server',
                            created_by=story,
                            note=row.get('note', ''),
                            physical_format=format,
                            multimedia_type=mo_type,
                        )
                        if x := row.get('photoDate'):
                            mo.date_created = x
                        if x := row.get('creationDate'):
                            mo.created = x
                        if x := row.get('updateDate'):
                            mo.updated = x

                        if x := row.get('imgAuthorID'):
                            if person := Person.query.filter(Person.source_data['pid'] == x).first():
                                mo.creator = person.full_name
                                mo.creator_id = person.id

                        if x := row.get('providerID'):
                            if provider := Person.query.filter(Person.source_data['pid'] == x).first():
                                mo.source_text = provider.full_name
                                mo.provider_id = provider.id

                        session.add(mo)
                        session.commit()

                        if x := row.get('greenhouse'):
                            moa_g = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=14,
                                value=1
                            )
                            session.add(moa_g)
                        if x := row.get('wholePlant'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=3,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('root'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=4,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('stem'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=5,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('leaf'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=6,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('flower'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=7,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('fruit'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=8,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('seed'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=9,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('sorus'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=10,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('label'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=11,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('pistillateFlower'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=12,
                                value=1
                            )
                            session.add(moa)
                        if x := row.get('staminateFlower'):
                            moa = MultimediaObjectAnnotation(
                                multimedia_object_id=mo.id,
                                annotation_type_id=13,
                                value=1
                            )
                            session.add(moa)

                        session.commit()

                    if counter % 100 == 0:
                        print(counter, flush=True)
                else:
                    stats['no'] += 1
                    print(sn, row, flush=True)
            else:
                stats['no-sn'] += 1
                print('no-sn', row, flush=True)

    print('ok', stats, flush=True)
    return 't'

@base.route('/portals')
def portal_list():
    site_list = Organization.query.filter(Organization.is_site==True).all()
    return render_template('portal-list.html', site_list=site_list)

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

@base.route('/login', methods=['GET', 'POST'])
def login():
    site = get_current_site(request)
    if not site:
        return abort(404)

    if request.method == 'GET':
        return render_template('login.html', site=site)
    elif request.method == 'POST':
        username = request.form.get('username', '')
        passwd = request.form.get('passwd', '')

        if u := User.query.filter(User.username==username, User.organization_id==site.id).first():
            if check_password_hash(u.passwd, passwd):
                login_user(u)
                flash('已登入')
                #next_url = flask.request.args.get('next')
                # is_safe_url should check if the url is safe for redirects.
                # See http://flask.pocoo.org/snippets/62/ for an example.
                #if not is_safe_url(next):
                #    return flask.abort(400)
                return redirect(url_for('admin.index'))

        flash('帳號或密碼錯誤')

        return redirect(url_for('base.login'))

@base.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('base.login'))


@base.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(current_app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')
@base.route('/robots.txt')
def robots_txt():
    return render_template('robots.txt')


'''
#################################3



'''

@base.route('/admin/biotope_options')
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
