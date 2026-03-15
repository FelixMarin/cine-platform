"""
Servicio de historial de optimizaciones

Maneja el registro de optimizaciones en la base de datos.
"""

import logging
import os
from typing import Optional
from datetime import datetime

from src.infrastructure.database.connection import get_session_maker
from src.infrastructure.models.optimization_history import OptimizationHistory

logger = logging.getLogger(__name__)


class OptimizationHistoryService:
    """Servicio para gestionar el historial de optimizaciones"""

    def add_entry(
        self,
        process_id: str,
        final_path: str,
        pending: dict,
        status: str = "completed",
        error_message: Optional[str] = None,
        transmission_client=None,
        progress=None,
    ):
        """
        Añade una entrada al historial de optimizaciones.

        Args:
            process_id: ID del proceso de optimización
            final_path: Ruta final del archivo optimizado
            pending: Datos pendientes del proceso
            status: Estado de la optimización ('completed', 'error', 'cancelled')
            error_message: Mensaje de error si falló
            transmission_client: Cliente de Transmission para obtener info de torrents
            progress: Objeto OptimizationProgress con datos de tiempo
        """
        db = None
        try:
            user_id = pending.get("user_id")

            logger.info(
                f"[HistoryService] Guardando historial para process_id={process_id}, status={status}"
            )

            if not user_id:
                logger.warning(
                    "[HistoryService] ⚠️ No hay user_id, el historial no tendrá usuario asignado"
                )

            optimization_duration = None
            if progress and hasattr(progress, "start_time"):
                optimization_duration = int(
                    datetime.now().timestamp() - progress.start_time
                )

            torrent = None
            torrent_id = pending.get("torrent_id")
            if torrent_id and transmission_client:
                try:
                    torrent = transmission_client.get_torrent(torrent_id)
                except Exception as e:
                    logger.warning(
                        f"[HistoryService] No se pudo obtener torrent {torrent_id}: {e}"
                    )

            download_duration = None
            if (
                torrent
                and hasattr(torrent, "added_date")
                and hasattr(torrent, "done_date")
            ):
                download_duration = int(torrent.done_date - torrent.added_date)

            original_size = None
            if source_path := pending.get("source_path"):
                if os.path.exists(source_path):
                    original_size = os.path.getsize(source_path)

            optimized_size = None
            if os.path.exists(final_path):
                optimized_size = os.path.getsize(final_path)

            compression_ratio = None
            if original_size and optimized_size:
                compression_ratio = round((1 - optimized_size / original_size) * 100, 2)

            opt_start = (
                datetime.fromtimestamp(progress.start_time)
                if progress and hasattr(progress, "start_time")
                else datetime.now()
            )
            opt_end = datetime.now() if status == "completed" else None

            history_data = {
                "process_id": process_id,
                "torrent_id": torrent_id,
                "torrent_name": torrent.name
                if torrent
                else pending.get("original_filename"),
                "category": pending.get("category"),
                "input_file": pending.get("source_path", ""),
                "output_file": final_path,
                "output_filename": pending.get("final_filename"),
                "optimization_start": opt_start,
                "optimization_end": opt_end,
                "download_duration_seconds": download_duration,
                "optimization_duration_seconds": optimization_duration,
                "status": status,
                "error_message": error_message,
                "file_size_bytes": optimized_size,
                "original_size_bytes": original_size,
                "compression_ratio": compression_ratio,
                "app_user_id": user_id,
            }

            SessionLocal = get_session_maker()
            db = SessionLocal()

            entry = OptimizationHistory(
                process_id=history_data["process_id"],
                torrent_id=history_data["torrent_id"],
                torrent_name=history_data["torrent_name"],
                category=history_data["category"],
                input_file=history_data["input_file"],
                output_file=history_data["output_file"],
                output_filename=history_data["output_filename"],
                optimization_start=history_data["optimization_start"],
                optimization_end=history_data["optimization_end"],
                download_duration_seconds=history_data["download_duration_seconds"],
                optimization_duration_seconds=history_data[
                    "optimization_duration_seconds"
                ],
                status=history_data["status"],
                error_message=history_data["error_message"],
                file_size_bytes=history_data["file_size_bytes"],
                original_size_bytes=history_data["original_size_bytes"],
                compression_ratio=history_data["compression_ratio"],
                app_user_id=history_data["app_user_id"],
            )

            db.add(entry)
            db.commit()

            logger.info(
                f"[HistoryService] ✅ Entrada añadida al historial (id={entry.id}, process_id={process_id})"
            )

        except Exception as e:
            logger.error(
                f"[HistoryService] ❌ Error añadiendo al historial: {type(e).__name__}: {e}"
            )
            import traceback

            logger.error(f"[HistoryService] Traceback: {traceback.format_exc()}")
            if db:
                try:
                    db.rollback()
                except Exception as rollback_err:
                    logger.error(f"[HistoryService] Error en rollback: {rollback_err}")
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass
