import pytest
from unittest.mock import patch, MagicMock
from src.adapters.outgoing.services.prowlarr.client import (
    ProwlarrClient,
    ProwlarrSearchResult,
    ProwlarrError,
    CATEGORY_MAPPING,
    QUALITY_PATTERNS,
    LANGUAGE_PATTERNS,
)


class TestProwlarrSearchResult:
    def test_create_result(self):
        result = ProwlarrSearchResult(
            guid="123",
            title="Test Movie",
            indexer="test",
            size=1024,
            seeders=10,
            leechers=5,
        )
        assert result.guid == "123"
        assert result.title == "Test Movie"
        assert result.size == 1024
        assert result.seeders == 10
        assert result.categories == []

    def test_to_dict(self):
        result = ProwlarrSearchResult(
            guid="123",
            title="Test Movie",
            indexer="test",
            size=1024,
            seeders=10,
            leechers=5,
        )
        d = result.to_dict()
        assert d["guid"] == "123"
        assert d["title"] == "Test Movie"
        assert d["size_formatted"] == "1.00 KB"

    def test_format_size_bytes(self):
        assert ProwlarrSearchResult._format_size(500) == "500.00 B"

    def test_format_size_kb(self):
        assert ProwlarrSearchResult._format_size(2048) == "2.00 KB"

    def test_format_size_mb(self):
        assert ProwlarrSearchResult._format_size(1048576) == "1.00 MB"

    def test_format_size_gb(self):
        assert ProwlarrSearchResult._format_size(1073741824) == "1.00 GB"


class TestProwlarrError:
    def test_error_with_status_code(self):
        err = ProwlarrError("Test error", 404)
        assert err.message == "Test error"
        assert err.status_code == 404

    def test_error_without_status_code(self):
        err = ProwlarrError("Test error")
        assert err.message == "Test error"
        assert err.status_code is None


