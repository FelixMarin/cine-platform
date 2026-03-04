"""
Cliente para la API de Prowlarr

Prowlarr es un indexador de torrents que permite buscar en múltiples fuentes.
Este cliente proporciona métodos para buscar películas y obtener información de los resultados.
"""
import logging
import re
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass
from datetime import datetime, timedelta
from src.infrastructure.config.settings import settings


logger = logging.getLogger(__name__)

# Mapeo de categorías de Prowlarr a carpetas locales
CATEGORY_MAPPING = {
    2070: 'Películas',   # Movies/DVD
    2040: 'Películas',   # Movies/HD
    2050: 'Películas',   # Movies/BluRay
    2030: 'Películas',   # Movies/SD
    2010: 'Películas',   # Movies Foreign
    2000: 'Películas',   # Movies
    5040: 'Series',      # TV/HD
    5030: 'Series',      # TV/SD
    5010: 'Series',      # TV
    5020: 'Series',      # TV Foreign
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
    'Español': [r'\bSPANISH\b', r'\bSPA\b', r'\bCASTELLANO\b', r'\bESPAÑOL\b'],
    'Latino': [r'\bLATIN\b', r'\bLATINO\b', r'\bLAT\b'],
    'Inglés': [r'\bENGLISH\b', r'\bENG\b', r'\bINGLÉS\b', r'\bINGLES\b'],
}


