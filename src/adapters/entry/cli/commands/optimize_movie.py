#!/usr/bin/env python3
# /src/adapters/entry/cli/commands/optimize_movie.py
"""
OPTIMIZE MOVIE — Versión auto-perfil + MKV streaming

- Usa contenedor Docker ffmpeg-cuda con GPU NVIDIA
- Detecta tipo de vídeo (codec, resolución, 10-bit, HDR)
- Elige automáticamente el "perfil" (bitrate, escala, codec, CPU/GPU)
- Salida SIEMPRE en MKV optimizado para streaming
"""

import argparse
import os
import sys
import time
import subprocess
import json
import tempfile

# Configuración del contenedor FFmpeg
FFMPEG_CONTAINER = "ffmpeg-cuda"
FFMPEG_CMD = ["docker", "exec", FFMPEG_CONTAINER, "ffmpeg"]
FFPROBE_CMD = ["docker", "exec", FFMPEG_CONTAINER, "ffprobe"]

# Directorios compartidos (deben coincidir con el docker-compose)
SHARED_INPUT = "/shared/input"
SHARED_OUTPUT = "/shared/output"
SHARED_TEMP = "/shared/temp"

class FFmpegInfo:
    PIX_FMT_10BIT = {
        "yuv420p10le", "yuv422p10le", "yuv444p10le",
        "yuv420p10", "yuv422p10", "yuv444p10"
    }
    HDR_TRANSFER = {"smpte2084", "arib-std-b67"}  # PQ, HLG
    HDR_PRIMARIES = {"bt2020"}
    HDR_MATRIX = {"bt2020nc"}

    def _map_to_shared_path(self, local_path: str) -> str:
        """Convierte una ruta local a su equivalente en el contenedor"""
        if "/mnt/DATA_2TB/audiovisual/mkv" in local_path:
            return local_path.replace("/mnt/DATA_2TB/audiovisual/mkv", "/shared/output")
        elif "/app/uploads" in local_path:
            return local_path.replace("/app/uploads", "/shared/uploads")
        elif "/app/temp" in local_path:
            return local_path.replace("/app/temp", "/shared/temp")
        elif "/app/outputs" in local_path:
            return local_path.replace("/app/outputs", "/shared/outputs")
        else:
            # Si no está mapeado, usar temp
            filename = os.path.basename(local_path)
            return f"{SHARED_TEMP}/{filename}"

    def probe(self, path: str) -> dict:
        """Ejecuta ffprobe en el contenedor"""
        shared_path = self._map_to_shared_path(path)
        cmd = FFPROBE_CMD + [
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            shared_path,
        ]
        try:
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=30)
            return json.loads(r.stdout) if r.returncode == 0 else {}
        except Exception as e:
            print(f"⚠️ Error en ffprobe: {e}")
            return {}

    def get_info(self, path: str) -> dict:
        data = self.probe(path)
        if not data:
            return {}

        fmt = data.get("format", {})
        streams = data.get("streams", [])

        info = {
            "path": path,
            "shared_path": self._map_to_shared_path(path),
            "filename": os.path.basename(path),
            "size": int(fmt.get("size", 0)),
            "duration": float(fmt.get("duration", 0.0) or 0.0),
            "vcodec": None,
            "acodec": None,
            "pix_fmt": None,
            "is_10bit": False,
            "is_hdr": False,
            "width": None,
            "height": None,
            "resolution_class": None,
            "fps": None,
        }

        for s in streams:
            if s.get("codec_type") == "video" and info["vcodec"] is None:
                info["vcodec"] = s.get("codec_name")
                info["pix_fmt"] = s.get("pix_fmt")
                info["width"] = s.get("width")
                info["height"] = s.get("height")
                info["is_10bit"] = info["pix_fmt"] in self.PIX_FMT_10BIT

                # FPS
                r_frame_rate = s.get("r_frame_rate", "0/1")
                try:
                    num, den = r_frame_rate.split("/")
                    info["fps"] = float(num) / float(den) if float(den) != 0 else None
                except Exception:
                    info["fps"] = None

                # HDR
                transfer = s.get("color_transfer")
                primaries = s.get("color_primaries")
                matrix = s.get("color_space")
                if (transfer in self.HDR_TRANSFER or
                        primaries in self.HDR_PRIMARIES or
                        matrix in self.HDR_MATRIX):
                    info["is_hdr"] = True

            elif s.get("codec_type") == "audio" and info["acodec"] is None:
                info["acodec"] = s.get("codec_name")

        # Clasificación por resolución
        w = info["width"] or 0
        h = info["height"] or 0
        if w == 0 or h == 0:
            info["resolution_class"] = "unknown"
        elif w <= 720 and h <= 576:
            info["resolution_class"] = "SD"
        elif w <= 1280 and h <= 720:
            info["resolution_class"] = "HD"
        elif w <= 1920 and h <= 1080:
            info["resolution_class"] = "FHD"
        elif w <= 3840 and h <= 2160:
            info["resolution_class"] = "UHD"
        else:
            info["resolution_class"] = "4K+"

        return info

    def nvenc_available(self) -> bool:
        """Verifica si el contenedor tiene codecs NVENC"""
        try:
            cmd = FFMPEG_CMD + ["-hide_banner", "-encoders"]
            r = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, timeout=10)
            return "h264_nvenc" in r.stdout
        except Exception:
            return False


