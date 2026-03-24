"""
Adaptador de salida - Servicio de codificación FFmpeg con aceleración NVIDIA
Implementación de IEncoderService usando FFmpeg API externa con NVENC/CUDA
"""

import os
import json
import logging
import requests
from typing import Dict, Optional, List
from src.core.ports.services.encoder_service import IEncoderService


logger = logging.getLogger(__name__)


class FFmpegEncoderService(IEncoderService):
    """Servicio de codificación usando FFmpeg API externa con aceleración NVIDIA NVENC"""

    def __init__(self):
        """Inicializa el servicio"""
        self._current_profile = "balanced"
        self.api_url = (
            os.environ.get("FFMPEG_API_URL", "http://ffmpeg-api:8080")
            or "http://ffmpeg-api:8080"
        )

        logger.info(f"[FFmpegEncoderService] Inicializado con API: {self.api_url}")

    def check_health(self) -> bool:
        """Verifica que la API está disponible"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False

    def get_gpu_available(self) -> bool:
        """Verifica que GPU está disponible"""
        try:
            response = requests.get(f"{self.api_url}/gpu-status", timeout=5)
            if response.status_code == 200:
                data = response.json()
                return data.get("gpu_available", False)
            return False
        except Exception as e:
            logger.warning(f"[FFmpegEncoderService] Error verificando GPU: {e}")
            return False

    def _run_probe_api(self, file_path: str) -> Optional[Dict]:
        """Obtiene información del video vía API"""
        try:
            response = requests.get(
                f"{self.api_url}/probe", params={"file": file_path}, timeout=30
            )
            if response.status_code == 200:
                return response.json()
            return None
        except Exception as e:
            logger.warning(f"[FFmpegEncoderService] Error en probe: {e}")
            return None

    def get_video_info(self, file_path: str) -> Dict:
        """Obtiene información de un archivo de video"""
        if not os.path.exists(file_path):
            return {}

        data = self._run_probe_api(file_path)
        if not data:
            return {}

        try:
            info = {
                "path": file_path,
                "filename": os.path.basename(file_path),
                "size": int(data.get("size", 0)),
                "duration": float(data.get("duration", 0)),
                "bit_rate": int(data.get("bit_rate", 0)),
            }

            for stream in data.get("streams", []):
                if stream.get("codec_type") == "video":
                    info["vcodec"] = stream.get("codec_name")
                    info["width"] = stream.get("width", 0)
                    info["height"] = stream.get("height", 0)
                    info["resolution"] = (
                        f"{stream.get('width', 0)}x{stream.get('height', 0)}"
                    )
                    info["pix_fmt"] = stream.get("pix_fmt")
                    info["is_10bit"] = stream.get("pix_fmt") in [
                        "yuv420p10le",
                        "yuv444p10le",
                    ]

                    r_frame_rate = stream.get("r_frame_rate", "0/1")
                    try:
                        num, den = r_frame_rate.split("/")
                        info["fps"] = (
                            float(num) / float(den) if float(den) != 0 else None
                        )
                    except Exception:
                        info["fps"] = None

                elif stream.get("codec_type") == "audio":
                    info["acodec"] = stream.get("codec_name")
                    info["channels"] = stream.get("channels", 0)
                    info["sample_rate"] = stream.get("sample_rate", 0)

            return info

        except Exception as e:
            logger.warning(f"[FFmpegEncoderService] Error parseando info: {e}")

        return {}

    def get_duration(self, file_path: str) -> Optional[float]:
        """Obtiene la duración de un video en segundos"""
        info = self.get_video_info(file_path)
        return info.get("duration")

    def optimize_video(
        self, input_path: str, output_path: str, profile: str = "balanced"
    ) -> bool:
        """Optimiza un video usando GPU NVIDIA con perfil específico vía API"""
        if not os.path.exists(input_path):
            logger.error(f"[FFmpegEncoderService] Archivo no existe: {input_path}")
            return False

        if profile not in self.PROFILES:
            logger.warning(
                f"[FFmpegEncoderService] Perfil '{profile}' no válido, usando 'balanced'"
            )
            profile = "balanced"

        profile_data = self.PROFILES[profile]

        if not output_path.lower().endswith(".mp4"):
            output_path = os.path.splitext(output_path)[0] + ".mp4"

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        params = [
            "-c:v",
            "h264_nvenc",
            "-preset",
            profile_data["preset"],
            "-cq",
            profile_data["quality"],
            "-rc",
            profile_data["rc"],
            "-b:v",
            profile_data["video_bitrate"],
            "-maxrate",
            profile_data["maxrate"],
            "-bufsize",
            profile_data["bufsize"],
            "-rc-lookahead",
            profile_data["rc_lookahead"],
            "-profile:v",
            profile_data["profile"],
            "-level",
            profile_data["level"],
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart+empty_moo+default_base_moof",
            "-avoid_negative_ts",
            "make_zero",
            "-fflags",
            "+genpts",
            "-c:a",
            "aac",
            "-b:a",
            profile_data["audio_bitrate"],
            "-ac",
            "2",
            "-ar",
            "48000",
            "-c:s",
            "mov_text",
        ]

        payload = {"input": input_path, "output": output_path, "params": params}

        try:
            response = requests.post(
                f"{self.api_url}/optimize", json=payload, timeout=10
            )

            if response.status_code == 200:
                logger.info(
                    f"[FFmpegEncoderService] Optimización iniciada: {input_path} -> {output_path}"
                )
                return True
            else:
                logger.error(f"[FFmpegEncoderService] Error en API: {response.text}")
                return False

        except Exception as e:
            logger.error(f"[FFmpegEncoderService] Error: {e}")
            return False

    def generate_thumbnail(
        self, video_path: str, output_path: str, timestamp: str = "00:00:01"
    ) -> bool:
        """Genera un thumbnail de un video usando GPU vía API"""
        if not os.path.exists(video_path):
            return False

        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        payload = {
            "input": video_path,
            "output": output_path,
            "params": [
                "-ss",
                timestamp,
                "-vf",
                "scale=320:240",
                "-vframes",
                "1",
                "-q:v",
                "2",
            ],
        }

        try:
            response = requests.post(
                f"{self.api_url}/thumbnail", json=payload, timeout=30
            )
            return response.status_code == 200
        except Exception:
            return False

    def estimate_size(self, input_path: str, profile: str) -> Optional[Dict]:
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

            video_bitrate_kbps = int(profile_data["video_bitrate"][:-1])
            audio_bitrate_kbps = int(profile_data["audio_bitrate"][:-1])

            video_bps = video_bitrate_kbps * 1000 / 8
            audio_bps = audio_bitrate_kbps * 1000 / 8

            estimated_bytes = (video_bps + audio_bps) * duration
            estimated_mb = estimated_bytes / (1024 * 1024)
            original_size = os.path.getsize(input_path) / (1024 * 1024)

            estimated_bitrate_kbps = ((estimated_bytes * 8) / duration) / 1000

            return {
                "original_mb": round(original_size, 2),
                "estimated_mb": round(estimated_mb, 2),
                "estimated_bitrate_kbps": int(estimated_bitrate_kbps),
                "duration_min": round(duration / 60, 1),
                "quality_cq": profile_data["quality"],
                "target_bitrate": profile_data["video_bitrate"],
                "compression_ratio": f"{int((1 - estimated_mb / original_size) * 100)}%",
                "warning": "El tamaño real puede variar según complejidad del video"
                if profile_data.get("rc") == "vbr_hq"
                else None,
            }

        except Exception as e:
            logger.warning(f"[FFmpegEncoderService] Error en estimate: {e}")
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
        self, input_path: str, output_dir: str, profiles: Optional[List[str]] = None
    ) -> Dict:
        """Genera múltiples calidades para streaming adaptativo vía API"""
        if profiles is None:
            profiles = ["ultra_fast", "fast", "balanced", "high_quality"]

        if not os.path.exists(input_path):
            return {"error": "Archivo de entrada no existe"}

        os.makedirs(output_dir, exist_ok=True)

        results = {}
        base_name = os.path.splitext(os.path.basename(input_path))[0]

        for profile in profiles:
            if profile not in self.PROFILES:
                results[profile] = {"success": False, "error": "Perfil no válido"}
                continue

            output_file = os.path.join(output_dir, f"{base_name}_{profile}.mp4")
            logger.info(f"[FFmpegEncoderService] Generando {profile}: {output_file}")

            success = self.optimize_video(input_path, output_file, profile)

            if success:
                info = self.get_video_info(output_file)
                results[profile] = {
                    "success": True,
                    "path": output_file,
                    "size_mb": round(info.get("size", 0) / (1024 * 1024), 2),
                    "resolution": info.get("resolution"),
                    "duration": round(info.get("duration", 0), 1),
                    "bitrate_kbps": int(info.get("bit_rate", 0) / 1000)
                    if info.get("bit_rate")
                    else None,
                }
            else:
                results[profile] = {"success": False, "error": "Error en codificación"}

        return results

    def verify_streaming_ready(self, file_path: str) -> Dict:
        """Verifica si un archivo está optimizado para streaming"""
        if not os.path.exists(file_path):
            return {"error": "Archivo no existe"}

        info = self.get_video_info(file_path)

        checks = {
            "exists": True,
            "is_mp4": file_path.lower().endswith(".mp4"),
            "has_faststart": False,
            "video_codec": info.get("vcodec"),
            "audio_codec": info.get("acodec"),
            "bitrate_kbps": int(info.get("bit_rate", 0) / 1000)
            if info.get("bit_rate")
            else None,
            "resolution": info.get("resolution"),
        }

        recommendations = []
        if not checks["is_mp4"]:
            recommendations.append("Convertir a MP4 para mejor compatibilidad")
        if not checks["has_faststart"]:
            recommendations.append("Añadir +faststart para reproducción instantánea")
        if checks.get("bitrate_kbps", 0) > 5000:
            recommendations.append(
                "Bitrate alto (>5Mbps) puede causar cortes en móviles"
            )

        checks["recommendations"] = recommendations
        checks["streaming_ready"] = len(recommendations) == 0

        return checks

    PROFILES = {
        "ultra_fast": {
            "preset": "p1",
            "quality": "28",
            "video_bitrate": "500k",
            "audio_bitrate": "64k",
            "scale": "854:480",
            "profile": "baseline",
            "bufsize": "1000k",
            "maxrate": "750k",
            "rc": "vbr_hq",
            "rc_lookahead": "20",
            "level": "3.0",
            "description": "📱 Móvil/3G - 480p (500 kbps)",
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
            "description": "📱 4G - 480p (1.2 Mbps)",
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
            "description": "💻 WiFi - 720p (2.5 Mbps)",
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
            "description": "🚀 Fibra - 1080p (4 Mbps)",
        },
        "master": {
            "preset": "p7",
            "quality": "19",
            "video_bitrate": "8000k",
            "audio_bitrate": "192k",
            "scale": None,
            "profile": "high",
            "bufsize": "16000k",
            "maxrate": "9000k",
            "rc": "vbr_hq",
            "rc_lookahead": "32",
            "level": "5.0",
            "description": "🎬 4K - Calidad original (8 Mbps)",
        },
    }
