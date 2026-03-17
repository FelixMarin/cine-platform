/**
 * Search Page - State Management
 */

// Estado global
const searchState = {
    mode: 'search',  // 'search' o 'url'
    currentCategory: '',
    downloadInterval: null,
    currentDownloadId: null
};

function getSearchState() {
    return searchState;
}

function setSearchMode(mode) {
    searchState.mode = mode;
    
    document.querySelectorAll('.search-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.mode === mode);
        tab.setAttribute('aria-selected', tab.dataset.mode === mode);
    });

    document.getElementById('search-mode-input').style.display = mode === 'search' ? 'flex' : 'none';
    document.getElementById('url-mode-input').style.display = mode === 'url' ? 'flex' : 'none';

    // Mostrar/ocultar category-selector basado en el modo
    const categorySelectors = document.querySelectorAll('.category-selector');
    categorySelectors.forEach(function(selector) {
        if (mode === 'url') {
            // URL Directa: mostrar
            selector.style.visibility = 'visible';
            selector.style.opacity = '1';
        } else {
            // Buscar película: ocultar pero mantener espacio
            selector.style.visibility = 'hidden';
            selector.style.opacity = '0';
        }
    });

    if (mode === 'search') {
        document.getElementById('torrent-url').value = '';
    } else {
        document.getElementById('search-query').value = '';
    }
}

function setCurrentCategory(category) {
    searchState.currentCategory = category;
}

function getCurrentCategory() {
    return searchState.currentCategory;
}

function setCurrentDownloadId(id) {
    searchState.currentDownloadId = id;
}

function getCurrentDownloadId() {
    return searchState.currentDownloadId;
}

function setDownloadInterval(interval) {
    searchState.downloadInterval = interval;
}

function getDownloadInterval() {
    return searchState.downloadInterval;
}
