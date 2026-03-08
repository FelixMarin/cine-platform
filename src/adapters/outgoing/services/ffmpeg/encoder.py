"""
Adaptador de salida - Servicio de codificación FFmpeg con aceleración NVIDIA
Implementación de IEncoderService usando FFmpeg con NVENC/CUDA en contenedor
"""
import os
import subprocess
import json
from typing import Dict, Optional, List
from src.core.ports.services.encoder_service import IEncoderService


class FFmpegEncoderService(IEncoderService):
    """Servicio de codificación usando FFmpeg con aceleración NVIDIA NVENC/CUDA en contenedor"""
    
    # Configuración del contenedor FFmpeg
    FFMPEG_CONTAINER = "ffmpeg-cuda"
    DOCKER_EXEC = ["docker", "exec", FFMPEG_CONTAINER]
    
    # Perfiles de optimización para streaming con NVENC
    PROFILES = {
        "ultra_fast": {
            "preset": "p1",                 # NVENC preset más rápido
            "quality": "28",                 # -cq value (18-51, menor = mejor)
            "video_bitrate": "500k",
            "audio_bitrate": "64k",
            "scale": "854:480",              # 480p para móvil
            "profile": "baseline",            # Máxima compatibilidad
            "bufsize": "1000k",
            "maxrate": "750k",
            "rc": "vbr_hq",                   # Rate control para NVENC
            "rc_lookahead": "20",
            "level": "3.0",
            "description": "📱 Móvil/3G - 480p (500 kbps)"
        },
        "fast": {
            "preset": "p3",
            "quality": "25",
            "video_bitrate": "1200k",
            "audio_bitrate": "96k",
            "scale": "854:480",
            "profile": "main",
            "bufsize": "2400k",
            "maxrate": "1500k",
            "rc": "vbr_hq",
            "rc_lookahead": "20",
            "level": "3.1",
            "description": "📱 4G - 480p (1.2 Mbps)"
        },
        "balanced": {
            "preset": "p4",
            "quality": "23",
            "video_bitrate": "2500k",
            "audio_bitrate": "128k",
            "scale": "1280:720",
            "profile": "high",
            "bufsize": "5000k",
            "maxrate": "3000k",
            "rc": "vbr_hq",
            "rc_lookahead": "25",
            "level": "4.0",
            "description": "💻 WiFi - 720p (2.5 Mbps)"
        },
        "high_quality": {
            "preset": "p6",
            "quality": "21",
            "video_bitrate": "4000k",
            "audio_bitrate": "128k",
            "scale": "1920:1080",
            "profile": "high",
            "bufsize": "8000k",
            "maxrate": "4500k",
            "rc": "vbr_hq",
            "rc_lookahead": "32",
            "level": "4.1",
            "description": "🚀 Fibra - 1080p (4 Mbps)"
        },
        "master": {
            "preset": "p7",                  # Máxima calidad NVENC
            "quality": "19",
            "video_bitrate": "8000k",
            "audio_bitrate": "192k",
            "scale": None,                    # Resolución original
            "profile": "high",
            "bufsize": "16000k",
            "maxrate": "9000k",
            "rc": "vbr_hq",
            "rc_lookahead": "32",
            "level": "5.0",
            "description": "🎬 4K - Calidad original (8 Mbps)"
        }
    }
    
    def __init__(self):
        """Inicializa el servicio"""
        self._current_profile = "balanced"
        self._check_container_available()
        self._check_cuda_availability()
    
    def _check_container_available(self) -> bool:
        """Verifica que el contenedor FFmpeg está corriendo"""
        try:
            result = subprocess.run(
                ["docker", "ps", "--filter", f"name={self.FFMPEG_CONTAINER}", "--format", "{{.Names}}"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if self.FFMPEG_CONTAINER in result.stdout:
                print(f"[FFmpeg] ✅ Contenedor {self.FFMPEG_CONTAINER} disponible")
                return True
            else:
                print(f"[FFmpeg] ❌ Contenedor {self.FFMPEG_CONTAINER} no está corriendo")
                return False
        except Exception as e:
            print(f"[FFmpeg] ❌ Error verificando contenedor: {e}")
            return False
    
    def _check_cuda_availability(self) -> bool:
        """Verifica que CUDA/NVENC está disponible en el contenedor"""
        try:
            cmd = self.DOCKER_EXEC + ["ffmpeg", "-hide_banner", "-encoders"]
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            available = "h264_nvenc" in result.stdout
            if available:
                print("[FFmpeg] ✅ GPU NVIDIA disponible en contenedor")
            else:
                print("[FFmpeg] ⚠️ GPU NVIDIA no disponible en contenedor")
            return available
        except Exception as e:
            print(f"[FFmpeg] ❌ Error verificando GPU: {e}")
            return False
    
    def _run_command(self, cmd: list) -> bool:
        """Ejecuta un comando de FFmpeg en el contenedor con logging"""
        try:
            # Prefijar con docker exec
            full_cmd = self.DOCKER_EXEC + cmd
            
            # Log del comando para debug
            cmd_str = " ".join(full_cmd)
            print(f"[FFmpeg] Ejecutando: {cmd_str}")
            
            result = subprocess.run(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=7200  # 2 horas máximo
            )
            
            if result.returncode != 0:
                error_msg = result.stderr.decode()[-500:] if result.stderr else "Error desconocido"
                print(f"[FFmpeg] Error: {error_msg}")
            
            return result.returncode == 0
        except subprocess.TimeoutExpired:
            print("[FFmpeg] Timeout: El proceso excedió el tiempo límite")
            return False
        except Exception as e:
            print(f"[FFmpeg] Excepción: {e}")
            return False
    
    def _run_probe_command(self, cmd: list) -> Optional[str]:
        """Ejecuta un comando ffprobe en el contenedor"""
        try:
            full_cmd = self.DOCKER_EXEC + cmd
            result = subprocess.run(
                full_cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=30
            )
            if result.returncode == 0:
                return result.stdout
            return None
        except Exception:
            return None
    
    def get_video_info(self, file_path: str) -> Dict:
        """Obtiene información de un archivo de video"""
        if not os.path.exists(file_path):
            return {}
        
        # Convertir ruta local a ruta en contenedor
        container_path = self._map_to_container_path(file_path)
        
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            container_path
        ]
        
        try:
            output = self._run_probe_command(cmd)
            if output:
                data = json.loads(output)
                
                # Extraer información relevante
                info = {
                    'path': file_path,
                    'filename': os.path.basename(file_path),
                    'size': int(data.get('format', {}).get('size', 0)),
                    'duration': float(data.get('format', {}).get('duration', 0)),
                    'bit_rate': int(data.get('format', {}).get('bit_rate', 0)),
                }
                
                # Buscar streams de video y audio
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        info['vcodec'] = stream.get('codec_name')
                        info['width'] = stream.get('width', 0)
                        info['height'] = stream.get('height', 0)
                        info['resolution'] = f"{stream.get('width', 0)}x{stream.get('height', 0)}"
                        info['pix_fmt'] = stream.get('pix_fmt')
                        info['is_10bit'] = stream.get('pix_fmt') in ['yuv420p10le', 'yuv444p10le']
                        
                        # FPS
                        r_frame_rate = stream.get('r_frame_rate', '0/1')
                        try:
                            num, den = r_frame_rate.split('/')
                            info['fps'] = float(num) / float(den) if float(den) != 0 else None
                        except Exception:
                            info['fps'] = None
                            
                    elif stream.get('codec_type') == 'audio':
                        info['acodec'] = stream.get('codec_name')
                        info['channels'] = stream.get('channels', 0)
                        info['sample_rate'] = stream.get('sample_rate', 0)
                
                return info
        
        except Exception as e:
            print(f"[FFprobe] Error: {e}")
        
        return {}
    
    def _map_to_container_path(self, local_path: str) -> str:
        """
        Convierte una ruta local a su equivalente en el contenedor
        
        Args:
            local_path: Ruta en el host
            
        Returns:
            Ruta equivalente en el contenedor
        """
        # Mapear rutas según los volúmenes definidos en docker-compose
        if "/mnt/DATA_2TB/audiovisual/mkv" in local_path:
            return local_path.replace("/mnt/DATA_2TB/audiovisual/mkv", "/shared/output")
        elif "/app/uploads" in local_path:
            return local_path.replace("/app/uploads", "/shared/uploads")
        elif "/app/temp" in local_path:
            return local_path.replace("/app/temp", "/shared/temp")
        elif "/app/outputs" in local_path:
            return local_path.replace("/app/outputs", "/shared/outputs")
        else:
            # Si no está mapeado, usar directorio temp
            filename = os.path.basename(local_path)
            return f"/shared/temp/{filename}"
    
    def get_duration(self, file_path: str) -> Optional[float]:
        """Obtiene la duración de un video en segundos"""
        info = self.get_video_info(file_path)
        return info.get('duration')
    
    def optimize_video(
        self,
        input_path: str,
        output_path: str,
        profile: str = "balanced"
    ) -> bool:
        """Optimiza un video usando GPU NVIDIA con perfil específico en contenedor"""
        if not os.path.exists(input_path):
            print(f"[FFmpeg] Error: Archivo de entrada no existe: {input_path}")
            return False
        
        if profile not in self.PROFILES:
            print(f"[FFmpeg] Perfil '{profile}' no válido, usando 'balanced'")
            profile = "balanced"
        
        profile_data = self.PROFILES[profile]
        
        # Asegurar extensión .mp4 para streaming
        if not output_path.lower().endswith('.mp4'):
            output_path = os.path.splitext(output_path)[0] + '.mp4'
        
        # Crear directorio de salida si no existe
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convertir rutas para el contenedor
        container_input = self._map_to_container_path(input_path)
        container_output = self._map_to_container_path(output_path)
        
        cmd = ["ffmpeg", "-y", "-hide_banner"]
        
        # Aceleración CUDA para decodificación
        cmd.extend(["-hwaccel", "cuda"])
        cmd.extend(["-hwaccel_output_format", "cuda"])  # Mantener frames en GPU
        
        cmd.extend(["-threads", "4"])
        cmd.extend(["-i", container_input])
        
        # Filtros de video (ejecutados en GPU)
        filters = []
        if profile_data["scale"]:
            # Usar filtro scale_cuda para mantener en GPU
            filters.append(f"scale_cuda={profile_data['scale']}")
        
        # Añadir pad para mantener relación de aspecto
        if profile_data["scale"]:
            w, h = profile_data["scale"].split(':')
            filters.append(f"pad_cuda={w}:{h}:(ow-iw)/2:(oh-ih)/2")
        
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # Codificación NVENC con parámetros optimizados
        cmd.extend([
            "-c:v", "h264_nvenc",
            "-preset", profile_data["preset"],
            "-cq", profile_data["quality"],
            "-rc", profile_data["rc"],
            "-b:v", profile_data["video_bitrate"],
            "-maxrate", profile_data["maxrate"],
            "-bufsize", profile_data["bufsize"],
            "-rc-lookahead", profile_data["rc_lookahead"],
            "-profile:v", profile_data["profile"],
            "-level", profile_data["level"],
            "-pix_fmt", "yuv420p",
        ])
        
        # Optimizaciones de streaming
        cmd.extend([
            "-movflags", "+faststart+empty_moov+default_base_moof",
            "-avoid_negative_ts", "make_zero",
            "-fflags", "+genpts",
        ])
        
        # Audio
        cmd.extend([
            "-c:a", "aac",
            "-b:a", profile_data["audio_bitrate"],
            "-ac", "2",
            "-ar", "48000",
        ])
        
        # Copy subtítulos si existen
        cmd.extend(["-c:s", "mov_text"])
        
        # Output
        cmd.append(container_output)
        
        return self._run_command(cmd)
    
    def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: str = "00:00:01"
    ) -> bool:
        """Genera un thumbnail de un video usando GPU en contenedor"""
        if not os.path.exists(video_path):
            return False
        
        # Crear directorio de salida
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Convertir rutas para el contenedor
        container_input = self._map_to_container_path(video_path)
        container_output = self._map_to_container_path(output_path)
        
        cmd = [
            "ffmpeg",
            "-y",
            "-hwaccel", "cuda",           # Usar GPU para decodificar
            "-ss", timestamp,
            "-i", container_input,
            "-vf", "scale_cuda=320:240",   # Escalar en GPU
            "-vframes", "1",
            "-q:v", "2",
            container_output
        ]
        
        return self._run_command(cmd)
    
    def estimate_size(
        self,
        input_path: str,
        profile: str
    ) -> Optional[Dict]:
        """Estima el tamaño final considerando calidad constante"""
        if profile not in self.PROFILES:
            return None
        
        if not os.path.exists(input_path):
            return None
        
        try:
            duration = self.get_duration(input_path)
            if not duration:
                return None
            
            profile_data = self.PROFILES[profile]
            
            # Para calidad constante (cq), el bitrate puede variar
            # Estimación basada en bitrate objetivo
            video_bitrate_kbps = int(profile_data["video_bitrate"][:-1])
            audio_bitrate_kbps = int(profile_data["audio_bitrate"][:-1])
            
            # Convertir a bytes/segundo
            video_bps = video_bitrate_kbps * 1000 / 8
            audio_bps = audio_bitrate_kbps * 1000 / 8
            
            estimated_bytes = (video_bps + audio_bps) * duration
            estimated_mb = estimated_bytes / (1024 * 1024)
            original_size = os.path.getsize(input_path) / (1024 * 1024)
            
            # Calcular bitrate promedio esperado
            estimated_bitrate_kbps = ((estimated_bytes * 8) / duration) / 1000
            
            return {
                "original_mb": round(original_size, 2),
                "estimated_mb": round(estimated_mb, 2),
                "estimated_bitrate_kbps": int(estimated_bitrate_kbps),
                "duration_min": round(duration / 60, 1),
                "quality_cq": profile_data["quality"],
                "target_bitrate": profile_data["video_bitrate"],
                "compression_ratio": f"{int((1 - estimated_mb/original_size) * 100)}%",
                "warning": "El tamaño real puede variar según complejidad del video" if profile_data.get("rc") == "vbr_hq" else None
            }
        
        except Exception as e:
            print(f"[Estimate] Error: {e}")
            return None
    
    def get_available_profiles(self) -> Dict:
        """Obtiene los perfiles de optimización disponibles"""
        return {
            name: {
                "name": name,
                "description": data["description"],
                "preset": data["preset"],
                "video_bitrate": data["video_bitrate"],
                "audio_bitrate": data["audio_bitrate"],
                "resolution": data["scale"] or "Original",
                "quality_cq": data["quality"],
                "profile": data["profile"],
            }
            for name, data in self.PROFILES.items()
        }
    
    def generate_adaptive_streams(
        self,
        input_path: str,
        output_dir: str,
        profiles: Optional[List[str]] = None
    ) -> Dict:
        """Genera múltiples calidades para streaming adaptativo en contenedor"""
        if profiles is None:
            profiles = ["ultra_fast", "fast", "balanced", "high_quality"]
        
        if not os.path.exists(input_path):
            return {"error": "Archivo de entrada no existe"}
        
        # Crear directorio de salida
        os.makedirs(output_dir, exist_ok=True)
        
        results = {}
        base_name = os.path.splitext(os.path.basename(input_path))[0]
        
        for profile in profiles:
            if profile not in self.PROFILES:
                results[profile] = {"success": False, "error": "Perfil no válido"}
                continue
            
            output_file = os.path.join(output_dir, f"{base_name}_{profile}.mp4")
            print(f"[Adaptive] Generando {profile}: {output_file}")
            
            success = self.optimize_video(input_path, output_file, profile)
            
            if success:
                info = self.get_video_info(output_file)
                results[profile] = {
                    "success": True,
                    "path": output_file,
                    "size_mb": round(info.get('size', 0) / (1024 * 1024), 2),
                    "resolution": info.get('resolution'),
                    "duration": round(info.get('duration', 0), 1),
                    "bitrate_kbps": int(info.get('bit_rate', 0) / 1000) if info.get('bit_rate') else None
                }
            else:
                results[profile] = {
                    "success": False,
                    "error": "Error en codificación"
                }
        
        return results
    
    def verify_streaming_ready(self, file_path: str) -> Dict:
        """Verifica si un archivo está optimizado para streaming"""
        if not os.path.exists(file_path):
            return {"error": "Archivo no existe"}
        
        info = self.get_video_info(file_path)
        
        # Verificar características para streaming
        checks = {
            "exists": True,
            "is_mp4": file_path.lower().endswith('.mp4'),
            "has_faststart": False,
            "video_codec": info.get('vcodec'),
            "audio_codec": info.get('acodec'),
            "bitrate_kbps": int(info.get('bit_rate', 0) / 1000) if info.get('bit_rate') else None,
            "resolution": info.get('resolution'),
        }
        
        # Verificar faststart usando ffprobe en contenedor
        try:
            container_path = self._map_to_container_path(file_path)
            cmd = [
                "ffprobe",
                "-v", "quiet",
                "-show_entries", "format=format_name",
                "-of", "default=noprint_wrappers=1:nokey=1",
                container_path
            ]
            output = self._run_probe_command(cmd)
            checks["has_faststart"] = output and "mov,mp4,m4a,3gp,3g2,mj2" in output
        except:
            pass
        
        # Recomendaciones
        recommendations = []
        if not checks["is_mp4"]:
            recommendations.append("Convertir a MP4 para mejor compatibilidad")
        if not checks["has_faststart"]:
            recommendations.append("Añadir +faststart para reproducción instantánea")
        if checks.get("bitrate_kbps", 0) > 5000:
            recommendations.append("Bitrate alto (>5Mbps) puede causar cortes en móviles")
        
        checks["recommendations"] = recommendations
        checks["streaming_ready"] = len(recommendations) == 0
        
        return checks