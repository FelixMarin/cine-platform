import os
import subprocess
from modules.core import IMediaRepository
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

class FileSystemMediaRepository(IMediaRepository):
    def __init__(self, movies_folder):
        self.movies_folder = movies_folder
        logger.info(f"Movies folder: {self.movies_folder}")
        self.thumbnails_folder = os.path.join(movies_folder, "thumbnails")
        logger.info(f"Thumbnails folder: {self.thumbnails_folder}")
        if not os.path.exists(self.thumbnails_folder):
            os.makedirs(self.thumbnails_folder)

    def _check_ffmpeg_webp_support(self):
        """Verifica si ffmpeg soporta WebP"""
        try:
            result = subprocess.run([
                "ffmpeg", "-encoders"
            ], capture_output=True, text=True)
            return "libwebp" in result.stdout
        except:
            return False

    def _generate_thumbnail(self, video_path, thumbnail_path):
        try:
            # Verificar si debemos usar WebP
            use_webp = thumbnail_path.endswith('.webp')
            
            # Parámetros comunes
            base_cmd = [
                "ffmpeg", "-i", video_path,
                "-ss", "00:00:10",  # Capturar en el segundo 10
                "-vframes", "1",      # Un solo frame
                "-vf", "scale=320:-1", # Escalar a ancho 320, alto automático
            ]
            
            if use_webp:
                # Optimización para WebP
                cmd = base_cmd + [
                    "-c:v", "libwebp",   # Codec WebP
                    "-lossless", "0",     # Compresión con pérdida (más pequeño)
                    "-compression_level", "6",  # Nivel de compresión (0-6)
                    "-q:v", "75",         # Calidad (0-100)
                    "-preset", "picture",  # Preset para fotos
                    thumbnail_path
                ]
            else:
                # Optimización para JPG
                cmd = base_cmd + [
                    "-q:v", "5",          # Calidad (2-31, menor = mejor)
                    "-pix_fmt", "yuvj420p", # Formato de píxeles
                    thumbnail_path
                ]
            
            logger.debug(f"Generando thumbnail: {' '.join(cmd)}")
            
            subprocess.run(cmd, check=True, 
                         stdout=subprocess.DEVNULL, 
                         stderr=subprocess.DEVNULL)
            
            # Si generamos WebP, también crear una versión JPG como fallback
            if use_webp:
                jpg_path = thumbnail_path.replace('.webp', '.jpg')
                if not os.path.exists(jpg_path):
                    jpg_cmd = [
                        "ffmpeg", "-i", thumbnail_path,
                        "-q:v", "5",
                        jpg_path
                    ]
                    subprocess.run(jpg_cmd, check=True,
                                 stdout=subprocess.DEVNULL,
                                 stderr=subprocess.DEVNULL)
            
            logger.info(f"Thumbnail generado: {thumbnail_path}")
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Error al generar miniatura para {video_path}: {e}")
        except Exception as e:
            logger.error(f"Error inesperado al generar miniatura: {e}")

    def _generate_all_formats(self, video_path, base_name):
        """Genera thumbnails en múltiples formatos"""
        # Generar JPG (formato por defecto)
        jpg_path = os.path.join(self.thumbnails_folder, f"{base_name}.jpg")
        if not os.path.exists(jpg_path):
            self._generate_thumbnail(video_path, jpg_path)
        
        # Generar WebP si ffmpeg lo soporta
        if self._check_ffmpeg_webp_support():
            webp_path = os.path.join(self.thumbnails_folder, f"{base_name}.webp")
            if not os.path.exists(webp_path):
                self._generate_thumbnail(video_path, webp_path)

    def _clean_filename(self, filename):
        name = os.path.splitext(filename)[0]

        # Eliminar sufijos comunes
        for suffix in ["-optimized", "_optimized", "-serie"]:
            if name.lower().endswith(suffix):
                name = name[: -len(suffix)]

        # Reemplazar separadores por espacios
        name = name.replace("-", " ").replace("_", " ").replace(".", " ")

        # Capitalizar sin romper códigos tipo S01e01
        def smart_cap(word):
            # Si contiene números, solo capitaliza la primera letra
            if any(c.isdigit() for c in word):
                return word[0].upper() + word[1:]
            return word.capitalize()

        return " ".join(smart_cap(w) for w in name.split())

    def list_content(self):
        categorias = {}
        series = {}
        
        # Verificar soporte WebP al inicio
        webp_supported = self._check_ffmpeg_webp_support()
        logger.info(f"Soporte WebP en ffmpeg: {webp_supported}")

        for root, _, files in os.walk(self.movies_folder):
            categoria = os.path.relpath(root, self.movies_folder).replace("\\", "/")

            # Ignorar raíz y carpeta de miniaturas
            if categoria == "." or categoria.lower() == "thumbnails":
                categoria = "Sin categoría"

            for file in files:
                if file.endswith(('.mkv', '.mp4', '.avi')):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.movies_folder).replace("\\", "/")
                    
                    base_name = os.path.splitext(file)[0]
                    
                    # Verificar si existe WebP, si no, generar ambos formatos
                    webp_path = os.path.join(self.thumbnails_folder, f"{base_name}.webp")
                    jpg_path = os.path.join(self.thumbnails_folder, f"{base_name}.jpg")
                    
                    if not os.path.exists(webp_path) and not os.path.exists(jpg_path):
                        # No existe ningún thumbnail, generar ambos
                        self._generate_all_formats(full_path, base_name)
                    
                    # Determinar qué thumbnail servir
                    # En el listado, enviamos ambos formatos para que el frontend decida
                    thumbnail_urls = {
                        "jpg": f"/thumbnails/{base_name}.jpg" if os.path.exists(jpg_path) else None,
                        "webp": f"/thumbnails/{base_name}.webp" if os.path.exists(webp_path) else None
                    }
                    
                    # Usar JPG como fallback si no hay WebP
                    primary_thumbnail = thumbnail_urls["webp"] or thumbnail_urls["jpg"]

                    item = {
                        "name": self._clean_filename(file),
                        "path": relative_path,
                        "thumbnail": primary_thumbnail,
                        "thumbnails": thumbnail_urls  # Enviar ambos para detección en frontend
                    }

                    # Detectar series por sufijo
                    if "-serie" in file.lower():
                        series_name = item["name"].rsplit(" T", 1)[0]
                        if series_name not in series:
                            series[series_name] = []
                        series[series_name].append(item)
                    else:
                        # Agrupar por categoría
                        if categoria not in categorias:
                            categorias[categoria] = []
                        categorias[categoria].append(item)

        # Ordenar categorías y contenido
        categorias = {
            cat: sorted(pelis, key=lambda x: x["name"])
            for cat, pelis in sorted(categorias.items())
        }

        series = {
            k: sorted(v, key=lambda x: x["name"])
            for k, v in sorted(series.items())
        }

        # Estadísticas de formatos
        webp_count = sum(1 for cat in categorias.values() 
                        for m in cat if m.get("thumbnails", {}).get("webp"))
        jpg_count = sum(1 for cat in categorias.values() 
                       for m in cat if m.get("thumbnails", {}).get("jpg"))
        
        logger.info(
            f"Escaneo completado: {sum(len(v) for v in categorias.values())} películas "
            f"en {len(categorias)} categorías, {len(series)} series. "
            f"Thumbnails: {webp_count} WebP, {jpg_count} JPG"
        )

        return categorias, series

    def get_safe_path(self, filename):
        """
        Valida que la ruta solicitada esté realmente dentro del directorio base
        para prevenir ataques de Path Traversal.
        """
        base_dir = os.path.abspath(self.movies_folder)
        target_path = os.path.abspath(os.path.join(base_dir, filename))
        
        if not target_path.startswith(base_dir):
            logger.warning(f"ALERTA DE SEGURIDAD: Intento de Path Traversal detectado: {filename}")
            return None
        return target_path
    
    def get_thumbnails_folder(self):
        return self.thumbnails_folder