import os

from dotenv import load_dotenv

load_dotenv()

class Config(object):
    LANG_CODES = ('zh', 'en')
    DEFAULT_LANG_CODE = 'zh'
    TESTING = False
    DEBUG = True
    DATABASE_URI = 'postgresql+psycopg2://postgres:example@postgres:5432/naturedb'
    UPLOAD_FOLDER = '/uploads'
    MAX_CONTENT_LENGTH = 16 * 1000 * 1000 # 16MB, 1024*1024?

    PORTAL_HOST = os.getenv('PORTAL_HOST')
    SECRET_KEY = 'no secret'
    SERVICE_KEY = os.getenv('SERVICE_KEY')

    WEB_ENV = os.getenv('WEB_ENV')
    #PREFERRED_URL_SCHEME = 'https'
    FRONTEND_SEARCH_VERSION = os.getenv('FRONTEND_SEARCH_VERSION')
    BACKEND_SEARCH_VERSION = os.getenv('BACKEND_SEARCH_VERSION')

    JWT_COOKIE_SECURE = False
    JWT_TOKEN_LOCATION = ['cookies']
    JWT_SECRET_KEY = SECRET_KEY
    JWT_ACCESS_TOKEN_EXPIRES = 1209600 # 2 weeks: 14 * 24 * 60 * 60

class ProductionConfig(Config):
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_COOKIE_SECURE = True
    JWT_SECRET_KEY = SECRET_KEY

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True

