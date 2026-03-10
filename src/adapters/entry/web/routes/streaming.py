"""
Rutas de Streaming - Reproducción de video
"""
from flask import Blueprint, send_file, request, Response, jsonify
import os
import mimetypes

streaming_bp = Blueprint('streaming', __name__, url_prefix='/api/streaming')

# Blueprint adicional para /stream/ (sin prefijo /api/)
stream_page_bp = Blueprint('stream_page', __name__)


@stream_page_bp.route('/stream/<path:filename>')
def stream_page_video(filename):
    """Stream de video en /stream/ (para compatibilidad con templates)"""
    return stream_video(filename)


def init_streaming_routes():
    """Inicializa las rutas de streaming"""
    pass


@streaming_bp.route('/<path:filename>')
def stream_video(filename):
    """Stream de video con soporte para Range requests"""
    import time
    import logging
    logger = logging.getLogger(__name__)
    
    start_total = time.time()
    logger.info(f"🎬 Streaming iniciado para: {filename}")
    
    # Obtener la ruta del archivo
    movies_folder = os.environ.get('MOVIES_FOLDER', '/mnt/DATA_2TB/audiovisual')
    
    # URL decode el filename
    import urllib.parse
    filename = urllib.parse.unquote(filename)
    
    # El path de la URL no incluye el leading slash, pero las rutas son absolutas
    # Agregar '/' al inicio si no lo tiene
    if not filename.startswith('/'):
        filename = '/' + filename
    
    # Verificar si es una ruta válida existente
    # Primero probar como ruta absoluta
    start_check = time.time()
    if os.path.exists(filename):
        file_path = filename
    # Luego probar prependeando MOVIES_FOLDER
    elif os.path.exists(os.path.join(movies_folder, filename)):
        file_path = os.path.join(movies_folder, filename)
    else:
        return 'File not found', 404
    
    check_time = time.time() - start_check
    logger.debug(f"⏱️ File check: {check_time:.3f}s - path: {file_path}")
    
    if not os.path.exists(file_path):
        return 'File not found', 404
    
    # Obtener tamaño del archivo
    start_size = time.time()
    file_size = os.path.getsize(file_path)
    size_time = time.time() - start_size
    logger.debug(f"⏱️ File size: {size_time:.3f}s - {file_size/1024/1024:.2f}MB")
    
    # Obtener rango de bytes si existe
    range_header = request.headers.get('Range')
    
    if range_header:
        # Parsear rango
        range_match = range_header.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        
        # Limitar el rango
        if end >= file_size:
            end = file_size - 1
        
        # Calcular tamaño del chunk
        chunk_size = end - start + 1
        
        # Leer el chunk
        with open(file_path, 'rb') as f:
            f.seek(start)
            data = f.read(chunk_size)
        
        # Headers de respuesta
        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': chunk_size,
            'Content-Type': 'video/mp4',
        }
        
        total_time = time.time() - start_total
        logger.debug(f"⏱️ Range request TOTAL: {total_time:.3f}s")
        
        return Response(data, status=206, headers=headers)
    else:
        total_time = time.time() - start_total
        logger.info(f"⏱️ Full request TOTAL: {total_time:.3f}s")
        
        # Enviar archivo completo
        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=filename
        )


@streaming_bp.route('/info/<path:filename>')
def video_info(filename):
    """Información del video"""
    movies_folder = os.environ.get('MOVIES_FOLDER', '/mnt/DATA_2TB/audiovisual')
    file_path = os.path.join(movies_folder, filename)
    
    if not os.path.exists(file_path):
        return jsonify({'error': 'File not found'}), 404
    
    file_size = os.path.getsize(file_path)
    return jsonify({
        'filename': filename,
        'size': file_size,
        'size_mb': round(file_size / (1024 * 1024), 2)
    })


@streaming_bp.route('/id/<movie_id>')
def stream_video_by_id(movie_id):
    """Streaming de video usando ID de película (desde caché) - Optimizado para NAS"""
    import time
    import logging
    import urllib.parse
    from flask import send_file, request, Response
    
    logger = logging.getLogger(__name__)
    start_total = time.time()
    
    logger.info(f"🎬 Streaming por ID: {movie_id}")
    
    # Buffer grande para mejor rendimiento en NAS/HDD
    BUFFER_SIZE = 1024 * 1024  # 1MB buffer
    
    # Usar el repositorio para obtener la película por ID (usa caché)
    try:
        from src.adapters.config.dependencies import get_movie_repository
        repo = get_movie_repository()
        movie = repo.get_by_id(movie_id)
        
        if not movie:
            logger.warning(f"⚠️ Película no encontrada: {movie_id}")
            return 'Movie not found', 404
        
        file_path = movie['path']
        logger.info(f"✅ ID {movie_id} -> {file_path}")
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo película {movie_id}: {e}")
        return f'Error: {str(e)}', 500
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        logger.warning(f"⚠️ Archivo no encontrado: {file_path}")
        return 'File not found', 404
    
    # Obtener tamaño del archivo
    start_size = time.time()
    file_size = os.path.getsize(file_path)
    size_time = time.time() - start_size
    logger.debug(f"⏱️ File size: {size_time:.3f}s - {file_size/1024/1024:.2f}MB")
    
    # Obtener rango de bytes si existe
    range_header = request.headers.get('Range')
    
    if range_header:
        # Parsear rango
        range_match = range_header.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        
        # Limitar el rango
        if end >= file_size:
            end = file_size - 1
        
        # Calcular tamaño del chunk
        chunk_size = end - start + 1
        
        logger.debug(f"📡 Range: {start}-{end} ({chunk_size/1024/1024:.1f}MB) - Buffer: {BUFFER_SIZE/1024}KB")
        
        # Generador con buffer grande para streaming eficiente
        def generate_large_chunks():
            with open(file_path, 'rb') as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(BUFFER_SIZE, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)
        
        # Headers de respuesta
        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(chunk_size),
            'Content-Type': 'video/mp4',
        }
        
        total_time = time.time() - start_total
        logger.info(f"⏱️ Range request TOTAL: {total_time:.3f}s")
        
        return Response(generate_large_chunks(), status=206, headers=headers)
    else:
        total_time = time.time() - start_total
        logger.info(f"⏱️ Full request TOTAL: {total_time:.3f}s")
        
        # Enviar archivo completo
        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=os.path.basename(file_path)
        )


