/**
 * Downloads Page - JavaScript para la página unificada de descargas y optimización
 * Maneja búsqueda, descargas, optimizaciones y historial
 */

// ==========================================================================
// CONFIGURACIÓN
// ==========================================================================

const CONFIG = {
    pollInterval: 3000,          // Intervalo de polling en ms
    maxHistoryItems: 50,         // Máximo elementos en historial
    endpoints: {
        search: '/api/search-movie',
        downloadTorrent: '/api/download-torrent',
        downloadUrl: '/api/download-url',
        downloadsActive: '/api/downloads/active',
        downloadStatus: (id) => `/api/downloads/${id}/status`,
        downloadCancel: (id) => `/api/downloads/${id}/cancel`,
        optimizeStart: '/api/optimizer/optimize',
        optimizeStatus: '/api/optimizer/status',
        optimizeCancel: '/api/optimizer/cancel',
        optimizeProfiles: '/api/optimizer/profiles'
    }
};

// ==========================================================================
// ESTADO GLOBAL
// ==========================================================================

const state = {
    activeTab: 'search',
    downloads: [],
    optimizations: [],
    history: [],
    isPolling: false,
    searchResults: []
};

// ==========================================================================
// UTILIDADES
// ==========================================================================

/**
 * Muestra una notificación
 */
