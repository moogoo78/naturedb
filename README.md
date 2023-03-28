# NatureDB


## Development

Create .env (copy dotenv.sample & edit)

```
$ cp dotenv.sample .env

postgres: create database naturedb;

flask:
$ flask migrate
```


## import hast21 process

1. create database naturedb
2. flask migrate
3. insert init-db.sql
4. sql (skip?):
```
SELECT setval('record_id_seq', (SELECT max(id) FROM record));
SELECT setval('organization_id_seq', (SELECT max(id) FROM organization));
SELECT setval('collection_id_seq', (SELECT max(id) FROM collection));
SELECT setval('assertion_type_id_seq', (SELECT max(id) FROM assertion_type));
SELECT setval('assertion_type_option_id_seq', (SELECT max(id) FROM assertion_type_option));
SELECT setval('annotation_type_id_seq', (SELECT max(id) FROM annotation_type));
SELECT setval('project_id_seq', (SELECT max(id) FROM project));
SELECT setval('user_id_seq', (SELECT max(id) FROM "user"));
SELECT setval('article_category_id_seq', (SELECT max(id) FROM article_category));
```
5. flask conv_hast21




## workflow

create db (naturedb) use adminer web ui


## migrate

```bash
  $/root/.local/bin/alembic revision --autogenerate -m 'some-comment'
  $/root/.local/bin/alembic upgrade head
```
