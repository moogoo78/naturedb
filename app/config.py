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
    SCRIBE_HOSTS = ('scribe.naturedb.org', 'scribe.sh21.ml')

    _scribe_origins = [f'https://{h}' for h in SCRIBE_HOSTS]
    if PORTAL_HOST:
        _scribe_subdomain = 'scribe.' + PORTAL_HOST.removeprefix('www.')
        _scribe_origins.append(f'http://{_scribe_subdomain}')
    CORS_ORIGINS = _scribe_origins

    SCRIBE_COLLECTION_LABELS = {
        1: 'HAST:vascular',
        2: 'HAST:alga',
        3: 'HAST:fungi',
        4: 'HAST:lichen',
        5: 'PPI',
        6: 'BISH:sample_material',
        7: 'BISH:barcode',
        8: 'ASIZ:fossil',
    }
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

    # AI label extractor (see openspec/changes/ai-label-extractor)
    FEATURE_AI_LABEL = os.getenv('FEATURE_AI_LABEL', 'false').lower() in ('true', '1', 'yes')
    ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY')
    AI_LABEL_DEFAULT_BACKEND = os.getenv('AI_LABEL_DEFAULT_BACKEND', 'remote')  # 'api' | 'remote'
    AI_LABEL_REMOTE_SOCKET = os.getenv('AI_LABEL_REMOTE_SOCKET', '/tmp/naturedb-ai-label.sock')
    AI_LABEL_REMOTE_TIMEOUT = int(os.getenv('AI_LABEL_REMOTE_TIMEOUT', '60'))
    AI_LABEL_RATE_PER_HOUR = int(os.getenv('AI_LABEL_RATE_PER_HOUR', '60'))

class ProductionConfig(Config):
    SECRET_KEY = os.getenv('SECRET_KEY')
    JWT_COOKIE_SECURE = True
    JWT_SECRET_KEY = SECRET_KEY

class DevelopmentConfig(Config):
    DEBUG = True

class TestingConfig(Config):
    TESTING = True

