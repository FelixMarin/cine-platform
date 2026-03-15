"""
Constantes y modelos para Prowlarr
"""

from dataclasses import dataclass
from typing import Optional, List, Dict, Any

CATEGORY_MAPPING = {
    2070: "Películas",
    2040: "Películas",
    2050: "Películas",
    2030: "Películas",
    2010: "Películas",
    2000: "Películas",
    5040: "Series",
    5030: "Series",
    5010: "Series",
    5020: "Series",
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
    "Español": [r"\bSPANISH\b", r"\bSPA\b", r"\bCASTELLANO\b", r"\bESPAÑOL\b"],
    "Latino": [r"\bLATIN\b", r"\bLATINO\b", r"\bLAT\b"],
    "Inglés": [r"\bENGLISH\b", r"\bENG\b", r"\bINGLÉS\b", r"\bINGLES\b"],
}


@dataclass
class ProwlarrSearchResult:
    """Resultado de búsqueda de Prowlarr"""

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
        }

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"