class PipelineSelector:
    """
    Decide automáticamente:
    - codec de salida
    - filtros (escala, HDR→SDR, 10→8 bit)
    - uso de CPU/GPU
    - bitrate objetivo
    """

    def __init__(self, ffinfo: FFmpegInfo):
        self.ffinfo = ffinfo

    def auto_profile(self, info: dict) -> dict:
        """
        Devuelve un dict con:
        - use_gpu: bool
        - vcodec_out: str
        - vf: str or None
        - vparams: list
        - description: str
        - target_bitrate: str
        """
        vcodec = info["vcodec"]
        is_10bit = info["is_10bit"]
        is_hdr = info["is_hdr"]
        res_class = info["resolution_class"]
        nvenc = self.ffinfo.nvenc_available()

        # Bitrates base por clase de resolución
        if res_class == "SD":
            base_bitrate = "800k"
        elif res_class == "HD":
            base_bitrate = "1500k"
        elif res_class == "FHD":
            base_bitrate = "2500k"
        elif res_class in ("UHD", "4K+"):
            base_bitrate = "4000k"
        else:
            base_bitrate = "2000k"

        vf_filters = []
        use_gpu = False
        vcodec_out = "libx264"
        vparams = []
        desc = ""

        # === CASO 1: HEVC Main10 (10-bit) ===
        if vcodec == "hevc" and is_10bit:
            if nvenc:
                # GPU: convertir HDR→SDR + 8-bit, bajar a 1080p máx
                use_gpu = True
                if is_hdr:
                    vf_filters.append("zscale=t=bt709:m=bt709:p=bt709")
                vf_filters.append("format=nv12")
                if res_class in ("UHD", "4K+"):
                    vf_filters.append("scale_cuda=1920:1080")
                vcodec_out = "h264_nvenc"
                vparams = ["-preset", "p4", "-b:v", base_bitrate]
                desc = "HEVC Main10 HDR → GPU H.264 8-bit SDR"
            else:
                # CPU: mantener 10-bit, usar x265 main10, bajar a 1080p si es UHD+
                if res_class in ("UHD", "4K+"):
                    vf_filters.append("scale=1920:1080")
                vcodec_out = "libx265"
                vparams = ["-preset", "medium", "-x265-params", "profile=main10"]
                desc = "HEVC Main10 HDR → CPU x265 main10 (mantiene 10-bit)"

        # === CASO 2: HEVC 8-bit ===
        elif vcodec == "hevc" and not is_10bit:
            if nvenc:
                use_gpu = True
                if res_class in ("UHD", "4K+"):
                    vf_filters.append("scale_cuda=1920:1080")
                vcodec_out = "h264_nvenc"
                vparams = ["-preset", "p4", "-b:v", base_bitrate]
                desc = "HEVC 8-bit → GPU H.264 8-bit"
            else:
                if res_class in ("UHD", "4K+"):
                    vf_filters.append("scale=1920:1080")
                vcodec_out = "libx264"
                vparams = ["-preset", "medium", "-b:v", base_bitrate]
                desc = "HEVC 8-bit → CPU H.264"

        # === CASO 3: H.264 ===
        elif vcodec == "h264":
            if nvenc:
                use_gpu = True
                if res_class in ("UHD", "4K+"):
                    vf_filters.append("scale_cuda=1920:1080")
                vcodec_out = "h264_nvenc"
                vparams = ["-preset", "p4", "-b:v", base_bitrate]
                desc = "H.264 → GPU H.264"
            else:
                if res_class in ("UHD", "4K+"):
                    vf_filters.append("scale=1920:1080")
                vcodec_out = "libx264"
                vparams = ["-preset", "medium", "-b:v", base_bitrate]
                desc = "H.264 → CPU H.264"

        # === CASO 4: AV1 ===
        elif vcodec == "av1":
            if res_class in ("UHD", "4K+"):
                vf_filters.append("scale=1920:1080")
            vcodec_out = "libx265"
            vparams = ["-preset", "medium"]
            desc = "AV1 → CPU x265"

        # === CASO 5: VP9 ===
        elif vcodec == "vp9":
            if res_class in ("UHD", "4K+"):
                vf_filters.append("scale=1920:1080")
            vcodec_out = "libx265"
            vparams = ["-preset", "medium"]
            desc = "VP9 → CPU x265"

        else:
            # Fallback genérico
            if res_class in ("UHD", "4K+"):
                vf_filters.append("scale=1920:1080")
            vcodec_out = "libx264"
            vparams = ["-preset", "medium", "-b:v", base_bitrate]
            desc = f"{vcodec or 'desconocido'} → CPU H.264 (fallback)"

        vf = ",".join(vf_filters) if vf_filters else None

        return {
            "use_gpu": use_gpu,
            "vcodec_out": vcodec_out,
            "vf": vf,
            "vparams": vparams,
            "description": desc,
            "target_bitrate": base_bitrate,
        }


