/**
 * Search Page - Main
 * Inicialización y puntos de entrada
 */
(function() {
    'use strict';

    // Variables para controlar la inicialización
    var dependenciesReady = false;
    var initAttempts = 0;
    var MAX_ATTEMPTS = 20; // 2 segundos máximo (20 * 100ms)

    /**
     * Verifica la conexión con los servicios
     */
    window.checkConnection = async function() {
        try {
            var endpoint = window.SEARCH_CONFIG ? window.SEARCH_CONFIG.endpoints.checkConnection : '/status';
            var response = await fetch(endpoint);
            var data = await response.json();

            // El endpoint /status devuelve {status: "ok"}
            // Verificar que el servidor está funcionando
            if (!data.status || data.status !== 'ok') {
                if (typeof window.showStatus === 'function') {
                    window.showStatus('Error de conexión con los servicios de descarga', 'error');
                }
            }
        } catch (error) {
            console.error('Error verificando conexión:', error);
            if (typeof window.showStatus === 'function') {
                window.showStatus('No se pudo conectar con el servidor', 'error');
            }
        }
    };

    // Función de inicialización
    function init() {
        console.log('[Search] Inicializando página de búsqueda');

        // Cargar categorías
        if (typeof window.loadCategories === 'function') {
            window.loadCategories();
        }

        // Verificar conexión
        if (typeof window.checkConnection === 'function') {
            window.checkConnection();
        }

        // Event listeners para tabs
        document.querySelectorAll('.search-tab').forEach(function(tab) {
            tab.addEventListener('click', function() {
                var mode = tab.dataset.mode;
                if (mode && typeof window.setSearchMode === 'function') {
                    window.setSearchMode(mode);
                }
            });
        });

        // Event listener para input de búsqueda (tecla Enter)
        var searchQuery = document.getElementById('search-query');
        if (searchQuery) {
            searchQuery.addEventListener('keypress', window.handleSearchKeypress);
        }

        // Botón de búsqueda
        var searchButton = document.getElementById('search-button');
        if (searchButton) {
            searchButton.addEventListener('click', function() {
                if (typeof window.performSearch === 'function') {
                    window.performSearch();
                }
            });
        }

        // Botón de URL download
        var urlDownloadBtn = document.getElementById('url-download-btn');
        if (urlDownloadBtn) {
            urlDownloadBtn.addEventListener('click', function() {
                if (typeof window.startUrlDownload === 'function') {
                    window.startUrlDownload();
                }
            });
        }

        // Category select change
        var categorySelect = document.getElementById('category-select');
        if (categorySelect) {
            categorySelect.addEventListener('change', function() {
                window.searchState.currentCategory = this.value;
            });
        }

        // Close modal button
        var closeModalBtn = document.getElementById('close-modal');
        if (closeModalBtn) {
            closeModalBtn.addEventListener('click', function() {
                if (typeof window.closeDownloadModal === 'function') {
                    window.closeDownloadModal();
                }
            });
        }

        // Modal click outside
        var modal = document.getElementById('download-modal');
        if (modal) {
            modal.addEventListener('click', function(e) {
                if (e.target === modal && typeof window.closeDownloadModal === 'function') {
                    window.closeDownloadModal();
                }
            });
        }

        // View downloads button
        var viewDownloadsBtn = document.getElementById('view-downloads-btn');
        if (viewDownloadsBtn) {
            viewDownloadsBtn.addEventListener('click', function() {
                if (typeof window.viewDownloads === 'function') {
                    window.viewDownloads();
                }
            });
        }

        console.log('[Search] Inicialización completada');
    }

    // Función que verifica dependencias antes de inicializar
    function checkDependenciesAndInit() {
        initAttempts++;

        // Verificar que todas las dependencias necesarias existen
        var missing = [];
        
        if (!window.SEARCH_CONFIG) missing.push('SEARCH_CONFIG');
        if (!window.searchState) missing.push('searchState');
        if (!window.escapeHtml) missing.push('escapeHtml');
        if (!window.formatSize) missing.push('formatSize');
        if (!window.formatSpeed) missing.push('formatSpeed');
        if (!window.showStatus) missing.push('showStatus');
        if (!window.loadCategories) missing.push('loadCategories');
        if (!window.setSearchMode) missing.push('setSearchMode');
        if (!window.handleSearchKeypress) missing.push('handleSearchKeypress');
        if (!window.performSearch) missing.push('performSearch');
        if (!window.displayResults) missing.push('displayResults');
        if (!window.startDownload) missing.push('startDownload');
        if (!window.startUrlDownload) missing.push('startUrlDownload');
        if (!window.openDownloadModal) missing.push('openDownloadModal');
        if (!window.closeDownloadModal) missing.push('closeDownloadModal');
        if (!window.viewDownloads) missing.push('viewDownloads');
        if (!window.startProgressPolling) missing.push('startProgressPolling');
        if (!window.updateDownloadProgress) missing.push('updateDownloadProgress');
        if (!window.updateProgressUI) missing.push('updateProgressUI');

        if (missing.length === 0) {
            console.log('[Main] Todas las dependencias están listas, inicializando...');
            dependenciesReady = true;
            init();
        } else if (initAttempts < MAX_ATTEMPTS) {
            console.log('[Main] Esperando dependencias: ' + missing.join(', ') + ' (intento ' + initAttempts + '/' + MAX_ATTEMPTS + ')');
            setTimeout(checkDependenciesAndInit, 100);
        } else {
            console.error('[Main] Tiempo de espera agotado para dependencias:', missing);
            // Intentar inicializar de todos modos para no dejar la página sin funcionar
            console.warn('[Main] Intentando inicializar sin todas las dependencias...');
            init();
        }
    }

    // Escuchar el evento de módulos cargados (disparado por el archivo principal)
    document.addEventListener('search-modules-loaded', function() {
        console.log('[Main] Evento search-modules-loaded recibido');
        checkDependenciesAndInit();
    });

    // También intentar inmediatamente si los módulos ya están cargados
    setTimeout(checkDependenciesAndInit, 100);

})();
