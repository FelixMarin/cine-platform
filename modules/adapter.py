# modules/adapter.py
import os
import threading
import shutil
import time
from datetime import datetime
from modules.core import IOptimizerService
from modules.logging.logging_config import setup_logging
from .state import StateManager
from .ffmpeg import FFmpegHandler
from .pipeline import PipelineSteps

# Logging usando la carpeta definida en entorno
logger = setup_logging(os.environ.get("LOG_FOLDER"))


def mover_a_audiovisual(ruta_output):
    """
    Mueve el archivo optimizado a la carpeta final definida en MOVIES_FOLDER.
    Dentro de ella, usa el subdirectorio 'mkv'.
    """

    base_dir = os.environ["MOVIES_FOLDER"]  # obligatorio
    destino_dir = os.path.join(base_dir, "mkv")

    if not os.path.exists(destino_dir):
        logger.error(f"No se ha podido copiar el vídeo: la carpeta {destino_dir} no está disponible")
        return False

    try:
        os.makedirs(destino_dir, exist_ok=True)
        nombre_archivo = os.path.basename(ruta_output)
        destino = os.path.join(destino_dir, nombre_archivo)

        shutil.copy2(ruta_output, destino)
        logger.info(f"Vídeo copiado correctamente a {destino}")

        os.remove(ruta_output)
        logger.info(f"Archivo eliminado de outputs: {ruta_output}")

        return True

    except Exception as e:
        logger.error(f"Error copiando el archivo a {destino_dir}: {e}")
        return False


class FFmpegOptimizerAdapter(IOptimizerService):
    def __init__(self, upload_folder, temp_folder, output_folder):
        self.upload_folder = upload_folder
        self.temp_folder = temp_folder
        self.output_folder = output_folder

        # Extensiones válidas (si quieres, las pasamos a .env)
        self.valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}

        self.state_manager = StateManager()
        self.ffmpeg = FFmpegHandler(self.state_manager)
        self.steps = PipelineSteps(self.ffmpeg)

        for folder in [upload_folder, temp_folder, output_folder]:
            os.makedirs(folder, exist_ok=True)

    def _process_logic(self, video_path):
        start_time = time.time()
        if "-optimized" in video_path:
            return

        video_filename = os.path.basename(video_path)
        self.state_manager.set_current_video(video_filename)

        current_info = self.state_manager.state.video_info
        if not current_info or current_info.get("name") != video_filename:
            info = self.ffmpeg.get_video_info(video_path)
            self.state_manager.set_video_info(info)

        temp_original = os.path.join(self.temp_folder, video_filename)
        optimized_name = video_filename.rsplit('.', 1)[0] + "-optimized.mkv"
        temp_optimized = os.path.join(self.temp_folder, optimized_name)
        final_output = os.path.join(self.output_folder, optimized_name)

        status_msg = "Procesado correctamente"

        try:
            logger.info(f"Procesando {video_filename}")
            shutil.copy2(video_path, temp_original)

            # Paso único: Process (antes eran 1,2,3)
            self.state_manager.set_step(1)
            self.steps.process(temp_original, temp_optimized)

            # Validar duración (paso 2 visualmente)
            self.state_manager.set_step(2)
            dur_orig = self.ffmpeg.get_duration(temp_original)
            dur_opt = self.ffmpeg.get_duration(temp_optimized)
            if abs(dur_orig - dur_opt) > 2:
                raise ValueError("Discrepancia de duración")

            shutil.move(temp_optimized, final_output)

            # Mover al directorio final
            mover_a_audiovisual(final_output)

            # Cleanup
            if os.path.exists(temp_original):
                os.remove(temp_original)

            logger.info(f"Video {video_filename} finalizado.")

        except Exception as e:
            logger.exception(f"Error en video {video_filename}")
            status_msg = f"Error: {str(e)}"
        finally:
            finish_time = datetime.now().strftime("%d/%m/%Y %H:%M:%S")
            duration = f"{round(time.time() - start_time, 1)}s"
            self.state_manager.add_history({
                "name": video_filename,
                "status": status_msg,
                "timestamp": finish_time,
                "duration": duration
            })
            self.state_manager.reset()


    def process_file(self, file_path):
        info = self.ffmpeg.get_video_info(file_path)
        self.state_manager.set_video_info(info)
        threading.Thread(target=self._process_logic, args=(file_path,)).start()

    def process_folder(self, folder_path):
        def _folder_worker():
            self.state_manager.state.history = []
            self.state_manager.save()

            for root, _, files in os.walk(folder_path):
                for file in files:
                    if os.path.splitext(file)[1].lower() in self.valid_extensions:
                        self._process_logic(os.path.join(root, file))

        threading.Thread(target=_folder_worker).start()

    def get_status(self):
        s = self.state_manager.state
        return {
            "current_video": s.current_video,
            "current_step": s.current_step,
            "history": s.history,
            "log_line": s.log_line,
            "video_info": s.video_info
        }

    def get_output_folder(self):
        return self.output_folder

    def get_upload_folder(self):
        return self.upload_folder
