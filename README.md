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
make sure data folder exist

insert default collection, organization, by hand

- person
- proj
- geo

insert assertion_type SQL

- assertion_type_option
- taxon
- entity
- other-csv
- name-comment

optional 
- img
## workflow

create db (naturedb) use adminer web ui


## migrate

```bash
  $/root/.local/bin/alembic revision --autogenerate -m 'some-comment'
  $/root/.local/bin/alembic upgrade head
```
