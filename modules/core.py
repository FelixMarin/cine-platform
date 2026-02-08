from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any

# --- ENTITIES ---

@dataclass
class MediaItem:
    name: str
    path: str
    thumbnail: str

@dataclass
class OptimizationState:
    current_video: Optional[str] = None
    current_step: int = 0
    history: List[Dict] = field(default_factory=list)
    log_line: str = ""
    video_info: Dict = field(default_factory=dict)

# --- PORTS (INTERFACES) ---

class IAuthService(ABC):
    @abstractmethod
    def login(self, email, password) -> Tuple[bool, Any]:
        pass

class IMediaRepository(ABC):
    @abstractmethod
    def list_content(self) -> Tuple[List[Dict], Dict[str, List[Dict]]]:
        pass

    @abstractmethod
    def get_safe_path(self, filename: str) -> Optional[str]:
        pass

class IOptimizerService(ABC):
    @abstractmethod
    def process_file(self, file_path: str):
        pass

    @abstractmethod
    def process_folder(self, folder_path: str):
        pass

    @abstractmethod
    def get_status(self) -> Dict:
        pass