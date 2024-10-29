from datetime import datetime
from flask import (
    request,
    g,
)

def str_to_date(string, format='%Y-%m-%d'):
    return datetime.strptime(string, format)

def get_locale():
    #print(request.cookies.get('language'), flush=True)
    locale = 'zh'
    if request.path[0:3] == '/en':
        locale = 'en'
    #elif request.path[0:3] == '/zh':
    #    locale = 'zh'
    #else:
    # locale = request.accept_languages.best_match(['zh', 'en'])

    #print('get_locale', locale, flush=True)
    return getattr(g, 'LOCALE', locale)

def get_lang_path(lang):
    #locale = get_locale()
    by = None
    #if m = re.match(r'/(en|zh)/', request.path):
    #    print(m.group(''))
    if request.path[0:3] == '/en':
        by = 'prefix'
    elif request.path[0:3] == '/zh':
        by = 'prefix'
    else:
        locale = request.accept_languages.best_match(['zh', 'en'])
        by = 'accept-languages'
        #print('get_lang_path', locale, flush=True)
    #print(by, lang, flush=True)
    if by == 'prefix':
        return f'/{lang}{request.path[3:]}'
    elif by == 'accept-languages':
        return f'/{lang}{request.path}'
