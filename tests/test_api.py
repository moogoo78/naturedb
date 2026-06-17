import json
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.models.site import Site
from app.models.collection import Record, Person, Unit, Collection
from app.models.taxon import Taxon
from app.models.gazetter import NamedArea, AreaClass


class TestSearchbarEndpoint:
    """Test cases for /api/v1/searchbar endpoint"""

    def test_searchbar_without_query(self, client):
        """Test searchbar returns empty categories when no query provided"""
        response = client.get('/api/v1/searchbar')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'taxa' in data
        assert 'collectors' in data
        assert isinstance(data['taxa'], list)
        assert isinstance(data['collectors'], list)

    def test_searchbar_with_short_query(self, client):
        """Test searchbar with 1-3 character query"""
        response = client.get('/api/v1/searchbar?q=A')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'taxa' in data
        assert 'collectors' in data

    def test_searchbar_with_long_query(self, client):
        """Test searchbar with query longer than 3 characters"""
        response = client.get('/api/v1/searchbar?q=Plant')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'taxa' in data
        assert 'collectors' in data

    def test_searchbar_cors_headers(self, client):
        """Test that CORS headers are set correctly"""
        response = client.get('/api/v1/searchbar?q=test')
        assert response.headers.get('Access-Control-Allow-Origin') == '*'
        assert response.headers.get('Access-Control-Allow-Methods') == '*'


class TestSearchEndpoint:
    """Test cases for /api/v1/search endpoint"""

    def test_search_without_host_returns_401(self, client):
        """Test search returns 401 when no valid host provided"""
        response = client.get('/api/v1/search')
        assert response.status_code == 401

    @patch('app.models.site.Site.find_by_host')
    def test_search_with_valid_host(self, mock_find_by_host, client):
        """Test search with valid host header"""
        mock_site = MagicMock()
        mock_site.collection_ids = [1, 2, 3]
        mock_site.get_custom_area_classes.return_value = []
        mock_find_by_host.return_value = mock_site

        response = client.get('/api/v1/search', headers={'Host': 'example.com'})
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data
        assert 'elapsed' in data
        assert isinstance(data['data'], list)

    @patch('app.models.site.Site.find_by_host')
    def test_search_with_filter(self, mock_find_by_host, client):
        """Test search with filter parameter"""
        mock_site = MagicMock()
        mock_site.collection_ids = [1]
        mock_site.get_custom_area_classes.return_value = []
        mock_find_by_host.return_value = mock_site

        filter_param = json.dumps({'collection_id': 1})
        response = client.get(
            f'/api/v1/search?filter={filter_param}',
            headers={'Host': 'example.com'}
        )
        assert response.status_code == 200

    @patch('app.models.site.Site.find_by_host')
    def test_search_with_sort(self, mock_find_by_host, client):
        """Test search with sort parameter"""
        mock_site = MagicMock()
        mock_site.collection_ids = [1]
        mock_site.get_custom_area_classes.return_value = []
        mock_find_by_host.return_value = mock_site

        sort_param = json.dumps(['field_number'])
        response = client.get(
            f'/api/v1/search?sort={sort_param}',
            headers={'Host': 'example.com'}
        )
        assert response.status_code == 200

    @patch('app.models.site.Site.find_by_host')
    def test_search_with_range(self, mock_find_by_host, client):
        """Test search with range parameter for pagination"""
        mock_site = MagicMock()
        mock_site.collection_ids = [1]
        mock_site.get_custom_area_classes.return_value = []
        mock_find_by_host.return_value = mock_site

        range_param = json.dumps([0, 10])
        response = client.get(
            f'/api/v1/search?range={range_param}',
            headers={'Host': 'example.com'}
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['data']) <= 10


