from datetime import datetime

from sqlalchemy import (
    create_engine,
    inspect,
    Integer,
    Column,
    String,
    DateTime,
    ForeignKey
)
from sqlalchemy.orm import scoped_session, sessionmaker, Session
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

from app.utils import get_time

#engine = create_engine('sqlite:////tmp/test.db', convert_unicode=True)
engine = create_engine('postgresql+psycopg2://postgres:example@postgres:5432/naturedb', convert_unicode=True)
session = scoped_session(sessionmaker(autocommit=False,
                                         autoflush=False,
                                         bind=engine))
db_insp = inspect(engine)
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

class TimestampMixin(object):
    created = Column(DateTime, default=get_time)
    updated = Column(DateTime, default=get_time, onupdate=get_time)


#session = Session(engine, future=True)

class ModelHistory(Base):
    '''
    via: https://stackoverflow.com/a/56351576/644070
    '''
    __tablename__ = 'model_history'

    state = None
    model_changes = {}

    #__tablename__ = 'model_history'

    id = Column(Integer, primary_key=True)
    user_id = ForeignKey('user.id', ondelete='SET NULL', nullable=True)
    tablename = Column(String(500))
    item_id = Column(String(500))
    action = Column(String(500))
    changes = Column(JSONB)
    created = Column(DateTime, default=get_time)
    remarks = Column(String(500))

    def inspect(self, model):
        self.state = inspect(model)
        # print(model, flush=True)

    def get_changes(self):
        for attr in self.state.attrs:
            hist = self.state.get_history(attr.key, True)
            print(hist, flush=True)
            if not hist.has_changes():
                continue

            old_value = hist.deleted[0] if hist.deleted else None
            new_value = hist.added[0] if hist.added else None
            #self.changes[attr.key] = [old_value, new_value]
            self.model_changes[attr.key] = f'{old_value}=>{new_value}'

        return self.model_changes

class ChangeLog(object):
    '''
    via: https://stackoverflow.com/a/56351576/644070
    '''
    state = None
    changes = {}

    def __init__(self, model):
        self.state = inspect(model)

    #def inspect(self, model):
    #    self.state = inspect(model)
    #    # print(model, flush=True)

    def get_changes(self):
        for attr in self.state.attrs:
            hist = self.state.get_history(attr.key, True)
            # print(hist, flush=True)
            if not hist.has_changes():
                continue

            old_value = hist.deleted[0] if hist.deleted else None
            new_value = hist.added[0] if hist.added else None
            #self.changes[attr.key] = [old_value, new_value]
            self.changes[attr.key] = f'{old_value}=>{new_value}'

        return self.changes
