"""
Cola de optimización de video - Sistema de gestión de trabajos

Este módulo gestiona la cola de optimización de videos usando threading.
Permite ejecutar múltiples optimizaciones en paralelo.
"""
import uuid
import threading
import logging
import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Callable
from enum import Enum
from datetime import datetime

logger = logging.getLogger(__name__)


class JobStatus(Enum):
    """Estados de un trabajo de optimización"""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class OptimizationJob:
    """Representa un trabajo de optimización"""
    id: str
    input_path: str
    output_path: str
    category: str  # Categoría chosen by user
    profile: str = "balanced"  # Perfil de encoding
    status: JobStatus = JobStatus.PENDING
    progress: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    
    # Métricas en tiempo real
    current_time: float = 0.0
    total_duration: float = 0.0
    fps: float = 0.0
    bitrate: int = 0
    current_size: int = 0
    estimated_size: int = 0
    
    # Información adicional
    error_message: Optional[str] = None
    files_info: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        """Convierte el trabajo a diccionario"""
        return {
            'id': self.id,
            'input_path': self.input_path,
            'output_path': self.output_path,
            'category': self.category,
            'profile': self.profile,
            'status': self.status.value,
            'progress': round(self.progress, 1),
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'metrics': {
                'current_time': self.current_time,
                'total_duration': self.total_duration,
                'fps': self.fps,
                'bitrate': self.bitrate,
                'current_size': self.current_size,
                'estimated_size': self.estimated_size,
                'size_formatted': self._format_size(self.current_size)
            },
            'error': self.error_message,
            'files': self.files_info
        }
    
    @staticmethod
    def _format_size(size: int) -> str:
        """Formatea tamaño en bytes"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024.0:
                return f"{size:.2f} {unit}"
            size /= 1024.0
        return f"{size:.2f} TB"


class OptimizationQueue:
    """
    Cola de optimización de video
    
    Gestiona múltiples trabajos de optimización en paralelo usando threads.
    """
    
    def __init__(self, max_concurrent: int = 2):
        """
        Inicializa la cola de optimización
        
        Args:
            max_concurrent: Número máximo de trabajos simultáneos
        """
        self.max_concurrent = max_concurrent
        self._jobs: Dict[str, OptimizationJob] = {}
        self._lock = threading.Lock()
        self._running_count = 0
        self._workers: List[threading.Thread] = []
        self._stop_event = threading.Event()
        
        logger.info(f"[Optimizer] Cola inicializada (max concurrent: {max_concurrent})")
    
    def add_job(self, input_path: str, output_path: str, category: str, 
                profile: str = "balanced") -> str:
        """
        Añade un nuevo trabajo a la cola
        
        Args:
            input_path: Ruta del archivo de entrada
            output_path: Ruta del archivo de salida
            category: Categoría (Acción, Drama, etc.)
            profile: Perfil de encoding
            
        Returns:
            ID del trabajo creado
        """
        job_id = str(uuid.uuid4())
        
        job = OptimizationJob(
            id=job_id,
            input_path=input_path,
            output_path=output_path,
            category=category,
            profile=profile
        )
        
        with self._lock:
            self._jobs[job_id] = job
            logger.info(f"[Optimizer] Trabajo añadido: {job_id} ({category})")
        
        # Iniciar worker si hay espacio
        self._start_worker()
        
        return job_id
    
    def get_job(self, job_id: str) -> Optional[OptimizationJob]:
        """Obtiene un trabajo por su ID"""
        with self._lock:
            return self._jobs.get(job_id)
    
    def get_all_jobs(self) -> List[OptimizationJob]:
        """Obtiene todos los trabajos"""
        with self._lock:
            return list(self._jobs.values())
    
    def get_active_jobs(self) -> List[OptimizationJob]:
        """Obtiene los trabajos activos (running o pending)"""
        with self._lock:
            return [
                j for j in self._jobs.values()
                if j.status in [JobStatus.PENDING, JobStatus.RUNNING]
            ]
    
    def cancel_job(self, job_id: str) -> bool:
        """Cancela un trabajo"""
        with self._lock:
            if job_id not in self._jobs:
                return False
            
            job = self._jobs[job_id]
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.CANCELLED
                logger.info(f"[Optimizer] Trabajo cancelado: {job_id}")
                return True
            elif job.status == JobStatus.PENDING:
                job.status = JobStatus.CANCELLED
                return True
        
        return False
    
    def remove_completed_job(self, job_id: str) -> bool:
        """Elimina un trabajo completado de la lista"""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                if job.status in [JobStatus.COMPLETED, JobStatus.FAILED, JobStatus.CANCELLED]:
                    del self._jobs[job_id]
                    return True
        return False
    
    def _start_worker(self):
        """Inicia un worker si hay espacio y trabajos pendientes"""
        with self._lock:
            if self._running_count >= self.max_concurrent:
                return
            
            # Buscar trabajo pendiente
            pending_job = None
            for job in self._jobs.values():
                if job.status == JobStatus.PENDING:
                    pending_job = job
                    break
            
            if not pending_job:
                return
            
            # Marcar como running
            pending_job.status = JobStatus.RUNNING
            pending_job.started_at = datetime.now()
            self._running_count += 1
        
        # Iniciar thread de ejecución
        thread = threading.Thread(
            target=self._run_job,
            args=(pending_job,),
            daemon=True
        )
        thread.start()
    
    def _run_job(self, job: OptimizationJob):
        """Ejecuta un trabajo de optimización"""
        try:
            logger.info(f"[Optimizer] Iniciando optimización: {job.id}")
            
            # Importar aquí para evitar ciclos
            from src.adapters.outgoing.services.optimizer.runner import OptimizationRunner
            
            runner = OptimizationRunner(job, self)
            runner.run()
            
            with self._lock:
                if job.status != JobStatus.CANCELLED:
                    job.status = JobStatus.COMPLETED
                    job.completed_at = datetime.now()
                    job.progress = 100.0
                    logger.info(f"[Optimizer] Optimización completada: {job.id}")
                
        except Exception as e:
            logger.error(f"[Optimizer] Error en optimización: {job.id} - {str(e)}")
            with self._lock:
                job.status = JobStatus.FAILED
                job.error_message = str(e)
                job.completed_at = datetime.now()
        
        finally:
            with self._lock:
                self._running_count -= 1
            
            # Intentar iniciar otro trabajo
            self._start_worker()
    
    def update_job_progress(self, job_id: str, **kwargs):
        """Actualiza el progreso de un trabajo"""
        with self._lock:
            if job_id in self._jobs:
                job = self._jobs[job_id]
                for key, value in kwargs.items():
                    if hasattr(job, key):
                        setattr(job, key, value)
    
    def get_status(self) -> Dict:
        """
        Obtiene el estado actual de la cola de optimización
        
        Returns:
            Diccionario con el estado de la cola y los trabajos activos
        """
        with self._lock:
            active_jobs = [
                j for j in self._jobs.values()
                if j.status in [JobStatus.PENDING, JobStatus.RUNNING]
            ]
            
            # Obtener trabajo actual si hay alguno ejecutándose
            current_job = None
            for job in active_jobs:
                if job.status == JobStatus.RUNNING:
                    current_job = job
                    break
            
            return {
                'status': 'running' if self._running_count > 0 else 'idle',
                'current_job': current_job.to_dict() if current_job else None,
                'active_jobs': [j.to_dict() for j in active_jobs],
                'pending_count': sum(1 for j in self._jobs.values() if j.status == JobStatus.PENDING),
                'running_count': self._running_count,
                'total_jobs': len(self._jobs)
            }
    
    # Métodos para implementar IQueueService
    def add_task(self, task: Dict) -> bool:
        """
        Añade una tarea a la cola (interfaz IQueueService)
        
        Args:
            task: Diccionario con los datos de la tarea
            
        Returns:
            True si se añadió correctamente
        """
        try:
            filename = task.get('filename', 'unknown')
            filepath = task.get('filepath', '')
            profile = task.get('profile', 'balanced')
            
            if not filepath:
                return False
            
            # Generar output_path basado en el input_path
            import os
            base, ext = os.path.splitext(filepath)
            output_path = f"{base}_optimized{ext}"
            
            # Obtener categoría del task o usar 'default'
            category = task.get('category', 'default')
            
            self.add_job(filepath, output_path, category, profile)
            return True
        except Exception as e:
            logger.error(f"[Queue] Error adding task: {e}")
            return False
    
    def get_task(self) -> Optional[Dict]:
        """
        Obtiene la siguiente tarea de la cola (interfaz IQueueService)
        """
        with self._lock:
            for job in self._jobs.values():
                if job.status == JobStatus.PENDING:
                    return job.to_dict()
        return None
    
    def cancel_current_task(self) -> bool:
        """
        Cancela la tarea actual (interfaz IQueueService)
        """
        with self._lock:
            for job in self._jobs.values():
                if job.status == JobStatus.RUNNING:
                    job.status = JobStatus.CANCELLED
                    logger.info(f"[Queue] Task cancelled: {job.id}")
                    return True
        return False
    
    def clear_queue(self) -> bool:
        """
        Vacía la cola de procesamiento (interfaz IQueueService)
        """
        with self._lock:
            self._jobs.clear()
            logger.info("[Queue] Queue cleared")
            return True
    
    def get_queue_size(self) -> int:
        """
        Obtiene el tamaño de la cola (interfaz IQueueService)
        """
        with self._lock:
            return len(self._jobs)
    
    def start(self) -> bool:
        """
        Inicia el worker de procesamiento (interfaz IQueueService)
        """
        self._stop_event.clear()
        logger.info("[Queue] Queue started")
        return True
    
    def stop(self) -> bool:
        """
        Detiene el worker de procesamiento (interfaz IQueueService)
        """
        self._stop_event.set()
        logger.info("[Queue] Queue stopped")
        return True
    
    def is_running(self) -> bool:
        """
        Verifica si el worker está corriendo (interfaz IQueueService)
        """
        return self._running_count > 0


# Instancia global de la cola
_global_queue: Optional[OptimizationQueue] = None


def get_optimization_queue() -> OptimizationQueue:
    """Obtiene la instancia global de la cola de optimización"""
    global _global_queue
    if _global_queue is None:
        _global_queue = OptimizationQueue(max_concurrent=2)
    return _global_queue
