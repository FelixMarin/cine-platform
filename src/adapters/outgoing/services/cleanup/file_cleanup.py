"""
Implementación de ICleanupService para limpiar archivos temporales
"""

import os
import logging
from typing import Dict, Any, Optional

from src.core.ports.services.ICleanupService import ICleanupService


logger = logging.getLogger(__name__)


class FileCleanupService(ICleanupService):
    """
    Servicio para limpiar archivos temporales después de optimización
    """

    def cleanup(
        self,
        shared_input: Optional[str] = None,
        source_path: Optional[str] = None,
        torrent_id: Optional[int] = None,
        transmission_client: Any = None,
    ) -> Dict[str, Any]:
        """
        Limpia archivos temporales y opcionalmente elimina el torrent

        Args:
            shared_input: Ruta del archivo temporal en /shared/input/
            source_path: Ruta del archivo fuente original
            torrent_id: ID del torrent en Transmission
            transmission_client: Cliente de Transmission

        Returns:
            Dict con resultados de la limpieza
        """
        result = {
            "source_deleted": False,
            "shared_input_deleted": False,
            "torrent_deleted": False,
            "errors": [],
        }

        delete_source_file = (
            os.environ.get("DELETE_SOURCE_FILE", "true").lower() == "true"
        )

        if delete_source_file and source_path and os.path.exists(source_path):
            try:
                os.remove(source_path)
                logger.info(f"[FileCleanup] ✓ Archivo fuente eliminado: {source_path}")
                result["source_deleted"] = True
            except Exception as e:
                logger.error(f"[FileCleanup] Error eliminando archivo fuente: {e}")
                result["errors"].append(str(e))

        if shared_input and os.path.exists(shared_input):
            try:
                os.remove(shared_input)
                logger.info(
                    f"[FileCleanup] ✓ Archivo temporal eliminado: {shared_input}"
                )
                result["shared_input_deleted"] = True
            except Exception as e:
                logger.error(f"[FileCleanup] Error eliminando archivo temporal: {e}")
                result["errors"].append(str(e))

        delete_torrent = (
            os.environ.get("DELETE_TORRENT_AFTER_OPTIMIZATION", "true").lower()
            == "true"
        )
        
        # Eliminar el torrent de Transmission solo si la optimización fue exitosa
        if delete_torrent and transmission_client and torrent_id:
            try:
                transmission_client.remove_torrent(torrent_id, delete_files=False)
                logger.info(
                    f"🗑️ Torrent {torrent_id} eliminado de Transmission después de optimización exitosa"
                )
                result["torrent_deleted"] = True
            except Exception as e:
                logger.error(f"[FileCleanup] Error eliminando torrent {torrent_id}: {e}")
                result["errors"].append(str(e))

        return result