function showNotification(title, message, type = 'info') {
    const container = document.getElementById('notifications');
    if (!container) return;

    const notification = document.createElement('div');
    notification.className = `notification ${type}`;
    notification.innerHTML = `
        <div class="notification-title">${title}</div>
        <div class="notification-message">${message}</div>
        <button class="notification-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(notification);

    // Auto-remove después de 5 segundos
    setTimeout(() => {
        notification.remove();
    }, 5000);
}

/**
 * Formatea bytes a formato legible
 */
function formatBytes(bytes) {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

/**
 * Formatea tiempo
 */
function formatTime(seconds) {
    if (!seconds || seconds < 0) return '--';
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = Math.floor(seconds % 60);

    if (h > 0) {
        return `${h}h ${m}m`;
    } else if (m > 0) {
        return `${m}m ${s}s`;
    }
    return `${s}s`;
}

/**
 * Formatea fecha
 */
function formatDate(timestamp) {
    if (!timestamp) return '';
    const date = new Date(timestamp * 1000);
    return date.toLocaleDateString('es-ES', {
        day: '2-digit',
        month: 'short',
        year: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ==========================================================================
// GESTIÓN DE PESTAÑAS
// ==========================================================================

/**
 * Cambia la pestaña activa
 */
function switchTab(tabName) {
    // Actualizar estado
    state.activeTab = tabName;

    // Actualizar clases de pestañas
    document.querySelectorAll('.download-tab').forEach(tab => {
        tab.classList.remove('active');
    });
    document.querySelector(`.download-tab[data-tab="${tabName}"]`)?.classList.add('active');

    // Actualizar contenido
    document.querySelectorAll('.download-tab-content').forEach(content => {
        content.classList.remove('active');
    });
    document.getElementById(`tab-${tabName}`)?.classList.add('active');

    // Ejecutar acciones específicas de cada pestaña
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

// ==========================================================================
// BÚSQUEDA
// ==========================================================================

/**
 * Realiza búsqueda en Prowlarr
 */
async function searchMovies() {
    const query = document.getElementById('search-query')?.value?.trim();
    if (!query) {
        showNotification('Error', 'Por favor ingresa un término de búsqueda', 'error');
        return;
    }

    const btn = document.querySelector('.search-button');
    const resultsContainer = document.getElementById('results-container');
    const statusContainer = document.getElementById('search-status');

    // Mostrar estado de carga
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Buscando...';
    }
    if (resultsContainer) resultsContainer.innerHTML = '<div class="empty-state"><p>Buscando en índices...</p></div>';
    if (statusContainer) statusContainer.textContent = 'Buscando...';

    try {
        const response = await fetch(CONFIG.endpoints.search, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ query })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error en la búsqueda');
        }

        state.searchResults = data.results || [];
        renderSearchResults(state.searchResults);
    } catch (error) {
        console.error('Error en búsqueda:', error);
        resultsContainer.innerHTML = `<div class="empty-state"><p>Error: ${error.message}</p></div>`;
        showNotification('Error', error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '🔍 Buscar';
    }
}

/**
 * Renderiza resultados de búsqueda
 */
function renderSearchResults(results) {
    const container = document.getElementById('results-container');

    if (!results || results.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><h3>Sin resultados</h3><p>No se encontraron películas para tu búsqueda</p></div>';
        return;
    }

    container.innerHTML = results.map((movie, index) => `
        <div class="process-card">
            <div class="process-header">
                <h3 class="process-title">${movie.title || 'Sin título'}</h3>
                <span class="process-status downloading">${movie.seeders || 0} seeders</span>
            </div>
            <div class="process-meta">
                <span class="process-meta-item">📅 ${movie.year || 'N/A'}</span>
                <span class="process-meta-item">📊 ${movie.size || 'N/A'}</span>
                <span class="process-meta-item">🔗 ${movie.indexer || 'N/A'}</span>
            </div>
            <div class="process-actions">
                <button class="btn-process btn-view" onclick="selectResult(${index})">
                    ⬇️ Descargar
                </button>
            </div>
        </div>
    `).join('');
}

/**
 * Selecciona un resultado para descargar
 */
function selectResult(index) {
    const movie = state.searchResults[index];
    if (!movie) return;

    // Mostrar modal de descarga
    showDownloadModal(movie);
}

/**
 * Muestra el modal de descarga
 */
function showDownloadModal(movie) {
    const modal = document.getElementById('download-modal');
    if (!modal) return;

    // Llenar datos del modal
    const titleEl = document.getElementById('download-name');
    const infoEl = document.getElementById('download-category');
    const urlInput = document.getElementById('torrent-url');

    if (titleEl) titleEl.textContent = movie.title || 'Sin título';
    if (infoEl) infoEl.textContent = `${movie.year || 'N/A'} • ${movie.size || 'N/A'}`;
    if (urlInput) urlInput.value = movie.url || movie.downloadUrl || '';

    // Mostrar modal
    modal.style.display = 'flex';
}

/**
 * Cierra el modal de descarga
 */
function closeDownloadModal() {
    const modal = document.getElementById('download-modal');
    if (modal) {
        modal.style.display = 'none';
    }
}

/**
 * Descarga torrent desde URL
 */
async function downloadFromUrl() {
    const url = document.getElementById('torrent-url')?.value?.trim();
    const categorySelect = document.getElementById('category-select');
    const category = categorySelect?.value;

    // Validación: URL requerida
    if (!url) {
        showNotification('Error', 'Por favor ingresa una URL', 'error');
        return;
    }

    // Validación: Categoría obligatoria
    if (!category) {
        showNotification('Error', 'Por favor selecciona una categoría', 'error');
        // Enfocar el selector de categoría
        categorySelect?.focus();
        return;
    }

    const btn = document.getElementById('download-url-btn');
    btn.disabled = true;
    btn.textContent = 'Iniciando...';

    try {
        const response = await fetch(CONFIG.endpoints.downloadUrl || CONFIG.endpoints.downloadTorrent, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url,
                category
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al iniciar descarga');
        }

        showNotification('Descarga iniciada', `Descargando: ${data.title || 'Torrent'}`, 'success');
        closeDownloadModal();

        // Cambiar a pestaña de descargas
        switchTab('downloads');
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error', error.message, 'error');
    } finally {
        btn.disabled = false;
        btn.textContent = '⬇️ Iniciar Descarga';
    }
}

/**
 * Descarga torrent seleccionado
 */
async function downloadSelected() {
    const url = document.getElementById('torrent-url')?.value?.trim();
    const resultId = document.getElementById('download-result-id')?.value;
    const categorySelect = document.getElementById('modal-category-select');
    const category = categorySelect?.value;

    // Validación: URL requerida
    if (!url) {
        showNotification('Error', 'Por favor ingresa una URL', 'error');
        return;
    }

    // Validación: Categoría obligatoria
    if (!category) {
        showNotification('Error', 'Por favor selecciona una categoría', 'error');
        categorySelect?.focus();
        return;
    }

    const btn = document.getElementById('modal-download-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Iniciando...';
    }

    try {
        const response = await fetch(CONFIG.endpoints.downloadTorrent, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                url,
                resultId,
                category
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al iniciar descarga');
        }

        showNotification('Descarga iniciada', `Descargando: ${data.title || 'Torrent'}`, 'success');
        closeDownloadModal();

        // Cambiar a pestaña de descargas
        switchTab('downloads');
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error', error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.textContent = '⬇️ Iniciar Descarga';
        }
    }
}

// ==========================================================================
// GESTIÓN DE DESCARGAS
// ==========================================================================

/**
 * Obtiene descargas activas
 */
async function refreshDownloads() {
    try {
        console.log('📥 Obteniendo descargas activas...');
        const response = await fetch(CONFIG.endpoints.downloadsActive);
        const data = await response.json();

        console.log('📥 Datos recibidos:', data);

        if (response.ok) {
            state.downloads = data.downloads || [];
            console.log('📥 Descargas en estado:', state.downloads);
            renderDownloads();
        } else {
            console.error('❌ Error en respuesta:', data);
        }
    } catch (error) {
        console.error('Error al obtener descargas:', error);
    }
}

/**
 * Renderiza la lista de descargas activas
 */
function renderDownloads() {
    const container = document.getElementById('downloads-list');

    if (!state.downloads || state.downloads.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📥</div>
                <h3>Sin descargas activas</h3>
                <p>Inicia una descarga desde la pestaña de búsqueda</p>
            </div>
        `;
        updateHeaderStats();
        return;
    }

    container.innerHTML = state.downloads.map(download => {
        // Logs de depuración
        console.log('📊 Renderizando torrent:', {
            id: download.id,
            title: download.title,
            progress: download.progress,
            status: download.status,
            status_display: download.status_display
        });

        // Usar siempre status_display (string) si está disponible
        const statusValue = download.status_display || download.status || 'unknown';
        const progress = download.progress || 0;
        const statusClass = getStatusClass(statusValue);

        // Usar campos snake_case del backend o camelCase como fallback
        const downloadSpeed = download.download_speed || download.downloadSpeed || 0;
        const uploadSpeed = download.upload_speed || download.uploadSpeed || 0;
        const statusDisplay = download.status_display || download.statusDisplay || download.status;
        const etaFormatted = download.eta_formatted || download.etaFormatted || '--';
        const sizeFormatted = download.size_formatted || download.sizeFormatted || '0 B';

        // Determinar si está completado o no basado en status
        const isCompleted = progress >= 99.9 || statusValue === 'seeding' || statusValue === 6 || statusValue === 'completed';
        const isFailed = (progress >= 0 && statusValue === 'failed') || statusValue === 0 || statusValue === 'failed';

        if(progress > 100) {
            progress = 100;
        }

        // Log específico para la barra
        console.log(`📊 Barra ${download.id}: progress=${progress} (tipo=${typeof progress}), width=${progress}%`);

        return `
            <div class="process-card" data-id="${download.id}">
                <div class="process-header">
                    <h3 class="process-title">${download.title || 'Descarga'}</h3>
                    <span class="process-status ${statusClass}">${statusDisplay}</span>
                </div>
                <div class="process-meta">
                    <span class="process-meta-item">📊 ${typeof progress === 'number' ? progress.toFixed(1) : 0}%</span>
                    <span class="process-meta-item">⬇️ ${formatBytes(downloadSpeed)}/s</span>
                    <span class="process-meta-item">⬆️ ${formatBytes(uploadSpeed)}/s</span>
                    <span class="process-meta-item">⏱️ ${etaFormatted}</span>
                    <span class="process-meta-item">📁 ${download.category || 'N/A'}</span>
                </div>
                <div class="process-progress">
                    <div class="progress-container">
                        <div class="progress-bar" style="width: ${typeof progress === 'number' ? progress : 0}%"></div>
                        <span class="progress-size">${sizeFormatted}</span>
                    </div>
                </div>
                <div class="process-actions">
                    ${!isCompleted && !isFailed ? `
                        <button class="btn-process btn-cancel" onclick="cancelDownload('${download.id}')">
                            ❌ Cancelar
                        </button>
                    ` : ''}
                    ${isCompleted ? `
                        <button class="btn-process btn-optimize" onclick="TorrentOptimize.showOptimizeModal({id: '${download.id}', name: '${encodeURIComponent(download.title)}', size: ${download.size_total || download.sizeTotal || 0}})">
                            🚀 GPU Optimize
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');

    updateHeaderStats();
}

/**
 * Obtiene la clase CSS según el estado
 */
function getStatusClass(status) {
    // Si es número, convertir a string usando status_display
    const statusMap = {
        'downloading': 'downloading',
        'seeding': 'completed',
        'completed': 'completed',
        'paused': 'pending',
        'stopped': 'failed',
        'failed': 'failed',
        'checking': 'running',
        'queued': 'pending',
        // Códigos numéricos de Transmission
        '0': 'failed',   // stopped
        '1': 'pending',  // check queued
        '2': 'running',  // checking
        '3': 'pending',  // download queued
        '4': 'downloading',
        '5': 'pending',  // seed queued
        '6': 'completed' // seeding
    };

    // Si es número, convertir a string
    const statusStr = (typeof status === 'number') ? String(status) : status;
    return statusMap[statusStr?.toLowerCase()] || 'pending';
}

/**
 * Cancela una descarga
 */
async function cancelDownload(id) {
    if (!confirm('¿Estás seguro de que quieres cancelar esta descarga?')) {
        return;
    }

    try {
        const response = await fetch(CONFIG.endpoints.downloadCancel(id), {
            method: 'POST'
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al cancelar');
        }

        showNotification('Descarga cancelada', 'La descarga ha sido eliminada', 'success');
        refreshDownloads();
    } catch (error) {
        console.error('Error al cancelar:', error);
        showNotification('Error', error.message, 'error');
    }
}

// ==========================================================================
// GESTIÓN DE OPTIMIZACIONES
// ==========================================================================

/**
 * Obtiene optimizaciones activas
 */
async function refreshOptimizations() {
    try {
        const response = await fetch(CONFIG.endpoints.optimizeStatus);
        const data = await response.json();

        if (response.ok) {
            // El backend devuelve active_jobs, convertir al formato que espera el frontend
            state.optimizations = data.active_jobs || [];
            renderOptimizations();
        }
    } catch (error) {
        console.error('Error al obtener optimizaciones:', error);
    }
}

/**
 * Renderiza la lista de optimizaciones activas
 */
function renderOptimizations() {
    const container = document.getElementById('optimizations-list');

    if (!state.optimizations || state.optimizations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">⚡</div>
                <h3>Sin optimizaciones activas</h3>
                <p>Los archivos descargados aparecerán aquí para optimizar</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.optimizations.map(opt => {
        const progress = opt.progress || 0;
        const inputFilename = opt.input_path ? opt.input_path.split('/').pop().split('\\').pop() : 'Optimización';
        const metrics = opt.metrics || {};

        return `
            <div class="process-card" data-id="${opt.id}">
                <div class="process-header">
                    <h3 class="process-title">${inputFilename}</h3>
                    <span class="process-status ${opt.status === 'running' ? 'running' : 'pending'}">
                        ${opt.status === 'running' ? '⚡ ' + progress.toFixed(1) + '%' : opt.status}
                    </span>
                </div>
                <div class="process-meta">
                    <span class="process-meta-item">📋 ${opt.profile || 'balanced'}</span>
                    <span class="process-meta-item">📁 ${opt.category || 'default'}</span>
                </div>
                <div class="metrics-grid">
                    <div class="metric">
                        <div class="metric-value">${metrics.fps || '--'}</div>
                        <div class="metric-label">FPS</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${metrics.bitrate || '--'}</div>
                        <div class="metric-label">Bitrate</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${metrics.current_size ? metrics.size_formatted : '--'}</div>
                        <div class="metric-label">Size</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value">${metrics.current_time ? metrics.current_time.toFixed(0) + 's' : '--'}</div>
                        <div class="metric-label">Time</div>
                    </div>
                </div>
                <div class="process-progress">
                    <div class="progress-container">
                        <div class="progress-bar" style="width: ${progress}%"></div>
                    </div>
                </div>
                <div class="process-actions">
                    <button class="btn-process btn-cancel" onclick="cancelOptimization('${opt.id}')">
                        ❌ Cancelar
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * Inicia optimización de un archivo descargado
 */
async function startOptimization(downloadId, title, filePath) {
    const titleDecoded = decodeURIComponent(title);

    // Seleccionar perfil
    const profile = document.getElementById('optimize-profile')?.value || 'balanced';

    try {
        const response = await fetch(CONFIG.endpoints.optimizeStart, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                file_path: filePath,
                profile
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al iniciar optimización');
        }

        showNotification('Optimización iniciada', `Procesando: ${titleDecoded}`, 'success');
        switchTab('optimizations');
    } catch (error) {
        console.error('Error:', error);
        showNotification('Error', error.message, 'error');
    }
}

/**
 * Cancela una optimización
 */
async function cancelOptimization(id) {
    if (!confirm('¿Estás seguro de que quieres cancelar esta optimización?')) {
        return;
    }

    try {
        const response = await fetch(CONFIG.endpoints.optimizeCancel, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                process_id: id
            })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al cancelar');
        }

        showNotification('Optimización cancelada', 'La optimización ha sido detenida', 'success');
        refreshOptimizations();
    } catch (error) {
        console.error('Error al cancelar:', error);
        showNotification('Error', error.message, 'error');
    }
}

// ==========================================================================
// HISTORIAL
// ==========================================================================

/**
 * Carga el historial desde localStorage
 */
function loadHistory() {
    try {
        const saved = localStorage.getItem('cine-platform-history');
        if (saved) {
            state.history = JSON.parse(saved);
        }
    } catch (e) {
        state.history = [];
    }
    renderHistory();
}

/**
 * Guarda el historial en localStorage
 */
function saveHistory() {
    try {
        // Limitar a maxHistoryItems
        const toSave = state.history.slice(0, CONFIG.maxHistoryItems);
        localStorage.setItem('cine-platform-history', JSON.stringify(toSave));
    } catch (e) {
        console.error('Error guardando historial:', e);
    }
}

/**
 * Renderiza el historial
 */
function renderHistory() {
    const container = document.getElementById('history-list');

    if (!state.history || state.history.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📜</div>
                <h3>Sin historial</h3>
                <p>Las descargas y optimizaciones completadas aparecerán aquí</p>
            </div>
        `;
        return;
    }

    container.innerHTML = state.history.map(item => {
        const statusClass = item.type === 'download' ?
            (item.status === 'completed' ? 'completed' : 'failed') :
            (item.status === 'completed' ? 'completed' : 'failed');

        return `
            <div class="history-item">
                <div class="history-item-info">
                    <div class="history-item-title">${item.title}</div>
                    <div class="history-item-meta">
                        ${item.type === 'download' ? '📥' : '⚡'} 
                        ${item.type === 'download' ? 'Descarga' : 'Optimización'} • 
                        ${formatDate(item.completedAt || item.startedAt)}
                    </div>
                </div>
                <span class="history-item-status process-status ${statusClass}">
                    ${item.status}
                </span>
            </div>
        `;
    }).join('');
}

/**
 * Añade un elemento al historial
 */
function addToHistory(item) {
    state.history.unshift({
        ...item,
        completedAt: Math.floor(Date.now() / 1000)
    });
    saveHistory();
    if (state.activeTab === 'history') {
        renderHistory();
    }
}

// ==========================================================================
// ESTADÍSTICAS
// ==========================================================================

/**
 * Actualiza las estadísticas en el header
 */
function updateHeaderStats() {
    const downloadsEl = document.getElementById('stats-downloads');
    const optimizationsEl = document.getElementById('stats-optimizations');

    if (downloadsEl) {
        downloadsEl.textContent = state.downloads?.length || 0;
    }
    if (optimizationsEl) {
        optimizationsEl.textContent = state.optimizations?.length || 0;
    }
}

// ==========================================================================
// POLLING
// ==========================================================================

/**
 * Inicia el polling
 */
function startPolling() {
    if (state.isPolling) return;
    state.isPolling = true;

    pollAll();

    // Configurar intervalo
    state.pollIntervalId = setInterval(pollAll, CONFIG.pollInterval);
}

/**
 * Detiene el polling
 */
function stopPolling() {
    state.isPolling = false;
    if (state.pollIntervalId) {
        clearInterval(state.pollIntervalId);
        state.pollIntervalId = null;
    }
}

/**
 * Realiza polling de todos los datos
 */
async function pollAll() {
    if (state.activeTab === 'downloads') {
        await refreshDownloads();
    }
    if (state.activeTab === 'optimizations') {
        await refreshOptimizations();
    }
}

// ==========================================================================
// INICIALIZACIÓN
// ==========================================================================

// Funciones wrapper para compatibilidad con HTML
// (El HTML usa IDs diferentes a los del JavaScript)

function performSearch() {
    const query = document.getElementById('search-query')?.value?.trim();
    if (!query) {
        showNotification('Error', 'Por favor ingresa un término de búsqueda', 'error');
        return;
    }
    searchMovies();
}

function startUrlDownload() {
    const url = document.getElementById('torrent-url')?.value?.trim();
    if (!url) {
        showNotification('Error', 'Por favor ingresa una URL', 'error');
        return;
    }
    downloadFromUrl();
}

function handleSearchKeypress(event) {
    if (event.key === 'Enter') {
        performSearch();
    }
}

/**
 * Inicializa la página
 */
function initDownloadsPage() {
    console.log('Inicializando página de descargas...');

    // Configurar event listeners para pestañas
    document.querySelectorAll('.download-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            const tabName = tab.dataset.tab;
            if (tabName) switchTab(tabName);
        });
    });

    // Event listener para búsqueda
    const searchInput = document.getElementById('search-query');
    if (searchInput) {
        searchInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') performSearch();
        });
    }

    const searchBtn = document.getElementById('search-button');
    if (searchBtn) {
        searchBtn.addEventListener('click', performSearch);
    }

    // Event listener para descarga por URL
    const urlDownloadBtn = document.getElementById('url-download-btn');
    if (urlDownloadBtn) {
        urlDownloadBtn.addEventListener('click', downloadFromUrl);
    }

    // Event listeners del modal
    const downloadModalBtn = document.getElementById('download-url-btn');
    if (downloadModalBtn) {
        downloadModalBtn.addEventListener('click', downloadSelected);
    }

    const closeModalBtn = document.getElementById('close-modal');
    if (closeModalBtn) {
        closeModalBtn.addEventListener('click', closeDownloadModal);
    }

    // Cerrar modal al hacer click fuera
    const modal = document.getElementById('download-modal');
    if (modal) {
        modal.addEventListener('click', (e) => {
            if (e.target === modal) closeDownloadModal();
        });
    }

    // Event listeners para botones de refresh
    const refreshDownloadsBtn = document.getElementById('refresh-downloads');
    if (refreshDownloadsBtn) {
        refreshDownloadsBtn.addEventListener('click', refreshDownloads);
    }

    const refreshOptimizationsBtn = document.getElementById('refresh-optimizations');
    if (refreshOptimizationsBtn) {
        refreshOptimizationsBtn.addEventListener('click', refreshOptimizations);
    }

    // Iniciar polling
    startPolling();

    // Cargar categorías
    loadCategories();

    // Cargar historial
    loadHistory();

    console.log('Página de descargas inicializada');
}

