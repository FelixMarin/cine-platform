"""
Cliente asíncrono para la API de Jackett

Jackett es un indexador de torrents que permite buscar en múltiples fuentes.
Este cliente proporciona métodos para buscar películas y obtener información de los resultados.
Utiliza aiohttp para realizar peticiones asíncronas.
"""
import logging
import re
import aiohttp
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime
from src.infrastructure.config.settings import settings


logger = logging.getLogger(__name__)

# Mapeo de categorías de Jackett a carpetas locales
CATEGORY_MAPPING = {
    'movies': 'Películas',
    'tv': 'Series',
    'documentaries': 'Documentales',
    'music': 'Música',
    'audio': 'Música',
    'software': 'Software',
    'games': 'Juegos',
    'books': 'Libros',
    'anime': 'Anime',
    'xxx': 'Adultos',
}

# Patrones para extraer calidad del título
QUALITY_PATTERNS = [
    r'4K|UHD|2160p',
    r'1080p',
    r'720p',
    r'480p',
    r'BRRip|BRRip',
    r'BluRay|Blu-ray',
    r'WEB-DL|WEBDL|WEB',
    r'DVDRip|DVDrip',
    r'DVD|PDTV|HDTV',
    r'HDRip|HDRip',
    r'HDTV|HDTV',
]

# Detección de idioma en títulos
LANGUAGE_PATTERNS = {
    'Español': [r'\bSPANISH\b', r'\bSPA\b', r'\bCASTELLANO\b', r'\bESPAÑOL\b', r'\bES\b'],
    'Latino': [r'\bLATIN\b', r'\bLATINO\b', r'\bLAT\b'],
    'Inglés': [r'\bENGLISH\b', r'\bENG\b', r'\bINGLÉS\b', r'\bINGLES\b', r'\bEN\b'],
}


