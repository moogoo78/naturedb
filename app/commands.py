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
    Site,
)
from app.helpers_data import (
    export_specimens
)

@flask_app.cli.command('createuser')
@click.argument('username')
@click.argument('passwd')
@click.argument('site_id')
@click.argument('role')
def createuser(username, passwd, site_id, role):
    hashed_password = generate_password_hash(passwd)
    user = User(username=username, passwd=hashed_password, site_id=site_id, role=role)
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

@flask_app.cli.command('importdata')
@click.argument('csv_file')
@click.argument('collection_id')
@click.argument('record_group_id_or_name')
def import_data(csv_file, collection_id, record_group_id_or_name=None):
    # NOQA: record_group_id
    # TODO: auto add record_group
    ## TODO phase -> raw
    import csv
    from app.database import session
    from app.helpers_data import import_raw
    from app.models.collection import RecordGroup

    record_group_id = None
    if record_group_id_or_name.isdigit():
        record_group_id = int(record_group_id_or_name)
    else:
        record_group = RecordGroup(name=record_group_id_or_name, category='batch-import', collection_id=collection_id)
        session.add(record_group)
        session.commit()
        record_group_id = record_group.id

    with open(csv_file, newline='') as csvfile:
        spamreader = csv.DictReader(csvfile)
        counter = 0
        for row in spamreader:
            #TODO: trunc each row
            import_raw(row, int(collection_id), record_group_id)



@flask_app.cli.command('exportdata')
@click.argument('site_name')
@click.argument('collection_ids')
@click.argument('fmt')
def export_data(site_name, collection_ids, fmt):
    if site := Site.query.filter(Site.name==site_name.lower()).scalar():
        export_specimens(site, collection_ids, fmt)


@flask_app.cli.command('inspect')
@click.argument('record_key')
def inspect_record(record_key):
    """Dump record and all relations as JSON for debugging.

    RECORD_KEY can be a numeric record ID or "ORG_CODE:ACCESSION_NUMBER"
    (e.g. "HAST:123456").
    """
    import json
    from datetime import date, datetime
    from decimal import Decimal

    from app.models.collection import (
        Record, Unit, Collection, RecordGeologicalContext,
    )
    from app.models.site import Organization

    def _ser(obj):
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return str(obj)

    record = None
    if record_key.isdigit():
        record = Record.query.get(int(record_key))
    elif ':' in record_key:
        org_code, accession = record_key.split(':', 1)
        unit = (
            Unit.query
            .join(Collection, Collection.id == Unit.collection_id)
            .join(Organization, Organization.id == Collection.organization_id)
            .filter(
                Organization.code == org_code.upper(),
                Unit.accession_number == accession,
            )
            .first()
        )
        if unit:
            record = unit.record
        else:
            click.echo(f'No unit found for {record_key}')
            return
    else:
        click.echo(f'Invalid key: {record_key} (use record_id or ORG_CODE:ACCESSION_NUMBER)')
        return

    if not record:
        click.echo(f'Record {record_key} not found')
        return

    # --- record ---
    editable = Record.get_editable_fields()
    rec = {'id': record.id, 'collection_id': record.collection_id}
    for f in editable:
        rec[f] = getattr(record, f, None)
    rec['proxy_taxon_scientific_name'] = record.proxy_taxon_scientific_name
    rec['proxy_taxon_id'] = record.proxy_taxon_id
    rec['source_data'] = record.source_data
    rec['created'] = record.created
    rec['updated'] = record.updated

    # --- collector ---
    collector = None
    if record.collector:
        collector = {
            'id': record.collector.id,
            'name': record.collector.display_name,
        }

    # --- units (all columns) ---
    unit_columns = [c.key for c in Unit.__table__.columns]
    units = []
    for u in record.units:
        ud = {c: getattr(u, c) for c in unit_columns}
        ud['pids'] = [
            {'id': p.id, 'key': p.key, 'pid_type': p.pid_type}
            for p in u.pids
        ]
        units.append(ud)

    # --- identifications ---
    ids = []
    for ident in record.identifications.order_by('sequence'):
        taxon_name = None
        if ident.taxon:
            taxon_name = ident.taxon.display_name
        ids.append({
            'id': ident.id,
            'taxon_id': ident.taxon_id,
            'taxon_name': taxon_name,
            'identifier': ident.verbatim_identifier,
            'identifier_id': ident.identifier_id,
            'date': ident.date,
            'date_text': ident.date_text,
            'sequence': ident.sequence,
            'verification_level': ident.verification_level,
        })

    # --- record groups ---
    groups = [
        {'id': g.id, 'name': g.name, 'category': g.category}
        for g in record.record_groups
    ]

    # --- named areas ---
    named_areas = {}
    for m in record.named_area_maps:
        ac = m.named_area.area_class.name if m.named_area.area_class else str(m.named_area.area_class_id)
        named_areas[ac] = {
            'id': m.named_area.id,
            'name': m.named_area.name,
            'name_en': m.named_area.name_en if hasattr(m.named_area, 'name_en') else None,
        }

    # --- geological context ---
    geo = None
    if record.geological_context:
        geo = {}
        for f in RecordGeologicalContext.GEO_FIELDS:
            geo[f] = getattr(record.geological_context, f, None)

    output = {
        'record': rec,
        'collector': collector,
        'units': units,
        'identifications': ids,
        'record_groups': groups,
        'named_areas': named_areas,
        'geological_context': geo,
    }

    click.echo(json.dumps(output, indent=2, default=_ser, ensure_ascii=False))

