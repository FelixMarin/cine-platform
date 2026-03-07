"""
Tests para el cliente de Transmission
"""
import pytest
import base64
from unittest.mock import MagicMock, patch, PropertyMock


class TestTransmissionClient:
    """Tests para TransmissionClient"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock de requests.Session"""
        with patch('src.adapters.outgoing.services.transmission.client.requests.Session') as mock:
            session = MagicMock()
            mock.return_value = session
            yield session
    
    @pytest.fixture
    def transmission_client(self, mock_session):
        """Cliente de Transmission para tests"""
        from src.adapters.outgoing.services.transmission.client import TransmissionClient
        # Mock de settings
        with patch('src.adapters.outgoing.services.transmission.client.settings') as mock_settings:
            mock_settings.TRANSMISSION_RPC_URL = 'http://localhost:9091/transmission/rpc'
            mock_settings.TRANSMISSION_USERNAME = 'transmission'
            mock_settings.TRANSMISSION_PASSWORD = 'transmission'
            mock_settings.UPLOAD_FOLDER = '/tmp/uploads'
            mock_settings.MOVIES_BASE_PATH = '/tmp/movies'
            
            client = TransmissionClient()
            client._session = mock_session
            return client
    
    def test_add_torrent_with_magnet_link(self, transmission_client, mock_session):
        """Test: añadir torrent con magnet link"""
        # Arrange
        magnet_url = "magnet:?xt=urn:btih:611a46905d24ad040cdc7809d1436683aa9110ac&dn=f1-la-pelicula"
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 123,
                    'name': 'f1-la-pelicula',
                    'hashString': '611a46905d24ad040cdc7809d1436683aa9110ac'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(magnet_url)
        
        # Assert
        assert result['id'] == 123
        assert result['name'] == 'f1-la-pelicula'
        
        # Verificar que se usó el campo filename para magnets
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'filename' in arguments
        assert arguments['filename'] == magnet_url
        assert 'metainfo' not in arguments
    
    def test_add_torrent_with_magnet_link_with_whitespace(self, transmission_client, mock_session):
        """Test: añadir torrent con magnet link que tiene espacios al inicio/final"""
        # Arrange
        magnet_url = "  magnet:?xt=urn:btih:611a46905d24ad040cdc7809d1436683aa9110ac&dn=test  "
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 124,
                    'name': 'test',
                    'hashString': '611a46905d24ad040cdc7809d1436683aa9110ac'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(magnet_url)
        
        # Assert
        assert result['id'] == 124
        
        # Verificar que se limpió el whitespace
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'filename' in arguments
        # La URL debería tener los espacios al inicio/final removidos
        assert arguments['filename'].startswith('magnet:')
        assert not arguments['filename'].startswith(' ')
        assert not arguments['filename'].endswith(' ')
    
    def test_add_torrent_with_magnet_link_with_invisible_chars(self, transmission_client, mock_session):
        """Test: añadir torrent con magnet link que tiene caracteres invisibles"""
        # Arrange - Simular caracter invisible (BOM u otro)
        magnet_url = "\ufeffmagnet:?xt=urn:btih:611a46905d24ad040cdc7809d1436683aa9110ac&dn=test"
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 125,
                    'name': 'test',
                    'hashString': '611a46905d24ad040cdc7809d1436683aa9110ac'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(magnet_url)
        
        # Assert
        assert result['id'] == 125
        
        # Verificar que se eliminaron los caracteres invisibles
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'filename' in arguments
        assert arguments['filename'].startswith('magnet:')
    
    @patch('src.adapters.outgoing.services.transmission.client.requests.get')
    def test_add_torrent_with_http_url(self, mock_requests_get, transmission_client, mock_session):
        """Test: añadir torrent con URL HTTP"""
        # Arrange
        http_url = "https://example.com/torrent.torrent"
        
        # Mock de la descarga del torrent (respuesta 200 directa, sin redirect)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = b"fake torrent content"
        mock_response.raise_for_status = MagicMock()
        mock_response.url = http_url  # URL final sin redirect
        mock_requests_get.return_value = mock_response
        
        # Mock de la respuesta de Transmission
        mock_transmission_response = MagicMock()
        mock_transmission_response.status_code = 200
        mock_transmission_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 126,
                    'name': 'torrent.torrent',
                    'hashString': 'abc123'
                }
            }
        }
        mock_session.post.return_value = mock_transmission_response
        
        # Act
        result = transmission_client.add_torrent(http_url)
        
        # Assert
        assert result['id'] == 126
        
        # Verificar que se hizo la petición HTTP (sin redirects primero)
        mock_requests_get.assert_called_once_with(http_url, timeout=30, allow_redirects=False)
        
        # Verificar que se usó el campo metainfo
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'metainfo' in arguments
        assert 'filename' not in arguments
    
    @patch('src.adapters.outgoing.services.transmission.client.requests.get')
    def test_add_torrent_with_http_url_no_connection_adapters_error(self, mock_requests_get, transmission_client, mock_session):
        """Test: verificar que NO ocurre error 'No connection adapters' con magnet"""
        # Arrange - Este test verifica que un magnet no pase por requests.get
        magnet_url = "magnet:?xt=urn:btih:test"
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 127,
                    'name': 'test',
                    'hashString': 'testhash'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(magnet_url)
        
        # Assert - requests.get NO debe ser llamado para magnet links
        mock_requests_get.assert_not_called()
        assert result['id'] == 127
    
    def test_add_torrent_with_base64_metainfo(self, transmission_client, mock_session):
        """Test: añadir torrent con metainfo en base64"""
        # Arrange
        base64_torrent = "base64encodedtorrentdata"
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 128,
                    'name': 'torrent',
                    'hashString': 'hash123'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(base64_torrent)
        
        # Assert
        assert result['id'] == 128
        
        # Verificar que se usó el campo metainfo
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'metainfo' in arguments
        assert arguments['metainfo'] == base64_torrent
    
    def test_add_torrent_with_category(self, transmission_client, mock_session):
        """Test: añadir torrent con categoría"""
        # Arrange
        magnet_url = "magnet:?xt=urn:btih:test"
        category = "Acción"
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 129,
                    'name': 'test',
                    'hashString': 'testhash'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(magnet_url, category=category)
        
        # Assert
        assert result['id'] == 129
        assert result['category'] == category
        
        # Verificar que se envió la categoría como label
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'labels' in arguments
        assert arguments['labels'] == [category]
    
    @patch('os.makedirs')
    def test_add_torrent_with_download_dir(self, mock_makedirs, transmission_client, mock_session):
        """Test: añadir torrent con directorio de descarga"""
        # Arrange
        magnet_url = "magnet:?xt=urn:btih:test"
        download_dir = "/custom/path"
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 130,
                    'name': 'test',
                    'hashString': 'testhash'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(magnet_url, download_dir=download_dir)
        
        # Assert
        assert result['id'] == 130
        assert result['download_dir'] == download_dir
        
        # Verificar que se usó el directorio correcto
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert arguments['download-dir'] == download_dir
    
    def test_add_torrent_paused(self, transmission_client, mock_session):
        """Test: añadir torrent pausado"""
        # Arrange
        magnet_url = "magnet:?xt=urn:btih:test"
        
        # Mock de la respuesta de Transmission
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 131,
                    'name': 'test',
                    'hashString': 'testhash'
                }
            }
        }
        mock_session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_torrent(magnet_url, paused=True)
        
        # Assert
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert arguments['paused'] is True


