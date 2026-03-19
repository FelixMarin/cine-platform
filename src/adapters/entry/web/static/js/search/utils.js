/**
 * Search Page - Utilities
 * Funciones de utilidad: escapeHtml, formatSize, formatSpeed, showStatus
 */
(function() {
    'use strict';

    /**
     * Escapa HTML para prevenir XSS
     */
    window.escapeHtml = function(text) {
        if (!text) return '';
        var div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    };

    /**
     * Formatea el tamaño en bytes a formato legible
     */
    window.formatSize = function(bytes) {
        // Si ya es un string formateado, devolverlo
        if (typeof bytes === 'string') return bytes;
        if (!bytes) return '0 B';
        var units = ['B', 'KB', 'MB', 'GB', 'TB'];
        var unitIndex = 0;
        var size = bytes;

        while (size >= 1024 && unitIndex < units.length - 1) {
            size /= 1024;
            unitIndex++;
        }

        return size.toFixed(2) + ' ' + units[unitIndex];
    };

    /**
     * Formatea la velocidad de descarga
     */
    window.formatSpeed = function(bytesPerSecond) {
        if (!bytesPerSecond) return '0 B/s';
        var units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
        var unitIndex = 0;
        var speed = bytesPerSecond;

        while (speed >= 1024 && unitIndex < units.length - 1) {
            speed /= 1024;
            unitIndex++;
        }

        return speed.toFixed(1) + ' ' + units[unitIndex];
    };

    /**
     * Muestra un mensaje de estado
     */
    window.showStatus = function(message, type) {
        var statusEl = document.getElementById('search-status');
        if (!statusEl) return;
        
        statusEl.textContent = message;
        statusEl.className = 'search-status ' + type;

        // Auto-ocultar después de 5 segundos (excepto para errores)
        if (type !== 'error') {
            setTimeout(function() {
                statusEl.className = 'search-status';
            }, 5000);
        }
    };

})();
