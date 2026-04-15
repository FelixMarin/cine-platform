"""
Caso de uso - Optimizar video
"""
from typing import Dict, Optional

from src.domain.ports.out.services.IFileFinder import IFileFinder
from src.domain.ports.out.services.encoder_service import IEncoderService
from src.domain.ports.out.services.queue_service import IQueueService


class OptimizeMovieUseCase:
    """Caso de uso para optimizar videos"""

    VALID_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

    def __init__(
        self,
        queue_service: IQueueService,
        encoder_service: IEncoderService = None,
        file_finder: IFileFinder = None,
    ):
        self._queue_service = queue_service
        self._encoder_service = encoder_service
        self._file_finder = file_finder

    def execute(
        self,
        file_path: str,
        profile: str = "balanced",
    ) -> Dict:
        """
        Añade una tarea de optimización a la cola

        Args:
            file_path: Ruta del archivo a optimizar
            profile: Perfil de optimización

        Returns:
            Diccionario con el estado de la tarea
        """
        filename = file_path.rsplit("/", 1)[-1] if "/" in file_path else file_path

        task = {
            "filename": filename,
            "filepath": file_path,
            "profile": profile,
            "status": "queued",
        }

        success = self._queue_service.add_task(task)

        return {
            "success": success,
            "filename": filename,
            "profile": profile,
            "status": "queued" if success else "error",
        }

    def process_folder(
        self,
        folder_path: str,
        profile: str = "balanced",
    ) -> Dict:
        """
        Añade todos los videos de una carpeta a la cola

        Args:
            folder_path: Ruta de la carpeta
            profile: Perfil de optimización

        Returns:
            Diccionario con el resultado
        """
        if self._file_finder is None:
            return {
                "success": False,
                "added_count": 0,
                "profile": profile,
                "error": "FileFinder not configured",
            }

        added_count = 0
        files = self._file_finder.list_files(folder_path)

        for file_path in files:
            ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
            ext = f".{ext}"
            if ext in self.VALID_EXTENSIONS:
                task = {
                    "filename": file_path.rsplit("/", 1)[-1],
                    "filepath": file_path,
                    "profile": profile,
                    "status": "queued",
                }
                if self._queue_service.add_task(task):
                    added_count += 1

        return {
            "success": True,
            "added_count": added_count,
            "profile": profile,
        }

    def get_status(self) -> Dict:
        """Obtiene el estado actual del procesamiento"""
        return self._queue_service.get_status()

    def cancel_current(self) -> bool:
        """Cancela el procesamiento actual"""
        return self._queue_service.cancel_current_task()

    def get_available_profiles(self) -> Dict:
        """Obtiene los perfiles disponibles"""
        if self._encoder_service:
            return self._encoder_service.get_available_profiles()
        return {}


class EstimateSizeUseCase:
    """Caso de uso para estimar tamaño de video optimizado"""

    def __init__(self, encoder_service: IEncoderService):
        self._encoder_service = encoder_service

    def execute(
        self,
        file_path: str,
        profile: str = "balanced",
    ) -> Optional[Dict]:
        """
        Estima el tamaño final de un video optimizado

        Args:
            file_path: Ruta del archivo
            profile: Perfil de optimización

        Returns:
            Diccionario con la estimación
        """
        if not self._encoder_service:
            return None

        return self._encoder_service.estimate_size(file_path, profile)
