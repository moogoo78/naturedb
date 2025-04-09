import os
import re
import json
import logging
from logging.handlers import RotatingFileHandler
#from logging.config import dictConfig

from flask import (
    g,
    Flask,
    jsonify,
    render_template,
    redirect,
    request,
    flash,
    url_for,
    abort,
)
from flask_login import (
    LoginManager,
)
from flask_babel import (
    Babel,
    gettext,
    #ngettext,
)
# from babel.support import Translations
from flask_jwt_extended import JWTManager

#from app.database import init_db
from app.database import session

from app.models.site import (
    User,
    Site,
)
from app.utils import find_date
from app.jinja_func import *

#from scripts import load_data


# dictConfig({
#     'version': 1,
#     'formatters': {'default': {
#         'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
#     }},
#     'handlers': {'wsgi': {
#         'class': 'logging.StreamHandler',
#         'stream': 'ext://flask.logging.wsgi_errors_stream',
#         'formatter': 'default'
#     }},
#     'root': {
#         'level': 'DEBUG',
#         'handlers': ['wsgi']
#     }
# })

logger = logging.getLogger("myapp")
logger.setLevel(logging.DEBUG)

console_handler = logging.StreamHandler()
console_handler.setLevel(logging.WARNING)
console_handler.setFormatter(logging.Formatter('[CONSOLE] %(levelname)s: %(message)s'))

file_handler = RotatingFileHandler('/var/log/naturedb/flask.log', maxBytes=5 * 1024 * 1024, backupCount=10)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('[%(asctime)s] %(levelname)s in %(module)s: %(message)s'))

logger.addHandler(console_handler)
logger.addHandler(file_handler)


def apply_blueprints(app):
    from app.blueprints.base import base as base_bp
    from app.blueprints.frontpage import frontpage as frontpage_bp
    from app.blueprints.admin import admin as admin_bp;
    from app.blueprints.api import api as api_bp;

    app.register_blueprint(base_bp)
    app.register_blueprint(frontpage_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api/v1')

#session = init_db(flask_app.config)

def create_app():
    #app = Flask(__name__, subdomain_matching=True, static_folder=None)
    app = Flask(__name__)
    if os.getenv('WEB_ENV') == 'dev':
        app.config.from_object('app.config.DevelopmentConfig')
    elif os.getenv('WEB_ENV') == 'prod':
        app.config.from_object('app.config.ProductionConfig')
    else:
        app.config.from_object('app.config.Config')
    #app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations' # default translations
    app.config['BABEL_DEFAULT_LOCALE'] = app.config['DEFAULT_LANG_CODE']

    # print(app.config, flush=True)
    # subdomain
    #app.config['SERVER_NAME'] = 'sh21.ml:5000'
    #app.url_map.default_subdomain = 'www'
    #app.static_folder='static'
    #app.add_url_rule('/static/<path:filename>',
    #                 endpoint='static',
    #                 subdomain='static',
    #                 view_func=app.send_static_file)

    app.url_map.strict_slashes = False
    #print(app.config, flush=True)
    return app

flask_app = create_app()

apply_blueprints(flask_app)

# flask extensions
babel = Babel(flask_app, locale_selector=get_locale)
flask_app.jinja_env.globals['get_locale'] = get_locale
flask_app.jinja_env.globals['get_lang_path'] = get_lang_path
flask_app.jinja_env.globals['str_to_date'] = str_to_date
login_manager = LoginManager()
login_manager.init_app(flask_app)
jwt = JWTManager(flask_app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(id)

@flask_app.route('/')
def cover():
    host = request.headers.get('Host', '')
    if host == os.getenv('PORTAL_HOST'):
        return render_template('cover.html')

    if site := Site.find_by_host(host):
        return redirect(url_for('frontpage.index', lang_code='zh'))

    return 'naturedb: no site' #abort(404)

@login_manager.unauthorized_handler
def unauthorized():
    # do stuff
    return redirect(url_for('admin.login') + '?next=' + request.path)

@flask_app.route('/import')
def import_data():
    import csv
    import re

    people = []
    stat = {'date': { 'good': 0, 'bad': 0}}
    with open('./data/ppi-cleaned2.csv', newline='') as csvfile:
        spamreader = csv.DictReader(csvfile)
        #next(spamreader)
        for row in spamreader:
            #print(row, flush=True)
            col_date = row.get('採集日期', '')
            res = find_date(col_date)
            if res['error'] != '':
                print(res, col_date, flush=True)
                stat['date']['bad'] += 1
            else:
                stat['date']['good'] += 1
            #common_name = row.get('物種中文名')
            col_num = row.get('採集者編號', '')
            col = row.get('採集者', '')
            collector = None
            comp = []
            if ',' in col:
                colls = col.split(',')
                collector = colls[0]
                comp = colls[1:]
            elif '、' in col:
                colls =  col.split('、')
                collector = colls[0]
                comp = colls[1:]
            else:
                collector = col

            sci_name = row.get('物種學名', '')
            locality = row.get('採集地點(縣市-地名)', '')
            idenfier = row.get('鑑定者')

            # make collection
            rec = Record(field_number=col_num, source_data=row, collection_id=2, verbatim_locality=locality, verbatim_collector=col, companion_text='|'.join(comp))
            if res['error'] == '':
                rec.collect_date = res['date']
            #print(collector, comp, flush=True)
            if collector:
                if per := Person.query.filter(Person.full_name==collector).first():
                    rec.collector = per
            session.add(rec)
            session.commit()
            id_ = Identification(record_id=rec.id, verbatim_identification=sci_name, sequence=0)
            if idenfier:
                if per := Person.query.filter(Person.full_name==idenfier).first():
                    id_.identifier_id = per.id
            session.add(id_)

            u = Unit(accession_number=row.get('標本館館號', ''), record_id=rec.id, collection_id=2)
            session.add(u)
            session.commit()

            '''
            if col := row[4]:
                if ',' in col:
                    for x in col.split(','):
                        if x not in people:
                            people.append(x)
                elif '、' in col:
                    for x in col.split('、'):
                        if x not in people:
                            people.append(x)
                else:
                    if col not in people:
                        people.append(col)

            if ider := row[8]:
                if ',' in ider:
                    for x in ider.split(','):
                        if x not in people:
                            people.append(x)
                elif '、' in ider:
                    for x in ider.split('、'):
                        if x not in people:
                            people.append(x)
                else:
                    if ider not in people:
                        people.append(ider)
            '''
    print(stat, flush=True)
    '''
    # make person
    person_map = {}
    for p in people:
        if r := Person.query.filter(Person.full_name.like(f'%{p}%')).first():
            person_map[p] = r.id
        else:
            #per = Person(full_name=p)
            #session.add(per)
            print(p, flush=True)
    #session.commit()
    print(person_map, flush=True)
    '''
    return jsonify({})

@flask_app.route('/url_maps')
def debug_url_maps():
    rules = []
    for rule in flask_app.url_map.iter_rules():
        rules.append([str(rule), str(rule.methods), rule.endpoint])
    return jsonify(rules)

@flask_app.teardown_appcontext
def shutdown_session(exception=None):
    # SQLAlchemy won`t close connection, will occupy pool
    session.remove()

with flask_app.app_context():
    # needed to make CLI commands work
    from .commands import *
