/**
 * Torrent Optimize - Storage
 * Persistencia localStorage: getStoredProcesses, saveProcess, removeProcess
 */
(function() {
    'use strict';

    // Inicializar el objeto si no existe
    window.TorrentOptimize = window.TorrentOptimize || {};

    /**
     * Obtiene los procesos guardados en localStorage
     * @returns {Object} Objeto con torrentId -> {process_id, status, lastUpdate}
     */
    window.TorrentOptimize.getStoredProcesses = function() {
        try {
            var storageKey = window.TorrentOptimize.STORAGE_KEY || 'cine-platform-optimize-processes';
            var stored = localStorage.getItem(storageKey);
            if (!stored) return {};
            
            var processes = JSON.parse(stored);
            // Limpiar procesos antiguos (más de 5 minutos)
            var now = Date.now();
            var timeout = window.TorrentOptimize.STORAGE_TIMEOUT || (5 * 60 * 1000);
            var cleaned = {};
            for (var torrentId in processes) {
                if (processes.hasOwnProperty(torrentId)) {
                    var data = processes[torrentId];
                    if (now - data.lastUpdate < timeout) {
                        cleaned[torrentId] = data;
                    }
                }
            }
            return cleaned;
        } catch (e) {
            console.error('[TorrentOptimize] Error leyendo procesos guardados:', e);
            return {};
        }
    };

    /**
     * Guarda un proceso en localStorage
     * @param {string} torrentId - ID del torrent
     * @param {string} processId - ID del proceso
     * @param {string} status - Estado del proceso
     */
    window.TorrentOptimize.saveProcess = function(torrentId, processId, status) {
        try {
            var storageKey = window.TorrentOptimize.STORAGE_KEY || 'cine-platform-optimize-processes';
            var processes = window.TorrentOptimize.getStoredProcesses();
            processes[torrentId] = {
                process_id: processId,
                status: status,
                lastUpdate: Date.now()
            };
            localStorage.setItem(storageKey, JSON.stringify(processes));
        } catch (e) {
            console.error('[TorrentOptimize] Error guardando proceso:', e);
        }
    };

    /**
     * Elimina un proceso de localStorage
     * @param {string} torrentId - ID del torrent
     */
    window.TorrentOptimize.removeProcess = function(torrentId) {
        try {
            var storageKey = window.TorrentOptimize.STORAGE_KEY || 'cine-platform-optimize-processes';
            var processes = window.TorrentOptimize.getStoredProcesses();
            delete processes[torrentId];
            localStorage.setItem(storageKey, JSON.stringify(processes));
        } catch (e) {
            console.error('[TorrentOptimize] Error eliminando proceso:', e);
        }
    };

})();
