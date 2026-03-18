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
                if (result.success) {
                    // Actualizar el estado global de optimizaciones
                    if (window.state && result.optimizations) {
                        window.state.optimizations = result.optimizations;
                    }
                    // Actualizar UI de descargas para reflejar el estado
                    if (typeof window.renderDownloads === 'function') {
                        window.renderDownloads();
                    }
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
        var notificationShown = false;

        var poll = async function() {
            try {
                var getStatus = window.TorrentOptimize.getStatus;
                if (!getStatus) return;
                
                var result = await getStatus(processId);

                if (result.success) {
                    if (window.TorrentOptimize.updateProgressUI) {
                        window.TorrentOptimize.updateProgressUI(result);
                    }

                    if (window.TorrentOptimize.getButtonState && window.TorrentOptimize.updateOptimizeButton) {
                        var buttonState = window.TorrentOptimize.getButtonState(result.status);
                        window.TorrentOptimize.updateOptimizeButton(torrentId, buttonState, processId);
                    }

                    if (window.TorrentOptimize.saveProcess) {
                        window.TorrentOptimize.saveProcess(torrentId, processId, result.status);
                    }

                    if (window.state && window.state.optimizations) {
                        var existingIndex = -1;
                        var existingOpt = null;
                        for (var i = 0; i < window.state.optimizations.length; i++) {
                            if (window.state.optimizations[i].process_id === processId || 
                                window.state.optimizations[i].id === processId) {
                                existingIndex = i;
                                existingOpt = window.state.optimizations[i];
                                break;
                            }
                        }
                        
                        var optData = {
                            process_id: processId,
                            torrent_id: torrentId,
                            status: result.status,
                            progress: result.progress || 0,
                            error: result.error || null,
                            notificationShown: existingOpt && existingOpt.notificationShown ? true : false
                        };
                        
                        if (existingIndex >= 0) {
                            window.state.optimizations[existingIndex] = optData;
                        } else {
                            window.state.optimizations.push(optData);
                        }
                        
                        notificationShown = optData.notificationShown;
                        
                        if (typeof window.renderDownloads === 'function') {
                            window.renderDownloads();
                        }
                    }

                    if (result.status === 'completed' || result.status === 'error') {
                        if (window.TorrentOptimize.statusIntervals && window.TorrentOptimize.statusIntervals[processId]) {
                            clearInterval(window.TorrentOptimize.statusIntervals[processId]);
                            delete window.TorrentOptimize.statusIntervals[processId];
                        }

                        if (!notificationShown) {
                            notificationShown = true;
                            
                            if (window.state && window.state.optimizations) {
                                window.state.optimizations = window.state.optimizations.map(function(opt) {
                                    if (opt.process_id === processId || opt.id === processId) {
                                        return { ...opt, status: result.status, notificationShown: true };
                                    }
                                    return opt;
                                });
                            }

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
                        }

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
        
        poll();
    };

})();
