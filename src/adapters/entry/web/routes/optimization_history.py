"""
Rutas API para el historial de optimizaciones
"""

import logging

from flask import Blueprint, jsonify, request
from sqlalchemy import desc

from src.adapters.entry.web.middleware.auth_middleware import require_auth
from src.infrastructure.database.connection import get_session_maker
from src.adapters.outgoing.repositories.postgresql.models.optimization_history import OptimizationHistory

logger = logging.getLogger(__name__)
history_bp = Blueprint("history", __name__, url_prefix="/api/optimization-history")

# Log de las rutas registradas
logger.info("[History] Blueprint creado con prefijo: /api/optimization-history")


@history_bp.route("/", methods=["GET"])
@require_auth
def get_history():
    """
    Obtiene el historial de optimizaciones
    Se llama automáticamente al cargar la interfaz de descargas
    """
    db = None
    try:
        # Parámetros de paginación (opcionales)
        limit = int(request.args.get('limit', 100))
        offset = int(request.args.get('offset', 0))
        status = request.args.get('status')  # Filtrar por estado (opcional)

        SessionLocal = get_session_maker()
        db = SessionLocal()
        query = db.query(OptimizationHistory)

        if status:
            query = query.filter(OptimizationHistory.status == status)

        total = query.count()
        entries = query.order_by(desc(OptimizationHistory.created_at)).limit(limit).offset(offset).all()

        # Calcular duraciones para cada entrada
        entries_data = []
        for entry in entries:
            # Calcular duración de descarga si existen ambas fechas
            download_duration = None
            if entry.download_started and entry.download_completed:
                delta = entry.download_completed - entry.download_started
                download_duration = int(delta.total_seconds())

            # Calcular duración de optimización si existen ambas fechas
            optimization_duration = None
            if entry.optimization_started and entry.optimization_completed:
                delta = entry.optimization_completed - entry.optimization_started
                optimization_duration = int(delta.total_seconds())

            entries_data.append({
                "id": entry.id,
                "process_id": entry.process_id,
                "torrent_name": entry.torrent_name,
                "movie_name": entry.movie_name,
                "category": entry.category,
                "input_file": entry.input_file,
                "output_file": entry.output_file,
                "output_filename": entry.output_filename,
                # Usar los nombres correctos de la tabla
                "optimization_start": entry.optimization_started.isoformat() if entry.optimization_started else None,
                "optimization_end": entry.optimization_completed.isoformat() if entry.optimization_completed else None,
                "download_start": entry.download_started.isoformat() if entry.download_started else None,
                "download_end": entry.download_completed.isoformat() if entry.download_completed else None,
                # Duraciones calculadas
                "download_duration_seconds": download_duration,
                "optimization_duration_seconds": optimization_duration,
                "status": entry.status,
                "error_message": entry.error_message,
                "compression_ratio": float(entry.compression_ratio) if entry.compression_ratio else None,
                # Mapear optimized_size_bytes a file_size_bytes
                "file_size_bytes": entry.optimized_size_bytes,
                "original_size_bytes": entry.original_size_bytes,
                "created_at": entry.created_at.isoformat() if entry.created_at else None,
            })

        return jsonify({
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "entries": entries_data
        })
    except Exception as e:
        logger.error(f"[History] Error obteniendo historial: {e}")
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if db:
            db.close()


@history_bp.route("/<int:entry_id>", methods=["DELETE"])
@require_auth
def delete_history_entry(entry_id):
    """Elimina una entrada del historial (botón aspa)"""
    db = None
    try:
        SessionLocal = get_session_maker()
        db = SessionLocal()
        entry = db.query(OptimizationHistory).filter_by(id=entry_id).first()

        if not entry:
            return jsonify({"success": False, "error": "Entrada no encontrada"}), 404

        db.delete(entry)
        db.commit()

        logger.info(f"[History] Entrada {entry_id} eliminada del historial")
        return jsonify({"success": True, "message": "Entrada eliminada"})
    except Exception as e:
        logger.error(f"[History] Error eliminando entrada {entry_id}: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if db:
            db.close()


@history_bp.route("/latest", methods=["GET"])
@require_auth
def get_latest():
    """Obtiene las últimas 10 optimizaciones (para vista rápida)"""
    db = None
    try:
        SessionLocal = get_session_maker()
        db = SessionLocal()
        entries = db.query(OptimizationHistory).order_by(desc(OptimizationHistory.created_at)).limit(10).all()

        return jsonify({
            "success": True,
            "entries": [
                {
                    "id": e.id,
                    "torrent_name": e.torrent_name,
                    "status": e.status,
                    "created_at": e.created_at.isoformat() if e.created_at else None,
                }
                for e in entries
            ]
        })
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if db:
            db.close()


@history_bp.route("/add", methods=["POST"])
@require_auth
def add_history_entry():
    """Añade una nueva entrada al historial"""
    db = None
    try:
        data = request.get_json()
        if not data:
            return jsonify({"success": False, "error": "No se recibieron datos"}), 400

        SessionLocal = get_session_maker()
        db = SessionLocal()

        # Crear nueva entrada con los nombres correctos de la tabla
        entry = OptimizationHistory(
            process_id=data.get('process_id'),
            torrent_id=data.get('torrent_id'),
            torrent_name=data.get('torrent_name'),
            movie_name=data.get('movie_name'),
            category=data.get('category'),
            input_file=data.get('input_file'),
            output_file=data.get('output_file'),
            output_filename=data.get('output_filename'),
            # Usar los nombres correctos
            download_started=data.get('download_started') or data.get('download_start'),
            download_completed=data.get('download_completed') or data.get('download_end'),
            optimization_started=data.get('optimization_started') or data.get('optimization_start'),
            optimization_completed=data.get('optimization_completed') or data.get('optimization_end'),
            status=data.get('status', 'completed'),
            error_message=data.get('error_message'),
            # Mapear file_size_bytes a optimized_size_bytes
            optimized_size_bytes=data.get('file_size_bytes') or data.get('optimized_size_bytes'),
            original_size_bytes=data.get('original_size_bytes'),
            compression_ratio=data.get('compression_ratio'),
            app_user_id=data.get('app_user_id'),
        )

        db.add(entry)
        db.commit()

        logger.info(f"[History] Entrada añadida: {entry.process_id}")
        return jsonify({"success": True, "id": entry.id})
    except Exception as e:
        logger.error(f"[History] Error añadiendo entrada: {e}")
        if db:
            db.rollback()
        return jsonify({"success": False, "error": str(e)}), 500
    finally:
        if db:
            db.close()


def init_history_routes():
    """Inicializa las rutas de historial"""
    return history_bp
