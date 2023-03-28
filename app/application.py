
import subprocess
import click
import json
#import logging
from logging.config import dictConfig

from flask import (
    g,
    Flask,
    jsonify,
    render_template,
    redirect,
    request,
    flash,
    url_for,
)
from werkzeug.security import (
    generate_password_hash,
    check_password_hash,
)
from flask_login import (
    LoginManager,
    login_user,
    logout_user,
    login_required,
)
from flask_babel import (
    Babel,
    gettext,
    ngettext,
)
from babel.support import Translations

from app.database import session
from app.models.site import User
#from scripts import load_data

# TODO: similer to flask default
'''
dictConfig({
    'version': 1,
    'formatters': {'default': {
        'format': '[%(asctime)s] %(levelname)s in %(module)s: %(message)s',
    }},
    'handlers': {'wsgi': {
        'class': 'logging.StreamHandler',
        'stream': 'ext://flask.logging.wsgi_errors_stream',
        'formatter': 'default'
    }},
    'root': {
        'level': 'DEBUG',
        'handlers': ['wsgi']
    }
})
'''
def apply_blueprints(app):
    from app.blueprints.main import main as main_bp
    from app.blueprints.page import page as page_bp
    from app.blueprints.admin import admin as admin_bp;
    from app.blueprints.api import api as api_bp;

    app.register_blueprint(main_bp)
    app.register_blueprint(page_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(api_bp, url_prefix='/api/v1')


def get_locale():
    #print(request.cookies.get('language'), flush=True)
    locale = 'zh'
    if request.path[0:3] == '/en':
        locale = 'en'
    elif request.path[0:3] == '/zh':
        locale = 'zh'
    else:
        locale = request.accept_languages.best_match(['zh', 'en'])

    return getattr(g, 'LOCALE', locale)

def get_lang_path(lang):
    #locale = get_locale()
    by = None
    if request.path[0:3] == '/en':
        by = 'prefix'
    elif request.path[0:3] == '/zh':
        by = 'prefix'
    else:
        locale = request.accept_languages.best_match(['zh', 'en'])
        by = 'accept-languages'

    if by == 'prefix':
        return f'/{lang}{request.full_path[3:]}'
    elif by == 'accept-languages':
        return f'/{lang}{request.full_path}'


def create_app():
    app = Flask(__name__)

    #app.config['BABEL_TRANSLATION_DIRECTORIES'] = 'translations' # default translations
    app.config['BABEL_DEFAULT_LOCALE'] = 'zh'

    app.secret_key = 'no secret'
    #print(app.config, flush=True)
    return app

flask_app = create_app()


apply_blueprints(flask_app)

# flask extensions
babel = Babel(flask_app, locale_selector=get_locale)
flask_app.jinja_env.globals['get_locale'] = get_locale
flask_app.jinja_env.globals['get_lang_path'] = get_lang_path
login_manager = LoginManager()
login_manager.init_app(flask_app)

@login_manager.user_loader
def load_user(id):
    return User.query.get(id)

@flask_app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template('login.html')
    elif request.method == 'POST':
        username = request.form.get('username', '')
        passwd = request.form.get('passwd', '')

        if u := User.query.filter(username==username).first():
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
        return redirect('/login')

@flask_app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))

# @flask_app.route('/set_language/<locale>', methods=['GET'])
# def set_language(locale):

#     if locale not in ('en', 'zh'):
#         locale = 'zh'

#     g.LOCALE = locale
#     request.babel_translations = Translations.load('translations', [locale])
#     print(locale, request.babel_translations)
#     print(gettext('Hello world'), locale, flush=True)
#     return render_template('foo.html')

@flask_app.route('/url_maps')
def debug_url_maps():
    rules = []
    for rule in app.url_map.iter_rules():
        rules.append([str(rule), str(rule.methods), rule.endpoint])
    return jsonify(rules)

@flask_app.teardown_appcontext
def shutdown_session(exception=None):
    # SQLAlchemy won`t close connection, will occupy pool
    session.remove()

@flask_app.cli.command('makemigrations')
@click.argument('message')
def makemigrations(message):
    cmd_list = ['alembic', 'revision', '--autogenerate', '-m', message]
    subprocess.call(cmd_list)

@flask_app.cli.command('migrate')
def migrate():
    cmd_list = ['alembic', 'upgrade', 'head']
    subprocess.call(cmd_list)

@flask_app.cli.command('makemessages')
def makemessages():
    cmd_list = ['pybabel', 'extract', '-F', 'babel.cfg', '-o', 'messages.pot', './app']
    subprocess.call(cmd_list)

    cmd_list = ['pybabel', 'update', '-l', 'zh', '-d', './app/translations', '-i', 'messages.pot']
    subprocess.call(cmd_list)

    cmd_list = ['pybabel', 'update', '-l', 'en', '-d', './app/translations', '-i', 'messages.pot']
    subprocess.call(cmd_list)

@flask_app.cli.command('compilemessages')
def compilemessages():
    cmd_list = ['pybabel', 'compile', '-d', './app/translations']
    subprocess.call(cmd_list)

    return None

@flask_app.cli.command('createuser')
@click.argument('username')
@click.argument('passwd')
@click.argument('org_id')
def createuser(username, passwd, org_id):
    hashed_password = generate_password_hash(passwd)
    user = User(username=username, passwd=hashed_password, organization_id=org_id)
    session.add(user)
    session.commit()
    print(f'create user: {username}, {hashed_password}',flush=True)

@flask_app.cli.command('conv_hast21')
def conv_hast21():
    from datetime import datetime
    from .helpers import _conv_hast21

    for key in ['person', 'geo', 'taxon', 'record', 'other-csv', 'name-comment', 'trans', 'img']:
        start = datetime.now()
        _conv_hast21(key)
        end = datetime.now()
        print ('{}: {}'.format(key, (end-start).total_seconds()), flush=True)

