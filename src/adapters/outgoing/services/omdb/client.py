"""
Adaptador de salida - Cliente OMDB
Implementación de IMetadataService usando la API de OMDB
"""
import os
import re
import requests
from typing import Optional, Dict, List
from src.core.ports.services import IMetadataService


class OMDBMetadataService(IMetadataService):
    """Servicio de metadatos usando OMDB"""
    
    BASE_URL = "http://www.omdbapi.com/"
    
    def __init__(self, api_key: str = None, language: str = 'es'):
        """
        Inicializa el servicio
        
        Args:
            api_key: Clave API de OMDB
            language: Idioma de los resultados
        """
        self._api_key = api_key or os.environ.get('OMDB_API_KEY')
        self._language = language or os.environ.get('OMDB_LANGUAGE', 'es')
        self._session = requests.Session()
    
    def is_available(self) -> bool:
        """Verifica si el servicio está disponible"""
        return self._api_key is not None
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """Realiza una petición a la API"""
        if not self._api_key:
            return None
        
        try:
            params['apikey'] = self._api_key
            if self._language:
                params['lang'] = self._language
            
            response = self._session.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('Response') == 'False':
                return None
            
            return data
        
        except Exception:
            return None
    
    def get_movie_metadata(self, title: str, year: Optional[int] = None) -> Optional[Dict]:
        """Obtiene metadatos de una película"""
        params = {
            't': title,
            'plot': 'full',
            'r': 'json'
        }
        
        if year:
            params['y'] = year
        
        return self._make_request(params)
    
    def get_serie_metadata(self, serie_name: str) -> Optional[Dict]:
        """Obtiene metadatos de una serie"""
        params = {
            't': serie_name,
            'type': 'series',
            'plot': 'full',
            'r': 'json'
        }
        
        return self._make_request(params)
    
    def search_movies(self, query: str) -> List[Dict]:
        """Busca películas por título"""
        params = {
            's': query,
            'type': 'movie',
            'r': 'json'
        }
        
        data = self._make_request(params)
        
        if data and data.get('Search'):
            return data['Search']
        return []
    
    def get_poster_url(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """Obtiene la URL del póster de una película"""
        movie_data = self.get_movie_metadata(title, year)
        
        if movie_data and movie_data.get('Poster') != 'N/A':
            poster = movie_data.get('Poster')
            return f"/proxy-image?url={requests.utils.quote(poster)}"
        
        return None
    
    def get_serie_poster_url(self, serie_name: str) -> Optional[str]:
        """Obtiene la URL del póster de una serie"""
        serie_data = self.get_serie_metadata(serie_name)
        
        if serie_data and serie_data.get('Poster') != 'N/A':
            poster = serie_data.get('Poster')
            return f"/proxy-image?url={requests.utils.quote(poster)}"
        
        return None

    # Alias para compatibilidad con rutas
    def get_movie_thumbnail(self, title: str, year: Optional[int] = None) -> Optional[str]:
        """Alias de get_poster_url para compatibilidad"""
        return self.get_poster_url(title, year)

    def get_serie_poster(self, serie_name: str) -> Optional[str]:
        """Alias de get_serie_poster_url para compatibilidad"""
        return self.get_serie_poster_url(serie_name)
