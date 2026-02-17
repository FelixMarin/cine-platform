# modules/ffmpeg.py
import os
import subprocess
import json
import re
import signal
from modules.logging.logging_config import setup_logging

logger = setup_logging(os.environ.get("LOG_FOLDER"))

class FFmpegHandler:
    def __init__(self, state_manager):
        self.state_manager = state_manager
        self.is_jetson = os.path.exists("/usr/lib/aarch64-linux-gnu/tegra")
        self.current_process = None
        self.set_process_callback = None
        
        if self.is_jetson:
            logger.info("✅ Dispositivo Jetson detectado")
            self._check_nvmpi_decoders()

    def _check_nvmpi_decoders(self):
        """Verifica qué decodificadores NVMPI están disponibles"""
        try:
            result = subprocess.run(
                ["ffmpeg", "-decoders"],
                capture_output=True,
                text=True,
                timeout=10
            )
            decoders = result.stdout
            
            self.has_nvmpi_h264 = "h264_nvmpi" in decoders
            self.has_nvmpi_hevc = "hevc_nvmpi" in decoders
            self.has_nvmpi_vp9 = "vp9_nvmpi" in decoders
            
            logger.info(f"📊 Decodificadores NVMPI: H264={self.has_nvmpi_h264}, HEVC={self.has_nvmpi_hevc}, VP9={self.has_nvmpi_vp9}")
            
        except Exception as e:
            logger.error(f"Error verificando decodificadores: {e}")
            self.has_nvmpi_h264 = False
            self.has_nvmpi_hevc = False
            self.has_nvmpi_vp9 = False

    def get_video_info(self, video_path):
        try:
            cmd = [
                "ffprobe", "-v", "quiet",
                "-print_format", "json",
                "-show_format",
                "-show_streams",
                video_path
            ]

            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                check=True,
                timeout=30
            )
            data = json.loads(result.stdout)

            format_info = data.get("format", {})
            streams = data.get("streams", [])
            
            v_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
            a_stream = next((s for s in streams if s.get("codec_type") == "audio"), {})

            size_bytes = int(format_info.get("size", 0)) if format_info.get("size") else 0
            size_mb = round(size_bytes / (1024 * 1024), 2) if size_bytes else 0

            pix_fmt = v_stream.get("pix_fmt", "").lower()
            is_10bit = any(x in pix_fmt for x in ["10", "yuv420p10", "yuv422p10", "yuv444p10"])

            # Obtener duración como string y luego como float
            duration_str = format_info.get("duration", "0")
            try:
                duration_float = float(duration_str) if duration_str else 0.0
            except (ValueError, TypeError):
                duration_float = 0.0

            info = {
                "name": os.path.basename(video_path),
                "duration": duration_float,
                "duration_str": duration_str,
                "resolution": f"{v_stream.get('width', '??')}x{v_stream.get('height', '??')}",
                "format": format_info.get("format_name", "desconocido"),
                "vcodec": v_stream.get("codec_name", "desconocido"),
                "acodec": a_stream.get("codec_name", "desconocido"),
                "pix_fmt": pix_fmt,
                "is_10bit": is_10bit,
                "size": f"{size_mb} MB",
                "size_bytes": size_bytes
            }
            
            logger.debug(f"Info video: {info['name']} - {info['resolution']} - {info['vcodec']}")
            return info

        except subprocess.TimeoutExpired:
            logger.error(f"Timeout obteniendo info de {video_path}")
            return {}
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ffprobe: {e}")
            return {}
        except json.JSONDecodeError as e:
            logger.error(f"Error decodificando JSON: {e}")
            return {}
        except Exception as e:
            logger.error(f"Error info video: {e}")
            return {}

    def execute(self, cmd_args):
        cmd_str = ' '.join(str(arg) for arg in cmd_args)
        logger.debug(f"CMD: {cmd_str}")
        
        process = None
        try:
            # Crear proceso con grupo de procesos para poder matar hijos
            process = subprocess.Popen(
                cmd_args,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                universal_newlines=True,
                bufsize=1,
                preexec_fn=os.setsid  # Crear grupo de procesos
            )
            
            # Guardar referencia al proceso
            self.current_process = process
            if self.set_process_callback:
                self.set_process_callback(process)
            
            # Patrones para extraer datos numéricos de forma segura
            frame_pattern = re.compile(r'frame=\s*(\d+)')
            fps_pattern = re.compile(r'fps=\s*([\d.]+)')
            time_pattern = re.compile(r'time=\s*([\d:]+)')
            bitrate_pattern = re.compile(r'bitrate=\s*([\d.]+)kbits/s')
            speed_pattern = re.compile(r'speed=\s*([\d.]+)x')
            
            for line in process.stdout:
                line = line.strip()
                if line:
                    logger.debug(line)
                    
                    # Extraer información de progreso
                    if "frame=" in line or "fps=" in line:
                        stats_parts = []
                        
                        # Extraer cada valor de forma segura
                        frame_match = frame_pattern.search(line)
                        if frame_match:
                            stats_parts.append(f"frames={frame_match.group(1)}")
                        
                        fps_match = fps_pattern.search(line)
                        if fps_match:
                            stats_parts.append(f"fps={fps_match.group(1)}")
                        
                        time_match = time_pattern.search(line)
                        if time_match:
                            stats_parts.append(f"time={time_match.group(1)}")
                        
                        bitrate_match = bitrate_pattern.search(line)
                        if bitrate_match:
                            stats_parts.append(f"bitrate={bitrate_match.group(1)}k")
                        
                        speed_match = speed_pattern.search(line)
                        if speed_match:
                            stats_parts.append(f"speed={speed_match.group(1)}x")
                        
                        if stats_parts:
                            log_line = " | ".join(stats_parts)
                            # Llamar al método correcto del state_manager
                            if hasattr(self.state_manager, 'update_log'):
                                self.state_manager.update_log(log_line)
            
            process.wait()
            
            if process.returncode != 0:
                logger.error(f"❌ FFmpeg error code: {process.returncode}")
                return False
                
            return True
            
        except Exception as e:
            logger.error(f"❌ Error en execute: {e}")
            return False
        finally:
            self.current_process = None
            if self.set_process_callback:
                self.set_process_callback(None)
            if process and process.poll() is None:
                # Intentar terminar suavemente
                try:
                    os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                    process.wait(timeout=5)
                except:
                    # Forzar kill si no responde
                    try:
                        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
                    except:
                        pass

    def get_duration(self, video_path):
        try:
            result = subprocess.run(
                ["ffprobe", "-v", "error", "-show_entries", 
                 "format=duration", "-of", 
                 "default=noprint_wrappers=1:nokey=1", 
                 video_path],
                stdout=subprocess.PIPE, 
                stderr=subprocess.PIPE, 
                text=True, 
                check=True,
                timeout=10
            )
            duration_str = result.stdout.strip()
            if duration_str:
                return float(duration_str)
            return 0.0
        except subprocess.TimeoutExpired:
            logger.error(f"Timeout obteniendo duración de {video_path}")
            return 0.0
        except subprocess.CalledProcessError as e:
            logger.error(f"Error ffprobe en get_duration: {e}")
            return 0.0
        except ValueError as e:
            logger.error(f"Error convirtiendo duración a float: {e}")
            return 0.0
        except Exception as e:
            logger.error(f"Error inesperado en get_duration: {e}")
            return 0.0
    
    def cancel_current_process(self):
        """Método público para cancelar el proceso actual"""
        if self.current_process and self.current_process.poll() is None:
            try:
                logger.info("🛑 Cancelando proceso FFmpeg...")
                os.killpg(os.getpgid(self.current_process.pid), signal.SIGTERM)
                return True
            except Exception as e:
                logger.error(f"Error cancelando proceso: {e}")
                return False
        return False