"""
Caso de uso - Optimizar video
"""
from typing import Dict, Optional
from src.core.ports.services.queue_service import IQueueService
from src.core.ports.services.encoder_service import IEncoderService


class OptimizeMovieUseCase:
    """Caso de uso para optimizar videos"""
    
    def __init__(
        self,
        queue_service: IQueueService,
        encoder_service: IEncoderService = None
    ):
        self._queue_service = queue_service
        self._encoder_service = encoder_service
    
    def execute(
        self,
        file_path: str,
        profile: str = "balanced"
    ) -> Dict:
        """
        Añade una tarea de optimización a la cola
        
        Args:
            file_path: Ruta del archivo a optimizar
            profile: Perfil de optimización
            
        Returns:
            Diccionario con el estado de la tarea
        """
        import os
        from pathlib import Path
        
        filename = os.path.basename(file_path)
        
        # Añadir tarea a la cola
        task = {
            'filename': filename,
            'filepath': file_path,
            'profile': profile,
            'status': 'queued'
        }
        
        success = self._queue_service.add_task(task)
        
        return {
            'success': success,
            'filename': filename,
            'profile': profile,
            'status': 'queued' if success else 'error'
        }
    
    def process_folder(
        self,
        folder_path: str,
        profile: str = "balanced"
    ) -> Dict:
        """
        Añade todos los videos de una carpeta a la cola
        
        Args:
            folder_path: Ruta de la carpeta
            profile: Perfil de optimización
            
        Returns:
            Diccionario con el resultado
        """
        import os
        
        valid_extensions = {".mp4", ".mkv", ".avi", ".mov", ".flv", ".wmv"}
        added_count = 0
        
        for root, _, files in os.walk(folder_path):
            for file in files:
                if os.path.splitext(file)[1].lower() in valid_extensions:
                    file_path = os.path.join(root, file)
                    task = {
                        'filename': file,
                        'filepath': file_path,
                        'profile': profile,
                        'status': 'queued'
                    }
                    if self._queue_service.add_task(task):
                        added_count += 1
        
        return {
            'success': True,
            'added_count': added_count,
            'profile': profile
        }
    
    def get_status(self) -> Dict:
        """Obtiene el estado actual del procesamiento"""
        return self._queue_service.get_status()
    
    def cancel_current(self) -> bool:
        """Cancela el procesamiento actual"""
        return self._queue_service.cancel_current_task()
    
    def get_available_profiles(self) -> Dict:
        """Obtiene los perfiles disponibles"""
        if self._encoder_service:
            return self._encoder_service.get_available_profiles()
        return {}


class EstimateSizeUseCase:
    """Caso de uso para estimar tamaño de video optimizado"""
    
    def __init__(self, encoder_service: IEncoderService):
        self._encoder_service = encoder_service
    
    def execute(
        self,
        file_path: str,
        profile: str = "balanced"
    ) -> Optional[Dict]:
        """
        Estima el tamaño final de un video optimizado
        
        Args:
            file_path: Ruta del archivo
            profile: Perfil de optimización
            
        Returns:
            Diccionario con la estimación
        """
        if not self._encoder_service:
            return None
        
        return self._encoder_service.estimate_size(file_path, profile)
