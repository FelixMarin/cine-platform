# modules/pipeline.py

import subprocess
import os
import json
import time

class PipelineSteps:
    def __init__(self, ffmpeg_handler):
        self.ffmpeg = ffmpeg_handler
        
        # Perfiles de optimización para STREAMING
        self.profiles = {
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
        
        self.current_profile = "balanced"

    def set_profile(self, profile_name):
        if profile_name in self.profiles:
            self.current_profile = profile_name
            print(f"📊 Perfil cambiado a: {profile_name} - {self.profiles[profile_name]['description']}")
            return True
        return False

    def get_profiles(self):
        return {
            name: {
                "name": name,
                "description": data["description"],
                "preset": data["preset"],
                "video_bitrate": data["video_bitrate"],
                "audio_bitrate": data["audio_bitrate"],
                "resolution": data["scale"] or "Original",
                "maxrate": data.get("maxrate", data["video_bitrate"])
            }
            for name, data in self.profiles.items()
        }

    def estimate_size(self, input_path, profile=None):
        if profile is None:
            profile = self.current_profile
            
        profile_data = self.profiles[profile]
        
        try:
            duration = self.ffmpeg.get_duration(input_path)
            if not duration:
                return None
                
            video_bitrate = int(profile_data["video_bitrate"][:-1]) * 1000 / 8
            audio_bitrate = int(profile_data["audio_bitrate"][:-1]) * 1000 / 8
            
            estimated_bytes = (video_bitrate + audio_bitrate) * duration
            estimated_mb = estimated_bytes / (1024 * 1024)
            original_size = os.path.getsize(input_path) / (1024 * 1024)
            
            # Ratios de compresión realistas
            ratios = {
                "ultra_fast": 0.15,
                "fast": 0.25,
                "balanced": 0.35,
                "high_quality": 0.50,
                "master": 0.70
            }
            
            if estimated_mb > original_size * 0.8:
                estimated_mb = original_size * ratios.get(profile, 0.35)
            
            return {
                "original_mb": original_size,
                "estimated_mb": estimated_mb,
                "duration_min": duration / 60,
                "video_bitrate": profile_data["video_bitrate"],
                "audio_bitrate": profile_data["audio_bitrate"],
                "compression_ratio": f"{int((1 - estimated_mb/original_size) * 100)}%"
            }
        except Exception as e:
            print(f"Error estimando tamaño: {e}")
            return None

    def process(self, input_path, output_path, profile=None, custom_params=None):
        if profile is None:
            profile = self.current_profile
            
        if profile not in self.profiles:
            print(f"❌ Perfil '{profile}' no válido. Usando 'balanced'")
            profile = "balanced"
            
        profile_data = self.profiles[profile]
        
        print("\n" + "="*70)
        print(f"🎬 OPTIMIZACIÓN PARA STREAMING - Perfil: {profile.upper()}")
        print(f"📝 {profile_data['description']}")
        print("="*70)

        info = self.ffmpeg.get_video_info(input_path)
        vcodec = info.get("vcodec", "").lower()
        pix_fmt = info.get("pix_fmt", "").lower()
        is_10bit = info.get("is_10bit", False)
        
        try:
            original_width = int(info.get("resolution", "0x0").split("x")[0])
        except:
            original_width = 0

        print(f"📌 Codec detectado: {vcodec}")
        print(f"📌 Resolución original: {info.get('resolution', 'desconocida')}")
        
        # Manejar duración de forma segura
        duration_sec = info.get("duration", 0)
        if duration_sec and duration_sec > 0:
            print(f"📌 Duración: {duration_sec/60:.1f} minutos ({duration_sec:.0f} segundos)")
        else:
            print(f"📌 Duración: {info.get('duration_str', 'desconocida')}")
        
        print(f"📌 Tamaño original: {info.get('size', '0 MB')}")

        size_estimate = self.estimate_size(input_path, profile)
        if size_estimate:
            print(f"📊 Estimado final: {size_estimate['estimated_mb']:.1f} MB")
            print(f"📊 Compresión esperada: {size_estimate['compression_ratio']}")
            print(f"📊 Bitrate video: {profile_data['video_bitrate']}")
            print(f"📊 Bitrate audio: {profile_data['audio_bitrate']}")

        # CONSTRUCCIÓN DEL COMANDO - SOLO CPU (100% ESTABLE)
        cmd = ["ffmpeg", "-y", "-hide_banner"]
        
        # Optimizaciones para CPU en Jetson
        print("⚙️ Usando CPU con optimizaciones")
        cmd.extend(["-threads", "4"])
        cmd.extend(["-thread_type", "slice"])

        # Añadir input
        cmd.extend(["-i", input_path])

        # Filtros de video
        filters = []
        
        # Escalar según perfil
        if profile_data["scale"] and original_width > 0:
            target_width = int(profile_data["scale"].split(":")[0])
            if target_width < original_width:
                filters.append(f"scale={profile_data['scale']}")
                print(f"📐 Escalando a: {profile_data['scale']}")
            else:
                print(f"📐 Manteniendo resolución original")
        
        # Convertir 10-bit a 8-bit si es necesario
        if is_10bit:
            filters.append("format=yuv420p")
            print("🔧 Convirtiendo 10-bit a 8-bit")

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
            "-ar", "48000",
        ])

        # MOV flags para streaming
        cmd.extend(["-movflags", "+faststart"])

        # Metadatos
        cmd.extend([
            "-metadata", f"title={os.path.basename(input_path)}",
            "-metadata", f"encoder=Cine Platform",
            "-metadata", f"profile={profile}",
        ])

        # Output
        cmd.append(output_path)

        if custom_params:
            cmd.extend(custom_params)

        print("\n" + "="*70)
        print("📦 COMANDO FFmpeg:")
        print(" ".join(cmd))
        print("="*70 + "\n")

        # Ejecutar
        start_time = time.time()
        success = self.ffmpeg.execute(cmd)
        elapsed = time.time() - start_time

        if success and os.path.exists(output_path):
            final_size = os.path.getsize(output_path) / (1024 * 1024)
            
            print(f"\n✅ Optimización completada en {elapsed/60:.1f} minutos")
            print(f"📦 Tamaño final: {final_size:.1f} MB")
            
            # Calcular bitrate real solo si tenemos duración válida
            if duration_sec and duration_sec > 0:
                actual_bitrate = (final_size * 8 * 1024) / duration_sec
                print(f"📊 Bitrate real: {actual_bitrate:.0f} kbps")
            else:
                print(f"📊 Bitrate real: No disponible (duración desconocida)")
            
            # Guardar metadatos
            meta_path = output_path + ".json"
            with open(meta_path, 'w') as f:
                json.dump({
                    "profile": profile,
                    "preset": profile_data["preset"],
                    "video_bitrate": profile_data["video_bitrate"],
                    "audio_bitrate": profile_data["audio_bitrate"],
                    "resolution": profile_data["scale"] or "original",
                    "original_size_mb": size_estimate['original_mb'] if size_estimate else None,
                    "final_size_mb": final_size,
                    "processing_time": elapsed,
                    "hardware_accel": False,
                    "decoder": "cpu"
                }, f, indent=2)
            
            return True
        else:
            print("❌ Error en la optimización")
            return False