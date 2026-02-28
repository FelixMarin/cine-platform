"""
Puerto - Interfaz para servicio de cola de procesamiento
"""
from abc import ABC, abstractmethod
from typing import Dict, Optional, Callable


class IQueueService(ABC):
    """Puerto para servicios de cola de procesamiento"""
    
    @abstractmethod
    def add_task(self, task: Dict) -> bool:
        """Añade una tarea a la cola"""
        pass
    
    @abstractmethod
    def get_task(self) -> Optional[Dict]:
        """Obtiene la siguiente tarea de la cola"""
        pass
    
    @abstractmethod
    def get_status(self) -> Dict:
        """Obtiene el estado actual del procesamiento"""
        pass
    
    @abstractmethod
    def cancel_current_task(self) -> bool:
        """Cancela la tarea actual"""
        pass
    
    @abstractmethod
    def clear_queue(self) -> bool:
        """Vacía la cola de procesamiento"""
        pass
    
    @abstractmethod
    def get_queue_size(self) -> int:
        """Obtiene el tamaño de la cola"""
        pass
    
    @abstractmethod
    def start(self) -> bool:
        """Inicia el worker de procesamiento"""
        pass
    
    @abstractmethod
    def stop(self) -> bool:
        """Detiene el worker de procesamiento"""
        pass
    
    @abstractmethod
    def is_running(self) -> bool:
        """Verifica si el worker está corriendo"""
        pass
