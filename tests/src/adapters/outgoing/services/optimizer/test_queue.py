"""
Tests para la cola de optimización
"""
import pytest
import threading
import time
from unittest.mock import patch, MagicMock
from src.adapters.outgoing.services.optimizer.queue import (
    OptimizationQueue,
    OptimizationJob,
    JobStatus,
    get_optimization_queue,
)


class TestJobStatus:
    """Tests del enum JobStatus"""
    
    def test_job_status_values(self):
        """Verificar valores del enum"""
        assert JobStatus.PENDING.value == "pending"
        assert JobStatus.RUNNING.value == "running"
        assert JobStatus.COMPLETED.value == "completed"
        assert JobStatus.FAILED.value == "failed"
        assert JobStatus.CANCELLED.value == "cancelled"


class TestOptimizationJob:
    """Tests de la clase OptimizationJob"""
    
    def test_create_job_basic(self):
        """Test de creación básica de trabajo"""
        job = OptimizationJob(
            id="test-123",
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Drama"
        )
        
        assert job.id == "test-123"
        assert job.input_path == "/input/movie.mkv"
        assert job.output_path == "/output/movie.mkv"
        assert job.category == "Drama"
        assert job.status == JobStatus.PENDING
        assert job.progress == 0.0
    
    def test_create_job_with_profile(self):
        """Test de creación con perfil"""
        job = OptimizationJob(
            id="test-456",
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Acción",
            profile="high_quality"
        )
        
        assert job.profile == "high_quality"
    
    def test_to_dict(self):
        """Test de conversión a diccionario"""
        job = OptimizationJob(
            id="test-789",
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Comedia"
        )
        
        result = job.to_dict()
        
        assert result["id"] == "test-789"
        assert result["input_path"] == "/input/movie.mkv"
        assert result["output_path"] == "/output/movie.mkv"
        assert result["category"] == "Comedia"
        assert result["status"] == "pending"
        assert "metrics" in result
    
    def test_format_size_bytes(self):
        """Test de formateo de tamaño en bytes"""
        assert OptimizationJob._format_size(500) == "500.00 B"
    
    def test_format_size_kilobytes(self):
        """Test de formateo en kilobytes"""
        assert OptimizationJob._format_size(2048) == "2.00 KB"
    
    def test_format_size_megabytes(self):
        """Test de formateo en megabytes"""
        assert OptimizationJob._format_size(1048576) == "1.00 MB"
    
    def test_format_size_gigabytes(self):
        """Test de formateo en gigabytes"""
        assert OptimizationJob._format_size(1073741824) == "1.00 GB"


class TestOptimizationQueue:
    """Tests de la clase OptimizationQueue"""
    
    @pytest.fixture
    def queue(self):
        """Fixture de cola de optimización"""
        return OptimizationQueue(max_concurrent=2)
    
    def test_queue_initialization(self, queue):
        """Test de inicialización de la cola"""
        assert queue.max_concurrent == 2
        assert queue._running_count == 0
        assert len(queue._jobs) == 0
    
    def test_add_job(self, queue):
        """Test de añadir trabajo a la cola"""
        job_id = queue.add_job(
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Drama",
            profile="balanced"
        )
        
        assert job_id is not None
        assert len(job_id) > 0
        
        job = queue.get_job(job_id)
        assert job is not None
        assert job.input_path == "/input/movie.mkv"
        assert job.output_path == "/output/movie.mkv"
        assert job.category == "Drama"
    
    def test_add_job_default_profile(self, queue):
        """Test de añadir trabajo con perfil por defecto"""
        job_id = queue.add_job(
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Acción"
        )
        
        job = queue.get_job(job_id)
        assert job.profile == "balanced"
    
    def test_get_job_not_found(self, queue):
        """Test de obtener trabajo que no existe"""
        job = queue.get_job("non-existent-id")
        assert job is None
    
    def test_get_all_jobs_empty(self, queue):
        """Test de obtener todos los trabajos cuando está vacía"""
        jobs = queue.get_all_jobs()
        assert len(jobs) == 0
    
    def test_get_all_jobs_with_jobs(self, queue):
        """Test de obtener todos los trabajos"""
        queue.add_job("/input/m1.mkv", "/output/m1.mkv", "Drama")
        queue.add_job("/input/m2.mkv", "/output/m2.mkv", "Comedia")
        
        jobs = queue.get_all_jobs()
        assert len(jobs) == 2
    
    def test_get_active_jobs_empty(self, queue):
        """Test de obtener trabajos activos cuando no hay"""
        active = queue.get_active_jobs()
        assert len(active) == 0
    
    def test_cancel_pending_job(self, queue):
        """Test de cancelar trabajo pendiente"""
        job_id = queue.add_job(
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Drama"
        )
        
        result = queue.cancel_job(job_id)
        assert result is True
        
        job = queue.get_job(job_id)
        assert job.status == JobStatus.CANCELLED
    
    def test_cancel_non_existent_job(self, queue):
        """Test de cancelar trabajo que no existe"""
        result = queue.cancel_job("non-existent-id")
        assert result is False
    
    def test_remove_completed_job(self, queue):
        """Test de eliminar trabajo completado"""
        job_id = queue.add_job(
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Drama"
        )
        
        # Simular completado
        job = queue.get_job(job_id)
        job.status = JobStatus.COMPLETED
        
        result = queue.remove_completed_job(job_id)
        assert result is True
        
        # Verificar que se eliminó
        job = queue.get_job(job_id)
        assert job is None
    
    def test_remove_non_completed_job(self, queue):
        """Test de eliminar trabajo no completado"""
        job_id = queue.add_job(
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Drama"
        )
        
        # No completar el trabajo
        result = queue.remove_completed_job(job_id)
        assert result is False
    
    def test_update_job_progress(self, queue):
        """Test de actualizar progreso del trabajo"""
        job_id = queue.add_job(
            input_path="/input/movie.mkv",
            output_path="/output/movie.mkv",
            category="Drama"
        )
        
        queue.update_job_progress(
            job_id,
            progress=50.0,
            current_time=120.5,
            fps=24.5
        )
        
        job = queue.get_job(job_id)
        assert job.progress == 50.0
        assert job.current_time == 120.5
        assert job.fps == 24.5
    
    def test_get_status_idle(self, queue):
        """Test de obtener estado cuando está idle"""
        status = queue.get_status()
        
        assert status["status"] == "idle"
        assert status["current_job"] is None
        assert len(status["active_jobs"]) == 0
        assert status["pending_count"] == 0
        assert status["running_count"] == 0
    
    def test_get_status_with_pending(self, queue):
        """Test de obtener estado con trabajos pendientes - con mock para evitar ejecución real"""
        with patch.object(queue, '_start_worker'):
            queue.add_job("/input/m1.mkv", "/output/m1.mkv", "Drama")
            queue.add_job("/input/m2.mkv", "/output/m2.mkv", "Comedia")
            
            status = queue.get_status()
            
            # Con _start_worker mockeado, los trabajos no se inician
            # así que el estado es idle pero hay trabajos pendientes
            assert status["pending_count"] == 2
            assert len(status["active_jobs"]) == 2
    
    def test_add_task_interface(self, queue):
        """Test del método add_task (interfaz IQueueService)"""
        task = {
            "filename": "movie.mkv",
            "filepath": "/input/movie.mkv",
            "profile": "balanced",
            "category": "Drama"
        }
        
        result = queue.add_task(task)
        assert result is True
        
        # Verificar que se añadió
        jobs = queue.get_all_jobs()
        assert len(jobs) == 1
    
    def test_add_task_empty_filepath(self, queue):
        """Test add_task con filepath vacío"""
        task = {
            "filename": "movie.mkv",
            "filepath": "",
            "profile": "balanced"
        }
        
        result = queue.add_task(task)
        assert result is False
    
    def test_get_task(self, queue):
        """Test de obtener siguiente tarea - con mock para evitar ejecución real"""
        with patch.object(queue, '_start_worker'):
            job_id = queue.add_job(
                input_path="/input/movie.mkv",
                output_path="/output/movie.mkv",
                category="Drama"
            )
            
            task = queue.get_task()
            assert task is not None
            assert task["id"] == job_id
    
    def test_get_task_empty(self, queue):
        """Test de obtener tarea cuando no hay"""
        task = queue.get_task()
        assert task is None
    
    def test_clear_queue(self, queue):
        """Test de vaciar la cola"""
        queue.add_job("/input/m1.mkv", "/output/m1.mkv", "Drama")
        queue.add_job("/input/m2.mkv", "/output/m2.mkv", "Comedia")
        
        result = queue.clear_queue()
        assert result is True
        
        jobs = queue.get_all_jobs()
        assert len(jobs) == 0
    
    def test_get_queue_size(self, queue):
        """Test de obtener tamaño de la cola"""
        assert queue.get_queue_size() == 0
        
        queue.add_job("/input/m1.mkv", "/output/m1.mkv", "Drama")
        queue.add_job("/input/m2.mkv", "/output/m2.mkv", "Comedia")
        
        assert queue.get_queue_size() == 2
    
    def test_start_stop(self, queue):
        """Test de iniciar y detener la cola"""
        result_start = queue.start()
        assert result_start is True
        
        result_stop = queue.stop()
        assert result_stop is True
    
    def test_is_running_empty(self, queue):
        """Test de verificar si está corriendo"""
        assert queue.is_running() is False


class TestGetOptimizationQueue:
    """Tests de la función get_optimization_queue"""
    
    def test_get_global_queue(self):
        """Test de obtener la cola global"""
        queue = get_optimization_queue()
        assert queue is not None
        assert isinstance(queue, OptimizationQueue)
    
    def test_get_global_queue_same_instance(self):
        """Test de que siempre devuelve la misma instancia"""
        queue1 = get_optimization_queue()
        queue2 = get_optimization_queue()
        
        assert queue1 is queue2