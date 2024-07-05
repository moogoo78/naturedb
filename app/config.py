import os

from dotenv import load_dotenv

load_dotenv()

class Config(object):
    LANG_CODES = ('zh', 'en')
    DEFAULT_LANG_CODE = 'zh'
    TESTING = False
    DEBUG = True
    DATABASE_URI = 'postgresql+psycopg2://postgres:example@postgres:5432/naturedb'
    PORTAL_SITE = os.getenv('PORTAL_SITE')
    SECRET_KEY = 'no secret'

    WEB_ENV = os.getenv('WEB_ENV')

    JWT_COOKIE_SECURE = False
    JWT_TOKEN_LOCATION = ['headers', 'query_string']
    JWT_SECRET_KEY = SECRET_KEY

class ProductionConfig(Config):
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_COOKIE_SECURE = True
    JWT_SECRET_KEY = SECRET_KEY

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True

