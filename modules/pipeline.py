import subprocess
import os
import json
import time

class PipelineSteps:
    def __init__(self, ffmpeg_handler):
        self.ffmpeg = ffmpeg_handler
        
        # Perfiles de optimización
        self.profiles = {
            "ultra_fast": {
                "preset": "ultrafast",
                "crf": 28,
                "scale": "854:480",
                "profile": "baseline",
                "description": "⚠️ Máxima velocidad - Calidad baja"
            },
            "fast": {
                "preset": "veryfast",
                "crf": 26,
                "scale": "960:540",
                "profile": "main",
                "description": "⚡ Rápido - Calidad media-baja"
            },
            "balanced": {
                "preset": "medium",
                "crf": 23,
                "scale": "1280:720",
                "profile": "high",
                "description": "⚖️ Balanceado - Buena calidad/velocidad"
            },
            "high_quality": {
                "preset": "slow",
                "crf": 20,
                "scale": "1920:1080",
                "profile": "high",
                "description": "🎯 Alta calidad - Más lento"
            },
            "master": {
                "preset": "veryslow",
                "crf": 18,
                "scale": None,
                "profile": "high444",
                "description": "💎 Calidad master - Muy lento"
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
                "crf": data["crf"],
                "resolution": data["scale"] or "Original"
            }
            for name, data in self.profiles.items()
        }

    def estimate_size(self, input_path, profile=None):
        if profile is None:
            profile = self.current_profile
            
        try:
            original_size = os.path.getsize(input_path)
            
            compression_factors = {
                "ultra_fast": 0.15,
                "fast": 0.12,
                "balanced": 0.10,
                "high_quality": 0.25,
                "master": 0.50
            }
            
            factor = compression_factors.get(profile, 0.1)
            estimated = original_size * factor
            
            return {
                "original_mb": original_size / (1024 * 1024),
                "estimated_mb": estimated / (1024 * 1024),
                "estimated_kb": estimated / 1024,
                "compression_ratio": f"{int((1 - factor) * 100)}%"
            }
        except:
            return None

    def process(self, input_path, output_path, profile=None, custom_params=None):
        if profile is None:
            profile = self.current_profile
            
        if profile not in self.profiles:
            print(f"❌ Perfil '{profile}' no válido. Usando 'balanced'")
            profile = "balanced"
            
        profile_data = self.profiles[profile]
        
        print("\n" + "="*50)
        print(f"🔍 INICIANDO PIPELINE - Perfil: {profile}")
        print(f"📝 {profile_data['description']}")
        print("="*50)

        # Obtener info del vídeo
        info = self.ffmpeg.get_video_info(input_path)
        vcodec = info.get("vcodec", "").lower()
        pix_fmt = info.get("pix_fmt", "").lower()
        is_10bit = info.get("is_10bit", False)

        print(f"📌 Codec detectado: {vcodec}")
        print(f"📌 Pixel format: {pix_fmt}")
        print(f"📌 ¿Es 10‑bit?: {is_10bit}")

        # Estimar tamaño
        size_estimate = self.estimate_size(input_path, profile)
        if size_estimate:
            print(f"📊 Tamaño original: {size_estimate['original_mb']:.1f} MB")
            print(f"📊 Estimado final: {size_estimate['estimated_mb']:.1f} MB")

        # CONFIGURACIÓN HÍBRIDA: CPU decode + GPU encode
        cmd = ["ffmpeg", "-y"]
        
        # SOLUCIÓN: Usar CPU para decode (estable) y optimizar con threads
        print("⚙️ Usando decode por CPU (estable)")
        
        # Añadir optimizaciones de threads para CPU
        cmd.extend(["-threads", "4"])  # Usar 4 threads para decode

        # Añadir input
        cmd.extend(["-i", input_path])

        # Filtros de video
        filters = []
        
        # Escalar
        if profile_data["scale"]:
            filters.append(f"scale={profile_data['scale']}")
            print(f"📐 Escalando a: {profile_data['scale']}")
        
        # Convertir 10-bit a 8-bit si es necesario
        if is_10bit:
            filters.append("format=yuv420p")
            print("🔧 Convirtiendo 10-bit a 8-bit")

        if filters:
            cmd.extend(["-vf", ",".join(filters)])

        # Codificación con CPU (libx264 es rápido en Jetson)
        cmd.extend([
            "-c:v", "libx264",
            "-preset", profile_data["preset"],
            "-crf", str(profile_data["crf"]),
            "-profile:v", profile_data["profile"],
        ])

        # Optimizaciones adicionales
        if profile in ["ultra_fast", "fast"]:
            cmd.extend(["-tune", "fastdecode"])
        
        # Audio
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        # Metadatos
        cmd.extend([
            "-metadata", f"optimized_with=cine-platform",
            "-metadata", f"profile={profile}",
            "-metadata", f"crf={profile_data['crf']}",
        ])

        # Output
        cmd.append(output_path)

        if custom_params:
            cmd.extend(custom_params)

        print("\n" + "="*50)
        print("📦 COMANDO FFmpeg:")
        print(" ".join(cmd))
        print("="*50 + "\n")

        # Ejecutar
        start_time = time.time()
        success = self.ffmpeg.execute(cmd)
        elapsed = time.time() - start_time

        if success:
            if os.path.exists(output_path):
                final_size = os.path.getsize(output_path) / (1024 * 1024)
                print(f"\n✅ Optimización completada en {elapsed:.1f} segundos")
                print(f"📦 Tamaño final: {final_size:.1f} MB")
                print(f"📊 Velocidad: {elapsed/3600:.2f} horas por GB")
                
                meta_path = output_path + ".json"
                with open(meta_path, 'w') as f:
                    json.dump({
                        "profile": profile,
                        "preset": profile_data["preset"],
                        "crf": profile_data["crf"],
                        "original_size_mb": size_estimate['original_mb'] if size_estimate else None,
                        "final_size_mb": final_size,
                        "processing_time": elapsed,
                        "hardware_accel": False,
                        "decoder": "cpu"
                    }, f, indent=2)
            else:
                print("❌ Error: No se generó el archivo de salida")
        else:
            print("❌ Error en la optimización")

        return success