from flask import (
    Response,
    current_app,
    request,
)


def allow_cors(bp):
    '''Answer cross-origin requests from config CORS_ORIGINS on blueprint `bp`.

    Credentials are allowed so a client on another subdomain can send the JWT
    cookie; that is only safe because the origin is echoed from an allow-list,
    never '*'.
    '''
    def _set_headers(resp):
        origin = request.headers.get('Origin', '')
        if origin in current_app.config.get('CORS_ORIGINS', []):
            resp.headers['Access-Control-Allow-Origin'] = origin
            resp.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
            resp.headers['Access-Control-Allow-Headers'] = 'Content-Type, X-CSRF-TOKEN'
            resp.headers['Access-Control-Allow-Credentials'] = 'true'
            resp.headers.add('Vary', 'Origin')
        return resp

    @bp.before_request
    def handle_preflight():
        if request.method == 'OPTIONS':
            return _set_headers(Response())

    bp.after_request(_set_headers)
