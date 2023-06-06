import os

from dotenv import load_dotenv

load_dotenv()
class Config(object):
    TESTING = False
    DEBUG = True
    DATABASE_URI = 'postgresql+psycopg2://postgres:example@postgres:5432/naturedb'
    PORTAL_SITE = os.getenv('PORTAL_SITE')

class ProductionConfig(Config):
    pass

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True

