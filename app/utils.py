import re
import math
import random
from datetime import datetime, timedelta
import time
import pickle
import hashlib
import json
import base64

import redis

my_redis = redis.Redis(host='redis', port=6379, db=0) # TODO move to config

def find_date(s):
    '''
    error example:
    2019.10.12
    2019.07.06
    2018.2.2
    2017/12/21
    12/19/1983
    06/11/1984
    2021-03-21T16:00:00Z
    November 11.2016
    July 10.2020
    10月6日
    '''
    s = s.strip()
    patterns = [
        '%Y.%m.%d',
        '%Y-%m-%d',
        '%Y/%m/%d',
        '%Y-%m-%dT%H:%M:%SZ',
        '%m/%d/%Y',
        '%B %d.%Y',
    ]
    result = {
        'pattern': '',
        'date': '',
        'error': '',
    }
    for i in patterns:
        try:
            result['date'] = datetime.strptime(s, i).strftime('%Y-%m-%d')
            result['pattern'] = i
            result['error'] = ''
            break
        except ValueError as msg:
            #print(msg, flush=True)
            result['error'] = msg

    # regex
    # regex_list = [
    #     [r'([0-9]{4})\.([0-9]{1,2})\.([0-9]{1,2})', 'ymd'],
    #     [r'([0-9]{4})\-([0-9]{1,2})\-([0-9]{1,2})', 'ymd'],
    #     [r'([0-9]{4})/([0-9]{1,2})/([0-9]{1,2})', 'ymd'],
    #     [r'([0-9]{1,2})/([0-9]{1,2})/([0-9]{4})', 'mdy']
    # ]
    # result = {
    #     'y': '',
    #     'm': '',
    #     'd': '',
    #     'is_found': False,
    #     'regex': '',
    # }
    # for r in regex_list:
    #     if not result['is_found']:
    #         if m := re.search(r[0], s):
    #             result[r[1][0]] = m.group(1)
    #             result[r[1][1]] = m.group(2)
    #             result[r[1][2]] = m.group(3)
    #             result['is_found'] = True
    #             result['regex'] = r
    #             break

    return result

# DEPRECATE
def get_domain(req):
    if req:
        return req.headers['Host']
    return None

def delete_cache(key):
    my_redis.delete(key)

def get_cache(key):
    if x := my_redis.get(key):
        return pickle.loads(x)
    return None

def set_cache(key, value, expire=0):
    my_redis.set(key, pickle.dumps(value))
    if expire:
        my_redis.expire(key, expire)

def get_time(**args):
    if args:
        return datetime.utcnow() + timedelta(**args)
    else:
        return datetime.utcnow() + timedelta(hours=+8)


# via: https://en.proft.me/2015/09/20/converting-latitude-and-longitude-decimal-values-p/
def dd2dms(deg):
    '''Decimal-Degrees (DD) to Degrees-Minutes-Seconds (DMS)'''
    deg = float(deg) # 原本 decimal 欄位改成 char, 失去 decimal type
    d = int(deg)
    md = abs(deg - d) * 60
    m = int(md)
    sd = (md - m) * 60
    return [d, m, sd]

# HALT
def update_or_create(session, obj, params):
    data = {}
    # original value
    for c in obj.EDITABLE_COLUMNS:
        k = c[0]
        v = getattr(obj, k)
        if k in params:
            v = params[k]
        setattr(obj, k, v)
    session.commit()

    print('update_or_create', params, data, flush=True)

    return obj

def gen_time_hash():
    current_time = str(time.time() * 1000)
    random_number = str(random.randint(1000, 9999))
    hash_input = current_time + random_number
    hash_result = hashlib.sha256(hash_input.encode()).hexdigest()
    code = hash_result[:10]
    return code

    # def to_base62(num):
    #     chars = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
    #     base62 = ""
    #     while num > 0:
    #         num, i = divmod(num, 62)
    #         base62 = chars[i] + base62
    #     return base62

    # s1 = to_base62(int(time.time()*1000))
    # s2 = to_base62(random.randint(1000, 9999))
    # return f'{s1}-{s2}'

def decode_key(encoded):
    ''' via: https://stackoverflow.com/a/74584151/644070
    encode
    service_key = json.dumps(service_key)
    encoded_service_key = base64.b64encode(service_key.encode('utf-8'))
    '''
    return json.loads(base64.b64decode(encoded).decode('utf-8'))

def extract_integer(value):
    match = re.search(r'\d+', value)
    if match:
        return int(match.group())
    return None

def normalize_search_term(term: str) -> str:
    return re.sub(r'(?<=\w)\s*x\s*(?=\w)', '×', term, flags=re.IGNORECASE)
