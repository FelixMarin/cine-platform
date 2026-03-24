"""
Constantes para Transmission
"""

import os

TRANSMISSION_URL = os.environ.get(
    "TRANSMISSION_URL", "http://transmission:9091/transmission/rpc"
)
TRANSMISSION_USERNAME = os.environ.get("TRANSMISSION_USERNAME", "transmission")
TRANSMISSION_PASSWORD = os.environ.get("TRANSMISSION_PASSWORD", "transmission")
TRANSMISSION_TIMEOUT = int(os.environ.get("TRANSMISSION_TIMEOUT", 30))

TORRENT_STATUS_MAP = {
    0: "stopped",
    1: "check queued",
    2: "checking",
    3: "download queued",
    4: "downloading",
    5: "seed queued",
    6: "seeding",
}

TORRENT_CATEGORIES = {
    "movies": ["Películas", "movies"],
    "tv": ["Series", "tv"],
    "music": ["Música", "music"],
    "games": ["Juegos", "games"],
    "software": ["Software", "software"],
}

DEFAULT_CATEGORY = "uncategorized"

VIDEO_EXTENSIONS = (
    ".mkv",
    ".mp4",
    ".avi",
    ".mov",
    ".webm",
    ".m4v",
    ".wmv",
    ".flv",
    ".ts",
    ".m2ts",
)

MAX_FILE_SIZE = 50 * 1024 * 1024 * 1024
