
import subprocess
import click
import json
#import logging
from logging.config import dictConfig

from flask import (
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

from app.database import session
from app.models.site import User
#from scripts import load_data

ALEMBIC_BIN_PATH = '/root/.local/bin/alembic'


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


def create_app():
    app = Flask(__name__)

    apply_blueprints(app)

    #print(app.config, flush=True)
    app.secret_key = 'no secret'

    # flask extensions
    login_manager = LoginManager()
    login_manager.init_app(app)

    @login_manager.user_loader
    def load_user(id):
        return User.query.get(id)

    @app.route('/login', methods=['GET', 'POST'])
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

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(url_for('main.index'))

    @app.route('/url_maps')
    def debug_url_maps():
        rules = []
        for rule in app.url_map.iter_rules():
            rules.append([str(rule), str(rule.methods), rule.endpoint])
        return jsonify(rules)

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        # SQLAlchemy won`t close connection, will occupy pool
        session.remove()

    @app.cli.command('makemigrations')
    @click.argument('message')
    def makemigrations(message):
        cmd_list = [ALEMBIC_BIN_PATH, 'revision', '--autogenerate', '-m', message]
        subprocess.call(cmd_list)

        return None

    @app.cli.command('migrate')
    def migrate():
        cmd_list = [ALEMBIC_BIN_PATH, 'upgrade', 'head']
        subprocess.call(cmd_list)

    @app.cli.command('createuser')
    @click.argument('username')
    @click.argument('passwd')
    @click.argument('org_id')
    def createuser(username, passwd, org_id):
        hashed_password = generate_password_hash(passwd)
        user = User(username=username, passwd=hashed_password, organization_id=org_id)
        session.add(user)
        session.commit()
        print(f'create user: {username}, {hashed_password}',flush=True)

    # @app.cli.command('load_data')
    # def func_load_data():
    #     import load_data_conf
    #     load_data.import_csv(load_data_conf.conf)
    #     return None
    return app
