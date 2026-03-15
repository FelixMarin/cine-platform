/**
 * Downloads Page - JavaScript para la página unificada de descargas y optimización
 * Maneja búsqueda, descargas, optimizaciones y historial
 * 
 * Este archivo sirve como punto de entrada y re-exporta funciones de los módulos separados
 */

// Re-export configuration
const CONFIG = require('./config.js');

// Re-export state
const state = require('./state.js');

// Re-export utilities
const { showNotification, formatBytes, formatTime, formatDate, escapeHtml, debounce, getFileExtension } = require('./utils.js');

// Re-export Spanish filter
const { isSpanishContent, filterSpanishResults, toggleSpanishFilter, applySpanishFilter } = require('./spanishFilter.js');

// Make functions globally available for HTML onclicks
window.showNotification = showNotification;
window.formatBytes = formatBytes;
window.formatTime = formatTime;
window.formatDate = formatDate;
window.escapeHtml = escapeHtml;
window.debounce = debounce;
window.getFileExtension = getFileExtension;
window.isSpanishContent = isSpanishContent;
window.filterSpanishResults = filterSpanishResults;
window.toggleSpanishFilter = toggleSpanishFilter;

// Tab management
function switchTab(tabName) {
    const s = state.getState();
    s.activeTab = tabName;

    document.querySelectorAll('.download-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.download-tab[data-tab="${tabName}"]`)?.classList.add('active');

    document.querySelectorAll('.download-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`)?.classList.add('active');

    switch (tabName) {
        case 'downloads':
            refreshDownloads();
            break;
        case 'optimizations':
            refreshOptimizations();
            break;
        case 'history':
            loadHistory();
            break;
    }
}

window.switchTab = switchTab;
