"""
Servicio de búsqueda de archivos de torrent

Maneja la búsqueda de archivos de video en las carpetas de Transmission.
"""

import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)


class TorrentFileFinder:
    """Servicio para encontrar archivos de torrent"""

    TRANSMISSION_COMPLETE = os.environ.get(
        "TRANSMISSION_COMPLETE_PATH", "/downloads/complete"
    )
    TRANSMISSION_INCOMPLETE = os.environ.get(
        "TRANSMISSION_INCOMPLETE_PATH", "/downloads/incomplete"
    )

    def __init__(self, transmission_client=None):
        self.transmission_client = transmission_client

    def find_file(
        self,
        filename: str,
        torrent_id: Optional[int] = None,
    ) -> Optional[str]:
        """
        Busca el archivo en Transmission o en las carpetas tradicionales.

        Args:
            filename: Nombre del archivo a buscar
            torrent_id: ID del torrent en Transmission (opcional)

        Returns:
            Ruta completa del archivo si se encuentra, None si no
        """
        if torrent_id and self.transmission_client:
            source_path = self._find_via_transmission(torrent_id, filename)
            if source_path:
                return source_path

        return self._find_fallback(filename, torrent_id)

    def _find_via_transmission(self, torrent_id: int, filename: str) -> Optional[str]:
        """Busca el archivo usando TransmissionClient"""
        try:
            logger.info(
                f"[FileFinder] Intentando obtener ruta desde Transmission (torrent_id={torrent_id})"
            )
            source_path = self.transmission_client.get_torrent_file_path(
                torrent_id, filename
            )
            if source_path and os.path.exists(source_path):
                ext = os.path.splitext(source_path)[1]
                logger.info(
                    f"[FileFinder] ✅ Archivo encontrado: {source_path} (extensión: {ext})"
                )
                return source_path
            elif source_path:
                logger.warning(
                    f"[FileFinder] Transmission devolvió ruta pero no existe: {source_path}"
                )
            else:
                logger.warning(
                    f"[FileFinder] ❌ No se encontró archivo de video para torrent {torrent_id}"
                )
                debug_info = self.transmission_client.debug_torrent_files(torrent_id)
                logger.warning(
                    f"[FileFinder] Debug: download_dir={debug_info.get('download_dir')}, files_count={debug_info.get('files_count')}"
                )
        except Exception as e:
            logger.warning(f"[FileFinder] Error usando TransmissionClient: {e}")
        return None

    def _find_fallback(
        self, filename: str, torrent_id: Optional[int] = None
    ) -> Optional[str]:
        """Búsqueda tradicional en carpetas"""
        search_paths = [self.TRANSMISSION_COMPLETE, self.TRANSMISSION_INCOMPLETE]

        if torrent_id and self.transmission_client:
            try:
                torrent = self.transmission_client.get_torrent(torrent_id)
                if (
                    torrent
                    and torrent.download_dir
                    and os.path.exists(torrent.download_dir)
                ):
                    logger.info(
                        f"[FileFinder] Fallback: buscando en downloadDir del torrent: {torrent.download_dir}"
                    )
                    for f in torrent.files:
                        file_name = f.get("name", "")
                        if file_name.lower().endswith(
                            (
                                ".mkv",
                                ".mp4",
                                ".avi",
                                ".mov",
                                ".webm",
                                ".m4v",
                                ".wmv",
                                ".flv",
                                ".ts",
                                ".m2ts",
                            )
                        ):
                            full_path = os.path.join(torrent.download_dir, file_name)
                            if os.path.exists(full_path):
                                logger.info(
                                    f"[FileFinder] ✓ Archivo encontrado en downloadDir: {full_path}"
                                )
                                return full_path
            except Exception as e:
                if "torrent not found" in str(e).lower():
                    logger.error(
                        f"[FileFinder] ❌ Torrent {torrent_id} no existe en Transmission"
                    )
                    active_torrents = self.transmission_client.get_torrents()
                    for t in active_torrents[:5]:
                        logger.info(f"   - ID: {t.id}, Nombre: {t.name}")

        for base in search_paths:
            candidate = os.path.join(base, filename)
            if os.path.exists(candidate):
                return candidate

        common_extensions = [".mkv", ".mp4", ".avi", ".mov", ".webm", ".m4v"]
        for base in search_paths:
            for ext in common_extensions:
                if filename.lower().endswith(ext):
                    continue
                candidate = os.path.join(base, filename + ext)
                if os.path.exists(candidate):
                    return candidate

        for base in search_paths:
            if os.path.exists(base):
                try:
                    files = os.listdir(base)
                    logger.info(f"[FileFinder] Archivos en {base}: {files[:10]}...")
                except Exception as e:
                    logger.warning(f"[FileFinder] Error listando {base}: {e}")

        return None
