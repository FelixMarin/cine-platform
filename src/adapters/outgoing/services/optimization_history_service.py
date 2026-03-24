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
                user_id = 1
                logger.warning(
                    "[HistoryService] ⚠️ No hay user_id, usando user_id=1 por defecto"
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

            # Validar que optimization_start no sea None (es NOT NULL en el modelo)
            if not opt_start:
                opt_start = datetime.now()
                logger.warning(
                    "[HistoryService] ⚠️ optimization_start es None, usando datetime.now()"
                )

            history_data = {
                "process_id": process_id,
                "torrent_id": torrent_id,
                "torrent_name": torrent.name
                if torrent
                else pending.get("original_filename"),
                "movie_name": torrent.name
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

            # Validar campos requeridos antes de guardar
            if not history_data["torrent_name"]:
                # Usar el nombre del archivo de entrada como fallback
                source_path = pending.get("source_path", "")
                history_data["torrent_name"] = (
                    os.path.basename(source_path) or "Unknown"
                )
                logger.warning(
                    f"[HistoryService] ⚠️ torrent_name es None, usando fallback: {history_data['torrent_name']}"
                )

            if not history_data["category"]:
                history_data["category"] = "unknown"
                logger.warning(
                    f"[HistoryService] ⚠️ category es None, usando fallback: unknown"
                )

            # Validar status (es NOT NULL en el modelo)
            if not history_data["status"]:
                history_data["status"] = "completed"
                logger.warning(
                    "[HistoryService] ⚠️ status es None, usando fallback: completed"
                )

            SessionLocal = get_session_maker()
            db = SessionLocal()

            entry = OptimizationHistory(
                process_id=history_data["process_id"],
                torrent_id=history_data["torrent_id"],
                torrent_name=history_data["torrent_name"],
                movie_name=history_data.get("movie_name", history_data["torrent_name"]),
                category=history_data["category"],
                input_file=history_data["input_file"],
                output_file=history_data["output_file"],
                output_filename=history_data["output_filename"],
                download_started=history_data.get("torrent_download_start"),
                download_completed=history_data.get("torrent_download_end"),
                optimization_started=history_data["optimization_start"],
                optimization_completed=history_data["optimization_end"],
                download_duration_seconds=history_data["download_duration_seconds"],
                optimization_duration_seconds=history_data[
                    "optimization_duration_seconds"
                ],
                status=history_data["status"],
                error_message=history_data["error_message"],
                optimized_size_bytes=history_data["file_size_bytes"],
                original_size_bytes=history_data["original_size_bytes"],
                compression_ratio=history_data["compression_ratio"],
                app_user_id=history_data["app_user_id"],
            )

            db.add(entry)

            logger.info(
                f"[HistoryService] 💾 Guardando entrada: process_id={entry.process_id}, "
                f"torrent_name={entry.torrent_name}, movie_name={entry.movie_name}, "
                f"category={entry.category}, status={entry.status}"
            )
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
            # Re-lanzar la excepción para que el caller pueda manejarla
            raise
        finally:
            if db:
                try:
                    db.close()
                except Exception:
                    pass
