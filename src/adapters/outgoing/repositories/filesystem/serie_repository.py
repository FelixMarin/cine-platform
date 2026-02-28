"""
Adaptador de salida - Repositorio de series con Filesystem
Implementación de ISerieRepository escaneando archivos del disco
"""
import os
import re
import time
import unicodedata
from typing import List, Optional, Dict
from src.core.ports.repositories.serie_repository import ISerieRepository


def _clean_unicode(text: str) -> str:
    """
    Limpia caracteres Unicode problemáticos (surrogates) de nombres de archivos/carpetas.
    Convierte caracteres como \udced a la letra correcta (í).
    """
    if not text:
        return text
    
    # Mapeo de surrogates a caracteres válidos
    surrogate_map = {
        '\udce1': 'á',  # á
        '\udce9': 'é',  # é
        '\udced': 'í',  # í
        '\udcf3': 'ó',  # ó
        '\udcfa': 'ú',  # ú
        '\udcc1': 'Á',  # Á
        '\udcc9': 'É',  # É
        '\udccd': 'Í',  # Í
        '\udcf3': 'Ó',  # Ó
        '\udcfa': 'Ú',  # Ú
        '\udcf1': 'ñ',  # ñ
        '\udcd1': 'Ñ',  # Ñ
    }
    
    # Reemplazar todos los surrogates conocidos
    for surrogate, char in surrogate_map.items():
        text = text.replace(surrogate, char)
    
    # También limpiar otros surrogates problema
    text = text.encode('utf-8', errors='surrogatepass').decode('utf-8', errors='replace')
    # Normalizar a NFC para asegurar consistencia
    return unicodedata.normalize('NFC', text)


