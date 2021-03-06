from sqlalchemy import (
    create_engine,
    inspect
)
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base

#engine = create_engine('sqlite:////tmp/test.db', convert_unicode=True)
engine = create_engine('postgresql+psycopg2://postgres:example@postgres:5432/naturedb', convert_unicode=True)
session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))

# class MyBase(object):
#     def save(self, data={}):
#         if len(data):
#             print('save1')
#             inst = inspect(self)
#             field_names = [x.key for x in inst.mapper.column_attrs]
#             print(dir(inst), dir(self))
#             for k, v in data.items():
#                 if k in field_names and v != self[k]:
#                     setattr(obj, k, v)
#                     pass
#             #session.commit()

#Base = declarative_base(cls=MyBase)
Base = declarative_base()
Base.query = session.query_property()

#session = Session(engine, future=True)
