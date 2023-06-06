import math
from datetime import datetime, timedelta
import pickle

import redis

my_redis = redis.Redis(host='redis', port=6379, db=0) # TODO move to config


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
