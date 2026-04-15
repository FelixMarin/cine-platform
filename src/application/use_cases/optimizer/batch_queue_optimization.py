"""
Caso de uso - Encolar optimización batch de videos
"""

from typing import Dict

from src.domain.ports.out.services.IFileFinder import IFileFinder
from src.domain.ports.out.services.queue_service import IQueueService


class BatchQueueOptimizationUseCase:
    """Caso de uso para encolar múltiples videos de una carpeta"""

    VALID_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

    def __init__(self, queue_service: IQueueService, file_finder: IFileFinder):
        self._queue_service = queue_service
        self._file_finder = file_finder

    def execute(
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
