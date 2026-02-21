"""
Adaptador de salida - Servicio de codificación FFmpeg
Implementación de IEncoderService usando FFmpeg
"""
import os
import subprocess
import json
from typing import Dict, Optional
from src.core.ports.services.encoder_service import IEncoderService


class FFmpegEncoderService(IEncoderService):
    """Servicio de codificación usando FFmpeg"""
    
    # Perfiles de optimización
    PROFILES = {
        "ultra_fast": {
            "preset": "veryfast",
            "video_bitrate": "500k",
            "audio_bitrate": "96k",
            "scale": "640:360",
            "profile": "main",
            "bufsize": "1000k",
            "maxrate": "750k",
            "description": "📱 Móvil/3G - 360p (500 kbps)"
        },
        "fast": {
            "preset": "veryfast",
            "video_bitrate": "1000k",
            "audio_bitrate": "128k",
            "scale": "854:480",
            "profile": "main",
            "bufsize": "2000k",
            "maxrate": "1500k",
            "description": "📱 Tablet/4G - 480p (1 Mbps)"
        },
        "balanced": {
            "preset": "medium",
            "video_bitrate": "2000k",
            "audio_bitrate": "128k",
            "scale": "1280:720",
            "profile": "high",
            "bufsize": "4000k",
            "maxrate": "3000k",
            "description": "💻 WiFi - 720p (2 Mbps)"
        },
        "high_quality": {
            "preset": "slow",
            "video_bitrate": "4000k",
            "audio_bitrate": "192k",
            "scale": "1920:1080",
            "profile": "high",
            "bufsize": "8000k",
            "maxrate": "6000k",
            "description": "🚀 Fibra - 1080p (4 Mbps)"
        },
        "master": {
            "preset": "slow",
            "video_bitrate": "8000k",
            "audio_bitrate": "256k",
            "scale": None,
            "profile": "high",
            "bufsize": "16000k",
            "maxrate": "12000k",
            "description": "🎬 4K - Calidad original (8 Mbps)"
        }
    }
    
    def __init__(self):
        """Inicializa el servicio"""
        self._current_profile = "balanced"
    
    def _run_command(self, cmd: list) -> bool:
        """Ejecuta un comando de FFmpeg"""
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=3600  # 1 hora máximo
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_video_info(self, file_path: str) -> Dict:
        """Obtiene información de un archivo de video"""
        if not os.path.exists(file_path):
            return {}
        
        cmd = [
            "ffprobe",
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )
            
            if result.returncode == 0:
                data = json.loads(result.stdout)
                
                # Extraer información relevante
                info = {
                    'path': file_path,
                    'filename': os.path.basename(file_path),
                    'size': data.get('format', {}).get('size', 0),
                    'duration': float(data.get('format', {}).get('duration', 0)),
                }
                
                # Buscar streams de video y audio
                for stream in data.get('streams', []):
                    if stream.get('codec_type') == 'video':
                        info['vcodec'] = stream.get('codec_name')
                        info['resolution'] = f"{stream.get('width', 0)}x{stream.get('height', 0)}"
                        info['pix_fmt'] = stream.get('pix_fmt')
                        info['is_10bit'] = stream.get('pix_fmt') in ['yuv420p10le', 'yuv444p10le']
                    elif stream.get('codec_type') == 'audio':
                        info['acodec'] = stream.get('codec_name')
                
                return info
        
        except Exception:
            pass
        
        return {}
    
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
        """Optimiza un video usando un perfil específico"""
        if profile not in self.PROFILES:
            profile = "balanced"
        
        profile_data = self.PROFILES[profile]
        
        cmd = ["ffmpeg", "-y", "-hide_banner"]
        cmd.extend(["-threads", "4"])
        cmd.extend(["-i", input_path])
        
        # Filtros de video
        filters = []
        
        # Escalar según perfil
        if profile_data["scale"]:
            filters.append(f"scale={profile_data['scale']}")
        
        if filters:
            cmd.extend(["-vf", ",".join(filters)])
        
        # Codificación
        cmd.extend([
            "-c:v", "libx264",
            "-preset", profile_data["preset"],
            "-b:v", profile_data["video_bitrate"],
            "-maxrate", profile_data["maxrate"],
            "-bufsize", profile_data["bufsize"],
            "-profile:v", profile_data["profile"],
        ])
        
        # Audio
        cmd.extend([
            "-c:a", "aac",
            "-b:a", profile_data["audio_bitrate"],
        ])
        
        # Output
        cmd.append(output_path)
        
        return self._run_command(cmd)
    
    def generate_thumbnail(
        self,
        video_path: str,
        output_path: str,
        timestamp: str = "00:00:01"
    ) -> bool:
        """Genera un thumbnail de un video"""
        cmd = [
            "ffmpeg",
            "-y",
            "-ss", timestamp,
            "-i", video_path,
            "-vframes", "1",
            "-q:v", "2",
            output_path
        ]
        
        return self._run_command(cmd)
    
    def estimate_size(
        self,
        input_path: str,
        profile: str
    ) -> Optional[Dict]:
        """Estima el tamaño final de un video optimizado"""
        if profile not in self.PROFILES:
            return None
        
        try:
            duration = self.get_duration(input_path)
            if not duration:
                return None
            
            profile_data = self.PROFILES[profile]
            
            video_bitrate = int(profile_data["video_bitrate"][:-1]) * 1000 / 8
            audio_bitrate = int(profile_data["audio_bitrate"][:-1]) * 1000 / 8
            
            estimated_bytes = (video_bitrate + audio_bitrate) * duration
            estimated_mb = estimated_bytes / (1024 * 1024)
            original_size = os.path.getsize(input_path) / (1024 * 1024)
            
            return {
                "original_mb": original_size,
                "estimated_mb": estimated_mb,
                "duration_min": duration / 60,
                "video_bitrate": profile_data["video_bitrate"],
                "audio_bitrate": profile_data["audio_bitrate"],
                "compression_ratio": f"{int((1 - estimated_mb/original_size) * 100)}%"
            }
        
        except Exception:
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
            }
            for name, data in self.PROFILES.items()
        }