@dataclass
class ProwlarrSearchResult:
    """Resultado de búsqueda de Prowlarr"""
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
    
    def __post_init__(self):
        if self.categories is None:
            self.categories = []
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte el resultado a diccionario para el frontend"""
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
            'categories': self.categories
        }
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Formatea el tamaño en formato legible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


class ProwlarrError(Exception):
    """Excepción para errores de Prowlarr"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class ProwlarrClient:
    """
    Cliente para comunicarse con la API de Prowlarr
    
    Uso:
        client = ProwlarrClient()
        results = client.search_movies("The Matrix")
    """
    
    def __init__(self, url: Optional[str] = None, api_key: Optional[str] = None):
        """
        Inicializa el cliente de Prowlarr
        
        Args:
            url: URL base de Prowlarr (por defecto de settings)
            api_key: API key de Prowlarr (por defecto de settings)
        """
        self.url = url or settings.PROWLARR_URL
        self.api_key = api_key or settings.PROWLARR_API_KEY
        self._session = requests.Session()
        self._session.headers.update({
            'X-Api-Key': self.api_key,
            'Content-Type': 'application/json'
        })
        self._timeout = 30
        
        logger.info(f"[Prowlarr] Cliente inicializado con URL: {self.url}")
    
    def _check_config(self):
        """Verifica que Prowlarr esté configurado"""
        if not self.api_key:
            raise ProwlarrError("Prowlarr API key no configurada")
    
    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict[str, Any]:
        """
        Realiza una petición HTTP a Prowlarr
        
        Args:
            method: Método HTTP (GET, POST, etc.)
            endpoint: Endpoint de la API
            **kwargs: Argumentos adicionales para requests
            
        Returns:
            Respuesta JSON de Prowlarr
            
        Raises:
            ProwlarrError: Si hay un error en la comunicación
        """
        self._check_config()
        
        url = f"{self.url}{endpoint}"
        kwargs.setdefault('timeout', self._timeout)
        
        try:
            response = self._session.request(method, url, **kwargs)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ConnectionError:
            raise ProwlarrError(f"No se pudo conectar a Prowlarr en {self.url}")
        except requests.exceptions.Timeout:
            raise ProwlarrError("Tiempo de espera agotado al conectar con Prowlarr")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            if status_code == 401:
                raise ProwlarrError("API key de Prowlarr inválida", status_code)
            elif status_code == 403:
                raise ProwlarrError("Acceso denegado a Prowlarr", status_code)
            elif status_code == 404:
                raise ProwlarrError("Endpoint no encontrado en Prowlarr", status_code)
            else:
                raise ProwlarrError(f"Error HTTP {status_code} de Prowlarr", status_code)
        except requests.exceptions.RequestException as e:
            raise ProwlarrError(f"Error de comunicación con Prowlarr: {str(e)}")
    
    def search_movies(self, query: str, categories: Optional[List[int]] = None, 
                      limit: int = 20) -> List[ProwlarrSearchResult]:
        """
        Busca películas en Prowlarr
        
        Args:
            query: Término de búsqueda
            categories: Lista de IDs de categorías (2000=Movies, 2010=Movies Foreign, etc.)
            limit: Número máximo de resultados
            
        Returns:
            Lista de resultados de búsqueda
            
        Raises:
            ProwlarrError: Si hay un error en la búsqueda
        """
        if not query or not query.strip():
            logger.warning("[Prowlарr] Búsqueda vacía ignorada")
            return []
        
        logger.info(f"[Prowlarr] Buscando películas: '{query}'")
        
        # Construir query para Prowlarr
        # Prowlarr usa el endpoint /api/v1/search con parámetros específicos
        params = {
            'query': query,
            'type': 'search',
            'limit': limit
        }
        
        # Agregar categorías si se especifican
        if categories:
            params['categories'] = ','.join(map(str, categories))
        
        try:
            # Intentar con el endpoint de búsqueda de Prowlarr v3
            data = self._make_request('GET', '/api/v1/search', params=params)
            
            results = []
            if data and 'results' in data:
                for item in data['results']:
                    result = self._parse_search_result(item)
                    if result:
                        results.append(result)
            elif isinstance(data, list):
                # Si devuelve directamente una lista
                for item in data:
                    result = self._parse_search_result(item)
                    if result:
                        results.append(result)
            
            logger.info(f"[Prowlarr] Encontrados {len(results)} resultados para '{query}'")
            return results[:limit]
            
        except ProwlarrError:
            raise
        except Exception as e:
            logger.error(f"[Prowlarr] Error al buscar: {str(e)}")
            # Devolver lista vacía en lugar de fallar
            return []
    
    def _parse_search_result(self, item: Dict[str, Any]) -> Optional[ProwlarrSearchResult]:
        """
        Parsea un resultado de Prowlarr al formato interno
        
        Args:
            item: Item devuelto por la API de Prowlarr
            
        Returns:
            ProwlarrSearchResult o None si no es válido
        """
        try:
            # Extraer información del resultado
            guid = item.get('guid', '')
            title = item.get('title', item.get('release', ''))
            
            if not title:
                return None
            
            # Extraer URLs
            magnet_url = None
            torrent_url = None
            
            # Prowlarr puede devolver los enlaces de diferentes formas
            if 'magnetUrl' in item:
                magnet_url = item['magnetUrl']
            elif 'infoHash' in item:
                # Construir magnet desde infoHash
                info_hash = item['infoHash']
                title_encoded = requests.utils.quote(title)
                magnet_url = f"magnet:?xt=urn:btih:{info_hash}&dn={title_encoded}"
            
            if 'downloadUrl' in item:
                torrent_url = item['downloadUrl']
            
            # Extraer tamaño
            size = item.get('size', 0)
            if isinstance(size, str):
                # Parsear tamaño si viene como string (ej: "1.5 GB")
                size = self._parse_size_string(size)
            
            # Extraer seeders/leechers
            seeders = item.get('seeders', 0)
            leechers = item.get('leechers', 0)
            
            # Extraer fecha
            publish_date = item.get('publishDate', item.get('date', None))
            
            # Extraer indexador
            indexer = item.get('indexer', item.get('source', 'Unknown'))
            
            # Extraer categorías
            categories = []
            if 'categories' in item:
                categories = [cat.get('name', '') for cat in item['categories']]
            
            return ProwlarrSearchResult(
                guid=guid,
                title=title,
                indexer=indexer,
                size=size,
                seeders=seeders,
                leechers=leechers,
                magnet_url=magnet_url,
                torrent_url=torrent_url,
                publish_date=publish_date,
                categories=categories
            )
            
        except Exception as e:
            logger.warning(f"[Prowlarr] Error al parsear resultado: {str(e)}")
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
        """
        Extrae la calidad del título
        
        Args:
            title: Título del torrent
            
        Returns:
            Calidad detectada o 'Calidad desconocida'
        """
        title_upper = title.upper()
        
        for pattern in QUALITY_PATTERNS:
            if re.search(pattern, title_upper, re.IGNORECASE):
                # Limpiar el patrón para mostrarlo cleanly
                match = re.search(pattern, title_upper, re.IGNORECASE)
                if match:
                    return match.group(0).replace('-', ' ').strip()
        
        return 'Calidad desconocida'
    
    def _extract_language(self, title: str) -> str:
        """
        Detecta el idioma del título
        
        Args:
            title: Título del torrent
            
        Returns:
            Idioma detectado
        """
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
    
    def _map_category(self, categories: List[Dict]) -> str:
        """
        Mapea categorías de Prowlarr a carpeta local
        
        Args:
            categories: Lista de categorías de Prowlarr
            
        Returns:
            Nombre de carpeta local
        """
        if not categories:
            return 'Películas'
        
        for cat in categories:
            cat_id = cat.get('id')
            if cat_id in CATEGORY_MAPPING:
                return CATEGORY_MAPPING[cat_id]
        
        return 'Películas'
    
    def _format_relative_date(self, date_str: Optional[str]) -> str:
        """
        Formatea una fecha como fecha relativa
        
        Args:
            date_str: Fecha en formato ISO
            
        Returns:
            Fecha relativa (ej: 'hace 2 horas')
        """
        if not date_str:
            return 'Fecha desconocida'
        
        try:
            # Intentar parsear la fecha
            if 'Z' in date_str:
                date_str = date_str.replace('Z', '+00:00')
            
            # Intentar diferentes formatos
            for fmt in ['%Y-%m-%dT%H:%M:%S%z', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S', '%Y-%m-%d']:
                try:
                    date = datetime.strptime(date_str[:19], fmt[:19])
                    break
                except ValueError:
                    continue
            else:
                # Si no se puede parsear, devolver la fecha original
                return date_str[:10]
            
            # Calcular diferencia
            now = datetime.now()
            diff = now - date
            
            if diff.days > 365:
                return f"hace {diff.days // 365} año{'s' if diff.days // 365 > 1 else ''}"
            elif diff.days > 30:
                return f"hace {diff.days // 30} mes{'es' if diff.days // 30 > 1 else ''}"
            elif diff.days > 0:
                return f"hace {diff.days} día{'s' if diff.days > 1 else ''}"
            elif diff.seconds > 3600:
                return f"hace {diff.seconds // 3600} hora{'s' if diff.seconds // 3600 > 1 else ''}"
            elif diff.seconds > 60:
                return f"hace {diff.seconds // 60} minuto{'s' if diff.seconds // 60 > 1 else ''}"
            else:
                return "hace un momento"
                
        except Exception:
            return date_str[:10]
    
    def format_results_for_frontend(self, results: List[ProwlarrSearchResult]) -> List[Dict[str, Any]]:
        """
        Formatea los resultados para el frontend
        
        Args:
            results: Lista de resultados de Prowlarr
            
        Returns:
            Lista de resultados formateados
        """
        formatted = []
        
        for result in results:
            # Extraer información
            title = result.title
            full_title = title
            
            # Limpiar título para mostrar
            clean_title = re.sub(r'\s*\[.*?\]\s*', ' ', title)  # Quitar [Edición Especial]
            clean_title = re.sub(r'\s*\(.*?\)\s*', ' ', clean_title)  # Quitar (2023)
            clean_title = clean_title.strip()
            
            # Formatear tamaño
            size_mb = result.size / (1024 * 1024)
            if size_mb >= 1024:
                size_formatted = f"{size_mb / 1024:.2f} GB"
            else:
                size_formatted = f"{size_mb:.2f} MB"
            
            # Determinar si es magnet
            is_magnet = result.magnet_url is not None and result.magnet_url.startswith('magnet:')
            
            # URL de descarga
            download_url = result.magnet_url or result.torrent_url or ''
            
            # Mapear categoría
            category = self._map_category([{'id': cat} for cat in result.categories])
            
            # Formatear resultado
            formatted_result = {
                'id': result.guid or hash(result.title),
                'title': clean_title,
                'fullTitle': full_title,
                'size': size_formatted,
                'seeders': result.seeders if result.seeders else 'Desconocido',
                'leechers': result.leechers if result.leechers else 'Desconocido',
                'indexer': result.indexer,
                'quality': self._extract_quality(title),
                'language': self._extract_language(title),
                'poster': None,  # Prowlarr no devuelve poster por defecto
                'downloadUrl': download_url,
                'isMagnet': is_magnet,
                'category': category,
                'date': self._format_relative_date(result.publish_date),
                'url': download_url,  # Alias para compatibilidad
            }
            
            formatted.append(formatted_result)
        
        logger.info(f"[Prowlarr] Formateados {len(formatted)} resultados para frontend")
        return formatted
    
    def get_indexers(self) -> List[Dict[str, Any]]:
        """
        Obtiene la lista de indexadores configurados en Prowlarr
        
        Returns:
            Lista de indexadores
        """
        logger.info("[Prowlarr] Obteniendo lista de indexadores")
        
        try:
            data = self._make_request('GET', '/api/v1/indexer')
            return data if isinstance(data, list) else []
        except ProwlarrError:
            return []
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión con Prowlarr
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            self._check_config()
            self._make_request('GET', '/api/v1/system/status')
            logger.info("[Prowlarr] Conexión exitosa")
            return True
        except ProwlarrError as e:
            logger.error(f"[Prowlarr] Error de conexión: {e.message}")
            return False
