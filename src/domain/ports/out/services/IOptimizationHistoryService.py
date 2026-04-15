"""
Puerto para el servicio de historial de optimizaciones
"""

from typing import Optional


class IOptimizationHistoryService:
    """Interface para el servicio de historial de optimizaciones"""

    def add_entry(
        self,
        process_id: str,
        final_path: str,
        pending: dict,
        status: str = "completed",
        error_message: Optional[str] = None,
    ) -> None:
        """Añade una entrada al historial de optimizaciones"""
        raise NotImplementedError
