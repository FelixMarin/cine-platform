/**
 * SEARCH.JS - Lógica de la página de búsqueda y descarga
 */

// Estado global
const searchState = {
    mode: 'search',  // 'search' o 'url'
    currentCategory: '',
    downloadInterval: null,
    currentDownloadId: null
};

// =====================
// Gestión de modos de búsqueda
// =====================

/**
 * Cambia entre modo búsqueda y modo URL directa
 */
function setSearchMode(mode) {
    searchState.mode = mode;

    // Actualizar tabs
    document.querySelectorAll('.search-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.mode === mode);
        tab.setAttribute('aria-selected', tab.dataset.mode === mode);
    });

    // Mostrar/ocultar inputs
    document.getElementById('search-mode-input').style.display = mode === 'search' ? 'flex' : 'none';
    document.getElementById('url-mode-input').style.display = mode === 'url' ? 'flex' : 'none';

    // Limpiar inputs
    if (mode === 'search') {
        document.getElementById('torrent-url').value = '';
    } else {
        document.getElementById('search-query').value = '';
    }
}

/**
 * Maneja la tecla Enter en el input de búsqueda
 */
function handleSearchKeypress(event) {
    if (event.key === 'Enter') {
        performSearch();
    }
}

// =====================
// Carga de categorías
// =====================

/**
 * Carga las categorías disponibles desde el backend
 */
async function loadCategories() {
    try {
        const response = await fetch('/api/categories');
        const data = await response.json();

        if (data.success && data.categories) {
            const select = document.getElementById('category-select');

            // Guardar la categoría actual si existe
            const currentCategory = select.value;

            // Limpiar opciones existentes (excepto la primera)
            while (select.options.length > 1) {
                select.remove(1);
            }

            // Añadir nuevas categorías
            data.categories.forEach(category => {
                const option = document.createElement('option');
                option.value = category;
                option.textContent = category;
                select.appendChild(option);
            });

            // Restaurar categoría si existía
            if (currentCategory && data.categories.includes(currentCategory)) {
                select.value = currentCategory;
            }

            searchState.currentCategory = select.value;
        }
    } catch (error) {
        console.error('Error cargando categorías:', error);
        showStatus('Error al cargar categorías', 'error');
    }
}

// =====================
// Verificación de conexión
// =====================

/**
 * Verifica la conexión con los servicios
 */
async function checkConnection() {
    try {
        const response = await fetch('/api/download-test');
        const data = await response.json();

        // Mostrar estado de conexión (opcional)
        console.log('Estado de servicios:', data.services);

        if (!data.success) {
            showStatus('Error de conexión con los servicios de descarga', 'error');
        }
    } catch (error) {
        console.error('Error verificando conexión:', error);
        showStatus('No se pudo conectar con el servidor', 'error');
    }
}

// =====================
// Búsqueda de películas
// =====================

/**
 * Realiza la búsqueda de películas
 */
async function performSearch() {
    const query = document.getElementById('search-query').value.trim();

    if (!query) {
        showStatus('Por favor, introduce un término de búsqueda', 'error');
        return;
    }

    showStatus('Buscando...', 'loading');

    try {
        const response = await fetch(`/api/search-movie?q=${encodeURIComponent(query)}&limit=20`);
        const data = await response.json();

        if (data.success) {
            displayResults(data.results, data.count);

            if (data.count === 0) {
                showStatus('No se encontraron resultados para "' + query + '"', 'success');
            } else {
                showStatus(`Se encontraron ${data.count} resultados`, 'success');
            }
        } else {
            showStatus(data.error || 'Error en la búsqueda', 'error');
            displayResults([], 0);
        }
    } catch (error) {
        console.error('Error en búsqueda:', error);
        showStatus('Error de conexión durante la búsqueda', 'error');
        displayResults([], 0);
    }
}

/**
 * Muestra los resultados en el grid
 */
