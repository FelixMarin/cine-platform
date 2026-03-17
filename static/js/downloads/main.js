/**
 * Main - Inicialización y puntos de entrada
 */
(function() {
    'use strict';
    
    // Variables para controlar la inicialización
    let dependenciesReady = false;
    let initAttempts = 0;
    const MAX_ATTEMPTS = 20; // 2 segundos máximo (20 * 100ms)
    
    // Funciones de utilidad (siempre disponibles)
    window.performSearch = function() {
        var q = document.getElementById('search-query') ? document.getElementById('search-query').value.trim() : '';
        if (!q) { window.showNotification('Error','Por favor ingresa un término de búsqueda','error'); return; }
        window.searchMovies();
    };
    
    window.startUrlDownload = function() {
        var ui = document.getElementById('torrent-url');
        if (!ui) { window.showNotification('Error','Campo de URL no encontrado','error'); return; }
        var url = ui.value.trim();
        if (!url) { window.showNotification('Error','Por favor ingresa una URL','error'); return; }
        var cs = document.getElementById('category-select');
        var cat = cs ? cs.value : undefined;
        if (!cat) { window.showNotification('Error','Por favor selecciona una categoría','error'); if(cs)cs.focus(); return; }
        window.downloadFromUrl(url, cat);
    };
    
    window.handleSearchKeypress = function(e) { if (e.key === 'Enter') window.performSearch(); };
    
    window.startPolling = function() {
        if (window.state && window.state.isPolling) return;
        if (window.state) window.state.isPolling = true;
        window.pollAll();
        window.state.pollIntervalId = setInterval(window.pollAll, window.CONFIG ? window.CONFIG.pollInterval : 3000);
    };
    
    window.stopPolling = function() {
        if (window.state) {
            window.state.isPolling = false;
            if (window.state.pollIntervalId) { 
                clearInterval(window.state.pollIntervalId); 
                window.state.pollIntervalId = null; 
            }
        }
    };
    
    window.pollAll = async function() { 
        if (window.refreshDownloads) await window.refreshDownloads(); 
        if (window.refreshOptimizations) await window.refreshOptimizations(); 
    };
    
    // Función que verifica dependencias antes de inicializar
    function checkDependenciesAndInit() {
        initAttempts++;
        
        // Verificar que todas las dependencias necesarias existen
        const missing = [];
        if (!window.loadHistory) missing.push('loadHistory');
        if (!window.refreshDownloads) missing.push('refreshDownloads');
        if (!window.refreshOptimizations) missing.push('refreshOptimizations');
        if (!window.switchTab) missing.push('switchTab');
        if (!window.state) missing.push('state');
        if (!window.CONFIG) missing.push('CONFIG');
        
        if (missing.length === 0) {
            console.log('[Main] Todas las dependencias están listas, inicializando...');
            dependenciesReady = true;
            performInit();
        } else if (initAttempts < MAX_ATTEMPTS) {
            console.log(`[Main] Esperando dependencias: ${missing.join(', ')} (intento ${initAttempts}/${MAX_ATTEMPTS})`);
            setTimeout(checkDependenciesAndInit, 100);
        } else {
            console.error('[Main] Tiempo de espera agotado para dependencias:', missing);
        }
    }
    
    // Inicialización real
    function performInit() {
        console.log('[Main] Inicializando página de descargas');
        
        window.refreshDownloads();
        
        // Event listeners para pestañas
        document.querySelectorAll('.download-tab').forEach(function(t) { 
            t.addEventListener('click', function() { 
                var tn = t.dataset.tab; 
                if (tn) window.switchTab(tn); 
            }); 
        });
        
        // Search input
        var si = document.getElementById('search-query');
        if (si) si.addEventListener('keypress', function(e) { if (e.key === 'Enter') window.performSearch(); });
        
        // Spanish filter checkbox
        var scb = document.getElementById('spanish-filter-checkbox');
        if (scb && window.state) scb.checked = window.state.spanishFilterEnabled;
        
        // Search button
        var sb = document.getElementById('search-button');
        if (sb) sb.addEventListener('click', window.performSearch);
        
        // URL download button
        var udb = document.getElementById('url-download-btn');
        if (udb) udb.addEventListener('click', window.downloadFromUrl);
        
        // Modal download button
        var dmb = document.getElementById('download-url-btn');
        if (dmb) dmb.addEventListener('click', window.downloadSelected);
        
        // Close modal button
        var cmb = document.getElementById('close-modal');
        if (cmb) cmb.addEventListener('click', window.closeDownloadModal);
        
        // Modal click outside
        var mod = document.getElementById('download-modal');
        if (mod) mod.addEventListener('click', function(e) { if (e.target === mod) window.closeDownloadModal(); });
        
        // Refresh buttons
        var rdb = document.getElementById('refresh-downloads');
        if (rdb) rdb.addEventListener('click', window.refreshDownloads);
        
        var rob = document.getElementById('refresh-optimizations');
        if (rob) rob.addEventListener('click', window.refreshOptimizations);
        
        // Optimize buttons delegation
        var dl = document.getElementById('downloads-list');
        if (dl) dl.addEventListener('click', function(e) {
            var b = e.target.closest('.btn-optimize');
            if (!b) return;
            e.preventDefault(); e.stopPropagation();
            var tid = b.dataset.torrentId;
            var tnm = decodeURIComponent(b.dataset.torrentName || '');
            var tsz = b.dataset.torrentSize;
            if (typeof TorrentOptimize !== 'undefined' && TorrentOptimize.showOptimizeModal) {
                TorrentOptimize.showOptimizeModal({id:tid, name:tnm, size:tsz});
            } else {
                console.error('[Downloads] TorrentOptimize no disponible');
            }
        });
        
        // Check for TorrentOptimize
        if (typeof TorrentOptimize === 'undefined') {
            var ct = setInterval(function() {
                if (typeof TorrentOptimize !== 'undefined') {
                    clearInterval(ct);
                    if (TorrentOptimize.syncWithActiveOptimizations) {
                        TorrentOptimize.syncWithActiveOptimizations();
                    }
                }
            }, 500);
            setTimeout(function(){ clearInterval(ct); }, 10000);
        } else { 
            if (TorrentOptimize.syncWithActiveOptimizations) {
                TorrentOptimize.syncWithActiveOptimizations(); 
            }
        }
        
        // Start polling
        window.startPolling();
        
        // Load data
        window.loadHistory(1);
        window.loadCategories();
        
        console.log('[Main] Inicialización completada');
    }
    
    // Escuchar evento personalizado de downloads.js
    document.addEventListener('downloads-modules-loaded', function() {
        console.log('[Main] Evento recibido: módulos cargados');
        checkDependenciesAndInit();
    });
    
    // También intentar cuando el DOM esté listo
    document.addEventListener('DOMContentLoaded', function() {
        console.log('[Main] DOM listo, verificando dependencias...');
        checkDependenciesAndInit();
    });
    
    // Si ya estamos tarde, empezar a verificar
    if (document.readyState === 'complete' || document.readyState === 'interactive') {
        console.log('[Main] Documento ya cargado, verificando dependencias...');
        checkDependenciesAndInit();
    }
    
    // Exponer la función de inicialización por si alguien la necesita
    window.initDownloadsPage = function() {
        console.log('[Main] initDownloadsPage llamado manualmente');
        checkDependenciesAndInit();
    };
    
})();