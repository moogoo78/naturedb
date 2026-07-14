"""Google Analytics (GA4) dashboard summary.

Deliberately avoids the heavy `google-analytics-data` gRPC SDK. We mint an
OAuth2 access token from the service-account key with `google-auth`, then hit
the GA4 Data API REST endpoint with `requests` (both already dependencies).

The GA4 Data API is slow (~1s/call) and quota-limited, so the assembled result
is cached in Redis. It must never raise into the request path: any failure logs
and returns None so the admin dashboard degrades gracefully to "no GA data".
"""
import requests
from flask import current_app

from app.utils import get_cache, set_cache

CACHE_KEY = 'ga-dashboard-stats'
CACHE_EXPIRE = 3600  # 1 hour: 60 * 60

GA_SCOPE = 'https://www.googleapis.com/auth/analytics.readonly'
GA_API_TIMEOUT = 15  # seconds


def get_ga_stats():
    """Return cached GA4 summary dict, or None if disabled/unconfigured/failed."""
    if not current_app.config.get('FEATURE_GA_DASHBOARD'):
        return None

    if x := get_cache(CACHE_KEY):
        current_app.logger.debug('get_ga_stats via cache')
        return x

    stats = _fetch_ga_stats_now()
    if stats is not None:
        set_cache(CACHE_KEY, stats, CACHE_EXPIRE)
        current_app.logger.debug('get_ga_stats and save to cache')
    return stats


def _get_access_token():
    """Mint a short-lived GA read-only access token from the service account."""
    from google.oauth2 import service_account
    from google.auth.transport.requests import Request

    path = current_app.config.get('GA4_CREDENTIALS_PATH')
    if not path:
        current_app.logger.warning('get_ga_stats: GA4_CREDENTIALS_PATH not set')
        return None

    creds = service_account.Credentials.from_service_account_file(
        path, scopes=[GA_SCOPE])
    creds.refresh(Request())
    return creds.token


def _run_report(property_id, token, body):
    url = f'https://analyticsdata.googleapis.com/v1beta/properties/{property_id}:runReport'
    resp = requests.post(
        url,
        headers={'Authorization': f'Bearer {token}'},
        json=body,
        timeout=GA_API_TIMEOUT,
    )
    resp.raise_for_status()
    return resp.json()


def _rows(report):
    return report.get('rows', []) if report else []


def _fetch_ga_stats_now():
    property_id = current_app.config.get('GA4_PROPERTY_ID')
    if not property_id:
        current_app.logger.warning('get_ga_stats: GA4_PROPERTY_ID not set')
        return None

    try:
        token = _get_access_token()
        if not token:
            return None

        date_range = [{'startDate': '30daysAgo', 'endDate': 'today'}]

        totals = _run_report(property_id, token, {
            'dateRanges': date_range,
            'metrics': [
                {'name': 'activeUsers'},
                {'name': 'sessions'},
                {'name': 'screenPageViews'},
            ],
        })

        top_pages = _run_report(property_id, token, {
            'dateRanges': date_range,
            'dimensions': [{'name': 'pagePath'}],
            'metrics': [{'name': 'screenPageViews'}],
            'orderBys': [{'metric': {'metricName': 'screenPageViews'}, 'desc': True}],
            'limit': 5,
        })

        trend = _run_report(property_id, token, {
            'dateRanges': date_range,
            'dimensions': [{'name': 'date'}],
            'metrics': [{'name': 'activeUsers'}],
            'orderBys': [{'dimension': {'dimensionName': 'date'}}],
        })
    except Exception as e:
        current_app.logger.warning(f'get_ga_stats failed: {e}')
        return None

    # totals: single row, three metric values (strings) in metric order
    total_row = _rows(totals)
    metric_values = total_row[0]['metricValues'] if total_row else []
    active_users = int(metric_values[0]['value']) if len(metric_values) > 0 else 0
    sessions = int(metric_values[1]['value']) if len(metric_values) > 1 else 0
    page_views = int(metric_values[2]['value']) if len(metric_values) > 2 else 0

    pages = [
        {
            'path': r['dimensionValues'][0]['value'],
            'views': int(r['metricValues'][0]['value']),
        }
        for r in _rows(top_pages)
    ]

    # trend date comes back as 'YYYYMMDD'; reformat to 'YYYY-MM-DD' for the chart
    trend_labels = []
    trend_data = []
    for r in _rows(trend):
        d = r['dimensionValues'][0]['value']
        trend_labels.append(f'{d[0:4]}-{d[4:6]}-{d[6:8]}')
        trend_data.append(int(r['metricValues'][0]['value']))

    return {
        'active_users': active_users,
        'sessions': sessions,
        'page_views': page_views,
        'top_pages': pages,
        'trend': {'labels': trend_labels, 'data': trend_data},
    }
