/**
 * Torrent Optimize - Progress
 * Gestión de progreso: updateProgressUI, monitorOptimization, refreshOptimizationsList
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    // Intervalos para polling de estado
    window.TorrentOptimize.statusIntervals = {};

    /**
     * Actualiza la UI con el progreso
     * @param {Object} status 
     */
    window.TorrentOptimize.updateProgressUI = function(status) {
        var progressBar = document.getElementById('optimize-progress-bar');
        var progressText = document.getElementById('optimize-progress-text');
        var progressStatus = document.getElementById('optimize-progress-status');
        var etaText = document.getElementById('optimize-eta');

        if (progressBar) {
            progressBar.style.width = (status.progress || 0) + '%';
        }

        if (progressText) {
            progressText.textContent = Math.round(status.progress || 0) + '%';
        }

        if (progressStatus) {
            var statusMap = {
                'pending': '⏳ Pendiente',
                'running': '🔄 Ejecutando',
                'completed': '✅ Completado',
                'error': '❌ Error'
            };
            progressStatus.textContent = statusMap[status.status] || status.status;
        }

        if (etaText && status.eta_seconds) {
            var minutes = Math.floor(status.eta_seconds / 60);
            var seconds = status.eta_seconds % 60;
            etaText.textContent = '⏱️ ETA: ' + minutes + 'm ' + seconds + 's';
        }
    };

    /**
     * Refresca la lista de optimizaciones
     */
    window.TorrentOptimize.refreshOptimizationsList = function() {
        var listActive = window.TorrentOptimize.listActive;
        if (listActive) {
            listActive().then(function(result) {
                if (result.success && typeof refreshOptimizations === 'function') {
                    // Actualizar el estado global si es necesario
                    
                }
            });
        }
    };

    /**
     * Monitorea el progreso de una optimización
     * @param {string} processId - ID del proceso
     * @param {string} torrentId - ID del torrent
     */
    window.TorrentOptimize.monitorOptimization = function(processId, torrentId) {
        var poll = async function() {
            try {
                var getStatus = window.TorrentOptimize.getStatus;
                if (!getStatus) return;
                
                var result = await getStatus(processId);

                if (result.success) {
                    // Actualizar UI del modal si está abierto
                    if (window.TorrentOptimize.updateProgressUI) {
                        window.TorrentOptimize.updateProgressUI(result);
                    }

                    // Actualizar botón según resultado
                    if (window.TorrentOptimize.getButtonState && window.TorrentOptimize.updateOptimizeButton) {
                        var buttonState = window.TorrentOptimize.getButtonState(result.status);
                        window.TorrentOptimize.updateOptimizeButton(torrentId, buttonState, processId);
                    }

                    // Guardar estado
                    if (window.TorrentOptimize.saveProcess) {
                        window.TorrentOptimize.saveProcess(torrentId, processId, result.status);
                    }

                    // Detener si completó o falló
                    if (result.status === 'completed' || result.status === 'error') {
                        if (window.TorrentOptimize.statusIntervals && window.TorrentOptimize.statusIntervals[processId]) {
                            clearInterval(window.TorrentOptimize.statusIntervals[processId]);
                            delete window.TorrentOptimize.statusIntervals[processId];
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

                        // Refrescar lista
                        if (window.TorrentOptimize.refreshOptimizationsList) {
                            window.TorrentOptimize.refreshOptimizationsList();
                        }
                    }
                }
            } catch (error) {
                console.error('[TorrentOptimize] Error en monitoreo:', error);
            }
        };

        var pollInterval = window.TorrentOptimize.POLL_INTERVAL || 2000;
        window.TorrentOptimize.statusIntervals[processId] = setInterval(poll, pollInterval);
        
        // Ejecutar inmediatamente
        poll();
    };

})();