class TestTransmissionClientEdgeCases:
    """Tests para casos edge del TransmissionClient"""
    
    @pytest.fixture
    def transmission_client(self):
        """Cliente de Transmission para tests"""
        from src.adapters.outgoing.services.transmission.client import TransmissionClient
        with patch('src.adapters.outgoing.services.transmission.client.requests.Session') as mock:
            with patch('src.adapters.outgoing.services.transmission.client.settings') as mock_settings:
                mock_settings.TRANSMISSION_RPC_URL = 'http://localhost:9091/transmission/rpc'
                mock_settings.TRANSMISSION_USERNAME = 'transmission'
                mock_settings.TRANSMISSION_PASSWORD = 'transmission'
                mock_settings.UPLOAD_FOLDER = '/tmp/uploads'
                mock_settings.MOVIES_BASE_PATH = '/tmp/movies'
                
                client = TransmissionClient()
                client._session = MagicMock()
                return client
    
    def test_add_magnet_alias(self, transmission_client):
        """Test: add_magnet es un alias de add_torrent"""
        # Arrange
        magnet_url = "magnet:?xt=urn:btih:test"
        
        # Mock
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 200,
                    'name': 'test',
                    'hashString': 'testhash'
                }
            }
        }
        transmission_client._session.post.return_value = mock_response
        
        # Act
        result = transmission_client.add_magnet(magnet_url, category="Test")
        
        # Assert
        assert result['id'] == 200
    
    def test_add_torrent_https_url(self, transmission_client):
        """Test: añadir torrent con URL HTTPS"""
        # Arrange
        https_url = "https://example.com/torrent.torrent"
        
        # Mock de requests.get
        with patch('src.adapters.outgoing.services.transmission.client.requests.get') as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.content = b"torrent data"
            mock_response.raise_for_status = MagicMock()
            mock_get.return_value = mock_response
            
            # Mock de Transmission
            mock_transmission_response = MagicMock()
            mock_transmission_response.status_code = 200
            mock_transmission_response.json.return_value = {
                'result': 'success',
                'arguments': {
                    'torrent-added': {
                        'id': 201,
                        'name': 'torrent',
                        'hashString': 'hash'
                    }
                }
            }
            transmission_client._session.post.return_value = mock_transmission_response
            
            # Act
            result = transmission_client.add_torrent(https_url)
            
            # Assert
            assert result['id'] == 201
            mock_get.assert_called_once()
            call_url = mock_get.call_args[0][0]
            assert call_url.startswith('https://')