function displayResults(results, count) {
    const container = document.getElementById('results-container');

    if (!results || results.length === 0) {
        container.innerHTML = `
            <div class="no-results">
                <div class="no-results-icon">🔍</div>
                <h3>Sin resultados</h3>
                <p>Intenta con otros términos de búsqueda</p>
            </div>
        `;
        return;
    }

    container.innerHTML = results.map(result => `
        <div class="result-card" data-guid="${escapeHtml(result.guid)}">
            <div class="result-header">
                <h3 class="result-title" title="${escapeHtml(result.title)}">${escapeHtml(result.title)}</h3>
                <span class="result-indexer">${escapeHtml(result.indexer)}</span>
            </div>
            <div class="result-meta">
                <span class="result-meta-item size">
                    💾 ${result.size_formatted || formatSize(result.size)}
                </span>
                ${result.seeders ? `
                    <span class="result-meta-item seeders">
                        ⬆️ ${result.seeders} seeders
                    </span>
                ` : ''}
                ${result.leechers ? `
                    <span class="result-meta-item">
                        ⬇️ ${result.leechers} leechers
                    </span>
                ` : ''}
                ${result.publish_date ? `
                    <span class="result-meta-item">
                        📅 ${result.publish_date}
                    </span>
                ` : ''}
            </div>
            <div class="result-actions">
                <button 
                    class="btn-download" 
                    onclick="startDownload('${escapeHtml(result.magnet_url || result.torrent_url || '')}', '${escapeHtml(result.guid)}')"
                    ${!result.magnet_url && !result.torrent_url ? 'disabled' : ''}
                >
                    ⬇️ Descargar
                </button>
            </div>
        </div>
    `).join('');
}

// =====================
// Descarga de torrents
// =====================

/**
 * Inicia una descarga desde URL directa
 */
async function startUrlDownload() {
    const url = document.getElementById('torrent-url').value.trim();
    const category = document.getElementById('category-select').value;

    if (!url) {
        showStatus('Por favor, introduce una URL de torrent', 'error');
        return;
    }

    // Validar URL
    if (!url.startsWith('magnet:') && !url.startsWith('http')) {
        showStatus('La URL debe ser magnet: o http(s)://', 'error');
        return;
    }

    await startDownload(url, '', category);
}

/**
 * Inicia la descarga de un torrent
 */
async function startDownload(url, resultId, category) {
    // Usar la categoría seleccionada si no se proporciona
    const selectedCategory = category || document.getElementById('category-select').value;

    showStatus('Iniciando descarga...', 'loading');

    try {
        const response = await fetch('/api/download-torrent', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url: url,
                result_id: resultId,
                category: selectedCategory
            })
        });

        const data = await response.json();

        if (data.success) {
            showStatus('Descarga iniciada correctamente', 'success');

            // Abrir modal de progreso
            openDownloadModal(data.download, selectedCategory);

            // Iniciar polling de progreso
            startProgressPolling(data.download.torrent_id);
        } else {
            showStatus(data.error || 'Error al iniciar la descarga', 'error');
        }
    } catch (error) {
        console.error('Error iniciando descarga:', error);
        showStatus('Error de conexión al iniciar la descarga', 'error');
    }
}

// =====================
// Modal de progreso
// =====================

/**
 * Abre el modal de progreso de descarga
 */
function openDownloadModal(download, category) {
    const modal = document.getElementById('download-modal');
    const nameEl = document.getElementById('download-name');
    const categoryEl = document.getElementById('download-category');

    nameEl.textContent = download.name || 'Descarga';
    categoryEl.textContent = category ? `Categoría: ${category}` : 'Sin categoría';

    // Resetear progreso
    document.getElementById('progress-bar').style.width = '0%';
    document.getElementById('progress-text').textContent = '0%';
    document.getElementById('download-speed').textContent = 'Velocidad: --';
    document.getElementById('download-eta').textContent = 'Tiempo restante: --';

    modal.style.display = 'flex';
    searchState.currentDownloadId = download.torrent_id;
}

/**
 * Cierra el modal de progreso
 */
function closeDownloadModal() {
    const modal = document.getElementById('download-modal');
    modal.style.display = 'none';

    // Detener polling
    if (searchState.downloadInterval) {
        clearInterval(searchState.downloadInterval);
        searchState.downloadInterval = null;
    }

    searchState.currentDownloadId = null;
}