@dataclass
class JackettSearchResult:
    """Resultado de búsqueda de Jackett"""
    guid: str
    title: str
    indexer: str
    size: int
    seeders: int
    leechers: int
    magnet_url: Optional[str] = None
    torrent_url: Optional[str] = None
    publish_date: Optional[str] = None
    categories: List[str] = None
    source: str = 'jackett'
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario"""
        return {
            'guid': self.guid,
            'title': self.title,
            'indexer': self.indexer,
            'size': self.size,
            'size_formatted': self._format_size(self.size),
            'seeders': self.seeders,
            'leechers': self.leechers,
            'magnet_url': self.magnet_url,
            'torrent_url': self.torrent_url,
            'publish_date': self.publish_date,
            'categories': self.categories,
            'source': self.source
        }
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Formatea el tamaño en formato legible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


class JackettError(Exception):
    """Excepción para errores de Jackett"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class JackettClient:
    """
    Cliente asíncrono para comunicarse con la API de Jackett
    
    Uso:
        client = JackettClient()
        results = await client.search_movies("The Matrix")
    """
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None, timeout: Optional[int] = None):
        """
        Inicializa el cliente de Jackett
        
        Args:
            url: URL base de Jackett (por defecto de settings)
            api_key: API key de Jackett (por defecto de settings)
            timeout: Timeout en segundos (por defecto de settings)
        """
        self.url = url or settings.JACKETT_URL
        self.api_key = api_key or settings.JACKETT_API_KEY
        self.timeout = timeout or settings.JACKETT_TIMEOUT
        self._session: Optional[aiohttp.ClientSession] = None
        
        logger.info(f"[Jackett] Cliente inicializado con URL: {self.url}, timeout: {self.timeout}s")
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtiene o crea la sesión de aiohttp"""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session
    
    async def close(self):
        """Cierra la sesión de aiohttp"""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _check_config(self):
        """Verifica que Jackett esté configurado"""
        if not self.api_key:
            raise JackettError("Jackett API key no configurada")
    
    async def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Realiza una petición HTTP asíncrona a Jackett
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API
            **kwargs: Argumentos adicionales para aiohttp
            
        Returns:
            Respuesta JSON de Jackett
            
        Raises:
            JackettError: Si hay un error en la comunicación
        """
        self._check_config()
        
        session = await self._get_session()
        
        # Construir URL completa
        url = f"{self.url}{endpoint}"
        
        # Agregar API key como parámetro
        params = kwargs.get('params', {})
        params['apikey'] = self.api_key
        kwargs['params'] = params
        
        # Headers
        kwargs.setdefault('headers', {})
        kwargs['headers']['Content-Type'] = 'application/json'
        
        try:
            async with session.request(method, url, **kwargs) as response:
                if response.status == 401:
                    raise JackettError("API key de Jackett inválida", 401)
                elif response.status == 403:
                    raise JackettError("Acceso denegado a Jackett", 403)
                elif response.status == 404:
                    raise JackettError("Endpoint no encontrado en Jackett", 404)
                elif response.status >= 400:
                    raise JackettError(f"Error HTTP {response.status} de Jackett", response.status)
                
                # Intentar parsear como JSON
                try:
                    return await response.json()
                except aiohttp.ContentTypeError:
                    # Si no es JSON, intentar texto
                    text = await response.text()
                    logger.warning(f"[Jackett] Respuesta no JSON: {text[:200]}")
                    return {'raw': text}
                    
        except aiohttp.ClientConnectorError:
            raise JackettError(f"No se pudo conectar a Jackett en {self.url}")
        except TimeoutError:
            raise JackettError(f"Tiempo de espera agotado al conectar con Jackett ({self.timeout}s)")
        except Exception as e:
            raise JackettError(f"Error de comunicación con Jackett: {str(e)}")
    
    async def search_movies(self, query: str, limit: int = 20) -> List[JackettSearchResult]:
        """
        Busca películas en Jackett de forma asíncrona
        
        Args:
            query: Término de búsqueda
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados de búsqueda
            
        Raises:
            JackettError: Si hay un error en la búsqueda
        """
        if not query or not query.strip():
            logger.warning("[Jackett] Búsqueda vacía ignorada")
            return []
        
        logger.info(f"[Jackett] 🔍 Iniciando búsqueda: '{query}' (límite: {limit})")
        
        # Construir query para Jackett usando el endpoint /api/v2.0/indexers/all/results/torznab
        params = {
            't': 'search',
            'q': query,
            'limit': limit
        }
        
        try:
            # Usar el endpoint de Jackett
            data = await self._make_request('GET', '/api/v2.0/indexers/all/results', params=params)
            
            results = []
            
            # Parsear respuesta de Jackett (formato JSON)
            if data and 'Results' in data:
                for item in data['Results']:
                    result = self._parse_search_result(item)
                    if result:
                        results.append(result)
            elif isinstance(data, list):
                # Si devuelve directamente una lista
                for item in data:
                    result = self._parse_search_result(item)
                    if result:
                        results.append(result)
            
            logger.info(f"[Jackett] Encontrados {len(results)} resultados para '{query}'")
            return results[:limit]
            
        except JackettError:
            raise
        except Exception as e:
            logger.error(f"[Jackett] ❌ Error al buscar: {str(e)}")
            # Devolver lista vacía en lugar de fallar
            return []
    
    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[JackettSearchResult]:
        """
        Parsea un resultado de Jackett al formato interno
        
        Args:
            item: Item devuelto por la API de Jackett
            
        Returns:
            JackettSearchResult o None si no es válido
        """
        try:
            # Extraer información del resultado
            guid = item.get('Guid', item.get('ID', item.get('TrackerId', '')))
            title = item.get('Title', item.get('title', item.get('Name', '')))
            
            if not title:
                return None
            
            # Extraer URLs
            magnet_url = item.get('MagnetUri', item.get('MagnetUrl', None))
            torrent_url = item.get('DownloadUri', item.get('DownloadURL', item.get('Link', None)))
            
            # Si tenemos infoHash pero no magnet, construirlo
            if not magnet_url and 'InfoHash' in item:
                info_hash = item['InfoHash']
                title_encoded = aiohttp.helpers.quote(title)
                magnet_url = f"magnet:?xt=urn:btih:{info_hash}&dn={title_encoded}"
            
            # Extraer tamaño
            size = item.get('Size', item.get('size', 0))
            if isinstance(size, str):
                size = self._parse_size_string(size)
            
            # Extraer seeders/leechers
            seeders = item.get('Seeders', item.get('seeders', 0))
            leechers = item.get('Peers', item.get('Peers', item.get('Leechers', 0)))
            
            # Extraer fecha
            publish_date = item.get('PublishDate', item.get('publishDate', item.get('Date', None)))
            
            # Extraer indexador
            indexer = item.get('Tracker', item.get('indexer', item.get('TrackerName', 'Unknown')))
            
            # Extraer categorías
            categories = []
            if 'Category' in item:
                cat = item['Category']
                if isinstance(cat, list):
                    categories = [str(c) for c in cat]
                else:
                    categories = [str(cat)]
            elif 'Categories' in item:
                categories = item['Categories']
                if isinstance(categories, list):
                    categories = [str(c) if not isinstance(c, str) else c for c in categories]
            
            return JackettSearchResult(
                guid=str(guid),
                title=title,
                indexer=indexer,
                size=size,
                seeders=seeders,
                leechers=leechers,
                magnet_url=magnet_url,
                torrent_url=torrent_url,
                publish_date=publish_date,
                categories=categories,
                source='jackett'
            )
            
        except Exception as e:
            logger.warning(f"[Jackett] Error al parsear resultado: {str(e)}")
            return None
    
    def _parse_size_string(self, size_str: str) -> int:
        """Parsea un string de tamaño a bytes"""
        size_str = size_str.upper().strip()
        
        units = {
            'B': 1,
            'KB': 1024,
            'MB': 1024 ** 2,
            'GB': 1024 ** 3,
            'TB': 1024 ** 4
        }
        
        for unit, multiplier in units.items():
            if unit in size_str:
                try:
                    value = float(size_str.replace(unit, '').strip())
                    return int(value * multiplier)
                except ValueError:
                    return 0
        
        return 0
    
    def _extract_quality(self, title: str) -> str:
        """Extrae la calidad del título"""
        title_upper = title.upper()
        
        for pattern in QUALITY_PATTERNS:
            if re.search(pattern, title_upper, re.IGNORECASE):
                match = re.search(pattern, title_upper, re.IGNORECASE)
                if match:
                    return match.group(0).replace('-', ' ').strip()
        
        return 'Calidad desconocida'
    
    def _extract_language(self, title: str) -> str:
        """Detecta el idioma del título"""
        title_upper = title.upper()
        detected = []
        
        for lang, patterns in LANGUAGE_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, title_upper, re.IGNORECASE):
                    if lang not in detected:
                        detected.append(lang)
                    break
        
        if len(detected) > 1:
            return 'Multiidioma'
        elif len(detected) == 1:
            return detected[0]
        else:
            return 'Desconocido'
    
    def _map_category(self, categories: List[str]) -> str:
        """Mapea categorías de Jackett a carpeta local"""
        if not categories:
            return 'Películas'
        
        for cat in categories:
            cat_lower = str(cat).lower()
            if cat_lower in CATEGORY_MAPPING:
                return CATEGORY_MAPPING[cat_lower]
            # Intentar coincidencia parcial
            for key in CATEGORY_MAPPING:
                if key in cat_lower:
                    return CATEGORY_MAPPING[key]
        
        return 'Películas'
    
    def format_results_for_frontend(self, results: List[JackettSearchResult]) -> List[Dict[str, Any]]:
        """
        Formatea los resultados para el frontend
        
        Args:
            results: Lista de resultados de Jackett
            
        Returns:
            Lista de resultados formateados
        """
        formatted = []
        
        for result in results:
            title = result.title
            full_title = title
            
            # Limpiar título para mostrar
            clean_title = re.sub(r'\s*\[.*?\]\s*', ' ', title)
            clean_title = re.sub(r'\s*\(.*?\)\s*', ' ', clean_title)
            clean_title = clean_title.strip()
            
            # Formatear tamaño
            size_mb = result.size / (1024 * 1024)
            if size_mb >= 1024:
                size_formatted = f"{size_mb / 1024:.2f} GB"
            else:
                size_formatted = f"{size_mb:.2f} MB"
            
            # URL de descarga
            download_url = result.magnet_url or result.torrent_url or ''
            
            # Mapear categoría
            category = self._map_category(result.categories)
            
            # Formatear resultado
            formatted_result = {
                'id': result.guid or hash(result.title),
                'title': clean_title,
                'fullTitle': full_title,
                'size': size_formatted,
                'size_bytes': result.size,
                'seeders': result.seeders if result.seeders else 'Desconocido',
                'leechers': result.leechers if result.leechers else 'Desconocido',
                'indexer': result.indexer,
                'quality': self._extract_quality(title),
                'language': self._extract_language(title),
                'category': category,
                'download_url': download_url,
                'magnet_url': result.magnet_url,
                'torrent_url': result.torrent_url,
                'publish_date': result.publish_date,
                'source': 'jackett',  # Indicar que viene de Jackett
            }
            
            formatted.append(formatted_result)
        
        return formatted
    
    async def test_connection(self) -> bool:
        """
        Prueba la conexión con Jackett
        
        Returns:
            True si la conexión es exitosa
        """
        try:
            # Intentar una búsqueda simple
            await self.search_movies("test", limit=1)
            return True
        except Exception as e:
            logger.error(f"[Jackett] Error de conexión: {str(e)}")
            return False
