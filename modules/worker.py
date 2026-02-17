# modules/worker.py

import os
import time
import signal
import threading
from modules.pipeline import PipelineSteps
from modules.ffmpeg import FFmpegHandler
from modules.state import StateManager

# Variables globales del módulo
processing_queue = None
processing_status = None
optimizer_service = None
current_ffmpeg_process = None

def init_worker(queue, status, service):
    """Inicializa el worker con las referencias necesarias"""
    global processing_queue, processing_status, optimizer_service
    processing_queue = queue
    processing_status = status
    optimizer_service = service

def background_worker():
    """Procesa videos en segundo plano con capacidad de cancelación"""
    global current_ffmpeg_process
    
    while True:
        try:
            # Verificar si hay cancelación pendiente
            if processing_status.get("cancelled", False):
                print("🛑 Cancelación detectada, deteniendo proceso actual...")
                
                # Matar el proceso de FFmpeg si existe
                if current_ffmpeg_process:
                    try:
                        os.killpg(os.getpgid(current_ffmpeg_process.pid), signal.SIGTERM)
                        print(f"✅ Proceso FFmpeg terminado (PID: {current_ffmpeg_process.pid})")
                    except Exception as e:
                        print(f"⚠️ Error al terminar proceso: {e}")
                    finally:
                        current_ffmpeg_process = None
                
                # Limpiar estado
                processing_status["current"] = None
                processing_status["log_line"] = "Proceso cancelado por usuario"
                processing_status["frames"] = 0
                processing_status["fps"] = 0
                processing_status["time"] = ""
                processing_status["speed"] = ""
                processing_status["cancelled"] = False
                processing_status["video_info"] = {}
                
                # Vaciar la cola
                while not processing_queue.empty():
                    try:
                        processing_queue.get_nowait()
                    except:
                        pass
                
                continue
            
            if not processing_queue.empty():
                task = processing_queue.get()
                processing_status["current"] = task["filename"]
                processing_status["log_line"] = f"Iniciando {task['filename']}"
                processing_status["last_update"] = time.time()
                processing_status["cancelled"] = False
                processing_status["video_info"] = {}
                
                print(f"🎬 Worker procesando: {task['filename']} con perfil {task['profile']}")
                
                # Obtener información del video ANTES de procesar
                try:
                    temp_state = StateManager()
                    temp_ff = FFmpegHandler(temp_state)
                    video_info = temp_ff.get_video_info(task['filepath'])
                    
                    if video_info:
                        # Formatear duración para mostrarla bien
                        duration_sec = video_info.get('duration', 0)
                        if duration_sec:
                            hours = int(duration_sec // 3600)
                            minutes = int((duration_sec % 3600) // 60)
                            seconds = int(duration_sec % 60)
                            duration_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                        else:
                            duration_str = "–"
                        
                        processing_status["video_info"] = {
                            "name": video_info.get("name", "–"),
                            "duration": duration_str,
                            "resolution": video_info.get("resolution", "–"),
                            "format": video_info.get("format", "–"),
                            "vcodec": video_info.get("vcodec", "–"),
                            "acodec": video_info.get("acodec", "–"),
                            "size": video_info.get("size", "–"),
                        }
                        print(f"📹 Información del video obtenida: {video_info.get('resolution')} - {video_info.get('vcodec')}")
                except Exception as e:
                    print(f"⚠️ Error obteniendo info del video: {e}")
                
                # State propio del worker
                worker_state = StateManager()
                
                # Override del método update_log para capturar el progreso
                original_update_log = worker_state.update_log
                
                def update_log_wrapper(line):
                    # Verificar cancelación antes de actualizar
                    if processing_status.get("cancelled", False):
                        print("🛑 Cancelación detectada durante procesamiento")
                        raise Exception("Proceso cancelado por usuario")
                    
                    # Actualizar nuestro estado global
                    processing_status["log_line"] = line
                    
                    # Parsear la línea para extraer stats
                    if "frame=" in line:
                        parts = line.split()
                        for part in parts:
                            if "=" in part:
                                key, value = part.split("=")
                                if key == "frame":
                                    try:
                                        processing_status["frames"] = int(value)
                                    except:
                                        pass
                                elif key == "fps":
                                    try:
                                        processing_status["fps"] = float(value.split()[0]) if ' ' in value else float(value)
                                    except:
                                        pass
                                elif key == "time":
                                    processing_status["time"] = value
                                elif key == "speed":
                                    processing_status["speed"] = value
                    
                    # Llamar al original
                    original_update_log(line)
                
                worker_state.update_log = update_log_wrapper
                
                # Crear FFmpegHandler con capacidad de guardar el proceso
                ff = FFmpegHandler(worker_state)
                
                # Guardar referencia al proceso para poder cancelarlo
                def set_ffmpeg_process(proc):
                    global current_ffmpeg_process
                    current_ffmpeg_process = proc
                
                ff.set_process_callback = set_ffmpeg_process
                
                pipeline = PipelineSteps(ff)
                
                base, ext = os.path.splitext(task['filename'])
                output_filename = f"{base}_{task['profile']}{ext}"
                output_path = os.path.join(optimizer_service.get_output_folder(), output_filename)
                
                # Ejecutar pipeline con manejo de cancelación
                worker_state.set_current_video(task['filename'])
                
                try:
                    success = pipeline.process(task['filepath'], output_path, profile=task['profile'])
                    
                    if success and not processing_status.get("cancelled", False):
                        print(f"✅ Completado: {task['filename']}")
                        processing_status["log_line"] = f"Completado: {task['filename']}"
                    elif processing_status.get("cancelled", False):
                        print(f"🛑 Proceso cancelado: {task['filename']}")
                        processing_status["log_line"] = f"Cancelado: {task['filename']}"
                    else:
                        print(f"❌ Error: {task['filename']}")
                        processing_status["log_line"] = f"Error: {task['filename']}"
                        
                except Exception as e:
                    if "cancelado" in str(e).lower():
                        print(f"🛑 Proceso cancelado: {task['filename']}")
                        processing_status["log_line"] = f"Cancelado: {task['filename']}"
                    else:
                        print(f"❌ Error en pipeline: {e}")
                        processing_status["log_line"] = f"Error: {task['filename']}"
                
                # Limpiar proceso actual
                current_ffmpeg_process = None
                processing_status["current"] = None
                processing_status["last_update"] = time.time()
                
            processing_status["queue_size"] = processing_queue.qsize()
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error en worker: {e}")
            processing_status["log_line"] = f"Error: {str(e)}"
            processing_status["current"] = None
            processing_status["cancelled"] = False
            processing_status["video_info"] = {}
            current_ffmpeg_process = None
            time.sleep(5)


def start_worker(queue, status, service):
    """Inicia el worker en un thread separado"""
    init_worker(queue, status, service)
    worker_thread = threading.Thread(target=background_worker, daemon=True)
    worker_thread.start()
    print("🚀 Worker iniciado en segundo plano")
    return worker_thread