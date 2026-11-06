"""TBIA partner provider API v2 (/tbia/v2/occurrence, /tbia/v2/dataset).

Pure helpers are tested in isolation; endpoint tests run against the dev DB
with the HAST site (Host header resolves by site name in dev).
"""
from datetime import datetime

import pytest

from app.blueprints.tbia_api import (
    TbiaError,
    parse_modified,
    fmt_datetime,
    fmt_rank,
    fmt_type_status,
    split_taxon_name,
    nullable,
)

HAST = {'Host': 'hast.localhost'}

OCCURRENCE_MANDATORY = (
    'occurrenceID', 'modified', 'selfProduced', 'license',
    'datasetName', 'datasetID', 'scientificName', 'taxonRank',
)


class TestParseModified:
    def test_single_day_covers_whole_day(self):
        assert parse_modified('20240101') == (datetime(2024, 1, 1), datetime(2024, 1, 2))

    def test_range_is_inclusive(self):
        assert parse_modified('20240101,20241231') == (datetime(2024, 1, 1), datetime(2025, 1, 1))

    def test_empty_is_no_filter(self):
        assert parse_modified(None) is None
        assert parse_modified('') is None

    @pytest.mark.parametrize('bad', ['2024', '2024-01-01', '20241301', '20240102,20240101', 'a,b,c'])
    def test_invalid(self, bad):
        with pytest.raises(TbiaError) as e:
            parse_modified(bad)
        assert e.value.code == 400


class TestFormatting:
    def test_datetime(self):
        assert fmt_datetime(datetime(2024, 1, 5, 10, 30, 0)) == '20240105 103000'
        assert fmt_datetime(None) is None

    def test_rank_vocab(self):
        assert fmt_rank('species') == 'Species'
        assert fmt_rank('subspecies') == 'Subspecies'
        assert fmt_rank(None) is None

    def test_type_status_upper(self):
        assert fmt_type_status('holotype') == 'HOLOTYPE'
        assert fmt_type_status('isotype|paratype') == 'ISOTYPE|PARATYPE'
        assert fmt_type_status('') is None

    def test_nullable_never_empty_string(self):
        assert nullable('') is None
        assert nullable('  ') is None
        assert nullable(' x ') == 'x'
        assert nullable(0) == 0

    def test_split_taxon_name_taicol(self):
        assert split_taxon_name('Passer montanus', 'Passer montanus (Linnaeus, 1758)',
                                '(Linnaeus, 1758)', 'species') == ('Passer montanus', '(Linnaeus, 1758)')

    def test_split_taxon_name_legacy_inline_author(self):
        assert split_taxon_name(None, 'Acer mono var. glabrum (H. Lév.) H. Hara', None, 'variety') == \
            ('Acer mono var. glabrum', '(H. Lév.) H. Hara')

    def test_split_taxon_name_higher_rank(self):
        assert split_taxon_name(None, 'Ypsilandra', None, 'genus') == ('Ypsilandra', None)


class TestOccurrenceEndpoint:
    def test_unknown_site_is_404_envelope(self, client):
        r = client.get('/tbia/v2/occurrence', headers={'Host': 'nosuchsite.localhost'})
        assert r.status_code == 404
        assert r.get_json()['status']['code'] == 404

    def test_envelope_and_content_type(self, client):
        r = client.get('/tbia/v2/occurrence?limit=2', headers=HAST)
        assert r.status_code == 200
        assert r.headers['Content-Type'] == 'application/json; charset=utf-8'
        body = r.get_json()
        assert body['status'] == {'code': 200, 'message': 'Success'}
        assert body['meta']['limit'] == 2
        assert set(body['links']) == {'self', 'next'}
        assert len(body['data']) <= 2

    def test_mandatory_fields_present_and_typed(self, client):
        body = client.get('/tbia/v2/occurrence?limit=20', headers=HAST).get_json()
        for row in body['data']:
            for key in OCCURRENCE_MANDATORY:
                assert key in row
            assert isinstance(row['occurrenceID'], str)
            assert isinstance(row['selfProduced'], bool)
            assert len(row['modified']) == len('YYYYMMDD HHMMSS')
            # missing values are null, never ""
            assert '' not in row.values()

    def test_no_match_returns_200_empty(self, client):
        r = client.get('/tbia/v2/occurrence?occurrenceID=not-a-unit', headers=HAST)
        body = r.get_json()
        assert r.status_code == 200
        assert body['data'] == []
        assert body['meta']['total'] == 0
        assert body['links']['next'] is None

    def test_cursor_pages_do_not_overlap(self, client):
        first = client.get('/tbia/v2/occurrence?limit=3', headers=HAST).get_json()
        if not first['links']['next']:
            pytest.skip('not enough data for a second page')
        nxt = first['links']['next'].split('/tbia/v2', 1)[1]
        second = client.get(f'/tbia/v2{nxt}', headers=HAST).get_json()
        ids1 = [int(x['occurrenceID']) for x in first['data']]
        ids2 = [int(x['occurrenceID']) for x in second['data']]
        assert ids1 == sorted(ids1)
        assert min(ids2) > max(ids1)

    def test_next_link_honours_forwarded_https(self, client):
        body = client.get('/tbia/v2/occurrence?limit=1',
                          headers={**HAST, 'X-Forwarded-Proto': 'https'}).get_json()
        if body['links']['next']:
            assert body['links']['next'].startswith('https://')

    @pytest.mark.parametrize('qs', ['limit=0', 'limit=1001', 'limit=x', 'modified=2024',
                                    'offset=0&cursor=1'])
    def test_bad_params_are_400(self, client, qs):
        r = client.get(f'/tbia/v2/occurrence?{qs}', headers=HAST)
        assert r.status_code == 400
        assert r.get_json()['status']['code'] == 400


class TestDatasetEndpoint:
    def test_lists_configured_datasets(self, client):
        r = client.get('/tbia/v2/dataset', headers=HAST)
        body = r.get_json()
        assert r.status_code == 200
        assert body['meta']['total'] == len(body['data'])
        for ds in body['data']:
            assert ds['datasetID'] and ds['datasetName']

    def test_filter_by_dataset_id_no_match(self, client):
        body = client.get('/tbia/v2/dataset?datasetID=999999', headers=HAST).get_json()
        assert body['data'] == []
        assert body['meta']['total'] == 0
