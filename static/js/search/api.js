/**
 * Search Page - API Service
 */

const SEARCH_API = {
    endpoints: {
        categories: '/api/categories',
        checkConnection: '/api/download-check',
        search: '/api/search-movie',
        downloadTorrent: '/api/download-torrent',
        downloadUrl: '/api/download-url',
        downloadsActive: '/api/downloads/active',
        downloadStatus: (id) => `/api/downloads/${id}/status`,
        downloadCancel: (id) => `/api/downloads/${id}/cancel`,
        downloadRemove: (id) => `/api/download-remove/${id}`
    }
};

async function loadCategories() {
    try {
        const response = await fetch(SEARCH_API.endpoints.categories);
        const data = await response.json();

        if (data.success && data.categories) {
            const select = document.getElementById('category-select');
            const currentCategory = select.value;

            while (select.options.length > 1) {
                select.remove(1);
            }

            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                select.appendChild(option);
            });

            if (currentCategory && data.categories.includes(currentCategory)) {
                select.value = currentCategory;
            }

            const state = getSearchState();
            state.currentCategory = select.value;
        }
    } catch (error) {
        console.error('Error cargando categorías:', error);
        showStatus('Error al cargar categorías', 'error');
    }
}

async function checkConnection() {
    try {
        const response = await fetch(SEARCH_API.endpoints.checkConnection);
        return await response.json();
    } catch (error) {
        console.error('Error verificando conexión:', error);
        return { success: false, error: error.message };
    }
}

async function performSearch() {
    const query = document.getElementById('search-query').value.trim();
    if (!query) {
        showStatus('Ingresa un término de búsqueda', 'warning');
        return;
    }

    showStatus('Buscando...', 'info');

    try {
        const response = await fetch(SEARCH_API.endpoints.search, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ q: query })
        });

        const data = await response.json();

        if (data.success) {
            showStatus(`Encontrados ${data.count} resultados`, 'success');
            renderSearchResults(data.results);
        } else {
            showStatus(data.error || 'Error en la búsqueda', 'error');
        }
    } catch (error) {
        console.error('Error en búsqueda:', error);
        showStatus('Error al realizar búsqueda', 'error');
    }
}

async function startDownload(url, category, resultId = '') {
    try {
        const response = await fetch(SEARCH_API.endpoints.downloadTorrent, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ url, category, result_id: resultId })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Descarga iniciada', 'success');
            return data;
        } else {
            showStatus(data.error || 'Error al iniciar descarga', 'error');
            return null;
        }
    } catch (error) {
        console.error('Error iniciando descarga:', error);
        showStatus('Error al iniciar descarga', 'error');
        return null;
    }
}

function renderSearchResults(results) {
    const container = document.getElementById('search-results');
    if (!container) return;

    container.innerHTML = '';

    results.forEach(result => {
        const card = createResultCard(result);
        container.appendChild(card);
    });
}

function createResultCard(result) {
    const card = document.createElement('div');
    card.className = 'result-card';
    card.innerHTML = `
        <h3>${escapeHtml(result.title || result.name)}</h3>
        <p>${escapeHtml(result.description || '')}</p>
        <div class="result-meta">
            <span>${result.size || ''}</span>
            <span>${result.seeders || 0} seeders</span>
        </div>
        <button onclick="downloadResult('${escapeHtml(result.url)}', '${escapeHtml(result.title)}')">
            Descargar
        </button>
    `;
    return card;
}

function downloadResult(url, title) {
    const category = getSearchState().currentCategory || 'uncategorized';
    startDownload(url, category, title);
}

function showStatus(message, type = 'info') {
    if (typeof showNotification === 'function') {
        showNotification('Búsqueda', message, type);
    } else {
        console.log(`[${type}] ${message}`);
    }
}
