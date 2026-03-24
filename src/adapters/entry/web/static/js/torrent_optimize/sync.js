/**
 * Torrent Optimize - Sync
 * Sincronización: syncWithActiveOptimizations, restoreButtonStates, startOptimizationMonitoring
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    /**
     * Recupera los estados de optimización al cargar la página
     * Consulta el backend para cada proceso guardado
     */
    window.TorrentOptimize.restoreButtonStates = async function() {
        var getStored = window.TorrentOptimize.getStoredProcesses;
        var getStatus = window.TorrentOptimize.getStatus;
        var getButtonState = window.TorrentOptimize.getButtonState;
        var updateOptimizeButton = window.TorrentOptimize.updateOptimizeButton;
        var monitorOptimization = window.TorrentOptimize.monitorOptimization;
        var removeProcess = window.TorrentOptimize.removeProcess;
        var saveProcess = window.TorrentOptimize.saveProcess;
        var BUTTON_STATES = window.TorrentOptimize.BUTTON_STATES;
        
        if (!getStored || !getStatus || !getButtonState || !updateOptimizeButton) return;
        
        var processes = getStored ? getStored() : {};
        

        for (var torrentId in processes) {
            if (processes.hasOwnProperty(torrentId)) {
                var data = processes[torrentId];
                try {
                    var result = await getStatus(data.process_id);
                    if (result.success) {
                        var buttonState = getButtonState(result.status);
                        if (updateOptimizeButton) {
                            updateOptimizeButton(torrentId, buttonState, data.process_id);
                        }

                        // Actualizar el estado global de optimizaciones
                        if (window.state && window.state.optimizations) {
                            var existingIndex = -1;
                            for (var i = 0; i < window.state.optimizations.length; i++) {
                                if (window.state.optimizations[i].process_id === data.process_id || 
                                    window.state.optimizations[i].id === data.process_id) {
                                    existingIndex = i;
                                    break;
                                }
                            }
                            
                            var existingOpt = null;
                            if (window.state && window.state.optimizations) {
                                for (var j = 0; j < window.state.optimizations.length; j++) {
                                    if (window.state.optimizations[j].process_id === data.process_id || 
                                        window.state.optimizations[j].id === data.process_id) {
                                        existingOpt = window.state.optimizations[j];
                                        break;
                                    }
                                }
                            }
                            
                            var optData = {
                                process_id: data.process_id,
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
                        }

                        // Si está en proceso, continuar monitoreando
                        if (buttonState === BUTTON_STATES.OPTIMIZING) {
                            if (monitorOptimization) {
                                monitorOptimization(data.process_id, torrentId);
                            }
                        } else if (buttonState === BUTTON_STATES.OPTIMIZED) {
                            // Mantener en localStorage para saber que ya está optimizado
                            if (saveProcess) {
                                saveProcess(torrentId, data.process_id, 'completed');
                            }
                        } else if (buttonState === BUTTON_STATES.ERROR) {
                            // Error - limpiar
                            if (removeProcess) {
                                removeProcess(torrentId);
                            }
                        }
                    } else {
                        // Proceso no encontrado en backend, limpiar
                        if (removeProcess) {
                            removeProcess(torrentId);
                        }
                    }
                } catch (e) {
                    console.error('[TorrentOptimize] Error restaurando estado para ' + torrentId + ':', e);
                    if (removeProcess) {
                        removeProcess(torrentId);
                    }
                }
            }
        }
        
        // Forzar actualización de la UI de descargas después de restaurar estados
        if (typeof window.renderDownloads === 'function') {
            window.renderDownloads();
        }
    };

    /**
     * Sincroniza los botones con las optimizaciones activas del backend
     * @returns {Promise<Object>} Mapa de torrentId -> estado
     */
    window.TorrentOptimize.syncWithActiveOptimizations = async function() {
        try {
            var listActive = window.TorrentOptimize.listActive;
            if (!listActive) return {};
            
            var result = await listActive();
            if (!result.success) return {};

            var activeMap = {};
            var optimizations = result.optimizations || [];
            
            if (window.state) {
                var existingOptimizations = window.state.optimizations || [];
                window.state.optimizations = optimizations.map(function(newOpt) {
                    var existing = null;
                    for (var j = 0; j < existingOptimizations.length; j++) {
                        if (existingOptimizations[j].process_id === newOpt.process_id || 
                            existingOptimizations[j].id === newOpt.process_id) {
                            existing = existingOptimizations[j];
                            break;
                        }
                    }
                    if (existing && existing.notificationShown) {
                        return { ...newOpt, notificationShown: true };
                    }
                    return newOpt;
                });
            }
            
            for (var i = 0; i < window.state.optimizations.length; i++) {
                var opt = window.state.optimizations[i];
                if (opt.torrent_id) {
                    activeMap[opt.torrent_id] = {
                        process_id: opt.process_id,
                        status: opt.status
                    };
                    // Guardar en localStorage
                    if (window.TorrentOptimize.saveProcess) {
                        window.TorrentOptimize.saveProcess(String(opt.torrent_id), opt.process_id, opt.status);
                    }
                    
                    // Actualizar botón
                    if (window.TorrentOptimize.getButtonState && window.TorrentOptimize.updateOptimizeButton) {
                        var buttonState = window.TorrentOptimize.getButtonState(opt.status);
                        window.TorrentOptimize.updateOptimizeButton(String(opt.torrent_id), buttonState, opt.process_id);

                        // Iniciar monitoreo si está en proceso
                        if (buttonState === window.TorrentOptimize.BUTTON_STATES.OPTIMIZING) {
                            if (window.TorrentOptimize.monitorOptimization) {
                                window.TorrentOptimize.monitorOptimization(opt.process_id, String(opt.torrent_id));
                            }
                        }
                    }
                }
            }
            
            // Forzar actualización de la UI de descargas
            if (typeof window.renderDownloads === 'function') {
                window.renderDownloads();
            }
            
            return activeMap;
        } catch (e) {
            console.error('[TorrentOptimize] Error sincronizando optimizaciones activas:', e);
            return {};
        }
    };

    /**
     * Inicia el monitoreo de un proceso y actualiza el botón
     * @param {string} processId - ID del proceso
     * @param {string} torrentId - ID del torrent
     */
    window.TorrentOptimize.startOptimizationMonitoring = function(processId, torrentId) {
        var saveProcess = window.TorrentOptimize.saveProcess;
        var updateOptimizeButton = window.TorrentOptimize.updateOptimizeButton;
        var monitorOptimization = window.TorrentOptimize.monitorOptimization;
        var BUTTON_STATES = window.TorrentOptimize.BUTTON_STATES;
        
        // Guardar en localStorage
        if (saveProcess) {
            saveProcess(torrentId, processId, 'starting');
        }
        
        // Actualizar botón inmediatamente
        if (updateOptimizeButton && BUTTON_STATES) {
            updateOptimizeButton(torrentId, BUTTON_STATES.OPTIMIZING, processId);
        }
        
        // Iniciar monitoreo
        if (monitorOptimization) {
            monitorOptimization(processId, torrentId);
        }
    };

})();
