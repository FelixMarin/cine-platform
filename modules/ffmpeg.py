# modules/ffmpeg.py
"""
Módulo FFmpeg - Compatibilidad hacia atrás.
Las clases han sido movidas al paquete modules/ffmpeg/
"""
# Re-exportar clases para compatibilidad hacia atrás
from modules.ffmpeg import FFmpegConfig, FFmpegValidator, FFmpegProbe, FFmpegProcess, FFmpegHandler

__all__ = [
    'FFmpegConfig',
    'FFmpegValidator', 
    'FFmpegProbe',
    'FFmpegProcess',
    'FFmpegHandler'
]