/**
 * Carga las categorías disponibles
 */
async function loadCategories() {
    const select = document.getElementById('category-select');
    const modalSelect = document.getElementById('modal-category-select');

    // Función interna para formatear nombre de categoría
    const formatCatName = (cat) => {
        let formatted = cat.replace(/_/g, ' ');
        return formatted.split(' ').map(word => {
            return word.charAt(0).toUpperCase() + word.slice(1).toLowerCase();
        }).join(' ');
    };

    // Función para cargar opciones en un select
    const loadInSelect = (sel) => {
        if (!sel) return;
        sel.disabled = true;
        const opt = sel.options[0];
        if (opt) opt.textContent = 'Cargando categorías...';
    };

    loadInSelect(select);
    loadInSelect(modalSelect);

    try {
        const response = await fetch('/api/download/categories');
        const data = await response.json();

        if (!data.success) {
            throw new Error(data.error || 'Error al cargar categorías');
        }

        // Actualizar selector principal
        if (select) {
            while (select.options.length > 1) select.remove(1);
            if (data.categories && data.categories.length > 0) {
                data.categories.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    opt.textContent = formatCatName(cat);
                    select.appendChild(opt);
                });
                select.disabled = false;
                if (select.options[0]) select.options[0].textContent = 'Seleccionar categoría...';
            } else {
                if (select.options[0]) select.options[0].textContent = 'No hay categorías';
            }
        }

        // Actualizar selector del modal
        if (modalSelect) {
            while (modalSelect.options.length > 1) modalSelect.remove(1);
            if (data.categories && data.categories.length > 0) {
                data.categories.forEach(cat => {
                    const opt = document.createElement('option');
                    opt.value = cat;
                    opt.textContent = formatCatName(cat);
                    modalSelect.appendChild(opt);
                });
                modalSelect.disabled = false;
                if (modalSelect.options[0]) modalSelect.options[0].textContent = 'Seleccionar categoría...';
            } else {
                if (modalSelect.options[0]) modalSelect.options[0].textContent = 'No hay categorías';
            }
        }
    } catch (error) {
        console.error('Error cargando categorías:', error);
        if (select?.options[0]) select.options[0].textContent = 'Error al cargar';
        if (modalSelect?.options[0]) modalSelect.options[0].textContent = 'Error al cargar';
        showNotification('Error', error.message, 'error');
    }
}

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', initDownloadsPage);
