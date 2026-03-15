"""
Servicio de gestión de archivos de torrent

Maneja la búsqueda y gestión de archivos dentro de los torrents.
"""

import logging
import os
from typing import Optional, List, Dict, Any

from src.adapters.outgoing.services.transmission.models import (
    TorrentDownload,
    VIDEO_EXTENSIONS,
)

logger = logging.getLogger(__name__)


class TorrentFileManager:
    """Gestiona los archivos dentro de los torrents"""

    @staticmethod
    def find_video_files(torrent: TorrentDownload) -> List[Dict[str, Any]]:
        """
        Encuentra archivos de video en un torrent.

        Args:
            torrent: Objeto TorrentDownload

        Returns:
            Lista de archivos de video encontrados
        """
        video_files = []
        for f in torrent.files:
            file_name = f.get("name", "")
            if file_name.lower().endswith(VIDEO_EXTENSIONS):
                video_files.append(f)
        return video_files

    @staticmethod
    def get_video_file_path(
        download_dir: str,
        files: List[Dict[str, Any]],
    ) -> Optional[str]:
        """
        Obtiene la ruta del archivo de video principal.

        Args:
            download_dir: Directorio de descarga
            files: Lista de archivos del torrent

        Returns:
            Ruta completa del archivo de video o None
        """
        video_files = TorrentFileManager.find_video_files_by_extension(files)
        if video_files:
            primary_file = max(video_files, key=lambda f: f.get("length", 0))
            file_name = primary_file.get("name", "")
            return os.path.join(download_dir, file_name)
        return None

    @staticmethod
    def find_video_files_by_extension(
        files: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Filtra archivos por extensión de video.

        Args:
            files: Lista de archivos

        Returns:
            Lista de archivos de video
        """
        return [
            f for f in files if f.get("name", "").lower().endswith(VIDEO_EXTENSIONS)
        ]

    @staticmethod
    def get_largest_video_file(files: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Obtiene el archivo de video más grande.

        Args:
            files: Lista de archivos

        Returns:
            El archivo más grande o None
        """
        video_files = TorrentFileManager.find_video_files_by_extension(files)
        if video_files:
            return max(video_files, key=lambda f: f.get("length", 0))
        return None
