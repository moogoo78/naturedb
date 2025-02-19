from datetime import datetime
from decimal import Decimal
from flask import (
    current_app
)
from sqlalchemy import (
    create_engine,
    inspect,
    Integer,
    Column,
    String,
    DateTime,
    Date,
    ForeignKey,
    Numeric,
    Boolean,
)
from sqlalchemy.orm import (
    scoped_session,
    sessionmaker,
    Session,
    relationship,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.postgresql import JSONB

from app.utils import get_time
#session = None
#db_insp = None


#session = Session(engine, future=True)

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

#def init_db(config):
    #print(config, flush=True)
#engine = create_engine(config['DATABASE_URI'])
engine = create_engine('postgresql+psycopg2://postgres:example@postgres:5432/naturedb')
session = scoped_session(sessionmaker(autocommit=False,
                                      autoflush=False,
                                      bind=engine))
db_insp = inspect(engine)

Base.query = session.query_property()

#return session


class TimestampMixin(object):
    created = Column(DateTime, default=get_time)
    updated = Column(DateTime, default=get_time, onupdate=get_time)

    def get_modified_display(self):
        s = ''
        if self.created:
            s = self.created.strftime('%Y-%m-%d')
        if self.updated:
            s = s + '/' + self.updated.strftime('%Y-%m-%d')
        return s


class UpdateMixin:

    def _diff(self, key, pv, value):
        field_type = None
        # find field type
        for name, col in self.__table__.columns.items():
            if key == name:
                field_type = col.type
                break

        if isinstance(field_type, DateTime) or isinstance(field_type, Date):
            pv_date = pv.strftime('%Y-%m-%d') if pv else None
            v_date = value or None
            if pv_date != v_date:
                return value or None
        elif isinstance(field_type, Numeric):
            pv_decimal = Decimal(pv) if pv else None
            if (pv_decimal and value) and (pv_decimal != value):
                return Decimal(value)
        elif isinstance(field_type, Integer):
            v_int = int(value) if value else None
            if pv != v_int:
                return value
        elif isinstance(field_type, Boolean):
            bool_v = True if value else False
            if pv != bool_v:
                return bool_v
        else:
            if pv != value: # str
                return value or ''

        return '__NA__'

    def update_from_dict(self, data):
        changes = {}
        for k, v in data.items():
            if hasattr(self, k):
                sanity_value = self._diff(k, getattr(self, k), v)
                if sanity_value != '__NA__':
                    setattr(self, k, sanity_value)
                    changes[k] = sanity_value

        return changes

    @classmethod
    def create_from_dict(cls, data):
        obj = cls()
        changes = obj.update_from_dict(data)
        return obj, changes


class ModelHistory(Base):
    '''
    via: https://stackoverflow.com/a/56351576/644070
    '''
    __tablename__ = 'model_history'

    state = None
    model_changes = {}

    __tablename__ = 'model_history'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('user.id', ondelete='SET NULL'), nullable=True)
    tablename = Column(String(500))
    item_id = Column(String(500))
    action = Column(String(500))
    changes = Column(JSONB)
    created = Column(DateTime, default=get_time)
    remarks = Column(String(500))

    user = relationship('User')
