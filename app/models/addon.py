from sqlalchemy import (
    Column,
    Integer,
    SmallInteger,
    String,
    Text,
    DateTime,
    Boolean,
    ForeignKey,
    Table,
    desc,
)

from app.database import Base

class GeoName(Base):
    __tablename__ = 'addon_geoname'
    geonameid = Column(Integer, primary_key=True, autoincrement=False)
    name = Column(String(500))
    asciiname = Column(String(500))
    alternatenames = Column(Text)
    latitude = Column(String(500))
    longitude = Column(String(500))
    feature_class = Column(String(500))
    feature_code = Column(String(500))
    country_code = Column(String(2))
    cc2 = Column(String(500))
    admin1_code = Column(String(500))
    admin2_code = Column(String(500))
    admin3_code = Column(String(500))
    admin4_code = Column(String(500))
    population = Column(Integer)
    elevation = Column(Integer)
    dem = Column(String(500))
    timezone = Column(String(500))
    modification_date = Column(String(500))
