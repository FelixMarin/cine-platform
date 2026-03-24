"""
Rutas de API - Endpoints JSON
"""

from flask import Blueprint, jsonify

api_bp = Blueprint("api", __name__, url_prefix="/api")


def init_api_routes():
    """Inicializa las rutas de API"""
    pass


@api_bp.route("/health", methods=["GET"])
def health():
    """Health check"""
    return jsonify({"status": "ok"})
