import json
import pytest
from unittest.mock import patch, MagicMock, PropertyMock


class TestMintArkId:
    """Test cases for the mint_ark_id function in app/helpers.py"""

    def _make_mocks(self):
        """Build common mock objects for site, unit, collection, organization."""
        mock_org = MagicMock()
        mock_org.code = 'HAST'

        mock_collection = MagicMock()
        mock_collection.organization = mock_org

        mock_unit = MagicMock()
        mock_unit.id = 42
        mock_unit.accession_number = '123456'
        mock_unit.collection = mock_collection
        mock_unit.guid = None

        mock_site = MagicMock()
        mock_site.name = 'hast'
        mock_site.host = 'hast.biodiv.tw'
        mock_site.get_settings = MagicMock(side_effect=lambda key: {
            'admin.unit.auto-guid': {
                'ark': {
                    'api_url': 'https://pid.biodiv.tw/api/mint',
                    'api_key': 'test-api-key',
                    'naan': 18474,
                    'shoulder': 'b2',
                },
            },
            'frontend.specimens.url': '{org_code}:{accession_number}',
        }.get(key))

        return mock_site, mock_unit, mock_collection, mock_org

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_success(self, mock_post, mock_session, app):
        """Test successful ARK minting sets unit.guid and creates PID record."""
        from app.helpers import mint_ark_id

        mock_site, mock_unit, _, _ = self._make_mocks()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'ark': 'ark:/18474/b2x7k9m2p',
            'identifier': '18474/b2x7k9m2p',
            'url': 'https://hast.biodiv.tw/specimens/HAST:123456',
        }
        mock_response.raise_for_status = MagicMock()
        mock_post.return_value = mock_response

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        # Verify the returned ARK
        assert result == 'https://n2t.net/ark:/18474/b2x7k9m2p'

        # Verify unit.guid was set
        assert mock_unit.guid == 'https://n2t.net/ark:/18474/b2x7k9m2p'

        # Verify the API was called with correct payload
        mock_post.assert_called_once()
        call_kwargs = mock_post.call_args
        assert call_kwargs[1]['json']['naan'] == 18474
        assert call_kwargs[1]['json']['shoulder'] == 'b2'
        assert call_kwargs[1]['json']['who'] == 'HAST'
        assert 'HAST:123456' in call_kwargs[1]['json']['url']
        assert call_kwargs[1]['headers']['X-API-Key'] == 'test-api-key'

        # Verify session.commit was called to persist unit.guid
        mock_session.commit.assert_called()

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_no_config(self, mock_post, mock_session, app):
        """Test that mint_ark_id returns None when no ARK config exists."""
        from app.helpers import mint_ark_id

        mock_site = MagicMock()
        mock_site.get_settings = MagicMock(return_value=None)
        mock_unit = MagicMock()

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        assert result is None
        mock_post.assert_not_called()
        mock_session.add.assert_not_called()

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_no_api_key(self, mock_post, mock_session, app):
        """Test that mint_ark_id returns None when api_key is empty."""
        from app.helpers import mint_ark_id

        mock_site = MagicMock()
        mock_site.get_settings = MagicMock(return_value={
            'ark': {
                'api_url': 'https://pid.biodiv.tw/api/mint',
                'api_key': '',
                'naan': 18474,
                'shoulder': 'b2',
            },
        })
        mock_unit = MagicMock()

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        assert result is None
        mock_post.assert_not_called()

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_api_failure(self, mock_post, mock_session, app):
        """Test that unit creation succeeds even when ARK API is down."""
        import requests as req
        from app.helpers import mint_ark_id

        mock_site, mock_unit, _, _ = self._make_mocks()

        mock_post.side_effect = req.exceptions.ConnectionError('Service unavailable')

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        # Must return None without raising
        assert result is None
        # unit.guid should NOT be set
        assert mock_unit.guid is None

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_http_error(self, mock_post, mock_session, app):
        """Test that HTTP error from ARK service is handled gracefully."""
        import requests as req
        from app.helpers import mint_ark_id

        mock_site, mock_unit, _, _ = self._make_mocks()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = req.exceptions.HTTPError('500 Server Error')
        mock_post.return_value = mock_response

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        assert result is None
        assert mock_unit.guid is None

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_missing_ark_field(self, mock_post, mock_session, app):
        """Test handling of response missing the 'ark' field."""
        from app.helpers import mint_ark_id

        mock_site, mock_unit, _, _ = self._make_mocks()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'identifier': '18474/b2x7k9m2p',
            'url': 'https://hast.biodiv.tw/specimens/HAST:123456',
        }  # Missing 'ark' key
        mock_post.return_value = mock_response

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        assert result is None

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_url_from_template(self, mock_post, mock_session, app):
        """Test target URL is built from frontend.specimens.url template."""
        from app.helpers import mint_ark_id

        mock_site, mock_unit, _, _ = self._make_mocks()

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'ark': 'ark:/18474/b2z3y4x5w',
        }
        mock_post.return_value = mock_response

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        assert result == 'https://n2t.net/ark:/18474/b2z3y4x5w'
        call_kwargs = mock_post.call_args
        # Template is {org_code}:{accession_number} -> HAST:123456
        assert call_kwargs[1]['json']['url'] == 'https://hast.biodiv.tw/specimens/HAST:123456'

    @patch('app.helpers.session')
    @patch('app.helpers.requests.post')
    def test_mint_ark_fallback_template_when_no_setting(self, mock_post, mock_session, app):
        """Test target URL falls back to {unit_id} when no frontend.specimens.url setting."""
        from app.helpers import mint_ark_id

        mock_site, mock_unit, _, _ = self._make_mocks()
        # Override get_settings: no frontend.specimens.url
        mock_site.get_settings = MagicMock(side_effect=lambda key: {
            'admin.unit.auto-guid': {
                'ark': {
                    'api_url': 'https://pid.biodiv.tw/api/mint',
                    'api_key': 'test-api-key',
                    'naan': 18474,
                    'shoulder': 'b2',
                },
            },
        }.get(key))

        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json.return_value = {
            'ark': 'ark:/18474/b2z3y4x5w',
        }
        mock_post.return_value = mock_response

        with app.app_context():
            result = mint_ark_id(mock_site, mock_unit)

        assert result == 'https://n2t.net/ark:/18474/b2z3y4x5w'
        call_kwargs = mock_post.call_args
        # Fallback template is {unit_id} -> 42
        assert call_kwargs[1]['json']['url'] == 'https://hast.biodiv.tw/specimens/42'
