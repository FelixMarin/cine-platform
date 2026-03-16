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

VIDEO_EXTENSIONS = ('.mkv', '.mp4', '.avi', '.mov', '.webm', '.m4v', '.wmv', '.flv', '.ts', '.m2ts')

# Constantes para estados de Transmission
TORRENT_STATUS = {
    0: "stopped",
    1: "check queued",
    2: "checking",
    3: "download queued",
    4: "downloading",
    5: "seed queued",
    6: "seeding",
}

# Categorías válidas para organizar descargas (se leen del sistema de archivos)
VALID_CATEGORIES = None  # Se inicializa dinámicamente


def get_valid_categories() -> List[str]:
    """
    Obtiene las categorías válidas del sistema de archivos
    """
    global VALID_CATEGORIES

    if VALID_CATEGORIES is not None:
        return VALID_CATEGORIES

    try:
        import os

        base_path = settings.MOVIES_BASE_PATH
        if os.path.exists(base_path):
            VALID_CATEGORIES = [
                d
                for d in os.listdir(base_path)
                if os.path.isdir(os.path.join(base_path, d))
            ]
            VALID_CATEGORIES.sort()
        else:
            VALID_CATEGORIES = []
    except Exception as e:
        logger.warning(f"[Transmission] Error leyendo categorías: {e}")
        VALID_CATEGORIES = []

    return VALID_CATEGORIES


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
            "id": self.id,
            "name": self.name,
            "hash": self.hash_string,
            "status": self.status,
            "status_display": TORRENT_STATUS.get(self.status, "unknown"),
            "progress": round(self.progress * 100, 1),
            "size_total": self.size_when_done,
            "size_downloaded": self.downloaded_ever,
            "size_formatted": self._format_size(self.size_when_done),
            "upload_ratio": round(self.upload_ratio, 2),
            "rate_upload": self.rate_upload,
            "rate_download": self.rate_download,
            "download_speed_formatted": self._format_speed(self.rate_download),
            "upload_speed_formatted": self._format_speed(self.rate_upload),
            "eta": self.eta,
            "eta_formatted": self._format_eta(self.eta),
            "added_date": self.added_date,
            "done_date": self.done_date,
            "magnet_link": self.magnet_link,
            "files": self.files,
            "category": self.category,
            "download_dir": self.download_dir,
        }

    @staticmethod
    def _format_size(size: int) -> str:
        """Formatea el tamaño en formato legible"""
        for unit in ["B", "KB", "MB", "GB", "TB"]:
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

    @staticmethod
    def _format_speed(bytes_per_sec: int) -> str:
        """Formatea la velocidad en formato legible"""
        if bytes_per_sec <= 0:
            return "0 B/s"

        for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
            if bytes_per_sec < 1024.0:
                return f"{bytes_per_sec:.2f} {unit}"
            bytes_per_sec /= 1024.0
        return f"{bytes_per_sec:.2f} TB/s"


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

    def __init__(
        self,
        url: Optional[str] = None,
        username: Optional[str] = None,
        password: Optional[str] = None,
    ):
        """
        Inicializa el cliente de Transmission

        Args:
            url: URL RPC de Transmission (por defecto de settings)
            username: Usuario para autenticación (por defecto de settings)
            password: Contraseña para autenticación (por defecto de settings)
        """
        self.url = url or os.environ.get(
            "TRANSMISSION_URL", settings.TRANSMISSION_RPC_URL
        )
        self.username = username or os.environ.get(
            "TRANSMISSION_USERNAME", settings.TRANSMISSION_USERNAME
        )
        self.password = password or os.environ.get(
            "TRANSMISSION_PASSWORD", settings.TRANSMISSION_PASSWORD
        )
        self._session = requests.Session()
        self._session.headers.update({"Content-Type": "application/json"})

        if self.username and self.password:
            self._session.auth = (self.username, self.password)

        self._session_id = None
        self._timeout = int(os.environ.get("TRANSMISSION_TIMEOUT", 30))

        # Carpeta de descargas
        self.download_folder = settings.TRANSMISSION_DOWNLOAD_DIR
        logger.info(f"[Transmission] download_folder configurado: {self.download_folder}")

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
            # Primera petición - Transmission siempre devuelve 409 si no hay session ID válida
            response = self._session.post(self.url, json={"method": "session-get"})

            # Transmission devuelve 409 cuando no hay session ID válida
            # El session ID está en los headers de la respuesta 409
            if response.status_code == 409:
                session_id = response.headers.get("X-Transmission-Session-Id")
                if not session_id:
                    raise TransmissionError(
                        "No se pudo obtener X-Transmission-Session-Id de la respuesta 409"
                    )
            elif response.status_code == 200:
                # Ya tiene sesión válida
                session_id = response.headers.get(
                    "X-Transmission-Session-Id", "valid_session"
                )
            else:
                raise TransmissionError(
                    f"Error obteniendo session ID: HTTP {response.status_code}"
                )

            self._session_id = session_id
            self._session.headers["X-Transmission-Session-Id"] = session_id

            logger.info(f"[Transmission] ✅ Session ID obtained: {session_id[:20]}...")
            return session_id

        except TransmissionError:
            raise
        except requests.exceptions.RequestException as e:
            raise TransmissionError(f"Error al obtener session ID: {str(e)}")

    def _make_request(
        self, method: str, arguments: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
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
        logger.info(f"[Transmission] 📤 Petition {method}...")

        # Obtener session ID si no hay uno
        if not self._session_id:
            logger.info("[Transmission] 🔑 No session ID, obtaining...")
            self._get_session_id()

        payload = {"method": method, "arguments": arguments or {}}

        try:
            response = self._session.post(self.url, json=payload, timeout=self._timeout)

            # Si devuelve 409, necesitamos un nuevo session ID
            if response.status_code == 409:
                logger.warning("[Transmission] ⚠️ Got 409, re-fetching session ID...")
                self._get_session_id()
                self._session.headers["X-Transmission-Session-Id"] = self._session_id
                response = self._session.post(
                    self.url, json=payload, timeout=self._timeout
                )
                logger.info(
                    f"[Transmission] 📥 Retry response status: {response.status_code}"
                )

            response.raise_for_status()
            
            # Verificar que la respuesta no esté vacía
            if not response.text or len(response.text.strip()) == 0:
                raise TransmissionError(f"Respuesta vacía de Transmission para {method}")
            
            try:
                data = response.json()
            except Exception as e:
                logger.error(f"[Transmission] ❌ Error parseando JSON: {str(e)}")
                logger.error(f"[Transmission] Response text: {response.text[:200]}")
                raise TransmissionError(f"Respuesta inválida de Transmission: {str(e)}")

            if data.get("result") != "success":
                raise TransmissionError(f"Error de Transmission: {data.get('result')}")

            logger.info(f"[Transmission] ✅ {method} completed successfully")
            return data.get("arguments", {})

        except requests.exceptions.ConnectionError as e:
            logger.error(f"[Transmission] Error de conexión: {str(e)}")
            raise TransmissionError(f"No se pudo conectar a Transmission en {self.url}")
        except requests.exceptions.Timeout:
            raise TransmissionError(
                "Tiempo de espera agotado al conectar con Transmission"
            )
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            raise TransmissionError(
                f"Error HTTP {status_code} de Transmission", status_code
            )
        except requests.exceptions.RequestException as e:
            # Capturar errores específicos de requests como "No connection adapters"
            error_msg = str(e)
            if (
                "connection adapters" in error_msg.lower()
                or "magnet" in error_msg.lower()
            ):
                logger.error(
                    f"[Transmission] Error con la URL del torrent: {error_msg}"
                )
                raise TransmissionError(f"Error al procesar el torrent: {error_msg}")
            raise TransmissionError(f"Error de request: {error_msg}")
        except TransmissionError:
            raise
        except Exception as e:
            raise TransmissionError(f"Error de comunicación con Transmission: {str(e)}")

    def add_torrent(
        self,
        source: str,
        category: Optional[str] = None,
        download_dir: Optional[str] = None,
        paused: bool = False,
    ) -> Dict[str, Any]:
        """
        Añade un torrent o magnet a la cola de descargas
        """
        # Limpiar la fuente de cualquier caracter invisible
        source = source.strip()

        # Debug con logger (no print para que funcione en producción)
        logger.info(f"[Transmission] ===== ADD TORRENT =====")

        # Obtener categorías válidas del sistema de archivos
        valid_cats = get_valid_categories()

        # Validar categoría
        if category and category not in valid_cats:
            logger.warning(
                f"[Transmission] Categoría inválida: {category}, categorías válidas: {valid_cats}"
            )
            # No rechazamos, usamos la categoría como label

        # Determinar directorio de descarga
        target_dir = download_dir or self.download_folder
        logger.info(f"[Transmission] target_dir final: {target_dir}")

        # Asegurar que existe el directorio
        os.makedirs(target_dir, exist_ok=True)

        # Construir argumentos
        arguments = {"download-dir": target_dir, "paused": paused}
        logger.info(f"[Transmission] Argumentos enviados a Transmission: {arguments}")

        # Detectar si es un magnet o un archivo torrent
        # Limpiar caracteres invisibles comunes (BOM, zero-width space, etc.) al principio y final
        invisible_chars = (
            "\ufeff\u200b\u200c\u200d\ufeff"  # BOM, zero-width space, etc.
        )
        source_stripped = source
        for char in invisible_chars:
            source_stripped = source_stripped.replace(char, "")
        source_stripped = source_stripped.strip()

        if source_stripped.startswith("magnet:"):
            logger.info("[Transmission] Añadiendo magnet")
            arguments["filename"] = source_stripped
        elif source_stripped.startswith("http://") or source_stripped.startswith(
            "https://"
        ):
            # Es una URL HTTP (puede ser de Prowlarr, Jackett, o directamente un .torrent)
            # IMPORTANTE: No usamos allow_redirects=True directamente porque si la URL
            # redirige a un magnet, requests fallará con "No connection adapters"
            # En su lugar, primero obtenemos la respuesta sin seguir redirects para ver la Location
            logger.info("[Transmission] Procesando URL HTTP")
            try:
                # Primero hacer request sin seguir redirects para obtener la Location
                response = requests.get(
                    source_stripped, timeout=30, allow_redirects=False
                )

                # Verificar si hay redirect (301, 302, 307, 308)
                if response.status_code in (301, 302, 307, 308):
                    # Obtener la URL de redirect
                    final_url = response.headers.get("Location")
                    if final_url:
                        logger.info("[Transmission] Redirect detectado")
                        # Verificar si la URL final es un magnet
                        if final_url.startswith("magnet:"):
                            logger.info("[Transmission] Magnet del redirect")
                            arguments["filename"] = final_url
                        else:
                            # Es un redirect HTTP, hacer otro request al destino
                            logger.info("[Transmission] Redirect HTTP")
                            response2 = requests.get(final_url, timeout=30)
                            response2.raise_for_status()
                            arguments["metainfo"] = base64.b64encode(
                                response2.content
                            ).decode("utf-8")
                    else:
                        # No hay Location header, intentar obtener contenido
                        logger.warning(
                            "[Transmission] Redirect sin Location header, continuando..."
                        )
                        response = requests.get(source_stripped, timeout=30)
                        response.raise_for_status()
                        arguments["metainfo"] = base64.b64encode(
                            response.content
                        ).decode("utf-8")
                elif response.status_code == 200:
                    # No hay redirect, es contenido directo
                    # Verificar si la URL es un magnet (por si acaso)
                    if response.url.startswith("magnet:"):
                        logger.info("[Transmission] Magnet directo")
                        arguments["filename"] = response.url
                    else:
                        # Es contenido de torrent directo
                        logger.info("[Transmission] Torrent directo")
                        arguments["metainfo"] = base64.b64encode(
                            response.content
                        ).decode("utf-8")
                else:
                    # Otro código de estado
                    logger.warning(
                        f"[Transmission] Código de estado inesperado: {response.status_code}"
                    )
                    response.raise_for_status()
                    arguments["metainfo"] = base64.b64encode(response.content).decode(
                        "utf-8"
                    )

            except TransmissionError:
                raise
            except Exception as e:
                logger.error(
                    f"[Transmission] Error descargando torrent desde URL: {str(e)}"
                )
                raise TransmissionError(f"Error al descargar torrent: {str(e)}")
        else:
            # Este un archivo .torrent codificado en base64 o path local
            logger.info("[Transmission] Metainfo local")
            arguments["metainfo"] = source_stripped

        # Añadir categoría si se especifica
        if category:
            arguments["labels"] = [category]

        # Realizar la petición
        result = self._make_request("torrent-add", arguments)

        # Obtener información del torrent añadido
        torrent_info = result.get("torrent-added", result.get("torrent-duplicate", {}))

        logger.info(f"[Transmission] Torrent añadido con ID: {torrent_info.get('id')}")

        return {
            "id": torrent_info.get("id"),
            "name": torrent_info.get("name"),
            "hash": torrent_info.get("hashString"),
            "category": category,
            "download_dir": target_dir,
        }

    def add_magnet(
        self,
        magnet_url: str,
        category: Optional[str] = None,
        download_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
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
            "fields": [
                "id",
                "name",
                "hashString",
                "status",
                "progress",
                "sizeWhenDone",
                "downloadedEver",
                "uploadRatio",
                "rateUpload",
                "rateDownload",
                "eta",
                "addedDate",
                "doneDate",
                "magnetLink",
                "downloadDir",
                "labels",
                "files",
            ]
        }

        if ids:
            arguments["ids"] = ids

        result = self._make_request("torrent-get", arguments)

        torrents = []
        for item in result.get("torrents", []):
            # Extraer categoría de labels
            category = None
            labels = item.get("labels", [])
            if labels and len(labels) > 0:
                category = labels[0]

            # Extraer archivos
            files = []
            for f in item.get("files", []):
                files.append(
                    {
                        "name": f.get("name"),
                        "size": f.get("length"),
                        "bytes_completed": f.get("bytesCompleted"),
                    }
                )

            torrent = TorrentDownload(
                id=item.get("id"),
                name=item.get("name"),
                hash_string=item.get("hashString"),
                status=item.get("status"),
                progress=item.get("progress", 0),
                size_when_done=item.get("sizeWhenDone", 0),
                downloaded_ever=item.get("downloadedEver", 0),
                upload_ratio=item.get("uploadRatio", 0),
                rate_upload=item.get("rateUpload", 0),
                rate_download=item.get("rateDownload", 0),
                eta=item.get("eta", -1),
                added_date=item.get("addedDate", 0),
                done_date=item.get("doneDate"),
                magnet_link=item.get("magnetLink"),
                files=files,
                category=category,
                download_dir=item.get("downloadDir"),
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
            t
            for t in all_torrents
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
        completed = [t for t in all_torrents if t.progress >= 1.0]

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
        self._make_request("torrent-stop", {"ids": [torrent_id]})
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
        self._make_request("torrent-start", {"ids": [torrent_id]})
        return True

    def remove_torrent(self, torrent_id: int, delete_files: bool = False, delete_data: bool = None) -> bool:
        """
        Elimina un torrent de Transmission

        Args:
            torrent_id: ID del torrent a eliminar
            delete_files: Si True, elimina también los archivos descargados (alias: delete_data)
            delete_data: Alias para delete_files (para compatibilidad)

        Returns:
            True si se eliminó correctamente

        Raises:
            TransmissionError: Si hay un error de conexión o el torrent no existe
        """
        # Usar delete_data si se proporciona, sinon usar delete_files
        if delete_data is not None:
            delete_files = delete_data
            
        logger.info(f"[Transmission] Eliminando torrent {torrent_id} (delete_files={delete_files})")
        arguments = {"ids": [torrent_id], "delete-local-data": delete_files}
        
        try:
            self._make_request("torrent-remove", arguments)
            logger.info(f"[Transmission] ✅ Torrent {torrent_id} eliminado correctamente")
            return True
        except TransmissionError as e:
            # Si el torrent no existe (quizás ya fue eliminado manualmente), no es un error crítico
            if "torrent not found" in str(e.message).lower() or "invalid id" in str(e.message).lower():
                logger.warning(f"[Transmission] Torrent {torrent_id} no encontrado en Transmission (puede que ya estuviera eliminado)")              
                return True  # Consideramos éxito porque el resultado final es el mismo
            logger.error(f"[Transmission] ❌ Error eliminando torrent {torrent_id}: {e.message}")
            raise

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
        arguments = {"ids": [torrent_id], "labels": labels}

        self._make_request("torrent-set", arguments)
        logger.info(
            f"[Transmission] Categoría '{category}' asignada al torrent {torrent_id}"
        )
        return True

    def get_session_stats(self) -> Dict[str, Any]:
        """
        Obtiene estadísticas de la sesión de Transmission

        Returns:
            Diccionario con estadísticas
        """
        result = self._make_request("session-stats", {})

        return {
            "active_count": result.get("activeTorrentCount", 0),
            "download_speed": result.get("downloadSpeed", 0),
            "upload_speed": result.get("uploadSpeed", 0),
            "paused_count": result.get("pausedTorrentCount", 0),
            "total_count": result.get("torrentCount", 0),
            "completed_count": result.get("cumulativeStats", {}).get(
                "connectedCount", 0
            ),
        }

    def get_torrent_file_path(
        self, torrent_id: int, filename: Optional[str] = None
    ) -> Optional[str]:
        """
        Obtiene la ruta completa del archivo de video de un torrent usando:
        - downloadDir (directorio base)
        - files[].name (ruta relativa del archivo)

        Args:
            torrent_id: ID del torrent
            filename: Nombre del archivo específico (opcional)

        Returns:
            Ruta completa al archivo o None si no se encuentra
        """
        # Obtener torrent con get_torrent() que ya incluye files y downloadDir
        torrent = self.get_torrent(torrent_id)
        if not torrent:
            logger.warning(f"[Transmission] Torrent {torrent_id} no encontrado")
            return None

        # Si no tenemos información del directorio de descarga, no podemos continuar
        if not torrent.download_dir:
            logger.warning(
                f"[Transmission] Torrent {torrent_id} no tiene downloadDir"
            )
            return None

        logger.info(
            f"[Transmission] Torrent: {torrent.name}, downloadDir: {torrent.download_dir}"
        )
        logger.info(f"[Transmission] Archivos del torrent: {[f.get('name') for f in torrent.files]}")

        # Si se especifica un filename, buscar ese archivo específico
        if filename:
            logger.info(f"[Transmission] Buscando archivo: '{filename}'")
            
            # PRIMERO: buscar en los archivos del torrent
            for f in torrent.files:
                file_name = f.get("name", "")
                # El nombre puede ser solo el archivo o una ruta relativa
                base_name = os.path.basename(file_name)
                
                # Coincidencia exacta, por nombre base, o si filename está contenido
                if (file_name == filename or 
                    base_name == filename or 
                    filename in file_name or 
                    filename in base_name):
                    
                    full_path = os.path.join(torrent.download_dir, file_name)
                    
                    # Verificar que NO es un directorio
                    if os.path.isdir(full_path):
                        logger.warning(f"[Transmission] La ruta es un directorio, no un archivo: {full_path}")
                        # Buscar archivos dentro del directorio
                        for root, dirs, files in os.walk(full_path):
                            for file in files:
                                if any(file.lower().endswith(ext) for ext in VIDEO_EXTENSIONS):
                                    nested_path = os.path.join(root, file)
                                    logger.info(f"[Transmission] ✅ Archivo encontrado dentro del directorio: {nested_path}")
                                    return nested_path
                        continue
                    
                    if os.path.exists(full_path):
                        logger.info(f"[Transmission] ✅ Archivo encontrado: {full_path}")
                        return full_path
                    else:
                        logger.warning(f"[Transmission] Archivo no existe en disco: {full_path}")
            
            # SEGUNDO: intentar con el filename como ruta directa
            direct_path = os.path.join(torrent.download_dir, filename)
            if os.path.exists(direct_path) and not os.path.isdir(direct_path):
                logger.info(f"[Transmission] ✅ Archivo encontrado (ruta directa): {direct_path}")
                return direct_path
            
            # TERCERO: si filename es el nombre del directorio, buscar dentro
            dir_path = os.path.join(torrent.download_dir, filename)
            if os.path.isdir(dir_path):
                logger.info(f"[Transmission] Filename es un directorio, buscando archivos dentro: {dir_path}")
                for ext in VIDEO_EXTENSIONS:
                    for file in os.listdir(dir_path):
                        if file.lower().endswith(ext):
                            full_path = os.path.join(dir_path, file)
                            logger.info(f"[Transmission] ✅ Archivo encontrado dentro del directorio: {full_path}")
                            return full_path
            
            logger.warning(f"[Transmission] Archivo especificado no encontrado: {filename}")
            return None
        
        for f in torrent.files:
            file_name = f.get("name", "")
            full_path = os.path.join(torrent.download_dir, file_name)
            
            # Si es un directorio, explorar dentro
            if os.path.isdir(full_path):
                logger.info(f"[Transmission] Explorando directorio: {full_path}")
                for root, dirs, files in os.walk(full_path):
                    for file in files:
                        if file.lower().endswith(VIDEO_EXTENSIONS):
                            nested_path = os.path.join(root, file)
                            logger.info(f"[Transmission] ✅ Archivo de video encontrado en subdirectorio: {nested_path}")
                            return nested_path
                continue
            
            # Si es archivo, verificar extensión
            if file_name.lower().endswith(VIDEO_EXTENSIONS):
                if os.path.exists(full_path):
                    logger.info(f"[Transmission] ✅ Archivo de video encontrado: {full_path}")
                    return full_path
                else:
                    logger.warning(f"[Transmission] Archivo de video no existe en disco: {full_path}")

        # Si no se encontró ningún archivo de video, listar lo que hay para debug
        logger.warning(f"[Transmission] No se encontró archivo de video para torrent {torrent_id}")
        
        # Listar contenido del download_dir para depuración
        if os.path.exists(torrent.download_dir):
            try:
                contents = os.listdir(torrent.download_dir)
                logger.info(f"[Transmission] Contenido de {torrent.download_dir}: {contents[:10]}")
            except Exception as e:
                logger.error(f"[Transmission] Error listando directorio: {e}")

        return None

    def debug_torrent_files(self, torrent_id: int) -> Dict[str, Any]:
        """
        Devuelve información detallada de los archivos del torrent para depuración

        Args:
            torrent_id: ID del torrent

        Returns:
            Diccionario con información de debug del torrent y sus archivos
        """
        torrent = self.get_torrent(torrent_id)
        if not torrent:
            return {
                "error": f"Torrent {torrent_id} no encontrado",
                "torrent_id": torrent_id,
            }

        # Información del torrent
        debug_info = {
            "torrent_id": torrent.id,
            "name": torrent.name,
            "hash": torrent.hash_string,
            "status": torrent.status,
            "status_display": TORRENT_STATUS.get(torrent.status, "unknown"),
            "progress": round(torrent.progress * 100, 1),
            "download_dir": torrent.download_dir,
            "category": torrent.category,
            "files_count": len(torrent.files),
            "files": [],
        }

        # Información de cada archivo
        video_extensions = (".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v")
        for f in torrent.files:
            file_name = f.get("name", "")
            file_size = f.get("size", 0)
            file_completed = f.get("bytes_completed", 0)

            # Verificar si existe en disco
            full_path = os.path.join(torrent.download_dir, file_name) if torrent.download_dir else None
            exists = os.path.exists(full_path) if full_path else False

            file_info = {
                "name": file_name,
                "size": file_size,
                "size_formatted": self._format_size(file_size),
                "bytes_completed": file_completed,
                "completed_percent": round((file_completed / file_size * 100), 1) if file_size > 0 else 0,
                "full_path": full_path,
                "exists": exists,
                "is_video": file_name.lower().endswith(video_extensions),
            }
            debug_info["files"].append(file_info)

        # Intentar encontrar el archivo de video principal
        for f in debug_info["files"]:
            if f["is_video"] and f["exists"]:
                debug_info["primary_video_path"] = f["full_path"]
                break

        logger.info(f"[Transmission] Debug torrent {torrent_id}: {debug_info}")
        return debug_info

    def test_connection(self) -> bool:
        """
        Prueba la conexión con Transmission

        Returns:
            True si la conexión es exitosa, False en caso contrario
        """
        logger.info("[Transmission] 🔍 Verificando conexión...")
        try:
            # Reiniciar session ID para forzar una verificación limpia
            self._session_id = None
            self._session.headers.pop("X-Transmission-Session-Id", None)

            # Obtener session ID (maneja el flujo 409)
            self._get_session_id()

            # Hacer una petición de prueba
            self._make_request("session-get", {})

            logger.info("[Transmission] ✅ Conexión exitosa")
            return True
        except TransmissionError as e:
            logger.error(f"[Transmission] ❌ Error de conexión: {e.message}")
            return False
        except Exception as e:
            logger.error(f"[Transmission] ❌ Error inesperado: {str(e)}")
            return False


def generate_download_id() -> str:
    """Genera un ID único para una descarga"""
    return str(uuid.uuid4())
