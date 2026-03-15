"""
Servicio de manejo de errores de optimización

Maneja la limpieza y registro de errores cuando falla una optimización.
"""

import logging
import os

logger = logging.getLogger(__name__)


class OptimizationErrorHandler:
    """Maneja los errores de optimización"""

    def handle_error(
        self,
        process_id: str,
        error_message: str,
        pending: dict,
        history_service,
    ):
        """
        Maneja el error de optimización: limpia archivos temporales y registra el error.

        Args:
            process_id: ID del proceso de optimización
            error_message: Mensaje de error detallado
            pending: Datos pendientes del proceso
            history_service: Servicio de historial para registrar el error
        """
        if not pending:
            logger.error(
                f"[ErrorHandler] No se encontró metadata para proceso {process_id}"
            )
            return

        try:
            original_filename = pending.get("original_filename", "desconocido")
            shared_input = pending.get("shared_input")
            source_path = pending.get("source_path")
            torrent_id = pending.get("torrent_id")

            if shared_input and os.path.exists(shared_input):
                try:
                    os.remove(shared_input)
                    logger.info(
                        f"[ErrorHandler] Limpiado archivo temporal: {shared_input}"
                    )
                except Exception as e:
                    logger.warning(
                        f"[ErrorHandler] Error limpiando {shared_input}: {e}"
                    )

            output_path = pending.get("output_path")
            if output_path and os.path.exists(output_path):
                try:
                    os.remove(output_path)
                    logger.info(
                        f"[ErrorHandler] Limpiado archivo de salida: {output_path}"
                    )
                except Exception as e:
                    logger.warning(f"[ErrorHandler] Error limpiando {output_path}: {e}")

            if history_service:
                history_service.add_entry(
                    process_id=process_id,
                    final_path="",
                    pending=pending,
                    status="error",
                    error_message=error_message,
                )

            logger.warning(
                f"[ErrorHandler] ✓ Optimización fallida para {original_filename}. Error: {error_message}"
            )

        except Exception as e:
            logger.error(f"[ErrorHandler] Error manejando fallo de optimización: {e}")