class TestTorrentDownload:
    """Tests para la clase TorrentDownload"""
    
    def test_torrent_download_to_dict(self):
        """Test: conversión a diccionario"""
        from src.adapters.outgoing.services.transmission.client import TorrentDownload
        
        torrent = TorrentDownload(
            id=1,
            name="Test Movie",
            hash_string="abc123",
            status=4,
            progress=0.5,
            size_when_done=1000000,
            downloaded_ever=500000,
            upload_ratio=0.1,
            rate_upload=1000,
            rate_download=5000,
            eta=3600,
            added_date=1234567890,
            magnet_link="magnet:?xt=test",
            files=[],
            category="Acción",
            download_dir="/downloads"
        )
        
        result = torrent.to_dict()
        
        assert result['id'] == 1
        assert result['name'] == "Test Movie"
        assert result['hash'] == "abc123"
        assert result['status'] == 4
        assert result['progress'] == 50.0  # 0.5 * 100
        assert result['category'] == "Acción"
    
    def test_torrent_download_format_size(self):
        """Test: formateo de tamaño"""
        from src.adapters.outgoing.services.transmission.client import TorrentDownload
        
        # Test bytes
        result = TorrentDownload._format_size(500)
        assert "B" in result
        
        # Test KB
        result = TorrentDownload._format_size(2048)
        assert "KB" in result
        
        # Test MB
        result = TorrentDownload._format_size(2048 * 1024)
        assert "MB" in result
    
    def test_torrent_download_format_eta(self):
        """Test: formateo de tiempo restante"""
        from src.adapters.outgoing.services.transmission.client import TorrentDownload
        
        # Test segundos
        result = TorrentDownload._format_eta(30)
        assert "s" in result
        
        # Test minutos
        result = TorrentDownload._format_eta(120)
        assert "m" in result
        
        # Test horas
        result = TorrentDownload._format_eta(3600)
        assert "h" in result
        
        # Test infinito
        result = TorrentDownload._format_eta(-1)
        assert "∞" in result


