"""
Servicio de búsqueda paralela

Maneja la búsqueda paralela en múltiples indexadores (Prowlarr, Jackett).
"""

import asyncio
import logging
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


class ParallelSearchService:
    """Servicio para búsqueda paralela en múltiples indexadores"""

    def __init__(self, prowlarr_client=None, jackett_client=None):
        self._prowlarr_client = prowlarr_client
        self._jackett_client = jackett_client

    def set_clients(self, prowlarr_client=None, jackett_client=None):
        """Establece los clientes de los indexadores"""
        if prowlarr_client:
            self._prowlarr_client = prowlarr_client
        if jackett_client:
            self._jackett_client = jackett_client

    async def search(
        self, query: str, limit: int = 20
    ) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Realiza búsqueda en paralelo en Prowlarr y Jackett.

        Args:
            query: Término de búsqueda
            limit: Límite de resultados por indexador

        Returns:
            Tupla (resultados, información de fuentes)
        """
        logger.info(
            f"[ParallelSearchService] 🚀 Iniciando búsqueda paralela para: '{query}'"
        )
        all_results = []
        source_info = {}

        prowlarr_task = None
        jackett_task = None

        if self._prowlarr_client:
            prowlarr_task = asyncio.create_task(
                self._search_prowlarr_safe(query, limit)
            )

        if self._jackett_client:
            jackett_task = asyncio.create_task(self._search_jackett_safe(query, limit))

        if prowlarr_task:
            prowlarr_results, prowlarr_success = await prowlarr_task
            all_results.extend(prowlarr_results)
            source_info["prowlarr"] = {
                "results": len(prowlarr_results),
                "success": prowlarr_success,
            }

        if jackett_task:
            jackett_results, jackett_success = await jackett_task
            all_results.extend(jackett_results)
            source_info["jackett"] = {
                "results": len(jackett_results),
                "success": jackett_success,
            }

        if not source_info:
            logger.warning("[ParallelSearchService] ⚠️ No hay indexadores disponibles")
            source_info["error"] = "No hay indexadores configurados"

        all_results = sorted(
            all_results,
            key=lambda x: (
                x.get("seeders", 0) if isinstance(x.get("seeders"), int) else 0
            ),
            reverse=True,
        )

        logger.info(
            f"[ParallelSearchService] ✅ Búsqueda completada: {len(all_results)} resultados"
        )
        return all_results, source_info

    async def _search_prowlarr_safe(
        self, query: str, limit: int
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Busca en Prowlarr de forma segura"""
        logger.info("[ParallelSearchService Prowlarr] ▶️ Iniciando búsqueda...")
        try:
            results = self._prowlarr_client.search_movies(query, limit=limit)
            formatted = self._prowlarr_client.format_results_for_frontend(results)
            for r in formatted:
                r["source"] = "prowlarr"
            logger.info(
                f"[ParallelSearchService Prowlarr] ✅ {len(formatted)} resultados"
            )
            return formatted, True
        except Exception as e:
            logger.error(f"[ParallelSearchService Prowlarr] ❌ Error: {str(e)}")
            return [], False

    async def _search_jackett_safe(
        self, query: str, limit: int
    ) -> Tuple[List[Dict[str, Any]], bool]:
        """Busca en Jackett de forma segura"""
        logger.info("[ParallelSearchService Jackett] ▶️ Iniciando búsqueda...")
        try:
            results = await self._jackett_client.search_movies(query, limit=limit)
            formatted = self._jackett_client.format_results_for_frontend(results)
            for r in formatted:
                r["source"] = "jackett"
            logger.info(
                f"[ParallelSearchService Jackett] ✅ {len(formatted)} resultados"
            )
            return formatted, True
        except Exception as e:
            logger.error(f"[ParallelSearchService Jackett] ❌ Error: {str(e)}")
            return [], False
