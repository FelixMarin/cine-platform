"""
Rutas API para el historial de optimizaciones
"""

from flask import Blueprint, request, jsonify
from sqlalchemy import desc
from src.infrastructure.database.connection import get_session_maker
from src.infrastructure.models.optimization_history import OptimizationHistory
from src.adapters.entry.web.middleware.auth_middleware import require_auth
import logging

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

        return jsonify({
            "success": True,
            "total": total,
            "limit": limit,
            "offset": offset,
            "entries": [
                {
                    "id": entry.id,
                    "process_id": entry.process_id,
                    "torrent_name": entry.torrent_name,
                    "category": entry.category,
                    "output_filename": entry.output_filename,
                    "optimization_start": entry.optimization_start.isoformat() if entry.optimization_start else None,
                    "optimization_end": entry.optimization_end.isoformat() if entry.optimization_end else None,
                    "download_duration": entry.download_duration_seconds,
                    "optimization_duration": entry.optimization_duration_seconds,
                    "status": entry.status,
                    "error_message": entry.error_message,
                    "compression_ratio": float(entry.compression_ratio) if entry.compression_ratio else None,
                    "file_size": entry.file_size_bytes,
                    "original_size": entry.original_size_bytes,
                    "created_at": entry.created_at.isoformat() if entry.created_at else None,
                }
                for entry in entries
            ]
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

        # Crear nueva entrada
        entry = OptimizationHistory(
            process_id=data.get('process_id'),
            torrent_id=data.get('torrent_id'),
            torrent_name=data.get('torrent_name'),
            category=data.get('category'),
            input_file=data.get('input_file'),
            output_file=data.get('output_file'),
            output_filename=data.get('output_filename'),
            optimization_start=data.get('optimization_start'),
            optimization_end=data.get('optimization_end'),
            download_duration_seconds=data.get('download_duration_seconds'),
            optimization_duration_seconds=data.get('optimization_duration_seconds'),
            status=data.get('status', 'completed'),
            error_message=data.get('error_message'),
            file_size_bytes=data.get('file_size_bytes'),
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
