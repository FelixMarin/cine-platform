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
    // Helper: Fetch con manejo de 401
    // ==========================================================================

    /**
     * Función fetch con manejo automático de 401
     * @param {string} url - URL a.fetch
     * @param {Object} options - Opciones de fetch
     * @returns {Promise<Response>}
     */
    async function authFetch(url, options = {}) {
        const defaultOptions = {
            credentials: 'include'
        };
        const mergedOptions = { ...defaultOptions, ...options };
        
        const response = await fetch(url, mergedOptions);
        
        // Manejar 401 - redirigir a login
        if (response.status === 401) {
            console.warn('[TorrentOptimize] Sesión expirada, redirigiendo a login...');
            if (typeof showNotification === 'function') {
                showNotification('Sesión expirada', 'Por favor, inicia sesión nuevamente', 'warning');
            }
            // Redirigir a login después de un breve delay
            setTimeout(() => {
                window.location.href = '/login';
            }, 1500);
        }
        
        return response;
    }

    // ==========================================================================
    // API: Verificar disponibilidad de GPU
    // ==========================================================================

    /**
     * Verifica si hay GPU NVIDIA disponible para aceleración por hardware
     * @returns {Promise<{success: boolean, gpu_available: boolean}>}
     */
    async function checkGpuStatus() {
        try {
            const response = await authFetch('/api/optimize-torrent/gpu-status');
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
            const response = await authFetch('/api/optimize-torrent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
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
            const response = await authFetch(`/api/optimize-torrent/status/${processId}`);
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
            const response = await authFetch('/api/optimize-torrent/active');
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

        const decodedName = decodeURIComponent(torrent.name);
        // Llenar información del torrent
        document.getElementById('optimize-torrent-name').textContent = decodedName || 'Sin nombre';
        document.getElementById('optimize-torrent-size').textContent = formatSize(torrent.size || 0);
        document.getElementById('optimize-torrent-id').value = torrent.id;

        // Mostrar modal (no bloqueante - permite scroll)
        modal.classList.add('active');
        document.body.style.overflow = 'auto';

        // Resetear el progreso
        const progressContainer = document.getElementById('optimize-progress-container');
        if (progressContainer) {
            progressContainer.style.display = 'none';
        }
        
        const btn = document.getElementById('btn-start-optimize');
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '🚀 Iniciar Optimización';
        }

        // Verificar GPU
        checkGpuStatus().then(result => {
            const gpuStatus = document.getElementById('optimize-gpu-status');
            if (result.success) {
                if (result.gpu_available && result.gpu_name) {
                    gpuStatus.textContent = `✅ ${result.gpu_name} detectada`;
                    gpuStatus.className = 'status-success';
                } else {
                    gpuStatus.textContent = '⚠️ Sin GPU (usando CPU)';
                    gpuStatus.className = 'status-warning';
                }
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

        // Permitir scroll (asegurar que no queda bloqueado)
        document.body.style.overflow = 'auto';

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
        const torrentId = document.getElementById('optimize-torrent-id').value;
        const category = document.getElementById('optimize-category').value;
        let filename = document.getElementById('optimize-torrent-name').textContent;

        if (!torrentId) {
            alert('ID de torrent inválido');
            return;
        }

        // Si filename no tiene extensión, añadirla según el torrent_id
        // Esto es un mapeo temporal hasta que el frontend envíe la extensión correcta
        if (filename && !filename.includes('.')) {
            const extensions = {
                1: '.mp4',  // Spaceman
                2: '.mkv'   // TRON
            };
            const ext = extensions[torrentId];
            if (ext) {
                filename = filename + ext;
                console.log('[TorrentOptimize] Extensión añadida:', filename);
            }
        }

        console.log('[TorrentOptimize] Enviando optimización:', { torrentId, category, filename });

        const btn = document.getElementById('btn-start-optimize');
        btn.disabled = true;
        btn.innerHTML = '⏳ Iniciando...';

        try {
            const response = await authFetch('/api/optimize-torrent', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ 
                    torrent_id: torrentId, 
                    filename: filename,
                    category 
                })
            });
            
            const result = await response.json();

            if (result.success) {
                console.log(`[TorrentOptimize] Proceso iniciado: ${result.process_id}`);

                // Cerrar modal inmediatamente
                closeModal();
                
                // Actualizar botón en downloads
                if (window.updateDownloadButton) {
                    window.updateDownloadButton(torrentId, '⏳ Optimizando');
                }
                
                // Mostrar notificación indicando dónde ver el progreso
                if (typeof showNotification === 'function') {
                    showNotification(
                        '⚡ Optimización iniciada', 
                        'El proceso se está ejecutando en segundo plano. Puedes ver el progreso en la pestaña "Optimizaciones".',
                        'success'
                    );
                }

                // Iniciar monitoreo en segundo plano
                monitorOptimization(result.process_id, torrentId);
                
                // Intentar cambiar a la pestaña de optimizaciones si existe la función
                if (typeof switchTab === 'function') {
                    switchTab('optimizations');
                } else if (typeof window.switchToOptimizationsTab === 'function') {
                    window.switchToOptimizationsTab();
                }
            } else {
                throw new Error(result.error || 'Error desconocido');
            }
        } catch (error) {
            console.error('[TorrentOptimize] Error:', error);
            btn.disabled = false;
            btn.innerHTML = '🚀 Iniciar Optimización';
            
            // Actualizar botón con error
            if (window.updateDownloadButton) {
                window.updateDownloadButton(torrentId, '❌ Error', true);
            }
            
            if (typeof showNotification === 'function') {
                showNotification('Error', error.message, 'error');
            } else {
                alert(`Error: ${error.message}`);
            }
        }
    }

    // ==========================================================================
    // MONITOREO DE OPTIMIZACIÓN
    // ==========================================================================

    /**
     * Monitorea el progreso de una optimización
     * @param {string} processId - ID del proceso
     * @param {string} torrentId - ID del torrent
     */
    function monitorOptimization(processId, torrentId) {
        const poll = async () => {
            try {
                const result = await getStatus(processId);

                if (result.success) {
                    // Actualizar UI del modal si está abierto
                    updateProgressUI(result);

                    // Detener si completó o falló
                    if (result.status === 'completed' || result.status === 'error') {
                        // Detener el polling
                        if (statusIntervals[processId]) {
                            clearInterval(statusIntervals[processId]);
                            delete statusIntervals[processId];
                        }

                        // Actualizar botón según resultado
                        if (window.updateDownloadButton) {
                            if (result.status === 'completed') {
                                window.updateDownloadButton(torrentId, '✅ Optimizado');
                            } else {
                                window.updateDownloadButton(torrentId, '❌ Error', true);
                            }
                        }

                        // Mostrar notificación con mensaje de error si falló
                        if (result.status === 'error' && result.error) {
                            if (typeof showNotification === 'function') {
                                showNotification(
                                    '❌ Error en optimización',
                                    result.error,
                                    'error'
                                );
                            }
                            console.error('[TorrentOptimize] Error en optimización:', result.error);
                        } else if (result.status === 'completed') {
                            if (typeof showNotification === 'function') {
                                showNotification(
                                    '✅ Optimización completada',
                                    'El archivo ha sido optimizado correctamente',
                                    'success'
                                );
                            }
                        }

                        // Refrescar lista de optimizaciones
                        refreshOptimizationsList();
                    }
                }
            } catch (error) {
                console.error('[TorrentOptimize] Error en monitoreo:', error);
            }
        };

        // Iniciar intervalo de polling
        statusIntervals[processId] = setInterval(poll, POLL_INTERVAL);
        
        // Ejecutar inmediatamente
        poll();
    }

    /**
     * Refresca la lista de optimizaciones
     */
    function refreshOptimizationsList() {
        listActive().then(result => {
            if (result.success && typeof refreshOptimizations === 'function') {
                // Actualizar el estado global si es necesario
                console.log('[TorrentOptimize] Optimizaciones activas:', result.active_count);
            }
        });
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
            
            /* ESTADOS DEL BOTÓN GPU OPTIMIZE */
            .btn-optimize {
                background-color: #28a745;
                color: white;
                border: none;
                padding: 5px 10px;
                border-radius: 3px;
                cursor: pointer;
                transition: all 0.2s ease;
                font-size: 0.9rem;
            }
            
            .btn-optimize:hover {
                background-color: #218838;
            }
            
            .btn-optimize.optimizing {
                background-color: #ffc107;
                color: #212529;
                cursor: not-allowed;
                opacity: 0.8;
            }
            
            .btn-optimize.optimizing:hover {
                background-color: #ffc107;
            }
            
            .btn-optimize.optimized {
                background-color: #6c757d;
                color: white;
                cursor: not-allowed;
                opacity: 0.6;
            }
            
            .btn-optimize.optimized:hover {
                background-color: #6c757d;
            }
            
            .btn-optimize.error {
                background-color: #dc3545;
                color: white;
            }
            
            .btn-optimize.error:hover {
                background-color: #c82333;
            }
            
            .btn-optimize:disabled {
                cursor: not-allowed;
            }
        `;

        document.head.appendChild(styles);
    }

    // ==========================================================================
    // ESTADOS DEL BOTÓN GPU OPTIMIZE - Persistencia y gestión de estados
    // ==========================================================================

    // Constantes para estados del botón
    const BUTTON_STATES = {
        IDLE: 'idle',           // No optimizado o error - habilitado verde
        OPTIMIZING: 'optimizing', // Optimizando - deshabilitado amarillo
        OPTIMIZED: 'optimized',   // Optimizado con éxito - deshabilitado gris
        ERROR: 'error'            // Error - habilitado verde para reintentar
    };

    // Clave para localStorage
    const STORAGE_KEY = 'cine-platform-optimize-processes';
    const STORAGE_TIMEOUT = 5 * 60 * 1000; // 5 minutos

    /**
     * Obtiene los procesos guardados en localStorage
     * @returns {Object} Objeto con torrentId -> {process_id, status, lastUpdate}
     */
    function getStoredProcesses() {
        try {
            const stored = localStorage.getItem(STORAGE_KEY);
            if (!stored) return {};
            
            const processes = JSON.parse(stored);
            // Limpiar procesos antiguos (más de 5 minutos)
            const now = Date.now();
            const cleaned = {};
            for (const [torrentId, data] of Object.entries(processes)) {
                if (now - data.lastUpdate < STORAGE_TIMEOUT) {
                    cleaned[torrentId] = data;
                }
            }
            return cleaned;
        } catch (e) {
            console.error('[TorrentOptimize] Error leyendo procesos guardados:', e);
            return {};
        }
    }

    /**
     * Guarda un proceso en localStorage
     * @param {string} torrentId - ID del torrent
     * @param {string} processId - ID del proceso
     * @param {string} status - Estado del proceso
     */
    function saveProcess(torrentId, processId, status) {
        try {
            const processes = getStoredProcesses();
            processes[torrentId] = {
                process_id: processId,
                status: status,
                lastUpdate: Date.now()
            };
            localStorage.setItem(STORAGE_KEY, JSON.stringify(processes));
        } catch (e) {
            console.error('[TorrentOptimize] Error guardando proceso:', e);
        }
    }

    /**
     * Elimina un proceso de localStorage
     * @param {string} torrentId - ID del torrent
     */
    function removeProcess(torrentId) {
        try {
            const processes = getStoredProcesses();
            delete processes[torrentId];
            localStorage.setItem(STORAGE_KEY, JSON.stringify(processes));
        } catch (e) {
            console.error('[TorrentOptimize] Error eliminando proceso:', e);
        }
    }

    /**
     * Obtiene el estado del botón según el estado de optimización
     * @param {string} status - Estado del proceso (running, starting, copying, completed, error)
     * @returns {string} Estado del botón
     */
    function getButtonState(status) {
        if (!status) return BUTTON_STATES.IDLE;
        
        const lowerStatus = status.toLowerCase();
        if (['running', 'starting', 'copying'].includes(lowerStatus)) {
            return BUTTON_STATES.OPTIMIZING;
        } else if (lowerStatus === 'completed') {
            return BUTTON_STATES.OPTIMIZED;
        } else if (lowerStatus === 'error') {
            return BUTTON_STATES.ERROR;
        }
        return BUTTON_STATES.IDLE;
    }

    /**
     * Actualiza el botón GPU Optimize según el estado
     * @param {string} torrentId - ID del torrent
     * @param {string} state - Estado del botón
     * @param {string} processId - ID del proceso (opcional)
     */
    function updateOptimizeButton(torrentId, state, processId = null) {
        const btn = document.querySelector(`.btn-optimize[data-torrent-id="${torrentId}"]`);
        if (!btn) return;

        // Quitar todas las clases de estado
        btn.classList.remove('optimizing', 'optimized', 'error');
        btn.disabled = false;

        switch (state) {
            case BUTTON_STATES.OPTIMIZING:
                btn.textContent = '⚡ Optimizing...';
                btn.classList.add('optimizing');
                btn.disabled = true;
                break;
            case BUTTON_STATES.OPTIMIZED:
                btn.textContent = '✅ Optimized';
                btn.classList.add('optimized');
                btn.disabled = true;
                break;
            case BUTTON_STATES.ERROR:
                btn.textContent = '🚀 GPU Optimize';
                btn.classList.add('error');
                btn.disabled = false;
                // Limpiar proceso guardado si hubo error
                if (processId) {
                    removeProcess(torrentId);
                }
                break;
            case BUTTON_STATES.IDLE:
            default:
                btn.textContent = '🚀 GPU Optimize';
                btn.disabled = false;
                break;
        }
    }

    /**
     * Recupera los estados de optimización al cargar la página
     * Consulta el backend para cada proceso guardado
     */
    async function restoreButtonStates() {
        const processes = getStoredProcesses();
        console.log('[TorrentOptimize] Restaurando estados de botones:', Object.keys(processes));

        for (const [torrentId, data] of Object.entries(processes)) {
            try {
                const result = await getStatus(data.process_id);
                if (result.success) {
                    const buttonState = getButtonState(result.status);
                    updateOptimizeButton(torrentId, buttonState, data.process_id);

                    // Si está en proceso, continuar monitoreando
                    if (buttonState === BUTTON_STATES.OPTIMIZING) {
                        monitorOptimization(data.process_id, torrentId);
                    } else if (buttonState === BUTTON_STATES.OPTIMIZED) {
                        // Mantener en localStorage para saber que ya está optimizado
                        saveProcess(torrentId, data.process_id, 'completed');
                    } else if (buttonState === BUTTON_STATES.ERROR) {
                        // Error - limpiar
                        removeProcess(torrentId);
                    }
                } else {
                    // Proceso no encontrado en backend, limpiar
                    removeProcess(torrentId);
                }
            } catch (e) {
                console.error(`[TorrentOptimize] Error restaurando estado para ${torrentId}:`, e);
                removeProcess(torrentId);
            }
        }
    }

    /**
     * Sincroniza los botones con las optimizaciones activas del backend
     * @returns {Promise<Object>} Mapa de torrentId -> estado
     */
    async function syncWithActiveOptimizations() {
        try {
            const result = await listActive();
            if (!result.success) return {};

            const activeMap = {};
            for (const opt of result.optimizations || []) {
                if (opt.torrent_id) {
                    activeMap[opt.torrent_id] = {
                        process_id: opt.process_id,
                        status: opt.status
                    };
                    // Guardar en localStorage
                    saveProcess(String(opt.torrent_id), opt.process_id, opt.status);
                    
                    // Actualizar botón
                    const buttonState = getButtonState(opt.status);
                    updateOptimizeButton(String(opt.torrent_id), buttonState, opt.process_id);

                    // Iniciar monitoreo si está en proceso
                    if (buttonState === BUTTON_STATES.OPTIMIZING) {
                        monitorOptimization(opt.process_id, String(opt.torrent_id));
                    }
                }
            }
            return activeMap;
        } catch (e) {
            console.error('[TorrentOptimize] Error sincronizando optimizaciones activas:', e);
            return {};
        }
    }

    /**
     * Inicia el monitoreo de un proceso y actualiza el botón
     * @param {string} processId - ID del proceso
     * @param {string} torrentId - ID del torrent
     */
    function startOptimizationMonitoring(processId, torrentId) {
        // Guardar en localStorage
        saveProcess(torrentId, processId, 'starting');
        
        // Actualizar botón inmediatamente
        updateOptimizeButton(torrentId, BUTTON_STATES.OPTIMIZING, processId);
        
        // Iniciar monitoreo
        monitorOptimization(processId, torrentId);
    }


    // Modificar monitorOptimization para actualizar el botón correctamente
    const originalMonitorOptimization = monitorOptimization;
    monitorOptimization = function(processId, torrentId) {
        const poll = async () => {
            try {
                const result = await getStatus(processId);

                if (result.success) {
                    // Actualizar UI del modal si está abierto
                    updateProgressUI(result);

                    // Actualizar botón según resultado
                    const buttonState = getButtonState(result.status);
                    updateOptimizeButton(torrentId, buttonState, processId);

                    // Guardar estado
                    saveProcess(torrentId, processId, result.status);

                    // Detener si completó o falló
                    if (result.status === 'completed' || result.status === 'error') {
                        if (statusIntervals[processId]) {
                            clearInterval(statusIntervals[processId]);
                            delete statusIntervals[processId];
                        }

                        // Notificaciones
                        if (result.status === 'error' && result.error) {
                            if (typeof showNotification === 'function') {
                                showNotification(
                                    '❌ Error en optimización',
                                    result.error,
                                    'error'
                                );
                            }
                        } else if (result.status === 'completed') {
                            if (typeof showNotification === 'function') {
                                showNotification(
                                    '✅ Optimización completada',
                                    'El archivo ha sido optimizado correctamente',
                                    'success'
                                );
                            }
                        }

                        // Refrescar lista
                        refreshOptimizationsList();
                    }
                }
            } catch (error) {
                console.error('[TorrentOptimize] Error en monitoreo:', error);
            }
        };

        statusIntervals[processId] = setInterval(poll, POLL_INTERVAL);
        poll();
    };

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
        monitorOptimization,
        formatSize,
        // Nuevas funciones exportadas
        getStoredProcesses,
        saveProcess,
        removeProcess,
        getButtonState,
        updateOptimizeButton,
        restoreButtonStates,
        syncWithActiveOptimizations,
        startOptimizationMonitoring,
        BUTTON_STATES
    };
})();

// Exponer globalmente para que downloads.js pueda usarlo
window.TorrentOptimize = TorrentOptimize;
console.log('✅ TorrentOptimize expuesto globalmente');
