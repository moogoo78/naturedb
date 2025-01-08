from datetime import datetime

from sqlalchemy import (
    create_engine,
    inspect,
    Integer,
    Column,
    String,
    DateTime,
    ForeignKey,
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


#via: https://stackoverflow.com/a/44543183/644070
class UpdateMixin:
    """
    Add a simple update() method to instances that accepts
    a dictionary of updates.
    """
    def update(self, values):

        def _find_column_type(key):
            for name, col in self.__table__.columns.items():
                if key == name:
                    return col.type

        for k, v in values.items():
            col_type = _find_column_type(k)
            pv = getattr(self, k)
            if isinstance(col_type, DateTime):
                pv_date = None
                if pv:
                    pv_date = pv.strftime('%Y-%m-%d')
                if pv_date != str(v):
                    setattr(self, k, v)
            else:
                if pv != v:
                    #print(pv, v, type(pv), type(v), pv==v, type(col_type))
                    setattr(self, k, v)

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
