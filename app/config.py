import os

from dotenv import load_dotenv

load_dotenv()

class Config(object):
    TESTING = False
    DEBUG = True
    DATABASE_URI = 'postgresql+psycopg2://postgres:example@postgres:5432/naturedb'
    PORTAL_SITE = os.getenv('PORTAL_SITE')
    SECRET_KEY = 'no secret'

class ProductionConfig(Config):
    SECRET_KEY = os.getenv('SECRET_KEY')

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True

