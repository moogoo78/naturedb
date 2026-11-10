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
    dataset_id_for,
    build_dataset_map,
    name_according_to_for,
)
from app.helpers_image import media_url_rewriter

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


class TestNameAccordingTo:
    class Tree:
        def __init__(self, name):
            self.name = name

    @pytest.mark.parametrize('name,expected', [
        ('TaiCOL260224', '臺灣物種名錄 20260224版本'),
        ('TaiCOL-20250430', '臺灣物種名錄 20250430版本'),
        ('GBIF backbone', 'GBIF backbone'),
    ])
    def test_version_label(self, name, expected):
        assert name_according_to_for(self.Tree(name)) == expected

    def test_no_tree(self):
        assert name_according_to_for(None) is None


class TestDatasetId:
    CONF = {'datasets': {'1': {'datasetID': 'a1b2-uuid'}, '2': {'datasetName': 'x'}}}

    def test_configured_value_wins(self):
        assert dataset_id_for(self.CONF, 1) == 'a1b2-uuid'

    def test_falls_back_to_collection_id(self):
        assert dataset_id_for(self.CONF, 2) == '2'
        assert dataset_id_for({}, 9) == '9'

    def test_map(self):
        assert build_dataset_map(self.CONF, [1, 2]) == {'a1b2-uuid': 1, '2': 2}

    def test_duplicate_is_config_error(self):
        conf = {'datasets': {'1': {'datasetID': 'same'}, '2': {'datasetID': 'same'}}}
        with pytest.raises(TbiaError) as e:
            build_dataset_map(conf, [1, 2])
        assert e.value.code == 500

    def test_configured_id_cannot_shadow_another_collection(self):
        # collection 1 published as "2" collides with collection 2's fallback
        conf = {'datasets': {'1': {'datasetID': '2'}}}
        with pytest.raises(TbiaError):
            build_dataset_map(conf, [1, 2])


class TestMediaUrlRewriter:
    CDN = {'s3_bucket': 'brmas-media', 'base_url': 'https://media.naturedb.org/'}
    OUT = 'https://media.naturedb.org/hast/specimen/S_096138-l.jpg'

    @pytest.mark.parametrize('src', [
        'https://brmas-media.s3-ap-northeast-1.amazonaws.com/hast/specimen/S_096138-l.jpg',
        'https://brmas-media.s3.ap-northeast-1.amazonaws.com/hast/specimen/S_096138-l.jpg',
        'https://brmas-media.s3.amazonaws.com/hast/specimen/S_096138-l.jpg',
        'https://s3.ap-northeast-1.amazonaws.com/brmas-media/hast/specimen/S_096138-l.jpg',
        'http://brmas-media.s3.ap-northeast-1.amazonaws.com/hast/specimen/S_096138-l.jpg',
    ])
    def test_all_s3_spellings(self, src):
        assert media_url_rewriter(self.CDN)(src) == self.OUT

    @pytest.mark.parametrize('src', [
        'https://other-bucket.s3.ap-northeast-1.amazonaws.com/x.jpg',
        'https://brmas-media-old.s3.ap-northeast-1.amazonaws.com/x.jpg',
        'https://example.org/brmas-media.s3.amazonaws.com/x.jpg',
        None, '',
    ])
    def test_others_untouched(self, src):
        assert media_url_rewriter(self.CDN)(src) == src

    @pytest.mark.parametrize('conf', [None, {}, {'s3_bucket': 'brmas-media'}, {'base_url': 'https://x'}])
    def test_unconfigured_is_identity(self, conf):
        url = 'https://brmas-media.s3.ap-northeast-1.amazonaws.com/a.jpg'
        assert media_url_rewriter(conf)(url) == url


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

    def test_locality_excludes_administrative_areas(self, client):
        # admin levels have their own fields; locality must not repeat them
        body = client.get('/tbia/v2/occurrence?limit=200', headers=HAST).get_json()
        checked = 0
        for row in body['data']:
            if row['county'] and row['locality']:
                assert row['county'] not in row['locality']
                checked += 1
        if not checked:
            pytest.skip('no rows with both county and locality')

    def test_collection_code_only_from_settings(self, client, monkeypatch):
        from app.models.site import Site
        real = Site.get_settings

        def no_code(self, key=''):
            conf = real(self, key)
            if key == 'aggregator.tbia' and conf:
                for ds in conf.get('datasets', {}).values():
                    ds.pop('collectionCode', None)
            return conf

        monkeypatch.setattr(Site, 'get_settings', no_code)
        body = client.get('/tbia/v2/occurrence?limit=20', headers=HAST).get_json()
        assert body['data']
        assert all(row['collectionCode'] is None for row in body['data'])

    def test_name_fields_mapping(self, client):
        # verbatim* = the record's own name; scientificName & co. = TaiCOL match
        body = client.get('/tbia/v2/occurrence?limit=200', headers=HAST).get_json()
        rows = body['data']
        assert any(r['verbatimScientificName'] for r in rows)
        matched = [r for r in rows if r['scientificName']]
        if not matched:
            pytest.skip('no TaiCOL matches in sample')
        for r in matched:
            assert r['nameAccordingTo'].startswith('臺灣物種名錄 ')
            assert r['taxonRank']
        for r in rows:
            if not r['scientificName']:
                assert r['taxonID'] is None and r['nameAccordingTo'] is None
                assert r['scientificNameAuthorship'] is None and r['vernacularName'] is None

    def test_taxon_group_left_to_aggregator(self, client):
        body = client.get('/tbia/v2/occurrence?limit=50', headers=HAST).get_json()
        assert all(row['taxonGroup'] is None for row in body['data'])

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

    def test_dataset_id_round_trips_to_occurrence(self, client):
        datasets = client.get('/tbia/v2/dataset', headers=HAST).get_json()['data']
        if not datasets:
            pytest.skip('no datasets configured')
        did = datasets[0]['datasetID']
        body = client.get(f'/tbia/v2/occurrence?datasetID={did}&limit=3', headers=HAST).get_json()
        assert body['status']['code'] == 200
        assert body['data'], 'filter by a published datasetID should match rows'
        assert {row['datasetID'] for row in body['data']} == {did}

    def test_occurrence_unknown_dataset_id_is_empty(self, client):
        r = client.get('/tbia/v2/occurrence?datasetID=no-such-dataset', headers=HAST)
        assert r.status_code == 200
        assert r.get_json()['data'] == []

    def test_filter_by_dataset_id_no_match(self, client):
        body = client.get('/tbia/v2/dataset?datasetID=999999', headers=HAST).get_json()
        assert body['data'] == []
        assert body['meta']['total'] == 0
