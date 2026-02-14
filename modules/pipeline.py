import subprocess

class PipelineSteps:
    def __init__(self, ffmpeg_handler):
        self.ffmpeg = ffmpeg_handler

    def process(self, input_path, output_path):

        print("\n==============================")
        print("🔍 INICIANDO PIPELINE")
        print("==============================")

        # Obtener info del vídeo
        info = self.ffmpeg.get_video_info(input_path)
        vcodec = info.get("vcodec", "").lower()
        pix_fmt = info.get("pix_fmt", "").lower()

        print(f"📌 Codec detectado por ffprobe: {vcodec}")
        print(f"📌 Pixel format detectado: {pix_fmt}")

        # Detectar si es 10‑bit o superior
        is_10bit = (
            "10" in pix_fmt or
            "yuv420p10" in pix_fmt or
            "yuv422p10" in pix_fmt or
            "yuv444p10" in pix_fmt
        )

        print(f"📌 ¿Es 10‑bit o superior?: {is_10bit}")

        # Mapeo de codecs → decoders hardware
        hw_map = {
            "h264": "h264_nvv4l2dec",
            "hevc": "hevc_v4l2m2m",   # HEVC 8‑bit OK, 10‑bit NO
            "vp9": "vp9_nvv4l2dec",
            "vp8": "vp8_nvv4l2dec",
            "mpeg2video": "mpeg2_nvv4l2dec",
            "mpeg4": "mpeg4_nvv4l2dec"
        }

        decoder = hw_map.get(vcodec)
        print(f"🎯 Decoder hardware elegido según mapeo: {decoder}")

        hw_available = False

        # HEVC 10‑bit → NO hardware
        if is_10bit:
            print("⚠️ Vídeo ≥10‑bit detectado → NO existe soporte hardware en Jetson. Se convertirá a 8‑bit.")
            decoder = None

        # Comprobar si FFmpeg soporta ese decoder
        if decoder:
            print("🔎 Comprobando si FFmpeg soporta el decoder hardware…")
            try:
                result = subprocess.run(
                    ["ffmpeg", "-decoders"],
                    capture_output=True, text=True
                )

                if decoder in result.stdout:
                    hw_available = True
                    print(f"✅ HARDWARE DISPONIBLE: {decoder} encontrado")
                else:
                    print(f"❌ HARDWARE NO DISPONIBLE: {decoder} NO encontrado")

            except Exception as e:
                print(f"⚠️ Error comprobando decoders hardware: {e}")

        print(f"📌 Resultado final hardware disponible: {hw_available}")

        # Construcción del comando FFmpeg
        cmd = ["ffmpeg", "-y"]

        # Selección del método de aceleración
        if hw_available:

            if decoder.endswith("v4l2m2m"):
                print("🚀 ACTIVANDO V4L2 HARDWARE DECODING")
                cmd.extend(["-c:v", decoder])

            elif decoder.endswith("nvv4l2dec"):
                print("🚀 ACTIVANDO NVDEC")
                cmd.extend(["-hwaccel", "nvdec", "-c:v", decoder])

        else:
            print("⚠️ USANDO DECODIFICACIÓN POR CPU (fallback)")

        # Filtros de vídeo (optimización equilibrada)
        filters = [
            "scale=960:-1:flags=lanczos"  # ⭐ Reducción equilibrada para Jetson
        ]

        # Si es 10‑bit → convertir a 8‑bit
        if is_10bit:
            print("🔧 Convirtiendo a 8‑bit: añadiendo filtro format=yuv420p")
            filters.append("format=yuv420p")

        # Añadir filtros al comando
        cmd.extend(["-i", input_path, "-vf", ",".join(filters)])

        # Codificación final (CPU optimizada)
        cmd.extend([
            "-c:v", "libx264",
            "-preset", "ultrafast",          # Mucho más rápido
            "-crf", "26",                    # Equilibrio calidad/velocidad
            "-profile:v", "baseline",        # Reduce carga CPU
            "-c:a", "aac", "-b:a", "96k",
            "-movflags", "+faststart",
            output_path
        ])

        print("\n==============================")
        print("📦 COMANDO FINAL FFmpeg:")
        print(" ".join(cmd))
        print("==============================\n")

        # Ejecutar FFmpeg
        self.ffmpeg.execute(cmd)

        print("\n==============================")
        print("🏁 PIPELINE FINALIZADO")
        print("==============================\n")
