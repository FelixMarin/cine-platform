/**
 * Search Page - State Management
 * Estado global y getters/setters
 */
(function() {
    'use strict';

    window.searchState = {
        mode: 'search',  // 'search' o 'url'
        currentCategory: '',
        downloadInterval: null,
        currentDownloadId: null
    };

    window.getSearchState = function() {
        return window.searchState;
    };

    window.setSearchMode = function(mode) {
        window.searchState.mode = mode;
        
        document.querySelectorAll('.search-tab').forEach(function(tab) {
            tab.classList.toggle('active', tab.dataset.mode === mode);
            tab.setAttribute('aria-selected', tab.dataset.mode === mode);
        });

        var searchModeInput = document.getElementById('search-mode-input');
        var urlModeInput = document.getElementById('url-mode-input');
        
        if (searchModeInput) searchModeInput.style.display = mode === 'search' ? 'flex' : 'none';
        if (urlModeInput) urlModeInput.style.display = mode === 'url' ? 'flex' : 'none';

        // Mostrar/ocultar category-selector (mantiene el espacio con visibility)
        var categorySelectors = document.querySelectorAll('.search-form .category-selector');
        categorySelectors.forEach(function(selector) {
            if (mode === 'url') {
                selector.style.visibility = 'visible';
                selector.style.opacity = '1';
            } else {
                selector.style.visibility = 'hidden';
                selector.style.opacity = '0';
            }
        });

        // Limpiar inputs
        var torrentUrl = document.getElementById('torrent-url');
        var searchQuery = document.getElementById('search-query');
        
        if (mode === 'search' && torrentUrl) {
            torrentUrl.value = '';
        } else if (mode === 'url' && searchQuery) {
            searchQuery.value = '';
        }
    };

    window.setCurrentCategory = function(category) {
        window.searchState.currentCategory = category;
    };

    window.getCurrentCategory = function() {
        return window.searchState.currentCategory;
    };

    window.setCurrentDownloadId = function(id) {
        window.searchState.currentDownloadId = id;
    };

    window.getCurrentDownloadId = function() {
        return window.searchState.currentDownloadId;
    };

    window.setDownloadInterval = function(interval) {
        window.searchState.downloadInterval = interval;
    };

    window.getDownloadInterval = function() {
        return window.searchState.downloadInterval;
    };

})();
