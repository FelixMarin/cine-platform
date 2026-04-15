"""
Caso de uso - Encolar optimización de video
"""

from typing import Dict

from src.domain.ports.out.services.queue_service import IQueueService


class QueueOptimizationUseCase:
    """Caso de uso para encolar una tarea de optimización de video"""

    def __init__(self, queue_service: IQueueService):
        self._queue_service = queue_service

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