class FFmpegRunner:
    def __init__(self, info: dict, pipeline: dict):
        self.info = info
        self.pipeline = pipeline

    def run(self, input_path: str, output_path: str) -> bool:
        """Ejecuta FFmpeg en el contenedor"""
        # Convertir rutas locales a rutas en el contenedor
        input_shared = self.info["shared_path"]
        output_shared = self._map_to_shared_path(output_path)

        # Asegurar directorio de salida
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        # Construir comando para ejecutar en contenedor
        cmd = FFMPEG_CMD + [
            "-y", "-hide_banner", "-progress", "pipe:1",
            "-i", input_shared,
            "-map", "0"  # Preservar todos los streams
        ]

        if self.pipeline["vf"]:
            cmd.extend(["-vf", self.pipeline["vf"]])

        cmd.extend(["-c:v", self.pipeline["vcodec_out"]])
        cmd.extend(self.pipeline["vparams"])

        # Audio: AAC para streaming
        cmd.extend(["-c:a", "aac", "-b:a", "128k"])

        # Subtítulos: copiar
        cmd.extend(["-c:s", "copy"])

        # MKV optimizado para streaming
        cmd.extend(["-f", "matroska", "-movflags", "+faststart", "-max_interleave_delta", "0"])
        cmd.append(output_shared)

        print("\n🧩 Comando FFmpeg (en contenedor):")
        print(" ", " ".join(cmd))
        print("\n🚀 Iniciando optimización...\n")

        # Ejecutar proceso
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, bufsize=1)

        duration = self.info.get("duration", 0.0) or 0.0
        start = time.time()

        # Monitorear progreso
        while True:
            line = proc.stdout.readline()
            if not line:
                if proc.poll() is not None:
                    break
                continue

            if "out_time_ms=" in line and duration > 0:
                try:
                    ms = int(line.strip().split("=")[1])
                    sec = ms / 1_000_000
                    pct = max(0, min(100, int(sec / duration * 100)))
                    bar_len = 30
                    filled = int(bar_len * pct / 100)
                    bar = "█" * filled + "░" * (bar_len - filled)
                    elapsed = int(time.time() - start)
                    sys.stdout.write(f"\r[{bar}] {pct:3d}% | {elapsed}s")
                    sys.stdout.flush()
                except Exception:
                    pass

        ret = proc.wait()
        print()

        if ret == 0:
            in_mb = self.info["size"] / (1024 * 1024) if self.info["size"] else 0
            out_mb = os.path.getsize(output_path) / (1024 * 1024) if os.path.exists(output_path) else 0
            ratio = int((1 - out_mb / in_mb) * 100) if in_mb > 0 and out_mb > 0 else 0
            print("✅ Optimización completada.")
            print(f"   Original:   {in_mb:.1f} MB")
            print(f"   Optimizado: {out_mb:.1f} MB")
            print(f"   Reducción:  {ratio}%")
            return True
        else:
            stderr = proc.stderr.read()
            print("❌ Error en FFmpeg.")
            print(stderr[:800])
            return False

    def _map_to_shared_path(self, local_path: str) -> str:
        """Convierte ruta local a ruta en contenedor"""
        if "/mnt/DATA_2TB/audiovisual/mkv" in local_path:
            return local_path.replace("/mnt/DATA_2TB/audiovisual/mkv", "/shared/output")
        elif "/app/uploads" in local_path:
            return local_path.replace("/app/uploads", "/shared/uploads")
        elif "/app/temp" in local_path:
            return local_path.replace("/app/temp", "/shared/temp")
        elif "/app/outputs" in local_path:
            return local_path.replace("/app/outputs", "/shared/outputs")
        else:
            filename = os.path.basename(local_path)
            return f"/shared/temp/{filename}"


