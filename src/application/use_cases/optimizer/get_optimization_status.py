"""
Caso de uso - Obtener estado de optimización
"""

from typing import Dict

from src.domain.ports.out.services.queue_service import IQueueService


class GetOptimizationStatusUseCase:
    """Caso de uso para obtener el estado actual del procesamiento"""

    def __init__(self, queue_service: IQueueService):
        self._queue_service = queue_service

    def execute(self) -> Dict:
        """Obtiene el estado actual del procesamiento"""
        return self._queue_service.get_status()
