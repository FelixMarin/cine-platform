/**
 * Torrent Optimize - Cliente JavaScript para optimizar torrents descargados
 * 
 * Este módulo proporciona funcionalidad para:
 * - Iniciar optimización de torrents descargados
 * - Monitorear progreso de optimización
 * - Listar optimizaciones activas
 * - Verificar disponibilidad de GPU
 */

const TorrentOptimize = (function () {
    'use strict';

    // Intervalos para polling de estado
    let statusIntervals = {};
    const POLL_INTERVAL = 2000; // 2 segundos

    // ==========================================================================
    // API: Verificar disponibilidad de GPU
    // ==========================================================================

    /**
     * Verifica si hay GPU NVIDIA disponible para aceleración por hardware
     * @returns {Promise<{success: boolean, gpu_available: boolean}>}
     */
    async function checkGpuStatus() {
        try {
            const response = await fetch('/api/optimize-torrent/gpu-status', {
                credentials: 'include'
            });
            return await response.json();
        } catch (error) {
            console.error('[TorrentOptimize] Error verificando GPU:', error);
            return { success: false, gpu_available: false, error: error.message };
        }
    }

    // ==========================================================================
    // API: Iniciar optimización
    // ==========================================================================

    /**
     * Inicia la optimización de un torrent
     * @param {number} torrentId - ID del torrent en Transmission
     * @param {string} category - Categoría para organizar (action, comedy, etc.)
     * @returns {Promise<{success: boolean, process_id?: string, error?: string}>}
     */
    async function startOptimization(torrentId, category) {
        try {
            const response = await fetch('/api/optimize-torrent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                credentials: 'include',
                body: JSON.stringify({
                    torrent_id: torrentId,
                    category: category
                })
            });

            const result = await response.json();

            if (result.success && result.process_id) {
                console.log(`[TorrentOptimize] Optimización iniciada: ${result.process_id}`);
            }

            return result;
        } catch (error) {
            console.error('[TorrentOptimize] Error iniciando optimización:', error);
            return { success: false, error: error.message };
        }
    }

    // ==========================================================================
    // API: Consultar estado
    // ==========================================================================

    /**
     * Consulta el estado de una optimización
     * @param {string} processId - ID del proceso de optimización
     * @returns {Promise<{success: boolean, status?: string, progress?: number, error?: string}>}
     */
    async function getStatus(processId) {
        try {
            const response = await fetch(`/api/optimize-torrent/status/${processId}`, {
                credentials: 'include'
            });
            return await response.json();
        } catch (error) {
            console.error(`[TorrentOptimize] Error consultando estado de ${processId}:`, error);
            return { success: false, error: error.message };
        }
    }

    // ==========================================================================
    // API: Listar optimizaciones activas
    // ==========================================================================

    /**
     * Lista las optimizaciones activas
     * @returns {Promise<{success: boolean, active_count?: number, optimizations?: Array}>}
     */
    async function listActive() {
        try {
            const response = await fetch('/api/optimize-torrent/active', {
                credentials: 'include'
            });
            return await response.json();
        } catch (error) {
            console.error('[TorrentOptimize] Error listando activas:', error);
            return { success: false, error: error.message };
        }
    }

    // ==========================================================================
    // UI: Mostrar modal de optimización
    // ==========================================================================

    /**
     * Muestra el modal de optimización para un torrent
     * @param {Object} torrent - Información del torrent
     */
    function showOptimizeModal(torrent) {
        // Crear modal si no existe
        let modal = document.getElementById('torrent-optimize-modal');

        if (!modal) {
            modal = createOptimizeModal();
            document.body.appendChild(modal);
        }

        // Llenar información del torrent
        document.getElementById('optimize-torrent-name').textContent = torrent.name || 'Sin nombre';
        document.getElementById('optimize-torrent-size').textContent = formatSize(torrent.size || 0);
        document.getElementById('optimize-torrent-id').value = torrent.id;

        // Mostrar modal
        modal.classList.add('active');

        // Verificar GPU
        checkGpuStatus().then(result => {
            const gpuStatus = document.getElementById('optimize-gpu-status');
            if (result.success) {
                gpuStatus.textContent = result.gpu_available ? '✅ GPU NVIDIA detectada' : '⚠️ Sin GPU (usando CPU)';
                gpuStatus.className = result.gpu_available ? 'status-success' : 'status-warning';
            } else {
                gpuStatus.textContent = '❌ Error verificando GPU';
                gpuStatus.className = 'status-error';
            }
        });
    }

    /**
     * Crea el modal de optimización
     * @returns {HTMLElement}
     */
    function createOptimizeModal() {
        const modal = document.createElement('div');
        modal.id = 'torrent-optimize-modal';
        modal.className = 'modal';

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>🚀 Optimizar Torrent</h2>
                    <button class="modal-close" onclick="TorrentOptimize.closeModal()">&times;</button>
                </div>
                <div class="modal-body">
                    <div class="torrent-info">
                        <p><strong>Archivo:</strong> <span id="optimize-torrent-name">-</span></p>
                        <p><strong>Tamaño:</strong> <span id="optimize-torrent-size">-</span></p>
                        <p><strong>GPU:</strong> <span id="optimize-gpu-status">Verificando...</span></p>
                    </div>
                    
                    <div class="form-group">
                        <label for="optimize-category">Categoría:</label>
                        <select id="optimize-category" class="form-control">
                            <option value="action">Acción</option>
                            <option value="comedy">Comedia</option>
                            <option value="drama">Drama</option>
                            <option value="horror">Terror</option>
                            <option value="sci-fi">Ciencia Ficción</option>
                            <option value="animation">Animación</option>
                            <option value="documentary">Documental</option>
                            <option value="other">Otro</option>
                        </select>
                    </div>
                    
                    <input type="hidden" id="optimize-torrent-id">
                    
                    <div id="optimize-progress-container" class="progress-container" style="display: none;">
                        <div class="progress-bar">
                            <div id="optimize-progress-bar" class="progress-fill" style="width: 0%"></div>
                        </div>
                        <div class="progress-text">
                            <span id="optimize-progress-text">0%</span>
                            <span id="optimize-progress-status">Iniciando...</span>
                        </div>
                        <div id="optimize-eta" class="eta-text"></div>
                    </div>
                </div>
                <div class="modal-footer">
                    <button class="btn btn-secondary" onclick="TorrentOptimize.closeModal()">Cancelar</button>
                    <button class="btn btn-primary" id="btn-start-optimize" onclick="TorrentOptimize.submitOptimization()">
                        🚀 Iniciar Optimización
                    </button>
                </div>
            </div>
        `;

        return modal;
    }

    // ==========================================================================
    // UI: Cerrar modal
    // ==========================================================================

    /**
     * Cierra el modal de optimización
     */
    function closeModal() {
        const modal = document.getElementById('torrent-optimize-modal');
        if (modal) {
            modal.classList.remove('active');
        }

        // Detener polling
        stopStatusPolling();

        // Resetear UI
        const progressContainer = document.getElementById('optimize-progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }

        const progressBar = document.getElementById('optimize-progress-bar');
        if (progressBar) {
            progressBar.style.width = '0%';
        }

        const btn = document.getElementById('btn-start-optimize');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '🚀 Iniciar Optimización';
        }
    }

    // ==========================================================================
    // UI: Submit optimización
    // ==========================================================================

    /**
     * Envía la solicitud de optimización
     */
    async function submitOptimization() {
        const torrentId = parseInt(document.getElementById('optimize-torrent-id').value);
        const category = document.getElementById('optimize-category').value;

        if (!torrentId) {
            alert('ID de torrent inválido');
            return;
        }

        const btn = document.getElementById('btn-start-optimize');
        btn.disabled = true;
        btn.innerHTML = '⏳ Iniciando...';

        const result = await startOptimization(torrentId, category);

        if (result.success) {
            console.log(`[TorrentOptimize] Proceso iniciado: ${result.process_id}`);

            // Mostrar progress
            const progressContainer = document.getElementById('optimize-progress-container');
            progressContainer.style.display = 'block';

            // Iniciar polling de estado
            startStatusPolling(result.process_id);
        } else {
            alert(`Error: ${result.error}`);
            btn.disabled = false;
            btn.innerHTML = '🚀 Iniciar Optimización';
        }
    }

    // ==========================================================================
    // Polling de estado
    // ==========================================================================

    /**
     * Inicia el polling de estado para un proceso
     * @param {string} processId 
     */
    function startStatusPolling(processId) {
        // Detener cualquier polling anterior
        stopStatusPolling();

        // Función de polling
        const poll = async () => {
            const result = await getStatus(processId);

            if (result.success) {
                updateProgressUI(result);

                // Detener si completó o falló
                if (result.status === 'completed' || result.status === 'error') {
                    stopStatusPolling();

                    const btn = document.getElementById('btn-start-optimize');
                    if (result.status === 'completed') {
                        btn.innerHTML = '✅ Completado';
                        setTimeout(closeModal, 2000);
                    } else {
                        btn.innerHTML = '❌ Error';
                        btn.disabled = false;
                    }
                }
            }
        };

        // Iniciar intervalo
        statusIntervals[processId] = setInterval(poll, POLL_INTERVAL);

        // Ejecutar inmediatamente
        poll();
    }

    /**
     * Detiene el polling de estado
     */
    function stopStatusPolling() {
        Object.keys(statusIntervals).forEach(key => {
            if (statusIntervals[key]) {
                clearInterval(statusIntervals[key]);
                delete statusIntervals[key];
            }
        });
    }

    /**
     * Actualiza la UI con el progreso
     * @param {Object} status 
     */
    function updateProgressUI(status) {
        const progressBar = document.getElementById('optimize-progress-bar');
        const progressText = document.getElementById('optimize-progress-text');
        const progressStatus = document.getElementById('optimize-progress-status');
        const etaText = document.getElementById('optimize-eta');

        if (progressBar) {
            progressBar.style.width = `${status.progress || 0}%`;
        }

        if (progressText) {
            progressText.textContent = `${Math.round(status.progress || 0)}%`;
        }

        if (progressStatus) {
            const statusMap = {
                'pending': '⏳ Pendiente',
                'running': '🔄 Ejecutando',
                'completed': '✅ Completado',
                'error': '❌ Error'
            };
            progressStatus.textContent = statusMap[status.status] || status.status;
        }

        if (etaText && status.eta_seconds) {
            const minutes = Math.floor(status.eta_seconds / 60);
            const seconds = status.eta_seconds % 60;
            etaText.textContent = `⏱️ ETA: ${minutes}m ${seconds}s`;
        }
    }

    // ==========================================================================
    // Utilidades
    // ==========================================================================

    /**
     * Formatea bytes a tamaño legible
     * @param {number} bytes 
     * @returns {string}
     */
    function formatSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    }

    // ==========================================================================
    // Inicialización
    // ==========================================================================

    /**
     * Inicializa el módulo
     */
    function init() {
        console.log('[TorrentOptimize] Inicializado');

        // Agregar estilos si no existen
        addStyles();
    }

    /**
     * Agrega estilos CSS necesarios
     */
    function addStyles() {
        if (document.getElementById('torrent-optimize-styles')) return;

        const styles = document.createElement('style');
        styles.id = 'torrent-optimize-styles';
        styles.textContent = `
            .modal {
                display: none;
                position: fixed;
                top: 0;
                left: 0;
                width: 100%;
                height: 100%;
                background: rgba(0, 0, 0, 0.7);
                z-index: 9999;
                align-items: center;
                justify-content: center;
            }
            
            .modal.active {
                display: flex;
            }
            
            .modal-content {
                background: var(--bg-primary, #1a1a2e);
                border-radius: 12px;
                width: 90%;
                max-width: 500px;
                max-height: 90vh;
                overflow-y: auto;
                box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
            }
            
            .modal-header {
                display: flex;
                justify-content: space-between;
                align-items: center;
                padding: 20px;
                border-bottom: 1px solid var(--border-color, #333);
            }
            
            .modal-header h2 {
                margin: 0;
                font-size: 1.5rem;
                color: var(--text-primary, #fff);
            }
            
            .modal-close {
                background: none;
                border: none;
                color: var(--text-secondary, #aaa);
                font-size: 2rem;
                cursor: pointer;
                line-height: 1;
            }
            
            .modal-close:hover {
                color: var(--text-primary, #fff);
            }
            
            .modal-body {
                padding: 20px;
            }
            
            .modal-footer {
                padding: 20px;
                border-top: 1px solid var(--border-color, #333);
                display: flex;
                justify-content: flex-end;
                gap: 10px;
            }
            
            .torrent-info {
                background: var(--bg-secondary, #16213e);
                padding: 15px;
                border-radius: 8px;
                margin-bottom: 20px;
            }
            
            .torrent-info p {
                margin: 5px 0;
                color: var(--text-secondary, #aaa);
            }
            
            .torrent-info strong {
                color: var(--text-primary, #fff);
            }
            
            .form-group {
                margin-bottom: 20px;
            }
            
            .form-group label {
                display: block;
                margin-bottom: 8px;
                color: var(--text-primary, #fff);
                font-weight: 500;
            }
            
            .form-control {
                width: 100%;
                padding: 10px 15px;
                border: 1px solid var(--border-color, #333);
                border-radius: 6px;
                background: var(--bg-secondary, #16213e);
                color: var(--text-primary, #fff);
                font-size: 1rem;
            }
            
            .form-control:focus {
                outline: none;
                border-color: var(--accent-primary, #4f46e5);
            }
            
            .progress-container {
                margin-top: 20px;
            }
            
            .progress-bar {
                height: 8px;
                background: var(--bg-secondary, #16213e);
                border-radius: 4px;
                overflow: hidden;
            }
            
            .progress-fill {
                height: 100%;
                background: linear-gradient(90deg, #4f46e5, #06b6d4);
                transition: width 0.3s ease;
            }
            
            .progress-text {
                display: flex;
                justify-content: space-between;
                margin-top: 10px;
                color: var(--text-secondary, #aaa);
                font-size: 0.9rem;
            }
            
            .eta-text {
                text-align: center;
                margin-top: 10px;
                color: var(--text-secondary, #aaa);
                font-size: 0.85rem;
            }
            
            .status-success { color: #10b981; }
            .status-warning { color: #f59e0b; }
            .status-error { color: #ef4444; }
            
            .btn {
                padding: 10px 20px;
                border: none;
                border-radius: 6px;
                font-size: 1rem;
                cursor: pointer;
                transition: all 0.2s;
            }
            
            .btn-primary {
                background: linear-gradient(135deg, #4f46e5, #06b6d4);
                color: white;
            }
            
            .btn-primary:hover {
                transform: translateY(-2px);
                box-shadow: 0 4px 15px rgba(79, 70, 229, 0.4);
            }
            
            .btn-primary:disabled {
                opacity: 0.6;
                cursor: not-allowed;
                transform: none;
            }
            
            .btn-secondary {
                background: var(--bg-secondary, #16213e);
                color: var(--text-primary, #fff);
                border: 1px solid var(--border-color, #333);
            }
            
            .btn-secondary:hover {
                background: var(--bg-tertiary, #1f2937);
            }
        `;

        document.head.appendChild(styles);
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init);
    } else {
        init();
    }

    // API pública
    return {
        init,
        checkGpuStatus,
        startOptimization,
        getStatus,
        listActive,
        showOptimizeModal,
        closeModal,
        submitOptimization,
        formatSize
    };
})();