class TestProwlarrRedirects:
    """Tests para el manejo de redirecciones de Prowlarr"""
    
    @pytest.fixture
    def mock_session(self):
        """Mock de requests.Session"""
        with patch('src.adapters.outgoing.services.transmission.client.requests.Session') as mock:
            session = MagicMock()
            mock.return_value = session
            yield session
    
    @pytest.fixture
    def transmission_client(self, mock_session):
        """Cliente de Transmission para tests"""
        from src.adapters.outgoing.services.transmission.client import TransmissionClient
        with patch('src.adapters.outgoing.services.transmission.client.settings') as mock_settings:
            mock_settings.TRANSMISSION_RPC_URL = 'http://localhost:9091/transmission/rpc'
            mock_settings.TRANSMISSION_USERNAME = 'transmission'
            mock_settings.TRANSMISSION_PASSWORD = 'transmission'
            mock_settings.UPLOAD_FOLDER = '/tmp/uploads'
            mock_settings.MOVIES_BASE_PATH = '/tmp/movies'
            
            client = TransmissionClient()
            client._session = mock_session
            return client
    
    @patch('src.adapters.outgoing.services.transmission.client.requests.get')
    @patch('os.makedirs')
    def test_add_torrent_prowlarr_redirect_to_magnet(self, mock_makedirs, mock_requests_get, transmission_client, mock_session):
        """Test: URL de Prowlarr que redirige a magnet (301)"""
        # Arrange - URL de Prowlarr típica
        prowlarr_url = "http://prowlarr:9696/1/download?apikey=test123&file=movie"
        magnet_url = "magnet:?xt=urn:btih:611a46905d24ad040cdc7809d1436683aa9110ac&dn=f1"
        
        # Mock de la respuesta de Prowlarr (301 redirect a magnet)
        mock_response_301 = MagicMock()
        mock_response_301.status_code = 301
        mock_response_301.headers = {'Location': magnet_url}
        
        # Configurar el mock para devolver不同的 respuestas en llamadas последовательны
        mock_requests_get.side_effect = [mock_response_301]  # Primera llamada (sin redirect)
        
        # Mock de la respuesta de Transmission
        mock_transmission_response = MagicMock()
        mock_transmission_response.status_code = 200
        mock_transmission_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 300,
                    'name': 'f1',
                    'hashString': '611a46905d24ad040cdc7809d1436683aa9110ac'
                }
            }
        }
        mock_session.post.return_value = mock_transmission_response
        
        # Act
        result = transmission_client.add_torrent(prowlarr_url)
        
        # Assert
        assert result['id'] == 300
        
        # Verificar que se usó el campo filename (para magnets)
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'filename' in arguments
        assert arguments['filename'] == magnet_url
        assert 'metainfo' not in arguments
    
    @patch('src.adapters.outgoing.services.transmission.client.requests.get')
    @patch('os.makedirs')
    def test_add_torrent_prowlarr_redirect_to_torrent_file(self, mock_makedirs, mock_requests_get, transmission_client, mock_session):
        """Test: URL de Prowlarr que redirige a archivo .torrent (301)"""
        # Arrange - URL de Prowlarr que devuelve un archivo torrent
        prowlarr_url = "http://prowlarr:9696/1/download?apikey=test123&file=movie"
        torrent_url = "https://example.com/torrents/movie.torrent"
        torrent_content = b"fake torrent file content"
        
        # Mock de la respuesta de Prowlarr (301 redirect a torrent)
        mock_response_301 = MagicMock()
        mock_response_301.status_code = 301
        mock_response_301.headers = {'Location': torrent_url}
        
        # Mock de la respuesta del torrent
        mock_response_torrent = MagicMock()
        mock_response_torrent.status_code = 200
        mock_response_torrent.content = torrent_content
        mock_response_torrent.raise_for_status = MagicMock()
        
        mock_requests_get.side_effect = [mock_response_301, mock_response_torrent]
        
        # Mock de la respuesta de Transmission
        mock_transmission_response = MagicMock()
        mock_transmission_response.status_code = 200
        mock_transmission_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 301,
                    'name': 'movie.torrent',
                    'hashString': 'hash123'
                }
            }
        }
        mock_session.post.return_value = mock_transmission_response
        
        # Act
        result = transmission_client.add_torrent(prowlarr_url)
        
        # Assert
        assert result['id'] == 301
        
        # Verificar que se usó el campo metainfo (para archivos torrent)
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'metainfo' in arguments
        assert 'filename' not in arguments
    
    @patch('src.adapters.outgoing.services.transmission.client.requests.get')
    @patch('os.makedirs')
    def test_add_torrent_http_url_no_redirect(self, mock_makedirs, mock_requests_get, transmission_client, mock_session):
        """Test: URL HTTP directa sin redirecciones (200)"""
        # Arrange
        direct_url = "https://example.com/torrents/movie.torrent"
        torrent_content = b"torrent content"
        
        # Mock de la respuesta directa (200, sin redirect)
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.content = torrent_content
        mock_response.raise_for_status = MagicMock()
        mock_response.url = direct_url  # Sin redirect
        mock_requests_get.return_value = mock_response
        
        # Mock de Transmission
        mock_transmission_response = MagicMock()
        mock_transmission_response.status_code = 200
        mock_transmission_response.json.return_value = {
            'result': 'success',
            'arguments': {
                'torrent-added': {
                    'id': 302,
                    'name': 'movie',
                    'hashString': 'hash'
                }
            }
        }
        mock_session.post.return_value = mock_transmission_response
        
        # Act
        result = transmission_client.add_torrent(direct_url)
        
        # Assert
        assert result['id'] == 302
        
        # Verificar que se usó metainfo
        call_args = mock_session.post.call_args
        arguments = call_args.kwargs.get('json', call_args[1].get('json', {})).get('arguments', {})
        assert 'metainfo' in arguments