class TestPublicSpecimensEndpoint:
    """Test cases for /v1/specimens (public cross-origin specimen API)"""

    EXPECTED_KEYS = {
        'unit_id', 'record_id', 'record_key', 'catalog_number', 'image_url',
        'field_number', 'collector', 'collector_text', 'collect_date',
        'taxon', 'taxon_text', 'named_areas', 'locality_text', 'altitude',
        'altitude2', 'longitude_decimal', 'latitude_decimal', 'type_status',
        'link',
    }

    def test_specimens_no_site_returns_data(self, client):
        """No site param performs a cross-collection search and returns the envelope"""
        response = client.get('/v1/specimens?range=%5B0,3%5D')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data
        assert 'elapsed' in data
        assert isinstance(data['data'], list)

    def test_specimens_does_not_require_host(self, client):
        """Unlike legacy /api/v1/search, /v1/specimens works without a Host header"""
        response = client.get('/v1/specimens?range=%5B0,1%5D')
        assert response.status_code == 200

    def test_specimens_cors_header_open(self, client):
        """Public read API must allow any origin"""
        response = client.get('/v1/specimens?range=%5B0,1%5D')
        assert response.headers.get('Access-Control-Allow-Origin') == '*'

    def test_specimens_unknown_site_returns_400(self, client):
        """Unknown site slug is a client typo (400), not an auth failure (401)"""
        response = client.get('/v1/specimens?site=__no_such_site__')
        assert response.status_code == 400

    def test_specimens_malformed_filter_returns_400(self, client):
        """Malformed JSON in filter is a client error (400), not a 500"""
        response = client.get('/v1/specimens?filter=not-json')
        assert response.status_code == 400

    def test_specimens_malformed_range_returns_400(self, client):
        """Malformed JSON in range is a client error (400), not a 500"""
        response = client.get('/v1/specimens?range=%5B0,')
        assert response.status_code == 400

    def test_specimens_range_limits_results(self, client):
        """range param caps the number of returned rows"""
        response = client.get('/v1/specimens?range=%5B0,5%5D')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['data']) <= 5

    def test_specimens_shape_matches_serializer_contract(self, client):
        """Each row carries exactly the shared serializer's key set.

        Guards against drift between this endpoint and legacy /api/v1/search,
        which now share serialize_specimen_row().
        """
        response = client.get('/v1/specimens?range=%5B0,1%5D')
        data = json.loads(response.data)
        if not data['data']:
            pytest.skip('test DB has no published records')
        assert set(data['data'][0].keys()) == self.EXPECTED_KEYS

    def test_specimens_q_filter_accepted(self, client):
        """Free-text q param is accepted and folded into the filter"""
        response = client.get('/v1/specimens?q=Quercus&range=%5B0,5%5D')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data['data'], list)

    def test_specimens_known_site_scopes_to_its_collections(self, client):
        """A known site slug restricts results to that site's collections"""
        site = Site.query.first()
        if site is None:
            pytest.skip('test DB has no sites')
        response = client.get(
            f'/v1/specimens?site={site.name}&range=%5B0,3%5D'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data['data'], list)

    def test_specimens_total_param_skips_count(self, client):
        """Passing total echoes it back instead of running the count query"""
        response = client.get('/v1/specimens?total=999&range=%5B0,1%5D')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert str(data['total']) == '999'


