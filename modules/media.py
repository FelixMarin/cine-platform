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

    def _generate_thumbnail(self, video_path, thumbnail_path):
        try:
            subprocess.run([
                "ffmpeg", "-i", video_path,
                "-ss", "00:00:10", "-vframes", "1",
                "-vf", "scale=320:-1",
                thumbnail_path
            ], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error al generar miniatura para {video_path}: {e}")

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

        for root, _, files in os.walk(self.movies_folder):
            categoria = os.path.relpath(root, self.movies_folder).replace("\\", "/")

            # Ignorar raíz y carpeta de miniaturas
            if categoria == "." or categoria.lower() == "thumbnails":
                categoria = "Sin categoría"

            for file in files:
                if file.endswith(('.mkv', '.mp4', '.avi')):
                    full_path = os.path.join(root, file)
                    relative_path = os.path.relpath(full_path, self.movies_folder).replace("\\", "/")

                    thumbnail_path = os.path.join(
                        self.thumbnails_folder,
                        f"{os.path.splitext(file)[0]}.jpg"
                    )

                    if not os.path.exists(thumbnail_path):
                        self._generate_thumbnail(full_path, thumbnail_path)

                    item = {
                        "name": self._clean_filename(file),
                        "path": relative_path,
                        "thumbnail": f"/thumbnails/{os.path.basename(thumbnail_path)}"
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

        logger.info(
            f"Escaneo completado: {sum(len(v) for v in categorias.values())} películas "
            f"en {len(categorias)} categorías, {len(series)} series."
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