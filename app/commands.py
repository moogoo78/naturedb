import subprocess
import click
import importlib
import json

from app.application import flask_app



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

# @flask_app.cli.command('conv_hast21')
# def conv_hast21():
#     from datetime import datetime
#     from .helpers import _conv_hast21

#     for key in ['person', 'geo', 'taxon', 'record', 'other-csv', 'name-comment', 'trans', 'img']:
#         start = datetime.now()
#         _conv_hast21(key)
#         end = datetime.now()
#         print ('{}: {}'.format(key, (end-start).total_seconds()), flush=True)


@flask_app.cli.command('loaddata')
@click.argument('table')
def loaddata(table):
    '''
    mod = importlib.import_module('app.models')
    #print(dir(mod), flush=True)
    for m in dir(mod) :
        if str(m)[:2] != '__':
            model_part = getattr(mod, m)
            for schema in dir(model_part):
                if str(schema)[:2] != '__':
                    #print('sch', schema.__tablename__, flush=True)
                    cls = getattr(model_part, schema)
                    if hasattr(cls, '__tablename__'):
                        print(schema, flush=True)
    '''
    #from app.models.collocetion.Record
    pass


@flask_app.cli.command('dumpdata')
@click.argument('table')
def dumpdata(table):
    print('dump', table, flush=True)
    from app.models.collection import Record, Identification, Unit, Person

    data = {'table': table, rows: []}
    #with open(f'{table}.json', 'w') as jsonfile:
    #    jsonfile.w

    #rows = Record.query.limit(10).all()
    #for r in rows:
    #    print (r, flush=True)


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
