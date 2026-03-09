import pytest
from unittest.mock import patch, MagicMock
from src.adapters.outgoing.services.jackett.client import (
    JackettClient,
    JackettSearchResult,
    JackettError,
    CATEGORY_MAPPING,
    QUALITY_PATTERNS,
    LANGUAGE_PATTERNS,
)


class TestJackettSearchResult:
    def test_create_result(self):
        result = JackettSearchResult(
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
        result = JackettSearchResult(
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
        assert JackettSearchResult._format_size(500) == "500.00 B"

    def test_format_size_kb(self):
        assert JackettSearchResult._format_size(2048) == "2.00 KB"

    def test_format_size_mb(self):
        assert JackettSearchResult._format_size(1048576) == "1.00 MB"

    def test_format_size_gb(self):
        assert JackettSearchResult._format_size(1073741824) == "1.00 GB"

    def test_format_size_tb(self):
        assert JackettSearchResult._format_size(1099511627776) == "1.00 TB"


class TestJackettError:
    def test_error_with_status_code(self):
        err = JackettError("Test error", 404)
        assert err.message == "Test error"
        assert err.status_code == 404
        assert str(err) == "Test error"

    def test_error_without_status_code(self):
        err = JackettError("Test error")
        assert err.message == "Test error"
        assert err.status_code is None


class TestJackettClient:
    @pytest.fixture
    def client(self):
        with patch(
            "src.adapters.outgoing.services.jackett.client.settings"
        ) as mock_settings:
            mock_settings.JACKETT_URL = "http://localhost:9117"
            mock_settings.JACKETT_API_KEY = "test_key"
            mock_settings.JACKETT_TIMEOUT = 30
            return JackettClient()

    def test_client_init_default(self, client):
        assert client.url == "http://localhost:9117"
        assert client.api_key == "test_key"
        assert client.timeout == 30

    def test_client_init_custom(self):
        with patch(
            "src.adapters.outgoing.services.jackett.client.settings"
        ) as mock_settings:
            mock_settings.JACKETT_URL = "http://localhost:9117"
            mock_settings.JACKETT_API_KEY = "test_key"
            mock_settings.JACKETT_TIMEOUT = 30
            client = JackettClient(
                url="http://custom:9117", api_key="custom_key", timeout=60
            )
            assert client.url == "http://custom:9117"
            assert client.api_key == "custom_key"
            assert client.timeout == 60

    def test_check_config_raises_when_no_api_key(self):
        with patch(
            "src.adapters.outgoing.services.jackett.client.settings"
        ) as mock_settings:
            mock_settings.JACKETT_URL = "http://localhost:9117"
            mock_settings.JACKETT_API_KEY = ""
            mock_settings.JACKETT_TIMEOUT = 30
            client = JackettClient()
            with pytest.raises(JackettError) as exc:
                client._check_config()
            assert "API key" in exc.value.message

    def test_parse_size_string_bytes(self):
        assert JackettClient._parse_size_string(None, "500B") == 500

    def test_parse_size_string_invalid(self):
        assert JackettClient._parse_size_string(None, "invalid") == 0

    def test_extract_quality_4k(self):
        assert JackettClient._extract_quality(None, "Movie 2023 4K BluRay") == "4K"

    def test_extract_quality_720p(self):
        result = JackettClient._extract_quality(None, "Movie 720p WEB-DL")
        assert result.upper() == "720P"

    def test_extract_quality_unknown(self):
        assert JackettClient._extract_quality(None, "Movie") == "Calidad desconocida"

    def test_extract_language_spanish(self):
        assert JackettClient._extract_language(None, "Movie SPANISH") == "Español"

    def test_extract_language_latin(self):
        assert JackettClient._extract_language(None, "Movie LATIN") == "Latino"

    def test_extract_language_english(self):
        assert JackettClient._extract_language(None, "Movie ENGLISH") == "Inglés"

    def test_extract_language_multi(self):
        assert (
            JackettClient._extract_language(None, "Movie SPANISH ENGLISH")
            == "Multiidioma"
        )

    def test_map_category_movies(self):
        assert JackettClient._map_category(None, ["movies"]) == "Películas"

    def test_map_category_tv(self):
        assert JackettClient._map_category(None, ["tv"]) == "Series"

    def test_map_category_empty(self):
        assert JackettClient._map_category(None, []) == "Películas"

    def test_map_category_unknown(self):
        assert JackettClient._map_category(None, ["unknown"]) == "Películas"

    def test_format_results_for_frontend(self):
        with patch(
            "src.adapters.outgoing.services.jackett.client.settings"
        ) as mock_settings:
            mock_settings.JACKETT_URL = "http://localhost:9117"
            mock_settings.JACKETT_API_KEY = "test_key"
            mock_settings.JACKETT_TIMEOUT = 30
            client = JackettClient()

            results = [
                JackettSearchResult(
                    guid="123",
                    title="Test Movie 2023 1080p BluRay",
                    indexer="RARBG",
                    size=1500000000,
                    seeders=100,
                    leechers=50,
                    categories=["movies"],
                )
            ]

            formatted = client.format_results_for_frontend(results)
            assert len(formatted) == 1
            assert formatted[0]["category"] == "Películas"


class TestJackettConstants:
    def test_category_mapping(self):
        assert CATEGORY_MAPPING["movies"] == "Películas"
        assert CATEGORY_MAPPING["tv"] == "Series"
        assert CATEGORY_MAPPING["documentaries"] == "Documentales"

    def test_quality_patterns(self):
        assert len(QUALITY_PATTERNS) > 0
        assert any("2160p" in p for p in QUALITY_PATTERNS)

    def test_language_patterns(self):
        assert "Español" in LANGUAGE_PATTERNS
        assert "Latino" in LANGUAGE_PATTERNS
        assert "Inglés" in LANGUAGE_PATTERNS
