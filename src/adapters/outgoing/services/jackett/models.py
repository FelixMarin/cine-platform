"""
Constantes y modelos para Jackett
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

CATEGORY_MAPPING = {
    "movies": "Películas",
    "tv": "Series",
    "documentaries": "Documentales",
    "music": "Música",
    "audio": "Música",
    "software": "Software",
    "games": "Juegos",
    "books": "Libros",
    "anime": "Anime",
    "xxx": "Adultos",
}

QUALITY_PATTERNS = [
    r"4K|UHD|2160p",
    r"1080p",
    r"720p",
    r"480p",
    r"BRRip|BRRip",
    r"BluRay|Blu-ray",
    r"WEB-DL|WEBDL|WEB",
    r"DVDRip|DVDrip",
    r"DVD|PDTV|HDTV",
    r"HDRip|HDRip",
    r"HDTV|HDTV",
]

LANGUAGE_PATTERNS = {
    "Español": [
        r"\bSPANISH\b",
        r"\bSPA\b",
        r"\bCASTELLANO\b",
        r"\bESPAÑOL\b",
        r"\bES\b",
    ],
    "Latino": [r"\bLATIN\b", r"\bLATINO\b", r"\bLAT\b"],
    "Inglés": [r"\bENGLISH\b", r"\bENG\b", r"\bINGLÉS\b", r"\bINGLES\b", r"\bEN\b"],
}


@dataclass
class JackettSearchResult:
    """Resultado de búsqueda de Jackett"""

    guid: str
    title: str
    indexer: str
    size: int
    seeders: int
    leechers: int
    magnet_url: Optional[str] = None
    torrent_url: Optional[str] = None
    publish_date: Optional[str] = None
    categories: List[str] = None
    source: str = "jackett"

    def __post_init__(self):
        if self.categories is None:
            self.categories = []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "guid": self.guid,
            "title": self.title,
            "indexer": self.indexer,
            "size": self.size,
            "size_formatted": self._format_size(self.size),
            "seeders": self.seeders,
            "leechers": self.leechers,
            "magnet_url": self.magnet_url,
            "torrent_url": self.torrent_url,
            "publish_date": self.publish_date,
            "categories": self.categories,
            "source": self.source,
        }

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"


class JackettError(Exception):
    """Excepción para errores de Jackett"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
