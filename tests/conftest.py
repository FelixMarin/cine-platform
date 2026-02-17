import pytest
import sys
import os
import queue
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

@pytest.fixture(autouse=True)
def patch_worker(monkeypatch):
    """Parchear el módulo worker para evitar errores"""
    
    # Crear mocks para las variables globales
    mock_queue = queue.Queue()
    mock_status = {
        "current": None,
        "queue_size": 0,
        "log_line": "",
        "frames": 0,
        "fps": 0,
        "time": "",
        "speed": "",
        "video_info": {},
        "cancelled": False,
        "last_update": 0
    }
    mock_optimizer = MagicMock()
    
    # Parchear el módulo worker
    import modules.worker
    monkeypatch.setattr(modules.worker, 'processing_queue', mock_queue)
    monkeypatch.setattr(modules.worker, 'processing_status', mock_status)
    monkeypatch.setattr(modules.worker, 'optimizer_service', mock_optimizer)
    monkeypatch.setattr(modules.worker, 'current_ffmpeg_process', None)
    
    # Parchear start_worker para que no haga nada
    monkeypatch.setattr(modules.worker, 'start_worker', MagicMock(return_value=None))
    
    # Parchear background_worker para que no se ejecute
    monkeypatch.setattr(modules.worker, 'background_worker', MagicMock())
    
    return mock_queue, mock_status, mock_optimizer