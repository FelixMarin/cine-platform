"""
Cliente RPC para Transmission

Transmission es un cliente BitTorrent que proporciona una API RPC.
Este cliente permite añadir torrents, obtener estado de descargas y gestionar archivos.
"""
import logging
import uuid
import os
import base64
import requests
from typing import Optional, List, Dict, Any
from dataclasses import dataclass, field
from src.infrastructure.config.settings import settings


logger = logging.getLogger(__name__)


# Constantes para estados de Transmission
TORRENT_STATUS = {
    0: 'stopped',
    1: 'check queued',
    2: 'checking',
    3: 'download queued',
    4: 'downloading',
    5: 'seed queued',
    6: 'seeding'
}

# Categorías válidas para organizar descargas
VALID_CATEGORIES = [
    'Acción', 'Animación', 'Aventura', 'Ciencia Ficción', 
    'Comedia', 'Documental', 'Drama', 'Familia', 
    'Fantasía', 'Historia', 'Música', 'Misterio', 
    'Romance', 'Suspense', 'Terror', 'Western'
]


@dataclass
class TorrentDownload:
    """Representa una descarga en Transmission"""
    id: int
    name: str
    hash_string: str
    status: str
    progress: float
    size_when_done: int
    downloaded_ever: int
    upload_ratio: float
    rate_upload: int
    rate_download: int
    eta: int  # segundos restantes
    added_date: int
    done_date: Optional[int] = None
    magnet_link: Optional[str] = None
    files: List[Dict[str, Any]] = field(default_factory=list)
    category: Optional[str] = None
    download_dir: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convierte a diccionario para el frontend"""
        return {
            'id': self.id,
            'name': self.name,
            'hash': self.hash_string,
            'status': self.status,
            'status_display': TORRENT_STATUS.get(self.status, 'unknown'),
            'progress': round(self.progress * 100, 1),
            'size_total': self.size_when_done,
            'size_downloaded': self.downloaded_ever,
            'size_formatted': self._format_size(self.size_when_done),
            'upload_ratio': round(self.upload_ratio, 2),
            'rate_upload': self.rate_upload,
            'rate_download': self.rate_download,
            'eta': self.eta,
            'eta_formatted': self._format_eta(self.eta),
            'added_date': self.added_date,
            'done_date': self.done_date,
            'magnet_link': self.magnet_link,
            'files': self.files,
            'category': self.category,
            'download_dir': self.download_dir
        }
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Formatea el tamaño en formato legible"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
    
    @staticmethod
    def _format_eta(seconds: int) -> str:
        """Formatea el tiempo restante"""
        if seconds < 0:
            return "∞"
        
        if seconds < 60:
            return f"{seconds}s"
        
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"


class TransmissionError(Exception):
    """Excepción para errores de Transmission"""
    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)


class TransmissionClient:
    """
    Cliente RPC para Transmission
    
    Uso:
        client = TransmissionClient()
        client.add_torrent(magnet_url, category="Acción")
        torrents = client.get_torrents()
    """
    
    def __init__(self, url: Optional[str] = None, username: Optional[str] = None, 
                 password: Optional[str] = None):
        """
        Inicializa el cliente de Transmission
        
        Args:
            url: URL RPC de Transmission (por defecto de settings)
            username: Usuario para autenticación (por defecto de settings)
            password: Contraseña para autenticación (por defecto de settings)
        """
        self.url = url or settings.TRANSMISSION_RPC_URL
        self.username = username or settings.TRANSMISSION_USERNAME
        self.password = password or settings.TRANSMISSION_PASSWORD
        self._session = requests.Session()
        self._session.headers.update({
            'Content-Type': 'application/json',
            'X-Transmission-Session-Id': ''
        })
        
        # Configurar autenticación básica si está habilitada
        if self.username and self.password:
            self._session.auth = (self.username, self.password)
        
        self._session_id = None
        self._timeout = 30
        
        # Carpeta de descargas
        self.download_folder = settings.UPLOAD_FOLDER
        
        logger.info(f"[Transmission] Cliente inicializado con URL: {self.url}")
    
    def _get_session_id(self) -> str:
        """
        Obtiene un session ID de Transmission
        
        Returns:
            Session ID para las siguientes peticiones
            
        Raises:
            TransmissionError: Si no se puede obtener el session ID
        """
        try:
            response = self._session.post(self.url, json={'method': 'session-get'})
            
            # Transmission devuelve el session ID en el header
            session_id = response.headers.get('X-Transmission-Session-Id')
            
            if not session_id:
                # Intentar obtener del body
                data = response.json()
                if data.get('result') == 'success':
                    session_id = 'default'  # Fallback
            
            self._session_id = session_id
            self._session.headers['X-Transmission-Session-Id'] = session_id
            
            logger.debug(f"[Transmission] Session ID obtained: {session_id[:20]}...")
            return session_id
            
        except requests.exceptions.RequestException as e:
            raise TransmissionError(f"Error al obtener session ID: {str(e)}")
    
    def _make_request(self, method: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Realiza una petición RPC a Transmission
        
        Args:
            method: Método RPC de Transmission
            arguments: Argumentos para el método
            
        Returns:
            Respuesta de Transmission
            
        Raises:
            TransmissionError: Si hay un error en la comunicación
        """
        # Obtener session ID si no hay uno
        if not self._session_id:
            self._get_session_id()
        
        payload = {
            'method': method,
            'arguments': arguments or {}
        }
        
        try:
            response = self._session.post(self.url, json=payload, timeout=self._timeout)
            
            # Si devuelve 409, necesitamos un nuevo session ID
            if response.status_code == 409:
                self._get_session_id()
                self._session.headers['X-Transmission-Session-Id'] = self._session_id
                response = self._session.post(self.url, json=payload, timeout=self._timeout)
            
            response.raise_for_status()
            data = response.json()
            
            if data.get('result') != 'success':
                raise TransmissionError(f"Error de Transmission: {data.get('result')}")
            
            return data.get('arguments', {})
            
        except requests.exceptions.ConnectionError:
            raise TransmissionError(f"No se pudo conectar a Transmission en {self.url}")
        except requests.exceptions.Timeout:
            raise TransmissionError("Tiempo de espera agotado al conectar con Transmission")
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            raise TransmissionError(f"Error HTTP {status_code} de Transmission", status_code)
        except TransmissionError:
            raise
        except Exception as e:
            raise TransmissionError(f"Error de comunicación con Transmission: {str(e)}")
    
    def add_torrent(self, source: str, category: Optional[str] = None, 
                    download_dir: Optional[str] = None,
                    paused: bool = False) -> Dict[str, Any]:
        """
        Añade un torrent o magnet a la cola de descargas
        
        Args:
            source: URL del torrent (.torrent) o magnet
            category: Categoría para organizar la descarga
            download_dir: Directorio de descarga (por defecto: UPLOAD_FOLDER)
            paused: Si True, la descarga empieza pausada
            
        Returns:
            Información del torrent añadido
            
        Raises:
            TransmissionError: Si hay un error al añadir el torrent
        """
        logger.info(f"[Transmission] Añadiendo torrent: {source[:50]}...")
        
        # Validar categoría
        if category and category not in VALID_CATEGORIES:
            logger.warning(f"[Transmission] Categoría inválida: {category}, usando None")
            category = None
        
        # Determinar directorio de descarga
        target_dir = download_dir or self.download_folder
        
        # Asegurar que existe el directorio
        os.makedirs(target_dir, exist_ok=True)
        
        # Construir argumentos
        arguments = {
            'download-dir': target_dir,
            'paused': paused
        }
        
        # Detectar si es un magnet o un archivo torrent
        if source.startswith('magnet:'):
            arguments['filename'] = source
        else:
            # Es una URL de torrent, descargarlo primero
            try:
                response = requests.get(source, timeout=30)
                response.raise_for_status()
                # Codificar en base64 como espera Transmission
                arguments['metainfo'] = base64.b64encode(response.content).decode('utf-8')
            except Exception as e:
                raise TransmissionError(f"Error al descargar torrent: {str(e)}")
        
        # Añadir categoría si se especifica
        if category:
            arguments['labels'] = [category]
        
        # Realizar la petición
        result = self._make_request('torrent-add', arguments)
        
        # Obtener información del torrent añadido
        torrent_info = result.get('torrent-added', result.get('torrent-duplicate', {}))
        
        logger.info(f"[Transmission] Torrent añadido con ID: {torrent_info.get('id')}")
        
        return {
            'id': torrent_info.get('id'),
            'name': torrent_info.get('name'),
            'hash': torrent_info.get('hashString'),
            'category': category,
            'download_dir': target_dir
        }
    
    def add_magnet(self, magnet_url: str, category: Optional[str] = None,
                   download_dir: Optional[str] = None) -> Dict[str, Any]:
        """
        Añade un magnet URI a la cola de descargas
        
        Args:
            magnet_url: URL magnet (magnet:?xt=...)
            category: Categoría para organizar la descarga
            download_dir: Directorio de descarga
            
        Returns:
            Información del torrent añadido
        """
        return self.add_torrent(magnet_url, category, download_dir, paused=False)
    
    def get_torrents(self, ids: Optional[List[int]] = None) -> List[TorrentDownload]:
        """
        Obtiene la lista de torrents
        
        Args:
            ids: Lista de IDs específicos (None = todos)
            
        Returns:
            Lista de torrents
        """
        arguments = {
            'fields': [
                'id', 'name', 'hashString', 'status', 'progress',
                'sizeWhenDone', 'downloadedEver', 'uploadRatio',
                'rateUpload', 'rateDownload', 'eta', 'addedDate',
                'doneDate', 'magnetLink', 'downloadDir', 'labels',
                'files'
            ]
        }
        
        if ids:
            arguments['ids'] = ids
        
        result = self._make_request('torrent-get', arguments)
        
        torrents = []
        for item in result.get('torrents', []):
            # Extraer categoría de labels
            category = None
            labels = item.get('labels', [])
            if labels and len(labels) > 0:
                category = labels[0]
            
            # Extraer archivos
            files = []
            for f in item.get('files', []):
                files.append({
                    'name': f.get('name'),
                    'size': f.get('length'),
                    'bytes_completed': f.get('bytesCompleted')
                })
            
            torrent = TorrentDownload(
                id=item.get('id'),
                name=item.get('name'),
                hash_string=item.get('hashString'),
                status=item.get('status'),
                progress=item.get('progress', 0),
                size_when_done=item.get('sizeWhenDone', 0),
                downloaded_ever=item.get('downloadedEver', 0),
                upload_ratio=item.get('uploadRatio', 0),
                rate_upload=item.get('rateUpload', 0),
                rate_download=item.get('rateDownload', 0),
                eta=item.get('eta', -1),
                added_date=item.get('addedDate', 0),
                done_date=item.get('doneDate'),
                magnet_link=item.get('magnetLink'),
                files=files,
                category=category,
                download_dir=item.get('downloadDir')
            )
            torrents.append(torrent)
        
        return torrents
    
    def get_torrent(self, torrent_id: int) -> Optional[TorrentDownload]:
        """
        Obtiene un torrent específico por ID
        
        Args:
            torrent_id: ID del torrent
            
        Returns:
            TorrentDownload o None si no existe
        """
        torrents = self.get_torrents(ids=[torrent_id])
        return torrents[0] if torrents else None
    
    def get_active_downloads(self) -> List[TorrentDownload]:
        """
        Obtiene las descargas activas
        
        Returns:
            Lista de torrents en descarga o cola
        """
        all_torrents = self.get_torrents()
        
        # Filtrar solo los que están descargando o en cola
        active = [
            t for t in all_torrents 
            if t.status in [3, 4]  # download queued, downloading
        ]
        
        return active
    
    def get_completed_downloads(self) -> List[TorrentDownload]:
        """
        Obtiene las descargas completadas
        
        Returns:
            Lista de torrents completados
        """
        all_torrents = self.get_torrents()
        
        # Filtrar solo los completados (seeding o parados)
        completed = [
            t for t in all_torrents
            if t.progress >= 1.0
        ]
        
        return completed
    
    def stop_torrent(self, torrent_id: int) -> bool:
        """
        Detiene un torrent
        
        Args:
            torrent_id: ID del torrent
            
        Returns:
            True si se detuvo correctamente
        """
        logger.info(f"[Transmission] Deteniendo torrent {torrent_id}")
        self._make_request('torrent-stop', {'ids': [torrent_id]})
        return True
    
    def start_torrent(self, torrent_id: int) -> bool:
        """
        Reanuda un torrent
        
        Args:
            torrent_id: ID del torrent
            
        Returns:
            True si se inició correctamente
        """
        logger.info(f"[Transmission] Iniciando torrent {torrent_id}")
        self._make_request('torrent-start', {'ids': [torrent_id]})
        return True
    
    def remove_torrent(self, torrent_id: int, delete_files: bool = False) -> bool:
        """
        Elimina un torrent
        
        Args:
            torrent_id: ID del torrent
            delete_files: Si True, también elimina los archivos descargados
            
        Returns:
            True si se eliminó correctamente
        """
        logger.info(f"[Transmission] Eliminando torrent {torrent_id}")
        arguments = {'ids': [torrent_id], 'delete-local-data': delete_files}
        self._make_request('torrent-remove', arguments)
        return True
    
    def set_category(self, torrent_id: int, category: str) -> bool:
        """
        Asigna una categoría a un torrent
        
        Args:
            torrent_id: ID del torrent
            category: Nombre de la categoría
            
        Returns:
            True si se asignó correctamente
        """
        if category and category not in VALID_CATEGORIES:
            logger.warning(f"[Transmission] Categoría inválida: {category}")
            return False
        
        labels = [category] if category else []
        arguments = {'ids': [torrent_id], 'labels': labels}
        
        self._make_request('torrent-set', arguments)
        logger.info(f"[Transmission] Categoría '{category}' asignada al torrent {torrent_id}")
        return True
    
    def get_session_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la sesión de Transmission
        
        Returns:
            Diccionario con estadísticas
        """
        result = self._make_request('session-stats', {})
        
        return {
            'active_count': result.get('activeTorrentCount', 0),
            'download_speed': result.get('downloadSpeed', 0),
            'upload_speed': result.get('uploadSpeed', 0),
            'paused_count': result.get('pausedTorrentCount', 0),
            'total_count': result.get('torrentCount', 0),
            'completed_count': result.get('cumulativeStats', {}).get('connectedCount', 0)
        }
    
    def test_connection(self) -> bool:
        """
        Prueba la conexión con Transmission
        
        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        try:
            self._make_request('session-get', {})
            logger.info("[Transmission] Conexión exitosa")
            return True
        except TransmissionError as e:
            logger.error(f"[Transmission] Error de conexión: {e.message}")
            return False


def generate_download_id() -> str:
    """Genera un ID único para una descarga"""
    return str(uuid.uuid4())