/**
 * Redirige a la página de descargas
 */
function viewDownloads() {
    closeDownloadModal();
    // Por ahora, simplemente actualizamos la página
    // Podría abrirse una pestaña de descargas
    window.location.href = '/';
}

// =====================
// Polling de progreso
// =====================

/**
 * Inicia el polling de progreso de descarga
 */
function startProgressPolling(torrentId) {
    // Detener cualquier polling anterior
    if (searchState.downloadInterval) {
        clearInterval(searchState.downloadInterval);
    }

    // Actualizar cada 2 segundos
    searchState.downloadInterval = setInterval(async () => {
        await updateDownloadProgress(torrentId);
    }, 2000);
}

/**
 * Actualiza el progreso de descarga
 */
async function updateDownloadProgress(torrentId) {
    try {
        const response = await fetch('/api/download-status?status=active');
        const data = await response.json();

        if (data.success && data.downloads) {
            // Buscar el torrent específico
            const torrent = data.downloads.find(d => d.id === torrentId);

            if (torrent) {
                updateProgressUI(torrent);
            }
        }
    } catch (error) {
        console.error('Error actualizando progreso:', error);
    }
}

/**
 * Actualiza la UI con el progreso
 */
function updateProgressUI(torrent) {
    const progress = torrent.progress || 0;
    const progressBar = document.getElementById('progress-bar');
    const progressText = document.getElementById('progress-text');
    const speedEl = document.getElementById('download-speed');
    const etaEl = document.getElementById('download-eta');

    // Actualizar barra
    progressBar.style.width = `${progress}%`;
    progressText.textContent = `${progress.toFixed(1)}%`;

    // Actualizar velocidad
    if (torrent.rate_download > 0) {
        speedEl.textContent = `Velocidad: ${formatSpeed(torrent.rate_download)}`;
    }

    // Actualizar tiempo restante
    if (torrent.eta > 0 && torrent.eta < 31536000) {  // Menos de 1 año
        etaEl.textContent = `Tiempo restante: ${torrent.eta_formatted}`;
    } else if (torrent.progress >= 100) {
        etaEl.textContent = 'Completado';
        // Detener polling cuando termine
        if (searchState.downloadInterval) {
            clearInterval(searchState.downloadInterval);
            searchState.downloadInterval = null;
        }
    } else {
        etaEl.textContent = 'Tiempo restante: Calculando...';
    }
}

// =====================
// Utilidades
// =====================

/**
 * Muestra un mensaje de estado
 */
function showStatus(message, type) {
    const statusEl = document.getElementById('search-status');
    statusEl.textContent = message;
    statusEl.className = 'search-status ' + type;

    // Auto-ocultar después de 5 segundos (excepto para errores)
    if (type !== 'error') {
        setTimeout(() => {
            statusEl.className = 'search-status';
        }, 5000);
    }
}

/**
 * Escapa HTML para prevenir XSS
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

/**
 * Formatea el tamaño en bytes a formato legible
 */
function formatSize(bytes) {
    if (!bytes) return '0 B';
    const units = ['B', 'KB', 'MB', 'GB', 'TB'];
    let unitIndex = 0;
    let size = bytes;

    while (size >= 1024 && unitIndex < units.length - 1) {
        size /= 1024;
        unitIndex++;
    }

    return `${size.toFixed(2)} ${units[unitIndex]}`;
}

/**
 * Formatea la velocidad de descarga
 */
function formatSpeed(bytesPerSecond) {
    if (!bytesPerSecond) return '0 B/s';
    const units = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    let unitIndex = 0;
    let speed = bytesPerSecond;

    while (speed >= 1024 && unitIndex < units.length - 1) {
        speed /= 1024;
        unitIndex++;
    }

    return `${speed.toFixed(1)} ${units[unitIndex]}`;
}

// Guardar categoría seleccionada cuando cambie
document.addEventListener('DOMContentLoaded', function () {
    const categorySelect = document.getElementById('category-select');
    categorySelect.addEventListener('change', function () {
        searchState.currentCategory = this.value;
    });
});
