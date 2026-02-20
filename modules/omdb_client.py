"""
Cliente para la API de OMDb (The Open Movie Database)
Obtiene información de películas desde IMDb con soporte multi-idioma
"""
import os
import re
import requests
from typing import Optional, Dict, Any, List
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

class OMDBClient:
    """Cliente para la API de OMDb con soporte multi-idioma"""
    
    BASE_URL = "http://www.omdbapi.com/"
    
    def __init__(self, api_key: str = None, language: str = 'es'):
        """
        Inicializa el cliente de OMDb
        
        Args:
            api_key: Clave API de OMDb (si no se proporciona, se busca en entorno)
            language: Idioma de los resultados ('es' para español, 'en' para inglés)
        """
        self.api_key = api_key or os.environ.get('OMDB_API_KEY')
        if not self.api_key:
            logger.error("❌ OMDB_API_KEY no está configurada")
            # No lanzamos excepción para que la app funcione sin API
            self.api_key = None
        
        self.language = language or os.environ.get('OMDB_LANGUAGE', 'es')
        self.session = requests.Session()
        logger.info(f"✅ Cliente OMDb inicializado (idioma: {self.language})")
    
    def _make_request(self, params: Dict) -> Optional[Dict]:
        """
        Realiza una petición a la API de OMDb
        
        Args:
            params: Parámetros de la petición
            
        Returns:
            Diccionario con la respuesta o None si hay error
        """
        if not self.api_key:
            return None
        
        try:
            # Añadir API key a los parámetros
            params['apikey'] = self.api_key
            
            # Añadir idioma
            if self.language:
                params['lang'] = self.language
            
            response = self.session.get(
                self.BASE_URL,
                params=params,
                timeout=10
            )
            response.raise_for_status()
            
            data = response.json()
            
            # OMDb devuelve {'Response': 'False'} cuando no encuentra resultados
            if data.get('Response') == 'False':
                logger.debug(f"OMDb: No se encontraron resultados - {data.get('Error')}")
                return None
            
            return data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"❌ Error en petición a OMDb: {e}")
            return None
        except ValueError as e:
            logger.error(f"❌ Error decodificando JSON de OMDb: {e}")
            return None
    
    def search_by_title(self, title: str, year: int = None) -> Optional[Dict]:
        """
        Busca una película por título
        
        Args:
            title: Título de la película
            year: Año de estreno (opcional, ayuda a desambiguar)
            
        Returns:
            Datos de la película o None si no se encuentra
        """
        params = {
            't': title,
            'plot': 'full',
            'r': 'json'
        }
        
        if year:
            params['y'] = year
        
        logger.info(f"🔍 Buscando en OMDb: {title}" + (f" ({year})" if year else ""))
        return self._make_request(params)
    
    def search_by_id(self, imdb_id: str) -> Optional[Dict]:
        """
        Busca una película por su ID de IMDb
        
        Args:
            imdb_id: ID de IMDb (ej: tt1375666)
            
        Returns:
            Datos de la película o None si no se encuentra
        """
        params = {
            'i': imdb_id,
            'plot': 'full',
            'r': 'json'
        }
        
        logger.info(f"🔍 Buscando en OMDb por ID: {imdb_id}")
        return self._make_request(params)
    
    def search_multi(self, title: str) -> List[Dict]:
        """
        Busca múltiples resultados por título (para desambiguar)
        
        Args:
            title: Título de la película
            
        Returns:
            Lista de resultados (vacía si no hay)
        """
        params = {
            's': title,
            'type': 'movie',
            'r': 'json'
        }
        
        logger.info(f"🔍 Búsqueda múltiple en OMDb: {title}")
        data = self._make_request(params)
        
        if data and data.get('Search'):
            return data['Search']
        return []
    
    def parse_filename(self, filename: str) -> tuple:
        """
        Parsea el nombre del archivo para extraer título y año
        Formato esperado: nombre-(año)-optimized.mkv
        Ejemplo: multiple-(2016)-optimized.mkv -> ("multiple", 2016)
        """
        # Quitar extensión
        name_without_ext = filename.rsplit('.', 1)[0]
        
        # Quitar sufijo -optimized si existe
        name_without_suffix = name_without_ext.replace('-optimized', '')
        
        # Buscar año entre paréntesis
        year_match = re.search(r'\((\d{4})\)', name_without_suffix)
        year = int(year_match.group(1)) if year_match else None
        
        # Quitar el año del título
        if year:
            title = re.sub(r'\(\d{4}\)', '', name_without_suffix).strip('-').strip()
        else:
            title = name_without_suffix
        
        # Limpiar el título (reemplazar guiones por espacios)
        clean_title = title.replace('-', ' ').strip()
        
        return clean_title, year
    
    def _extract_year(self, year_str: str) -> int:
        """Extrae el año de un string como '2016' o '2016–2018'"""
        if not year_str or year_str == 'N/A':
            return 0
        match = re.search(r'\d{4}', year_str)
        return int(match.group()) if match else 0
    
    def get_poster_with_fallback(self, poster_url: str) -> list:
        """Sistema ultra robusto para obtener pósters con múltiples fallbacks"""
        if not poster_url or poster_url == 'N/A':
            return ['/static/images/default-poster.jpg']
        
        clean_url = poster_url.replace('https://', '').replace('http://', '')
        
        proxies = [
            f"/proxy-image?url={requests.utils.quote(poster_url)}",
            f"/proxy-image?url={requests.utils.quote(poster_url)}&retry=1",
            '/static/images/default-poster.jpg'
        ]
        
        return proxies
        
    def format_movie_info(self, movie_data: Dict) -> Dict:
        """
        Formatea los datos de OMDb para mostrarlos en la plantilla
        
        Args:
            movie_data: Datos crudos de OMDb
            
        Returns:
            Diccionario formateado para la plantilla
        """
        if not movie_data:
            return {}
        
        # Parsear ratings
        ratings = []
        for rating in movie_data.get('Ratings', []):
            source = rating.get('Source', '')
            value = rating.get('Value', '')
            if 'Rotten Tomatoes' in source:
                ratings.append(f"🍅 {value}")
            elif 'Metacritic' in source:
                ratings.append(f"📊 {value}")
            elif 'Internet Movie Database' in source:
                ratings.append(f"⭐ {value}")
        
        # Parsear género
        genres = [g.strip() for g in movie_data.get('Genre', '').split(',') if g.strip()]
        
        # Parsear reparto
        cast = [a.strip() for a in movie_data.get('Actors', '').split(',')[:5] if a.strip()]
        
        # Procesar póster
        poster = movie_data.get('Poster')
        poster_proxies = self.get_poster_with_fallback(poster)
        
        # Construir información formateada
        info = {
            'title': movie_data.get('Title'),
            'year': movie_data.get('Year'),
            'released': movie_data.get('Released'),
            'runtime': movie_data.get('Runtime'),
            'genre': movie_data.get('Genre'),
            'genres': genres,
            'director': movie_data.get('Director'),
            'writer': movie_data.get('Writer'),
            'actors': movie_data.get('Actors'),
            'cast': cast,
            'plot': movie_data.get('Plot'),
            'language': movie_data.get('Language'),
            'country': movie_data.get('Country'),
            'awards': movie_data.get('Awards'),
            'poster': poster_proxies,
            'poster_original': poster,
            'ratings': ratings,
            'imdb_rating': movie_data.get('imdbRating'),
            'imdb_votes': movie_data.get('imdbVotes'),
            'imdb_id': movie_data.get('imdbID'),
            'type': movie_data.get('Type'),
            'dvd': movie_data.get('DVD'),
            'box_office': movie_data.get('BoxOffice'),
            'production': movie_data.get('Production'),
            'website': movie_data.get('Website'),
        }
        
        # Limpiar valores None o 'N/A'
        for key, value in info.items():
            if value == 'N/A' or value is None:
                info[key] = None
        
        return info
    
    def get_movie_info(self, filename: str) -> Dict:
        """
        Busca información de la película a partir del nombre del archivo
        El nombre debe tener formato: nombre-(año)-optimized.mkv
        
        Args:
            filename: Nombre completo del archivo (ej: multiple-(2016)-optimized.mkv)
            
        Returns:
            Información formateada de la película o dict vacío
        """
        # Extraer título y año del nombre del archivo
        title, year = self.parse_filename(filename)
        
        if not title:
            logger.warning(f"❌ No se pudo extraer título de: {filename}")
            return {}
        
        logger.info(f"🔍 Buscando en OMDb: '{title}'" + (f" (año {year})" if year else ""))
        
        movie_data = None
        
        # 1. Intentar búsqueda exacta con año (si lo tenemos)
        if year:
            movie_data = self.search_by_title(title, year)
            if movie_data:
                logger.info(f"✅ Encontrada con año: {movie_data.get('Title')} ({movie_data.get('Year')})")
                return self.format_movie_info(movie_data)
        
        # 2. Intentar búsqueda exacta sin año
        movie_data = self.search_by_title(title)
        if movie_data:
            # Verificar que el año coincida aproximadamente (opcional)
            if year and movie_data.get('Year'):
                movie_year = self._extract_year(movie_data.get('Year'))
                if abs(movie_year - year) <= 1:
                    logger.info(f"✅ Encontrada con año aproximado: {movie_data.get('Title')} ({movie_data.get('Year')})")
                    return self.format_movie_info(movie_data)
            else:
                logger.info(f"✅ Encontrada sin año: {movie_data.get('Title')} ({movie_data.get('Year')})")
                return self.format_movie_info(movie_data)
        
        # 3. Si no encuentra, intentar búsqueda múltiple y coger el primero
        results = self.search_multi(title)
        if results:
            first_result = results[0]
            logger.info(f"✅ Usando primer resultado múltiple: {first_result.get('Title')} ({first_result.get('Year')})")
            imdb_id = first_result.get('imdbID')
            if imdb_id:
                movie_data = self.search_by_id(imdb_id)
                if movie_data:
                    return self.format_movie_info(movie_data)
        
        logger.info(f"❌ No se encontró información para: {title}")
        return {}

    def get_movie_thumbnail(self, title: str, year: int = None) -> str:
        """
        Obtiene SOLO la URL del póster/thumbnail de la película
        """
        if not self.api_key:
            return None
        
        movie_data = None
        
        # 1. Intentar con año exacto
        if year:
            movie_data = self.search_by_title(title, year)
        
        # 2. Intentar sin año
        if not movie_data:
            movie_data = self.search_by_title(title)
        
        # 3. Intentar búsqueda múltiple
        if not movie_data:
            results = self.search_multi(title)
            if results and len(results) > 0:
                # Intentar filtrar por año si tenemos
                if year:
                    for result in results:
                        result_year = self._extract_year(result.get('Year', ''))
                        if result_year and abs(result_year - year) <= 1:
                            imdb_id = result.get('imdbID')
                            movie_data = self.search_by_id(imdb_id)
                            break
                
                # Si no, coger el primero
                if not movie_data:
                    imdb_id = results[0].get('imdbID')
                    movie_data = self.search_by_id(imdb_id)
        
        if movie_data and movie_data.get('Poster') and movie_data.get('Poster') != 'N/A':
            poster = movie_data.get('Poster')
            return f"/proxy-image?url={requests.utils.quote(poster)}"
        
        return None

    def get_serie_poster(self, serie_name: str) -> str:
        """
        Obtiene el póster de una serie.
        OMDB trata las series igual que las películas, con 'type': 'series'
        """
        if not self.api_key:
            return None
        
        # Buscar la serie
        movie_data = self.search_by_title(serie_name)
        
        # Verificar que es una serie (opcional)
        if movie_data and movie_data.get('Type') == 'series':
            poster = movie_data.get('Poster')
            if poster and poster != 'N/A':
                return f"/proxy-image?url={requests.utils.quote(poster)}"
        
        # Si no encuentra, intentar búsqueda múltiple
        results = self.search_multi(serie_name)
        for result in results:
            if result.get('Type') == 'series':
                imdb_id = result.get('imdbID')
                if imdb_id:
                    movie_data = self.search_by_id(imdb_id)
                    if movie_data and movie_data.get('Poster') and movie_data.get('Poster') != 'N/A':
                        poster = movie_data.get('Poster')
                        return f"/proxy-image?url={requests.utils.quote(poster)}"
        
        return None        