class FilesystemSerieRepository(ISerieRepository):
    """Repositorio de series escaneando el sistema de archivos"""
    
    def __init__(self, base_folder: str = None):
        """
        Inicializa el repositorio
        
        Args:
            base_folder: Carpeta base donde están las series
        """
        self._base_folder = base_folder or os.environ.get('MOVIES_FOLDER', '/mnt/servidor/Data2TB/audiovisual')
        self._valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
    
    def _parse_season_folder(self, folder_name: str) -> tuple:
        """
        Parsea el nombre de una carpeta de temporada
        Formato: SerieName.S01 o SerieName.S01E01
        """
        # Buscar patrón de temporada: .S01 o .S01E01
        season_match = re.search(r'\.S(\d+)', folder_name, re.IGNORECASE)
        if season_match:
            season = int(season_match.group(1))
            # Extraer nombre de la serie
            serie_name = folder_name[:season_match.start()]
            # Limpiar nombre
            serie_name = serie_name.replace('.', ' ').strip()
            return serie_name, season
        
        return folder_name.replace('.', ' ').strip(), 1
    
    def _scan_folder(self) -> List[Dict]:
        """Escanea la carpeta de series"""
        series = {}
        
        if not os.path.exists(self._base_folder):
            return []
        
        # Buscar carpetas que parezcan series (contienen .S01, .S02, etc.)
        for item in os.listdir(self._base_folder):
            item_path = os.path.join(self._base_folder, item)
            
            # Skip si no es carpeta
            if not os.path.isdir(item_path):
                continue
            
            # Skip carpetas especiales
            if item.lower() in ['mkv', 'optimized', 'processed', 'thumbnails', 'pipeline']:
                continue
            
            # Detectar si es una carpeta de temporada (contiene .S##)
            if re.search(r'\.S\d+', item, re.IGNORECASE):
                # Es una carpeta de temporada
                serie_name, season = self._parse_season_folder(item)
                # Limpiar caracteres Unicode problemáticos
                serie_name = _clean_unicode(serie_name)
                
                # Crear o actualizar la serie
                if serie_name not in series:
                    series[serie_name] = {
                        'name': serie_name,
                        'path': os.path.dirname(item_path),
                        'seasons': {},
                        'episodes': []
                    }
                
                # Escanear episodios en esta carpeta
                for file in os.listdir(item_path):
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self._valid_extensions:
                        file_path = os.path.join(item_path, file)
                        size = os.path.getsize(file_path)
                        
                        # Calcular si es un episodio nuevo
                        try:
                            mtime = os.path.getmtime(file_path)
                            days_ago = int((time.time() - mtime) / (24 * 3600))
                            is_new = days_ago <= 30
                        except:
                            days_ago = -1
                            is_new = False
                        
                        # Parsear episodio
                        ep_match = re.search(r'[Ee](\d+)', file)
                        episode_num = int(ep_match.group(1)) if ep_match else 1
                        
                        # Crear nombre del episodio para mostrar
                        ep_title = f"{serie_name} S{season:02d}E{episode_num:02d}"
                        
                        episode = {
                            'filename': file,
                            'name': ep_title,
                            'title': ep_title,
                            'serie_name': serie_name,
                            'path': file_path,
                            'size': size,
                            'season': season,
                            'episode': episode_num,
                            'ext': ext,
                            'is_new': is_new,
                            'days_ago': days_ago
                        }
                        
                        series[serie_name]['episodes'].append(episode)
                        
                        if season not in series[serie_name]['seasons']:
                            series[serie_name]['seasons'][season] = []
                        series[serie_name]['seasons'][season].append(episode)
            
            # Detectar si es una carpeta de serie (sin número de temporada pero con archivos de video)
            # o subcarpetas con episodios
            else:
                # Verificar si tiene subcarpetas de temporadas o archivos sueltos
                has_files = False
                has_subdirs = False
                
                for subitem in os.listdir(item_path):
                    subitem_path = os.path.join(item_path, subitem)
                    if os.path.isdir(subitem_path):
                        has_subdirs = True
                    elif os.path.isfile(subitem_path):
                        ext = os.path.splitext(subitem)[1].lower()
                        if ext in self._valid_extensions:
                            has_files = True
                
                # Si tiene archivos sueltos (sin temporadas), es una serie de una temporada
                if has_files and not has_subdirs:
                    serie_name = item.replace('.', ' ').strip()
                    # Limpiar caracteres Unicode problemáticos
                    serie_name = _clean_unicode(serie_name)
                    
                    if serie_name not in series:
                        series[serie_name] = {
                            'name': serie_name,
                            'path': item_path,
                            'seasons': {1: []},
                            'episodes': []
                        }
                    
                    # Escanear episodios
                    episode_num = 1
                    for file in os.listdir(item_path):
                        ext = os.path.splitext(file)[1].lower()
                        if ext in self._valid_extensions:
                            file_path = os.path.join(item_path, file)
                            size = os.path.getsize(file_path)
                            
                            # Calcular si es un episodio nuevo
                            try:
                                mtime = os.path.getmtime(file_path)
                                days_ago = int((time.time() - mtime) / (24 * 3600))
                                is_new = days_ago <= 30
                            except:
                                days_ago = -1
                                is_new = False
                            
                            # Crear nombre del episodio para mostrar
                            ep_title = f"{serie_name} S01E{episode_num:02d}"
                            
                            episode = {
                                'filename': file,
                                'name': ep_title,
                                'title': ep_title,
                                'serie_name': serie_name,
                                'path': file_path,
                                'size': size,
                                'season': 1,
                                'episode': episode_num,
                                'ext': ext,
                                'is_new': is_new,
                                'days_ago': days_ago
                            }
                            
                            series[serie_name]['episodes'].append(episode)
                            series[serie_name]['seasons'][1].append(episode)
                            episode_num += 1
        
        # Convertir a lista
        result = []
        for serie in series.values():
            # Ordenar episodios
            serie['episodes'].sort(key=lambda x: (x['season'], x['episode']))
            result.append(serie)
        
        return result
    
    def list_all(self) -> List[Dict]:
        """Lista todas las series"""
        return self._scan_folder()
    
    def get_by_id(self, serie_id: int) -> Optional[Dict]:
        """Obtiene una serie por su ID"""
        series = self._scan_folder()
        if 0 <= serie_id < len(series):
            return series[serie_id]
        return None
    
    def get_by_name(self, name: str) -> Optional[Dict]:
        """Obtiene una serie por su nombre"""
        series = self._scan_folder()
        name_lower = name.lower()
        
        for serie in series:
            if name_lower in serie['name'].lower():
                return serie
        return None
    
    def get_by_path(self, path: str) -> Optional[Dict]:
        """Obtiene una serie por su ruta"""
        series = self._scan_folder()
        
        for serie in series:
            if serie.get('path') == path:
                return serie
        return None
    
    def get_by_imdb_id(self, imdb_id: str) -> Optional[Dict]:
        """Obtiene una serie por su ID de IMDb"""
        # No disponible en filesystem
        return None
    
    def search(self, query: str) -> List[Dict]:
        """Busca series por nombre"""
        series = self._scan_folder()
        query_lower = query.lower()
        
        return [s for s in series if query_lower in s['name'].lower()]
    
    def get_by_genre(self, genre: str) -> List[Dict]:
        """Obtiene series por género"""
        # No disponible sin metadatos
        return []
    
    def save(self, serie_data: Dict) -> Dict:
        """Guarda o actualiza una serie"""
        # No aplicable en filesystem
        return serie_data
    
    def delete(self, serie_id: int) -> bool:
        """Elimina una serie"""
        # No soportado en este repositorio
        return False
    
    def update_metadata(self, serie_id: int, metadata: Dict) -> Dict:
        """Actualiza los metadatos de una serie"""
        # No aplicable en filesystem
        return metadata
    
    def get_with_episodes(self, serie_id: int) -> Optional[Dict]:
        """Obtiene una serie con todos sus episodios"""
        serie = self.get_by_id(serie_id)
        if serie:
            return serie
        
        # También buscar por nombre
        series = self._scan_folder()
        for s in series:
            if s.get('name') == str(serie_id):
                return s
        return None
    
    def get_episodes_by_season(self, serie_name: str, season: int) -> List[Dict]:
        """Obtiene los episodios de una temporada específica"""
        serie = self.get_by_name(serie_name)
        if not serie:
            return []
        
        return serie.get('seasons', {}).get(season, [])
