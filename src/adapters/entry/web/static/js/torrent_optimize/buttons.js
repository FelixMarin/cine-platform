/**
 * Torrent Optimize - Buttons
 * Estados de botones: BUTTON_STATES, getButtonState, updateOptimizeButton
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    /**
     * Obtiene el estado del botón según el estado de optimización
     * @param {string} status - Estado del proceso (running, starting, copying, completed, error)
     * @returns {string} Estado del botón
     */
    window.TorrentOptimize.getButtonState = function(status) {
        var BUTTON_STATES = window.TorrentOptimize.BUTTON_STATES;
        if (!status) return BUTTON_STATES.IDLE;
        
        var lowerStatus = status.toLowerCase();
        if (['running', 'starting', 'copying'].indexOf(lowerStatus) !== -1) {
            return BUTTON_STATES.OPTIMIZING;
        } else if (lowerStatus === 'completed') {
            return BUTTON_STATES.OPTIMIZED;
        } else if (lowerStatus === 'error') {
            return BUTTON_STATES.ERROR;
        }
        return BUTTON_STATES.IDLE;
    };

    /**
     * Actualiza el botón GPU Optimize según el estado
     * @param {string} torrentId - ID del torrent
     * @param {string} state - Estado del botón
     * @param {string} processId - ID del proceso (opcional)
     */
    window.TorrentOptimize.updateOptimizeButton = function(torrentId, state, processId) {
        var btn = document.querySelector('.btn-optimize[data-torrent-id="' + torrentId + '"]');
        if (!btn) return;

        var BUTTON_STATES = window.TorrentOptimize.BUTTON_STATES;

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
                if (processId && window.TorrentOptimize.removeProcess) {
                    window.TorrentOptimize.removeProcess(torrentId);
                }
                break;
            case BUTTON_STATES.IDLE:
            default:
                btn.textContent = '🚀 GPU Optimize';
                btn.disabled = false;
                break;
        }
    };

})();
