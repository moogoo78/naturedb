import subprocess
import click
import importlib
import json
import configparser

from werkzeug.security import (
    generate_password_hash,
 )

from app.application import flask_app
from app.database import session

from app.models.site import (
    User,
)

@flask_app.cli.command('createuser')
@click.argument('username')
@click.argument('passwd')
@click.argument('site_id')
def createuser(username, passwd, site_id):
    hashed_password = generate_password_hash(passwd)
    user = User(username=username, passwd=hashed_password, site_id=site_id)
    session.add(user)
    session.commit()
    print(f'create user: {username}, {hashed_password}',flush=True)


@flask_app.cli.command('loaddata')
@click.argument('json_file')
def loaddata(json_file):
    #from app.models.collection import Person
    json_data = {}
    with open(json_file) as jfile:
        json_data = json.loads(jfile.read())

    model = json_data['model']
    pkg = importlib.import_module(f'app.models.{model}')
    cls = getattr(pkg, json_data['class'])

    def get_map_instance(s):
        map_field, map_value = s.split('=')
        cls_name, attr = map_field.split('.')
        cls2 = getattr(pkg, cls_name)
        if item := cls2.query.filter(getattr(cls2, attr)==map_value).first():
            return item

        return None


    def check_exist(filters, cls, item):
        for qk, qv in filters.items():
            if qv == 'eq':
                query = cls.query.filter(getattr(cls, qk)==item['fields'][qk])
            if exist := query.first():
                return True

        return False


    for i in json_data['rows']:
        pkg_rel = importlib.import_module(f'app.models.{model}')
        instance = cls()
        check_exist_filters = json_data.get('check_exist', None)

        if check_exist_filters is not None and check_exist(check_exist_filters, cls, i):
            continue
        else:
            for key, val in i['fields'].items():

                if isinstance(val, str) and len(val) > 5 and val[0:6] == '__map_':
                    if item := get_map_instance(val[6:-2]):
                        setattr(instance, key, item)
                else:
                    setattr(instance, key, val)

        session.add(instance)

        if rel_list := i.get('relations'):
            session.commit()
            pk = instance.id
            for rel in rel_list:
                rel_cls = getattr(pkg, rel['class'])
                rel_inst = rel_cls()
                for rel_key, rel_val in rel['fields'].items():
                    #print(rel['class'], rel_key, rel_val, flush=True)
                    if rel_val == '__pk__':
                        setattr(rel_inst, rel_key, pk)
                    elif isinstance(rel_val, str) and len(rel_val) > 5 and rel_val[0:6] == '__map_':
                        if rel_item := get_map_instance(rel_val[6:-2]):
                            setattr(rel_inst, rel_key, rel_item)
                    else:
                        setattr(rel_inst, rel_key, rel_val)

                session.add(rel_inst)

                if rel2_list := rel.get('relations'):
                    for rel2 in rel2_list:
                        session.commit()
                        pk2 = rel_inst.id
                        rel2_cls = getattr(pkg, rel2['class'])
                        rel2_inst = rel2_cls()

                        for rel2_key, rel2_val in rel2['fields'].items():
                            #print(rel2_key, rel2_val, flush=True)
                            if rel2_val == '__pk2__':
                                setattr(rel2_inst, rel2_key, pk2)
                            else:
                                setattr(rel2_inst, rel2_key, rel2_val)

                        session.add(rel2_inst)

    session.commit()

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

@flask_app.cli.command('import')
@click.argument('csv_file')
@click.argument('collection_id')
@click.argument('record_group_id')
def import_record(csv_file, collection_id, record_group_id):
    # NOQA: record_group_id
    # TODO: auto add record_group
    ## TODO phase -> raw
    import csv
    from app.helpers_data import import_raw

    with open(csv_file, newline='') as csvfile:
        spamreader = csv.DictReader(csvfile)
        counter = 0
        for row in spamreader:
            #TODO: trunc each row
            import_raw(row, int(collection_id), record_group_id)