class TestProwlarrClient:
    @pytest.fixture
    def client(self):
        with patch(
            "src.adapters.outgoing.services.prowlarr.client.settings"
        ) as mock_settings:
            mock_settings.PROWLARR_URL = "http://localhost:9696"
            mock_settings.PROWLARR_API_KEY = "test_key"
            return ProwlarrClient()

    def test_client_init_default(self, client):
        assert client.url == "http://localhost:9696"
        assert client.api_key == "test_key"
        assert client._timeout == 30

    def test_client_init_custom(self):
        with patch(
            "src.adapters.outgoing.services.prowlarr.client.settings"
        ) as mock_settings:
            mock_settings.PROWLARR_URL = "http://localhost:9696"
            mock_settings.PROWLARR_API_KEY = "test_key"
            client = ProwlarrClient(url="http://custom:9696", api_key="custom_key")
            assert client.url == "http://custom:9696"
            assert client.api_key == "custom_key"

    def test_check_config_raises_when_no_api_key(self):
        with patch(
            "src.adapters.outgoing.services.prowlarr.client.settings"
        ) as mock_settings:
            mock_settings.PROWLARR_URL = "http://localhost:9696"
            mock_settings.PROWLARR_API_KEY = ""
            client = ProwlarrClient()
            with pytest.raises(ProwlarrError) as exc:
                client._check_config()
            assert "API key" in exc.value.message

    def test_make_request_connection_error(self, client):
        import requests

        with patch.object(client, "_check_config"):
            with patch(
                "requests.Session.request",
                side_effect=requests.exceptions.ConnectionError(),
            ):
                with pytest.raises(ProwlarrError) as exc:
                    client._make_request("GET", "/api/v1/test")
                assert "conectar" in exc.value.message

    def test_make_request_timeout(self, client):
        import requests

        with patch.object(client, "_check_config"):
            with patch(
                "requests.Session.request", side_effect=requests.exceptions.Timeout()
            ):
                with pytest.raises(ProwlarrError) as exc:
                    client._make_request("GET", "/api/v1/test")
                assert "tiempo" in exc.value.message.lower()

    def test_make_request_401_error(self, client):
        import requests

        with patch.object(client, "_check_config"):
            mock_response = MagicMock()
            mock_response.status_code = 401
            mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
                response=mock_response
            )
            with patch("requests.Session.request", return_value=mock_response):
                with pytest.raises(ProwlarrError) as exc:
                    client._make_request("GET", "/api/v1/test")
                assert exc.value.status_code == 401

    def test_search_movies_empty_query(self, client):
        results = client.search_movies("")
        assert results == []

    def test_search_movies_whitespace_query(self, client):
        results = client.search_movies("   ")
        assert results == []

    def test_parse_search_result_basic(self, client):
        item = {
            "guid": "test-123",
            "title": "Test Movie 2023 1080p BluRay",
            "indexer": "RARBG",
            "size": 1500000000,
            "seeders": 100,
            "leechers": 50,
            "magnetUrl": "magnet:?xt=urn:btih:abc123",
        }
        result = client._parse_search_result(item)
        assert result is not None
        assert result.title == "Test Movie 2023 1080p BluRay"
        assert result.size == 1500000000

    def test_parse_search_result_with_infohash(self, client):
        item = {
            "guid": "test-456",
            "title": "Test Movie",
            "indexer": "TestIndexer",
            "size": 1000000,
            "seeders": 10,
            "leechers": 5,
            "infoHash": "abcdef1234567890",
        }
        result = client._parse_search_result(item)
        assert result is not None
        assert result.magnet_url is not None
        assert "abcdef1234567890" in result.magnet_url

    def test_parse_search_result_no_title(self, client):
        item = {"guid": "123"}
        result = client._parse_search_result(item)
        assert result is None

    def test_parse_search_result_with_categories(self, client):
        item = {
            "guid": "123",
            "title": "Test Movie",
            "indexer": "test",
            "size": 1000,
            "seeders": 1,
            "leechers": 0,
            "categories": [{"id": 2000, "name": "Movies"}],
        }
        result = client._parse_search_result(item)
        assert result is not None

    def test_parse_size_string_bytes(self):
        assert ProwlarrClient._parse_size_string(None, "500B") == 500

    def test_parse_size_string_invalid(self):
        assert ProwlarrClient._parse_size_string(None, "invalid") == 0

    def test_extract_quality_4k(self):
        assert ProwlarrClient._extract_quality(None, "Movie 2023 4K BluRay") == "4K"

    def test_extract_quality_720p(self):
        result = ProwlarrClient._extract_quality(None, "Movie 720p WEB-DL")
        assert result.upper() == "720P"

    def test_extract_quality_unknown(self):
        assert ProwlarrClient._extract_quality(None, "Movie") == "Calidad desconocida"

    def test_extract_language_spanish(self):
        assert ProwlarrClient._extract_language(None, "Movie SPANISH") == "Español"

    def test_extract_language_latin(self):
        assert ProwlarrClient._extract_language(None, "Movie LATIN") == "Latino"

    def test_extract_language_multi(self):
        assert (
            ProwlarrClient._extract_language(None, "Movie SPANISH ENGLISH")
            == "Multiidioma"
        )

    def test_map_category_movies(self):
        assert ProwlarrClient._map_category(None, [{"id": 2000}]) == "Películas"

    def test_map_category_tv(self):
        assert ProwlarrClient._map_category(None, [{"id": 5010}]) == "Series"

    def test_map_category_empty(self):
        assert ProwlarrClient._map_category(None, []) == "Películas"

    def test_format_relative_date_days(self):
        from datetime import datetime, timedelta

        date_str = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%dT%H:%M:%S")
        result = ProwlarrClient._format_relative_date(None, date_str=date_str)
        assert "día" in result

    def test_format_relative_date_hours(self):
        from datetime import datetime, timedelta

        date_str = (datetime.now() - timedelta(hours=3)).strftime("%Y-%m-%dT%H:%M:%S")
        result = ProwlarrClient._format_relative_date(None, date_str=date_str)
        assert "hora" in result

    def test_format_relative_date_none(self):
        result = ProwlarrClient._format_relative_date(None, date_str=None)
        assert result == "Fecha desconocida"

    def test_format_results_for_frontend(self):
        with patch(
            "src.adapters.outgoing.services.prowlarr.client.settings"
        ) as mock_settings:
            mock_settings.PROWLARR_URL = "http://localhost:9696"
            mock_settings.PROWLARR_API_KEY = "test_key"
            client = ProwlarrClient()

            results = [
                ProwlarrSearchResult(
                    guid="123",
                    title="Test Movie 2023 1080p BluRay",
                    indexer="RARBG",
                    size=1500000000,
                    seeders=100,
                    leechers=50,
                    categories=["2000"],
                )
            ]

            formatted = client.format_results_for_frontend(results)
            assert len(formatted) == 1

    def test_get_indexers(self, client):
        with patch.object(
            client, "_make_request", return_value=[{"id": 1, "name": "test"}]
        ):
            indexers = client.get_indexers()
            assert len(indexers) == 1

    def test_test_connection_success(self, client):
        with patch.object(client, "_check_config"):
            with patch.object(client, "_make_request"):
                assert client.test_connection() is True

    def test_test_connection_failure(self, client):
        with patch.object(client, "_check_config", side_effect=ProwlarrError("Error")):
            assert client.test_connection() is False


class TestProwlarrConstants:
    def test_category_mapping(self):
        assert CATEGORY_MAPPING[2000] == "Películas"
        assert CATEGORY_MAPPING[5010] == "Series"

    def test_quality_patterns(self):
        assert len(QUALITY_PATTERNS) > 0

    def test_language_patterns(self):
        assert "Español" in LANGUAGE_PATTERNS
        assert "Latino" in LANGUAGE_PATTERNS
