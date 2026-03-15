"""
Patrones Regex para parser de FFmpeg
"""

import re

FFMPEG_PATTERNS = {
    "time": re.compile(r"time=(\d{2}):(\d{2}):(\d{2})\.(\d{2})"),
    "fps": re.compile(r"fps=\s*(\d+\.?\d*)"),
    "bitrate": re.compile(r"bitrate=\s*(\d+\.?\d*\s*[kmg]?/s)"),
    "size": re.compile(r"size=\s*(\d+\.?\d*\s*[kmg]?B)"),
    "speed": re.compile(r"speed=\s*(\d+\.?\d*x)"),
    "progress": re.compile(r"progress=(\w+)"),
    "frame": re.compile(r"frame=\s*(\d+)"),
    "q": re.compile(r"q=\s*(\d+\.?\d*)"),
    "codec": re.compile(r"codec=(\w+)"),
    "stream": re.compile(r"Stream #0:(\d+)(?:\([\w:]+\))?: (\w+): (\w+)"),
}

SIZE_UNITS = {"B": 1, "KB": 1024, "MB": 1024**2, "GB": 1024**3, "TB": 1024**4}
