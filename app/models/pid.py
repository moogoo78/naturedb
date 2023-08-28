from sqlalchemy import (
    Column,
    Integer,
    Numeric,
    String,
    Text,
    DateTime,
    Date,
    Boolean,
    ForeignKey,
    Table,
    desc,
    select,
)

from app.database import (
    Base,
    session,
    TimestampMixin,
)

class Ark(Base, TimestampMixin):
    __tablename__ = 'pid_ark'

    identifier = Column(String(100), primary_key=True, autoincrement=False)
    naan = Column(Integer, ForeignKey('pid_ark_naan.naan'))
    who = Column(String(500))
    what = Column(String(500))
    when = Column(String(500))


class ArkNaan(Base, TimestampMixin):
    __tablename__ = 'pid_ark_naan'

    naan = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(500))
    description = Column(Text)
    url = Column(String(1000))


class ArkShoulder(Base, TimestampMixin):
    __tablename__ = 'pid_ark_shoulder'

    shoulder = Column(String(50), primary_key=True, autoincrement=False)
    naan = Column(Integer, ForeignKey('pid_ark_naan.naan'))
    name = Column(String(500))
    description = Column(Text)