def check_container():
    """Verifica que el contenedor ffmpeg-cuda está corriendo"""
    try:
        r = subprocess.run(["docker", "ps", "--filter", f"name={FFMPEG_CONTAINER}", "--format", "{{.Names}}"],
                          capture_output=True, text=True)
        return FFMPEG_CONTAINER in r.stdout
    except:
        return False


def main():
    parser = argparse.ArgumentParser(description="Optimizar película a MKV streaming (auto-perfil)")
    parser.add_argument("-i", "--input", required=True, help="Archivo de entrada")
    parser.add_argument("-o", "--output", required=True, help="Archivo de salida (.mkv recomendado)")
    parser.add_argument("--cpu", action="store_true", help="Forzar CPU (ignorar GPU aunque exista)")
    parser.add_argument("--info", action="store_true", help="Solo mostrar información del vídeo y salir")
    args = parser.parse_args()

    # Verificar contenedor
    if not check_container():
        print(f"❌ El contenedor '{FFMPEG_CONTAINER}' no está corriendo.")
        print("   Ejecuta: docker-compose up -d en el directorio de ffmpeg-cuda")
        return 1

    if not os.path.exists(args.input):
        print(f"❌ El archivo de entrada no existe: {args.input}")
        return 1

    ffinfo = FFmpegInfo()
    info = ffinfo.get_info(args.input)
    if not info:
        print("❌ No se pudo obtener información del vídeo.")
        return 1

    print("\n📊 Información del vídeo:")
    print(f"   Archivo:   {info['filename']}")
    print(f"   Codec:     {info['vcodec']}")
    print(f"   Resolución:{info['width']}x{info['height']} ({info['resolution_class']})")
    print(f"   PixFmt:    {info['pix_fmt']}")
    print(f"   10-bit:    {'Sí' if info['is_10bit'] else 'No'}")
    print(f"   HDR:       {'Sí' if info['is_hdr'] else 'No'}")
    print(f"   Duración:  {info['duration'] / 60:.1f} min")
    print()

    if args.info:
        return 0

    selector = PipelineSelector(ffinfo)
    pipeline = selector.auto_profile(info)

    # Si el usuario fuerza CPU, ignoramos GPU
    if args.cpu:
        pipeline["use_gpu"] = False
        if pipeline["vcodec_out"] == "h264_nvenc":
            pipeline["vcodec_out"] = "libx264"
            vparams = pipeline["vparams"]
            if "-preset" in vparams:
                idx = vparams.index("-preset")
                vparams[idx + 1] = "medium"
            else:
                vparams.extend(["-preset", "medium"])
            pipeline["description"] += " (forzado CPU)"

    print("🎯 Perfil automático seleccionado:")
    print(f"   Descripción: {pipeline['description']}")
    print(f"   Codec out:   {pipeline['vcodec_out']}")
    print(f"   Filtros:     {pipeline['vf'] or 'Ninguno'}")
    print()

    runner = FFmpegRunner(info, pipeline)
    ok = runner.run(args.input, args.output)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())