@streaming_bp.route('/episode/<episode_id>')
def stream_episode_by_id(episode_id):
    """Streaming de video usando ID de episodio"""
    import time
    import logging
    import urllib.parse
    from flask import send_file, request, Response
    
    logger = logging.getLogger(__name__)
    start_total = time.time()
    
    logger.info(f"📺 Streaming de episodio: {episode_id}")
    
    # Buffer grande para mejor rendimiento en NAS/HDD
    BUFFER_SIZE = 1024 * 1024  # 1MB buffer
    
    # Usar el repositorio de series para obtener el episodio
    try:
        from src.adapters.config.dependencies import get_serie_repository
        from src.infrastructure.config.settings import get_settings
        
        settings = get_settings()
        series_folder = settings.SERIES_FOLDER
        
        serie_repo = get_serie_repository()
        
        if not serie_repo:
            logger.error("❌ Repositorio de series no disponible")
            return 'Serie repository not available', 500
        
        # Buscar el episodio
        episode = None
        series = serie_repo.list_all()
        
        for serie in series:
            episodes = serie.get('episodes', [])
            for ep in episodes:
                ep_id = str(ep.get('id') or ep.get('episode_id') or '')
                if ep_id == episode_id or ep_id == episode_id.replace('ep_', ''):
                    episode = ep
                    break
            if episode:
                break
        
        if not episode:
            logger.warning(f"⚠️ Episodio no encontrado: {episode_id}")
            return 'Episode not found', 404
        
        # Obtener la ruta del archivo
        filename = episode.get('filename')
        
        # Buscar en las carpetas de series
        if not series_folder:
            series_folder = '/mnt/servidor/Data2TB/audiovisual/series'
        
        # Buscar el archivo en la carpeta de la serie
        serie_name = episode.get('serie_name', '')
        season = episode.get('season', 1)
        
        # Construir posibles rutas
        possible_paths = [
            os.path.join(series_folder, serie_name, f"Season {season}", filename),
            os.path.join(series_folder, serie_name, filename),
            os.path.join(series_folder, filename),
        ]
        
        file_path = None
        for path in possible_paths:
            if os.path.exists(path):
                file_path = path
                break
        
        if not file_path:
            logger.warning(f"⚠️ Archivo de episodio no encontrado en ninguna ruta: {possible_paths}")
            return 'File not found', 404
        
        logger.info(f"✅ Episodio {episode_id} -> {file_path}")
        
    except Exception as e:
        logger.error(f"❌ Error obteniendo episodio {episode_id}: {e}")
        return f'Error: {str(e)}', 500
    
    # Verificar que el archivo existe
    if not os.path.exists(file_path):
        logger.warning(f"⚠️ Archivo no encontrado: {file_path}")
        return 'File not found', 404
    
    # Obtener tamaño del archivo
    start_size = time.time()
    file_size = os.path.getsize(file_path)
    size_time = time.time() - start_size
    logger.debug(f"⏱️ File size: {size_time:.3f}s - {file_size/1024/1024:.2f}MB")
    
    # Obtener rango de bytes si existe
    range_header = request.headers.get('Range')
    
    if range_header:
        # Parsear rango
        range_match = range_header.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if range_match[1] else file_size - 1
        
        # Limitar el rango
        if end >= file_size:
            end = file_size - 1
        
        # Calcular tamaño del chunk
        chunk_size = end - start + 1
        
        logger.debug(f"📡 Range: {start}-{end} ({chunk_size/1024/1024:.1f}MB)")
        
        # Generador con buffer grande para streaming eficiente
        def generate_large_chunks():
            with open(file_path, 'rb') as f:
                f.seek(start)
                remaining = chunk_size
                while remaining > 0:
                    read_size = min(BUFFER_SIZE, remaining)
                    chunk = f.read(read_size)
                    if not chunk:
                        break
                    yield chunk
                    remaining -= len(chunk)
        
        # Headers de respuesta
        headers = {
            'Content-Range': f'bytes {start}-{end}/{file_size}',
            'Accept-Ranges': 'bytes',
            'Content-Length': str(chunk_size),
            'Content-Type': 'video/mp4',
        }
        
        total_time = time.time() - start_total
        logger.info(f"⏱️ Range request TOTAL: {total_time:.3f}s")
        
        return Response(generate_large_chunks(), status=206, headers=headers)
    else:
        total_time = time.time() - start_total
        logger.info(f"⏱️ Full request TOTAL: {total_time:.3f}s")
        
        # Enviar archivo completo
        return send_file(
            file_path,
            mimetype='video/mp4',
            as_attachment=False,
            download_name=os.path.basename(file_path)
        )
