"""
Constantes para codificación FFmpeg
"""

VIDEO_CODECS = {
    'h264': 'h264_nvenc',
    'hevc': 'hevc_nvenc', 
    'av1': 'libaom-av1'
}

PRESETS = {
    'ultra_fast': 'p1',
    'fast': 'p2', 
    'balanced': 'p4',
    'high_quality': 'p6',
    'master': 'p7'
}

PIXEL_FORMATS = {
    '8bit': 'yuv420p',
    '10bit': 'p010le',
    'hdr': 'yuv420p10le'
}

RESOLUTION_Bitrates = {
    '480p': 1500000,
    '720p': 3000000,
    '1080p': 5000000,
    '4k': 15000000
}

RESOLUTIONS = {
    '480': {'width': 854, 'height': 480},
    '720': {'width': 1280, 'height': 720},
    '1080': {'width': 1920, 'height': 1080},
    '4k': {'width': 3840, 'height': 2160}
}

HDR_FORMATS = ['hdr10', 'hlg', 'dolbyvision']
TEN_BIT_FORMATS = ['yuv420p10le', 'yuv444p10le']
