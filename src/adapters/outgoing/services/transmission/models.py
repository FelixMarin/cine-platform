"""
Modelos y constantes para Transmission
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

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

TORRENT_STATUS = {
    0: "stopped",
    1: "check queued",
    2: "checking",
    3: "download queued",
    4: "downloading",
    5: "seed queued",
    6: "seeding",
}


@dataclass
class TorrentDownload:
    """Representa una descarga en Transmission"""

    id: int
    name: str
    hash_string: str
    status: str
    progress: float
    size_when_done: int
    downloaded_ever: int
    upload_ratio: float
    rate_upload: int
    rate_download: int
    eta: int
    added_date: int
    done_date: Optional[int] = None
    magnet_link: Optional[str] = None
    files: List[Dict[str, Any]] = field(default_factory=list)
    category: Optional[str] = None
    download_dir: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "hash": self.hash_string,
            "status": self.status,
            "status_display": TORRENT_STATUS.get(self.status, "unknown"),
            "progress": round(self.progress * 100, 1),
            "size_total": self.size_when_done,
            "size_downloaded": self.downloaded_ever,
            "size_formatted": self._format_size(self.size_when_done),
            "upload_ratio": round(self.upload_ratio, 2),
            "rate_upload": self.rate_upload,
            "rate_download": self.rate_download,
            "download_speed_formatted": self._format_speed(self.rate_download),
            "upload_speed_formatted": self._format_speed(self.rate_upload),
            "eta": self.eta,
            "eta_formatted": self._format_eta(self.eta),
            "added_date": self.added_date,
            "done_date": self.done_date,
            "magnet_link": self.magnet_link,
            "files": self.files,
            "category": self.category,
            "download_dir": self.download_dir,
        }

    @staticmethod
    def _format_size(size: int) -> str:
        for unit in ["B", "KB", "MB", "GB", "TB"]:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} PB"

    @staticmethod
    def _format_eta(seconds: int) -> str:
        if seconds < 0:
            return "∞"
        if seconds < 60:
            return f"{seconds}s"
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        if hours > 0:
            return f"{hours}h {minutes}m"
        return f"{minutes}m"

    @staticmethod
    def _format_speed(bytes_per_sec: int) -> str:
        if bytes_per_sec <= 0:
            return "0 B/s"
        for unit in ["B/s", "KB/s", "MB/s", "GB/s"]:
            if bytes_per_sec < 1024.0:
                return f"{bytes_per_sec:.2f} {unit}"
            bytes_per_sec /= 1024.0
        return f"{bytes_per_sec:.2f} TB/s"


class TransmissionError(Exception):
    """Excepción para errores de Transmission"""

    def __init__(self, message: str, status_code: Optional[int] = None):
        self.message = message
        self.status_code = status_code
        super().__init__(self.message)
