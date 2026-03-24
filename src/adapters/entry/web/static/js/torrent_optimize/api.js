/**
 * Torrent Optimize - API
 * Llamadas fetch: authFetch, checkGpuStatus, startOptimization, getStatus, listActive
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    // ==========================================================================
    // Helper: Fetch con manejo de 401
    // ==========================================================================

    /**
     * Función fetch con manejo automático de 401
     * @param {string} url - URL a.fetch
     * @param {Object} options - Opciones de fetch
     * @returns {Promise<Response>}
     */
    window.TorrentOptimize.authFetch = async function(url, options) {
        options = options || {};
        var defaultOptions = {
            credentials: 'include'
        };
        var mergedOptions = Object.assign({}, defaultOptions, options);
        
        var response = await fetch(url, mergedOptions);
        
        // Manejar 401 - redirigir a login
        if (response.status === 401) {
            console.warn('[TorrentOptimize] Sesión expirada, redirigiendo a login...');
            if (typeof showNotification === 'function') {
                showNotification('Sesión expirada', 'Por favor, inicia sesión nuevamente', 'warning');
            }
            // Redirigir a login después de un breve delay
            setTimeout(function() {
                window.location.href = '/login';
            }, 1500);
        }
        
        return response;
    };

    // ==========================================================================
    // API: Verificar disponibilidad de GPU
    // ==========================================================================

    /**
     * Verifica si hay GPU NVIDIA disponible para aceleración por hardware
     * @returns {Promise<{success: boolean, gpu_available: boolean}>}
     */
    window.TorrentOptimize.checkGpuStatus = async function() {
        try {
            var response = await window.TorrentOptimize.authFetch('/api/optimize-torrent/gpu-status');
            return await response.json();
        } catch (error) {
            console.error('[TorrentOptimize] Error verificando GPU:', error);
            return { success: false, gpu_available: false, error: error.message };
        }
    };

    // ==========================================================================
    // API: Iniciar optimización
    // ==========================================================================

    /**
     * Inicia la optimización de un torrent
     * @param {number} torrentId - ID del torrent en Transmission
     * @param {string} category - Categoría para organizar (action, comedy, etc.)
     * @returns {Promise<{success: boolean, process_id?: string, error?: string}>}
     */
    window.TorrentOptimize.startOptimization = async function(torrentId, category) {
        try {
            var response = await window.TorrentOptimize.authFetch('/api/optimize-torrent', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    torrent_id: torrentId,
                    category: category
                })
            });

            var result = await response.json();
            return result;
        } catch (error) {
            console.error('[TorrentOptimize] Error iniciando optimización:', error);
            return { success: false, error: error.message };
        }
    };

    // ==========================================================================
    // API: Consultar estado
    // ==========================================================================

    /**
     * Consulta el estado de una optimización
     * @param {string} processId - ID del proceso de optimización
     * @returns {Promise<{success: boolean, status?: string, progress?: number, error?: string}>}
     */
    window.TorrentOptimize.getStatus = async function(processId) {
        try {
            var response = await window.TorrentOptimize.authFetch('/api/optimize-torrent/status/' + processId);
            return await response.json();
        } catch (error) {
            console.error('[TorrentOptimize] Error consultando estado de ' + processId + ':', error);
            return { success: false, error: error.message };
        }
    };

    // ==========================================================================
    // API: Listar optimizaciones activas
    // ==========================================================================

    /**
     * Lista las optimizaciones activas
     * @returns {Promise<{success: boolean, active_count?: number, optimizations?: Array}>}
     */
    window.TorrentOptimize.listActive = async function() {
        try {
            var response = await window.TorrentOptimize.authFetch('/api/optimize-torrent/active');
            return await response.json();
        } catch (error) {
            console.error('[TorrentOptimize] Error listando activas:', error);
            return { success: false, error: error.message };
        }
    };

})();