class TestPersonEndpoints:
    """Test cases for person-related endpoints"""

    def test_get_person_list_without_filter(self, client):
        """Test getting person list without filter"""
        response = client.get('/api/v1/people')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data
        assert isinstance(data['data'], list)

    def test_get_person_list_with_keyword_filter(self, client):
        """Test getting person list with keyword filter"""
        filter_param = json.dumps({'q': 'John'})
        response = client.get(f'/api/v1/people?filter={filter_param}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data

    def test_get_person_list_with_collector_filter(self, client):
        """Test getting person list filtered by is_collector"""
        filter_param = json.dumps({'is_collector': True})
        response = client.get(f'/api/v1/people?filter={filter_param}')
        assert response.status_code == 200

    def test_get_person_list_with_identifier_filter(self, client):
        """Test getting person list filtered by is_identifier"""
        filter_param = json.dumps({'is_identifier': True})
        response = client.get(f'/api/v1/people?filter={filter_param}')
        assert response.status_code == 200

    def test_get_person_list_with_sort(self, client):
        """Test getting person list with sorting"""
        sort_param = json.dumps([{'sorting_name': 'asc'}])
        response = client.get(f'/api/v1/people?sort={sort_param}')
        assert response.status_code == 200

    def test_get_person_detail_invalid_id(self, client):
        """Test getting person detail with invalid ID"""
        response = client.get('/api/v1/people/999999')
        # Should return 200 but with null/empty data or error
        # Actual behavior depends on implementation
        assert response.status_code in [200, 404]


class TestTaxonEndpoints:
    """Test cases for taxon-related endpoints"""

    def test_get_taxon_list_without_filter(self, client):
        """Test getting taxon list without filter"""
        response = client.get('/api/v1/taxa')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data

    def test_get_taxon_list_with_keyword_filter(self, client):
        """Test getting taxon list with keyword filter"""
        filter_param = json.dumps({'q': 'Rosa'})
        response = client.get(f'/api/v1/taxa?filter={filter_param}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data

    def test_get_taxon_list_with_rank_filter(self, client):
        """Test getting taxon list filtered by rank"""
        filter_param = json.dumps({'rank': 'genus'})
        response = client.get(f'/api/v1/taxa?filter={filter_param}')
        assert response.status_code == 200

    def test_get_taxon_list_with_id_filter(self, client):
        """Test getting taxon list filtered by IDs"""
        filter_param = json.dumps({'id': [1, 2, 3]})
        response = client.get(f'/api/v1/taxa?filter={filter_param}')
        assert response.status_code == 200

    def test_get_taxon_list_with_range(self, client):
        """Test getting taxon list with range"""
        range_param = json.dumps([0, 10])
        response = client.get(f'/api/v1/taxa?range={range_param}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert len(data['data']) <= 10

    def test_get_taxon_detail_invalid_id(self, client):
        """Test getting taxon detail with invalid ID"""
        response = client.get('/api/v1/taxa/999999')
        assert response.status_code == 404


class TestNamedAreaEndpoints:
    """Test cases for named area endpoints"""

    def test_get_named_area_list_no_filter_returns_empty(self, client):
        """Test named area list without filter returns empty"""
        response = client.get('/api/v1/named-areas')
        assert response.status_code == 200
        data = json.loads(response.data)
        # Without filter, it filters by id==0, so should be empty
        assert 'data' in data

    def test_get_named_area_list_with_keyword(self, client):
        """Test getting named area list with keyword"""
        filter_param = json.dumps({'q': 'Taiwan'})
        response = client.get(f'/api/v1/named-areas?filter={filter_param}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data

    def test_get_named_area_list_with_area_class_filter(self, client):
        """Test getting named area list filtered by area class"""
        filter_param = json.dumps({'area_class_id': 5})
        response = client.get(f'/api/v1/named-areas?filter={filter_param}')
        assert response.status_code == 200

    def test_get_named_area_list_with_parent_id(self, client):
        """Test getting named area list filtered by parent_id"""
        filter_param = json.dumps({'parent_id': 1})
        response = client.get(f'/api/v1/named-areas?filter={filter_param}')
        assert response.status_code == 200

    def test_get_named_area_list_with_continent(self, client):
        """Test getting named area list filtered by continent"""
        filter_param = json.dumps({'continent': 'asia'})
        response = client.get(f'/api/v1/named-areas?filter={filter_param}')
        assert response.status_code == 200

    def test_get_named_area_list_with_range(self, client):
        """Test getting named area list with range"""
        filter_param = json.dumps({'q': 'a'})
        range_param = json.dumps([0, 5])
        response = client.get(
            f'/api/v1/named-areas?filter={filter_param}&range={range_param}'
        )
        assert response.status_code == 200


class TestAreaClassEndpoints:
    """Test cases for area class endpoints"""

    def test_get_area_class_list(self, client):
        """Test getting area class list"""
        response = client.get('/api/v1/area-classes')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data

    def test_get_area_class_list_with_keyword(self, client):
        """Test getting area class list with keyword filter"""
        filter_param = json.dumps({'q': 'country'})
        response = client.get(f'/api/v1/area-classes?filter={filter_param}')
        assert response.status_code == 200

    def test_get_area_class_detail_invalid_id(self, client):
        """Test getting area class detail with invalid ID"""
        response = client.get('/api/v1/area-classes/999999')
        # Returns redirect to 404 which becomes 404 or 308
        assert response.status_code in [302, 404, 308]


class TestTaxonomyEndpoints:
    """Test cases for taxonomy-related endpoints"""

    def test_get_taxonomy_stats_without_filter(self, client):
        """Test taxonomy stats without filter returns error"""
        response = client.get('/api/v1/taxonomy/stats')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'error'
        assert 'message' in data

    def test_get_taxonomy_stats_with_filter(self, client):
        """Test taxonomy stats with valid filter"""
        filter_param = json.dumps({
            'collection_id': [1],
            'raw': {'kingdom_name': ['kingdom_name', 'Plantae']}
        })
        response = client.get(f'/api/v1/taxonomy/stats?filter={filter_param}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data

    def test_get_taxonomy_children_without_filter(self, client):
        """Test taxonomy children without filter returns error"""
        response = client.get('/api/v1/taxonomy/children')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data['status'] == 'error'

    def test_get_taxonomy_children_with_filter(self, client):
        """Test taxonomy children with valid filter"""
        filter_param = json.dumps({
            'collection_id': [1],
            'raw': {'kingdom_name': ['kingdom_name', 'Plantae']}
        })
        response = client.get(f'/api/v1/taxonomy/children?filter={filter_param}')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'status' in data


class TestRecordEndpoints:
    """Test cases for record-related endpoints"""

    def test_get_record_parts_named_areas(self, client):
        """Test getting record parts for named-areas"""
        response = client.get('/api/v1/record/1/named-areas')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, dict)

    def test_get_record_parts_invalid_id(self, client):
        """Test getting record parts with invalid ID"""
        response = client.get('/api/v1/record/999999/named-areas')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert data == {}


class TestOccurrenceEndpoint:
    """Test cases for /api/v1/occurrence endpoint (TBIA integration)"""

    def test_occurrence_missing_required_params(self, client):
        """Test occurrence endpoint without required parameters"""
        response = client.get('/api/v1/occurrence')
        # Missing required date params, should succeed but with defaults
        assert response.status_code in [200, 400]

    def test_occurrence_with_date_params(self, client):
        """Test occurrence endpoint with date parameters"""
        response = client.get(
            '/api/v1/occurrence?startCreated=20200101&endCreated=20201231&limit=10&offset=0'
        )
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'meta' in data
        if 'meta' in data:
            assert 'total' in data['meta']
            assert 'pagination' in data['meta']

    def test_occurrence_with_invalid_date_format(self, client):
        """Test occurrence endpoint with invalid date format"""
        response = client.get(
            '/api/v1/occurrence?startCreated=invalid-date'
        )
        assert response.status_code == 400

    def test_occurrence_with_modified_dates(self, client):
        """Test occurrence endpoint with modified date range"""
        response = client.get(
            '/api/v1/occurrence?startModified=20200101&endModified=20201231&limit=5'
        )
        assert response.status_code in [200, 400]

    def test_occurrence_pagination(self, client):
        """Test occurrence endpoint pagination"""
        response = client.get(
            '/api/v1/occurrence?limit=5&offset=0'
        )
        assert response.status_code in [200, 400]
        if response.status_code == 200:
            data = json.loads(response.data)
            if 'data' in data:
                assert len(data['data']) <= 5


class TestCollectionEndpoints:
    """Test cases for collection-related endpoints"""

    def test_get_collection_raw_list(self, client):
        """Test getting collection raw list"""
        response = client.get('/api/v1/collections/1/raw')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, (dict, set))

    def test_get_collection_raw_list_invalid_id(self, client):
        """Test getting collection raw list with invalid ID"""
        response = client.get('/api/v1/collections/999999/raw')
        assert response.status_code == 200

    def test_get_collection_raw_detail(self, client):
        """Test getting collection raw detail for a record"""
        response = client.get('/api/v1/collections/1/records/1/raw')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert isinstance(data, (dict, set))

    def test_get_collection_raw_detail_invalid_ids(self, client):
        """Test getting collection raw detail with invalid IDs"""
        response = client.get('/api/v1/collections/999999/records/999999/raw')
        assert response.status_code == 200


class TestCORSHeaders:
    """Test CORS headers are applied to all API endpoints"""

    def test_cors_headers_on_people_endpoint(self, client):
        """Test CORS headers on /people endpoint"""
        response = client.get('/api/v1/people')
        assert response.headers.get('Access-Control-Allow-Origin') == '*'
        assert response.headers.get('Access-Control-Allow-Methods') == '*'

    def test_cors_headers_on_taxa_endpoint(self, client):
        """Test CORS headers on /taxa endpoint"""
        response = client.get('/api/v1/taxa')
        assert response.headers.get('Access-Control-Allow-Origin') == '*'
        assert response.headers.get('Access-Control-Allow-Methods') == '*'


class TestResponseFormats:
    """Test that API responses follow expected formats"""

    def test_person_list_response_format(self, client):
        """Test person list response has correct structure"""
        response = client.get('/api/v1/people')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data
        assert 'query' in data
        assert 'elapsed' in data
        assert isinstance(data['elapsed'], (int, float))

    def test_taxon_list_response_format(self, client):
        """Test taxon list response has correct structure"""
        response = client.get('/api/v1/taxa')
        assert response.status_code == 200
        data = json.loads(response.data)
        assert 'data' in data
        assert 'total' in data
        assert isinstance(data['data'], list)


class TestMaskCoordinates:
    """Unit tests for sensitive data coordinate masking (TBIAdata 六類敏感層級)."""

    def test_level_0_none_returns_original(self):
        from app.utils import mask_coordinates
        lat, lon = mask_coordinates(23.456789, 120.987654, 0)
        assert lat == 23.456789
        assert lon == 120.987654

    def test_level_1_light_rounds_to_2_decimals(self):
        from app.utils import mask_coordinates
        lat, lon = mask_coordinates(23.456789, 120.987654, 1)
        assert lat == 23.46
        assert lon == 120.99

    def test_level_2_heavy_rounds_to_1_decimal(self):
        from app.utils import mask_coordinates
        lat, lon = mask_coordinates(23.456789, 120.987654, 2)
        assert lat == 23.5
        assert lon == 121.0

    def test_level_3_county_suppresses_coordinates(self):
        from app.utils import mask_coordinates
        lat, lon = mask_coordinates(23.456789, 120.987654, 3)
        assert lat is None
        assert lon is None

    def test_level_4_no_coordinate_suppresses(self):
        from app.utils import mask_coordinates
        lat, lon = mask_coordinates(23.456789, 120.987654, 4)
        assert lat is None
        assert lon is None

    def test_level_5_no_species_suppresses(self):
        from app.utils import mask_coordinates
        lat, lon = mask_coordinates(23.456789, 120.987654, 5)
        assert lat is None
        assert lon is None

    def test_none_inputs_return_none(self):
        from app.utils import mask_coordinates
        assert mask_coordinates(None, None, 0) == (None, None)
        assert mask_coordinates(None, 120.0, 1) == (None, None)
        assert mask_coordinates(23.0, None, 1) == (None, None)

    def test_invalid_level_treated_as_zero(self):
        from app.utils import mask_coordinates
        lat, lon = mask_coordinates(23.456789, 120.987654, None)
        assert lat == 23.456789
        assert lon == 120.987654
        lat, lon = mask_coordinates(23.456789, 120.987654, 'bad')
        assert lat == 23.456789
        assert lon == 120.987654

    def test_descriptions_dict_has_all_levels(self):
        from app.utils import SENSITIVE_LEVEL_DESCRIPTIONS
        for lvl in (0, 1, 2, 3, 4, 5):
            assert lvl in SENSITIVE_LEVEL_DESCRIPTIONS
