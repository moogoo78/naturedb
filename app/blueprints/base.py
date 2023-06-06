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
from flask_login import (
    login_required,
    login_user,
    logout_user,
)
from werkzeug.security import (
    check_password_hash,
)
from app.models.site import(
    Organization,
    User,
)
from app.helpers import (
    get_current_site,
)
from app.utils import (
    get_domain,
)


base = Blueprint('base', __name__)

@base.route('/portals')
def portal_list():
    site_list = Organization.query.filter(Organization.is_site==True).all()
    return render_template('portal-list.html', site_list=site_list)

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
