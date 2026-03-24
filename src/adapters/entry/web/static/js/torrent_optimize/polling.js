/**
 * Torrent Optimize - Polling
 * Polling de estado: startStatusPolling, stopStatusPolling, statusIntervals
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    /**
     * Inicia el polling de estado para un proceso
     * @param {string} processId 
     */
    window.TorrentOptimize.startStatusPolling = function(processId) {
        // Detener cualquier polling anterior
        if (window.TorrentOptimize.stopStatusPolling) {
            window.TorrentOptimize.stopStatusPolling();
        }

        // Función de polling
        var poll = async function() {
            var getStatus = window.TorrentOptimize.getStatus;
            var updateProgressUI = window.TorrentOptimize.updateProgressUI;
            var stopStatusPolling = window.TorrentOptimize.stopStatusPolling;
            
            if (!getStatus) return;
            
            var result = await getStatus(processId);

            if (result.success) {
                if (updateProgressUI) {
                    updateProgressUI(result);
                }

                // Detener si completó o falló
                if (result.status === 'completed' || result.status === 'error') {
                    if (stopStatusPolling) {
                        stopStatusPolling();
                    }

                    var btn = document.getElementById('btn-start-optimize');
                    if (result.status === 'completed') {
                        if (btn) btn.innerHTML = '✅ Completado';
                        // Cerrar modal después de 2 segundos
                        setTimeout(function() {
                            if (window.TorrentOptimize.closeModal) {
                                window.TorrentOptimize.closeModal();
                            }
                        }, 2000);
                    } else {
                        if (btn) {
                            btn.innerHTML = '❌ Error';
                            btn.disabled = false;
                        }
                    }
                }
            }
        };

        // Iniciar intervalo
        var pollInterval = window.TorrentOptimize.POLL_INTERVAL || 2000;
        window.TorrentOptimize.statusIntervals[processId] = setInterval(poll, pollInterval);

        // Ejecutar inmediatamente
        poll();
    };

    /**
     * Detiene el polling de estado
     */
    window.TorrentOptimize.stopStatusPolling = function() {
        if (window.TorrentOptimize.statusIntervals) {
            for (var key in window.TorrentOptimize.statusIntervals) {
                if (window.TorrentOptimize.statusIntervals.hasOwnProperty(key) && window.TorrentOptimize.statusIntervals[key]) {
                    clearInterval(window.TorrentOptimize.statusIntervals[key]);
                    delete window.TorrentOptimize.statusIntervals[key];
                }
            }
        }
    };

})();
