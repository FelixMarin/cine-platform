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
        downloadRemove: (id) => `/api/download-remove/${id}`,
        optimizeStart: '/api/optimizer/optimize',
        optimizeStatus: '/api/optimizer/status',
        optimizeCancel: '/api/optimizer/cancel',
        optimizeProfiles: '/api/optimizer/profiles',
        // Torrent optimize endpoints (nuevos para GPU optimization)
        torrentOptimizeActive: '/api/optimize-torrent/active',
        torrentOptimizeStatus: (id) => `/api/optimize-torrent/status/${id}`,
        torrentOptimizeStart: '/api/optimize-torrent',
        // Optimization history endpoints
        optimizationHistory: '/api/optimization-history/',
        optimizationHistoryLatest: '/api/optimization-history/latest'
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
    searchResults: [],
    originalSearchResults: [],  // Resultados sin filtrar
    spanishFilterEnabled: true  // Filtro de español activado por defecto
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

// ==========================================================================
// FILTRO DE IDIOMA ESPAÑOL
// ==========================================================================

/**
 * Patrones para detectar contenido en español (case insensitive)
 */
const SPANISH_PATTERNS = [
    // Etiquetas de idioma entre corchetes
    /\[esp\]/i,
    /\[español\]/i,
    /\[spanish\]/i,
    /\[castellano\]/i,
    // Palabras completas
    /\bespañol\b/i,
    /\bspanish\b/i,
    /\bcastellano\b/i,
    /\bsubtitulado\b/i,
    /\bvo\b/i,                  // Versión Original
    /\bversión original\b/i,
    // Abreviaturas comunes
    /\bsp\./i,
    /\besp\./i,
    // Códigos de idioma
    /\bes(-)?es\b/i,
    /\bes(-)?la\b/i,
    // Audio
    /\baudio español\b/i,
    /\baudio spanish\b/i,
    // Doblamiento
    /\bdoblado\b/i,
    /\bdubbed\b/i,
    /\bdub\b/i
];

/**
 * Detecta si un resultado es en español buscando en título y descripción
 * @param {Object} result - Resultado de búsqueda
 * @returns {boolean} - true si el resultado es en español
 */
function isSpanishContent(result) {
    if (!result) return false;
    
    // Buscar en título (title) y título completo (fullTitle)
    const searchText = [
        result.title,
        result.fullTitle,
        result.description
    ].filter(Boolean).join(' ').toLowerCase();
    
    if (!searchText) return false;
    
    // Probar cada patrón
    for (const pattern of SPANISH_PATTERNS) {
        if (pattern.test(searchText)) {
            return true;
        }
    }
    
    return false;
}

/**
 * Filtra los resultados mostrando solo los en español
 * @param {Array} results - Resultados a filtrar
 * @returns {Array} - Resultados filtrados
 */
function filterSpanishResults(results) {
    if (!results || !Array.isArray(results)) return [];
    return results.filter(result => isSpanishContent(result));
}

/**
 * Alterna el filtro de español y vuelve a renderizar
 */
function toggleSpanishFilter() {
    state.spanishFilterEnabled = !state.spanishFilterEnabled;
    
    // Actualizar estado del checkbox
    const checkbox = document.getElementById('spanish-filter-checkbox');
    if (checkbox) {
        checkbox.checked = state.spanishFilterEnabled;
    }
    
    // Volver a renderizar con los resultados originales
    renderSearchResults(state.originalSearchResults);
}

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

        // Guardar resultados originales sin filtrar
        state.originalSearchResults = data.results || [];
        state.searchResults = data.results || [];
        
        // Aplicar filtro de español si está activado
        if (state.spanishFilterEnabled) {
            state.searchResults = filterSpanishResults(state.originalSearchResults);
        }
        
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
    const statusContainer = document.getElementById('search-status');

    if (!results || results.length === 0) {
        // Mostrar mensaje según si hay resultados originales o no
        const hasOriginalResults = state.originalSearchResults && state.originalSearchResults.length > 0;
        const message = hasOriginalResults && state.spanishFilterEnabled 
            ? 'No se encontraron resultados en español para tu búsqueda'
            : 'No se encontraron películas para tu búsqueda';
        
        container.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><h3>Sin resultados</h3><p>' + message + '</p></div>';
        
        // Actualizar indicador de cantidad
        if (statusContainer && state.originalSearchResults) {
            const originalCount = state.originalSearchResults.length;
            if (state.spanishFilterEnabled) {
                statusContainer.textContent = `Mostrando 0 de ${originalCount} resultados (sin filtro: ${originalCount})`;
            } else {
                statusContainer.textContent = `Mostrando ${originalCount} resultados`;
            }
        }
        return;
    }

    // Actualizar indicador de cantidad
    if (statusContainer) {
        const filteredCount = results.length;
        const originalCount = state.originalSearchResults ? state.originalSearchResults.length : filteredCount;
        if (state.spanishFilterEnabled && filteredCount < originalCount) {
            statusContainer.textContent = `Mostrando ${filteredCount} de ${originalCount} resultados`;
        } else {
            statusContainer.textContent = `Mostrando ${filteredCount} resultados`;
        }
    }
    
    // Añadir clase para identificar contenido en español
    container.innerHTML = results.map((movie, index) => {
        const isSpanish = isSpanishContent(movie);
        const spanishBadge = isSpanish ? '<span class="spanish-badge">🇪🇸 Español</span>' : '';
        
        return `
        <div class="process-card ${isSpanish ? 'spanish-content' : ''}">
            <div class="process-header">
                <h3 class="process-title">${movie.title || 'Sin título'}</h3>
                <span class="process-status downloading">${movie.seeders || 0} seeders ${spanishBadge}</span>
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
        `;
    }).join('');
}

/**
 * Selecciona un resultado para descargar
 */
function selectResult(index) {
    const movie = state.searchResults[index];
    console.log('🎬 Película seleccionada:', movie);
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
    const urlInput = document.getElementById('modal-torrent-url');

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
async function downloadFromUrl(url, category) {
    // Si no se pasan parámetros, obtener del DOM
    if (url === undefined || category === undefined) {
        url = document.getElementById('torrent-url')?.value?.trim();
        const categorySelect = document.getElementById('category-select');
        category = categorySelect?.value;
    }
    
    // Validación: URL requerida
    if (!url) {
        showNotification('Error', 'Por favor ingresa una URL', 'error');
        return;
    }

    // Validación: Categoría obligatoria
    if (!category) {
        showNotification('Error', 'Por favor selecciona una categoría', 'error');
        const categorySelect = document.getElementById('category-select');
        categorySelect?.focus();
        return;
    }

    const btn = document.getElementById('download-url-btn');
    if (btn) {
        btn.disabled = true;
        btn.textContent = 'Iniciando...';
    }

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
        if (btn) {
            btn.disabled = false;
            btn.textContent = '⬇️ Iniciar Descarga';
        }
    }
}

/**
 * Descarga torrent seleccionado
 */
async function downloadSelected() {
    console.log('🔍 downloadSelected() ejecutándose');
    
    const urlInput = document.getElementById('modal-torrent-url');
    console.log('📌 urlInput:', urlInput);
    
    const url = urlInput?.value?.trim();
    console.log('📌 url:', url);
    
    const resultId = document.getElementById('download-result-id')?.value;
    console.log('📌 resultId:', resultId);
    
    const categorySelect = document.getElementById('modal-category-select');
    console.log('📌 categorySelect:', categorySelect);
    
    const category = categorySelect?.value;
    console.log('📌 category:', category);

    // Validación: URL requerida
    if (!url) {
        console.error('❌ URL vacía');
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
        // Construir payload - resultId opcional
        const payload = {
            url: url,
            category: category
        };
        
        // Solo incluir resultId si existe
        if (resultId) {
            payload.resultId = resultId;
        }

        const response = await fetch(CONFIG.endpoints.downloadTorrent, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(payload)
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
    console.log('[DEBUG] renderDownloads - INICIO');
    console.log('[DEBUG] state.optimizations actual:', state.optimizations.map(o => ({id: o.process_id, status: o.status, torrent_id: o.torrent_id})));
    console.log('[DEBUG] state.downloads:', state.downloads.map(d => ({id: d.id, title: d.title})));
    
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
        const isFailed = (progress >= 0 && statusValue === 'failed') || statusValue === '0' || statusValue === 'failed';
        // Torrent detenido o detenido/completado (status 0 = stopped en Transmission)
        const isStoppedOrCompleted = isCompleted || statusValue === 'stopped' || statusValue === '0' || statusValue === 'completed';

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
                        ${(() => {
                            // Verificar estado de optimización desde el estado global
                            const optState = getOptimizationState(download.id);
                            const isOptimizing = hasActiveOptimization(download.id);
                            const isOptimized = hasCompletedOptimization(download.id);
                            const optError = getOptimizationError(download.id);
                            
                            console.log(`[DEBUG] Torrent ${download.id} (${download.title}): opt encontrado?`, optState ? `SÍ - status:${optState.status}, torrent_id:${optState.torrent_id}` : 'NO');
                            console.log(`[DEBUG]   hasActiveOptimization: ${isOptimizing}`);
                            console.log(`[DEBUG]   hasCompletedOptimization: ${isOptimized}`);
                            console.log(`[DEBUG]   botón debería ser: ${isOptimizing ? 'Optimizing...' : isOptimized ? 'Optimized' : 'GPU Optimize'}`);
                            
                            if (isOptimizing) {
                                return `<button class="btn-process btn-optimize optimizing" 
                                            data-torrent-id="${download.id}"
                                            data-torrent-name="${encodeURIComponent(download.title)}"
                                            data-torrent-size="${download.size_total || download.sizeTotal || 0}"
                                            disabled>
                                            ⏳ Optimizing...
                                        </button>`;
                            } else if (isOptimized) {
                                return `<button class="btn-process btn-optimize optimized" 
                                            data-torrent-id="${download.id}"
                                            data-torrent-name="${encodeURIComponent(download.title)}"
                                            data-torrent-size="${download.size_total || download.sizeTotal || 0}"
                                            disabled>
                                            ✅ Optimized
                                        </button>`;
                            } else if (optError) {
                                return `<button class="btn-process btn-optimize error" 
                                            data-torrent-id="${download.id}"
                                            data-torrent-name="${encodeURIComponent(download.title)}"
                                            data-torrent-size="${download.size_total || download.sizeTotal || 0}"
                                            title="Error: ${optError}">
                                            ❌ Error
                                        </button>`;
                            }
                            return `<button class="btn-process btn-optimize" 
                                        data-torrent-id="${download.id}"
                                        data-torrent-name="${encodeURIComponent(download.title)}"
                                        data-torrent-size="${download.size_total || download.sizeTotal || 0}">
                                        🚀 GPU Optimize
                                    </button>`;
                        })()}
                    ` : ''}
                    ${isStoppedOrCompleted ? `
                        <button class="btn-process btn-remove" onclick="removeTorrent('${download.id}', false)" title="Eliminar torrent (mantener archivos)">
                            🗑️ Eliminar
                        </button>
                        <button class="btn-process btn-remove-files" onclick="removeTorrent('${download.id}', true)" title="Eliminar torrent y archivos descargados">
                            🗑️📁 Eliminar todo
                        </button>
                    ` : ''}
                </div>
            </div>
        `;
    }).join('');

    updateHeaderStats();
    
    // Ya no necesitamos llamar a syncWithActiveOptimizations() aquí porque:
    // 1. pollAll() siempre llama a refreshOptimizations()
    // 2. refreshOptimizations() llama a renderDownloads() cuando está en la pestaña de descargas
    // 3. renderDownloads() ahora usa state.optimizations directamente para los botones
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

/**
 * Elimina un torrent de Transmission
 * @param {number} id - ID del torrent
 * @param {boolean} deleteFiles - Si true, elimina también los archivos descargados
 */
async function removeTorrent(id, deleteFiles = false) {
    // Mensaje de confirmación diferente según si se eliminan archivos o no
    const confirmMessage = deleteFiles 
        ? '¿Eliminar torrent y archivos descargados? Esta acción no se puede deshacer.'
        : '¿Eliminar el torrent? Los archivos descargados se mantendrán.';
    
    if (!confirm(confirmMessage)) {
        return;
    }

    try {
        const response = await fetch(CONFIG.endpoints.downloadRemove(id), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ delete_files: deleteFiles })
        });

        const data = await response.json();

        if (!response.ok) {
            throw new Error(data.error || 'Error al eliminar el torrent');
        }

        const message = deleteFiles 
            ? 'Torrent y archivos eliminados correctamente'
            : 'Torrent eliminado correctamente. Los archivos se han mantenido.';
        
        showNotification('Torrent eliminado', message, 'success');
        refreshDownloads();
    } catch (error) {
        console.error('Error al eliminar torrent:', error);
        showNotification('Error', error.message, 'error');
    }
}

// ==========================================================================
// GESTIÓN DE OPTIMIZACIONES
// ==========================================================================

/**
 * Obtiene optimizaciones activas
 /**
 * Obtiene las optimizaciones activas de torrent_optimize
 * Esta función consulta el endpoint /api/optimize-torrent/active
 * que es usado por las optimizaciones GPU de torrents
 * 
 * IMPORTANTE: Siempre actualiza state.optimizations y renderiza los botones
 * para mantener sincronizado el estado global
 */
async function refreshOptimizations() {
    console.log('[DEBUG] refreshOptimizations - INICIO');
    console.log('[DEBUG] state.optimizations ANTES:', JSON.stringify(state.optimizations.map(o => ({id: o.process_id, status: o.status, torrent_id: o.torrent_id}))));
    
    try {
        // Usar el endpoint correcto de torrent_optimize
        console.log('[DEBUG] Llamando a /api/optimize-torrent/active');
        const response = await fetch(CONFIG.endpoints.torrentOptimizeActive, {
            credentials: 'include'
        });
        
        // Manejar 401 - sesión expirada
        if (response.status === 401) {
            console.warn('[Downloads] Sesión expirada, redirigiendo a login...');
            if (typeof showNotification === 'function') {
                showNotification('Sesión expirada', 'Por favor, inicia sesión nuevamente', 'warning');
            }
            setTimeout(() => { window.location.href = '/login'; }, 1500);
            return;
        }
        
        const data = await response.json();
        console.log('[DEBUG] Respuesta de /active:', data);
        console.log('[DEBUG] optimizations recibidas:', data.optimizations?.map(o => ({id: o.process_id, status: o.status, torrent_id: o.torrent_id})));

        if (response.ok && data.success) {
            // El backend devuelve: { success: true, active_count: N, optimizations: [...] }
            const basicOptimizations = data.optimizations || [];
            
            // Obtener información detallada de cada optimización
            console.log('[DEBUG] Obteniendo detalles de', basicOptimizations.length, 'optimizaciones');
            const detailedOptimizations = await Promise.all(
                basicOptimizations.map(async (opt) => {
                    try {
                        console.log('[DEBUG] Obteniendo status para:', opt.process_id);
                        const statusResponse = await fetch(
                            CONFIG.endpoints.torrentOptimizeStatus(opt.process_id),
                            { credentials: 'include' }
                        );
                        
                        // Manejar 401 en status
                        if (statusResponse.status === 401) {
                            console.warn('[Downloads] Sesión expirada al obtener status');
                            return opt;
                        }
                        
                        const statusData = await statusResponse.json();
                        console.log('[DEBUG] Status para', opt.process_id, ':', statusData);
                        if (statusResponse.ok && statusData.success) {
                            return {
                                ...opt,
                                eta_seconds: statusData.eta_seconds,
                                output_file: statusData.output_file,
                                error: statusData.error
                            };
                        }
                    } catch (e) {
                        console.error('Error obteniendo detalle:', e);
                    }
                    return opt;
                })
            );
            
            console.log('[DEBUG] detailed optimizations:', detailedOptimizations.map(o => ({id: o.process_id, status: o.status, progress: o.progress, torrent_id: o.torrent_id})));
            
            // ACTUALIZAR ESTADO GLOBAL - esto es crítico para la sincronización
            console.log('[DEBUG] ACTUALIZANDO state.optimizations DE', state.optimizations.length, 'a', detailedOptimizations.length);
            state.optimizations = detailedOptimizations;
            console.log('[DEBUG] state.optimizations DESPUÉS:', JSON.stringify(state.optimizations.map(o => ({id: o.process_id, status: o.status, torrent_id: o.torrent_id}))));
            
            // Actualizar contador en header
            const countElement = document.getElementById('active-optimizations-count');
            if (countElement) {
                countElement.textContent = data.active_count || 0;
            }
            
            // SIEMPRE renderizar downloads para actualizar botones
            // Esto evita el parpadeo al mantener los botones sincronizados
            console.log('[DEBUG] activeTab actual:', state.activeTab);
            if (state.activeTab === 'downloads') {
                console.log('[DEBUG] Llamando a renderDownloads()');
                renderDownloads();
            }
            
            // Solo renderizar pestaña de optimizaciones si está activa
            if (state.activeTab === 'optimizations') {
                console.log('[DEBUG] Llamando a renderOptimizations()');
                renderOptimizations();
            }
        } else {
            console.error('Error en respuesta de optimizaciones:', data.error);
            // También probar el endpoint legacy por compatibilidad
            try {
                const legacyResponse = await fetch(CONFIG.endpoints.optimizeStatus);
                const legacyData = await legacyResponse.json();
                if (legacyResponse.ok) {
                    state.optimizations = legacyData.active_jobs || [];
                    
                    // Actualizar contador
                    const countElement = document.getElementById('active-optimizations-count');
                    if (countElement) {
                        countElement.textContent = state.optimizations.length;
                    }
                    
                    // Renderizar si es necesario
                    if (state.activeTab === 'downloads') {
                        renderDownloads();
                    } else if (state.activeTab === 'optimizations') {
                        renderOptimizations();
                    }
                }
            } catch (legacyError) {
                console.error('Error en endpoint legacy:', legacyError);
            }
        }
    } catch (error) {
        console.error('Error al obtener optimizaciones:', error);
    }
}

/**
 * Formatea segundos a formato legible
 */
function formatTime(seconds) {
    if (!seconds || seconds < 0) return '--';
    const hours = Math.floor(seconds / 3600);
    const minutes = Math.floor((seconds % 3600) / 60);
    const secs = Math.floor(seconds % 60);
    
    if (hours > 0) return `${hours}h ${minutes}m`;
    if (minutes > 0) return `${minutes}m ${secs}s`;
    return `${secs}s`;
}

/**
 * Renderiza la lista de optimizaciones activas
 * Ahora soporta tanto el endpoint de torrent_optimize como el legacy
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
        // Compatibilidad: el endpoint de torrent_optimize usa diferentes campos
        const progress = opt.progress || 0;
        
        // Determinar el nombre del archivo según el formato de datos
        let inputFilename = 'Optimización';
        if (opt.input_file) {
            inputFilename = opt.input_file.split('/').pop().split('\\').pop();
        } else if (opt.input_path) {
            inputFilename = opt.input_path.split('/').pop().split('\\').pop();
        }

        // Determinar el estado
        const status = opt.status || 'unknown';
        const isRunning = status === 'running';
        const isCompleted = status === 'completed';
        const isError = status === 'error' || status === 'failed';
        
        // Obtener ETA si está disponible
        const eta = opt.eta_seconds || opt.eta;
        
        // Obtener error si existe
        const errorMsg = opt.error || null;

        // Determinar clase de estado
        let statusClass = 'pending';
        if (isRunning) statusClass = 'running';
        else if (isCompleted) statusClass = 'completed';
        else if (isError) statusClass = 'error';

        // Texto de estado
        let statusText = status;
        if (isRunning) statusText = `⚡ ${progress.toFixed(1)}%`;
        else if (isCompleted) statusText = '✅ Completado';
        else if (isError) statusText = '❌ Error';

        return `
            <div class="process-card" data-id="${opt.process_id || opt.id}">
                <div class="process-header">
                    <h3 class="process-title">${inputFilename}</h3>
                    <span class="process-status ${statusClass}">
                        ${statusText}
                    </span>
                </div>
                <div class="process-meta">
                    <span class="process-meta-item">📋 ${opt.category || 'default'}</span>
                    <span class="process-meta-item">⏱️ ${eta ? formatTime(eta) : '--'}</span>
                    ${opt.output_file ? `<span class="process-meta-item">📁 ${opt.output_file.split('/').pop().split('\\').pop()}</span>` : ''}
                </div>
                ${errorMsg ? `
                <div class="process-error">
                    <span class="error-message">⚠️ ${errorMsg}</span>
                </div>
                ` : ''}
                <div class="process-progress">
                    <div class="progress-container">
                        <div class="progress-bar" style="width: ${progress}%"></div>
                    </div>
                    <div class="progress-text">${progress.toFixed(1)}%</div>
                </div>
                <div class="process-actions">
                    <button class="btn-process btn-cancel" onclick="cancelOptimization('${opt.process_id || opt.id}')">
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

/**
 * Obtiene el estado de optimización para un torrent desde el estado global
 * @param {number|string} torrentId - ID del torrent
 * @returns {Object|null} - Objeto con status y process_id o null si no hay optimización
 */
function getOptimizationState(torrentId) {
    console.log(`[DEBUG] getOptimizationState(${torrentId}) - Buscando en state.optimizations (${state.optimizations.length} elementos)`);
    
    if (!state.optimizations || !torrentId) {
        console.log(`[DEBUG] getOptimizationState - Retornando null (state.optimizations vacío o torrentId inválido)`);
        return null;
    }
    
    // Buscar optimización activa para este torrent
    const result = state.optimizations.find(opt => {
        const match = opt.torrent_id == torrentId || opt.torrent_id === torrentId;
        console.log(`[DEBUG] Comparando torrent_id=${opt.torrent_id} con ${torrentId}: ${match}`);
        return match;
    });
    
    console.log(`[DEBUG] getOptimizationState(${torrentId}) - Resultado:`, result ? {process_id: result.process_id, status: result.status, torrent_id: result.torrent_id} : 'null');
    return result || null;
}

/**
 * Determina si hay una optimización activa para un torrent
 * @param {number|string} torrentId - ID del torrent
 * @returns {boolean}
 */
function hasActiveOptimization(torrentId) {
    const opt = getOptimizationState(torrentId);
    if (!opt) return false;
    
    // Estados que indican optimización en progreso
    const activeStatuses = ['running', 'starting', 'copying', 'pending'];
    return activeStatuses.includes(opt.status);
}

/**
 * Determina si la optimización está completada para un torrent
 * @param {number|string} torrentId - ID del torrent
 * @returns {boolean}
 */
function hasCompletedOptimization(torrentId) {
    const opt = getOptimizationState(torrentId);
    return opt && opt.status === 'completed';
}

/**
 * Obtiene el mensaje de error de optimización para un torrent
 * @param {number|string} torrentId - ID del torrent
 * @returns {string|null}
 */
function getOptimizationError(torrentId) {
    const opt = getOptimizationState(torrentId);
    return opt?.error || null;
}

/**
 * Actualiza el botón de optimización de una descarga
 * Esta función es llamada desde torrent_optimize.js
 * @param {string} torrentId - ID del torrent
 * @param {string} text - Texto del botón
 * @param {boolean} isError - Si es un error
 */
function updateDownloadButton(torrentId, text, isError = false) {
    const btn = document.querySelector(`.btn-optimize[data-torrent-id="${torrentId}"]`);
    if (btn) {
        btn.textContent = text;
        if (isError) {
            btn.classList.add('btn-error');
        } else if (text.includes('✅')) {
            btn.classList.add('btn-success');
            btn.disabled = true;
        } else if (text.includes('⏳')) {
            btn.classList.add('btn-pending');
            btn.disabled = true;
        }
    }
}

// Hacer la función disponible globalmente para TorrentOptimize
window.updateDownloadButton = updateDownloadButton;

// Hacer la función disponible globalmente para TorrentOptimize
window.updateDownloadButton = updateDownloadButton;

// ==========================================================================
// HISTORIAL
// ==========================================================================

// ==========================================================================
// HISTORIAL DE OPTIMIZACIONES (desde API)
// ==========================================================================

// Variables globales para el historial
let historyData = [];
let historyCurrentPage = 1;
let historyTotalEntries = 0;
const HISTORY_PER_PAGE = 20;

/**
 * Carga el historial de optimizaciones desde el API
 * Se llama automáticamente al acceder a la pestaña de historial
 */
async function loadHistory(page = 1) {
    try {
        console.log('[History] Cargando historial de optimizaciones...');
        
        const url = `${CONFIG.endpoints.optimizationHistory}?limit=${HISTORY_PER_PAGE}&offset=${(page-1)*HISTORY_PER_PAGE}`;
        console.log('[History] URL de la petición:', url);
        
        const response = await fetch(url, {
            credentials: 'include'
        });
        
        console.log('[History] Status de respuesta:', response.status);
        
        // Manejar 401 - sesión expirada
        if (response.status === 401) {
            console.warn('[History] Sesión expirada, redirigiendo a login...');
            showNotification('Sesión expirada', 'Por favor, inicia sesión nuevamente', 'warning');
            setTimeout(() => { window.location.href = '/login'; }, 1500);
            return;
        }
        
        const data = await response.json();
        
        if (data.success) {
            historyData = data.entries;
            historyTotalEntries = data.total;
            historyCurrentPage = page;
            renderHistoryTable(historyData, page);
            console.log(`[History] ✅ Historial cargado: ${data.total} entradas`);
        } else {
            console.error('[History] Error cargando historial:', data.error);
            // Fallback a localStorage
            loadHistoryFromLocalStorage();
        }
    } catch (error) {
        console.error('[History] Error de red:', error);
        // Fallback a localStorage
        loadHistoryFromLocalStorage();
    }
}

/**
 * Fallback: Carga el historial desde localStorage
 */
function loadHistoryFromLocalStorage() {
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
 * Renderiza la tabla de historial (nuevo formato)
 */
function renderHistoryTable(entries, currentPage) {
    const container = document.getElementById('history-list');
    if (!container) {
        // Si no existe el contenedor nuevo, usar el render legacy
        renderHistory();
        return;
    }
    
    if (!entries || entries.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📜</div>
                <h3>Sin historial</h3>
                <p>Las optimizaciones completadas aparecerán aquí</p>
            </div>
        `;
        return;
    }
    
    container.innerHTML = entries.map(entry => {
        // Formatear fechas
        const date = entry.created_at ? new Date(entry.created_at).toLocaleString('es-ES') : '-';
        const optStart = entry.optimization_start ? new Date(entry.optimization_start).toLocaleString('es-ES') : '-';
        const optDuration = entry.optimization_duration ? `${Math.round(entry.optimization_duration / 60)} min` : '-';
        const downloadDuration = entry.download_duration ? `${Math.round(entry.download_duration / 60)} min` : '-';
        
        // Estado con icono
        let statusIcon = '';
        let statusClass = '';
        if (entry.status === 'completed') {
            statusIcon = '✅';
            statusClass = 'status-completed';
        } else if (entry.status === 'error') {
            statusIcon = '❌';
            statusClass = 'status-error';
        } else {
            statusIcon = '⏳';
            statusClass = 'status-pending';
        }
        
        // Compresión
        const compression = entry.compression_ratio ? `${entry.compression_ratio}%` : '-';
        
        return `
            <div class="history-card">
                <div class="history-card-header">
                    <h4 class="history-card-title">${entry.torrent_name || 'Optimización'}</h4>
                    <span class="history-card-status ${statusClass}">${statusIcon} ${entry.status}</span>
                </div>
                <div class="history-card-meta">
                    <span class="history-meta-item">📁 ${entry.category || 'default'}</span>
                    <span class="history-meta-item">📅 ${date}</span>
                </div>
                <div class="history-card-meta">
                    <span class="history-meta-item">⬇️ Descarga: ${downloadDuration}</span>
                    <span class="history-meta-item">⚡ Optimización: ${optDuration}</span>
                </div>
                <div class="history-card-meta">
                    <span class="history-meta-item">📊 Compresión: ${compression}</span>
                    ${entry.output_filename ? `<span class="history-meta-item">📄 ${entry.output_filename}</span>` : ''}
                </div>
                ${entry.error_message ? `<div class="history-card-error">⚠️ ${entry.error_message}</div>` : ''}
                <div class="history-card-actions">
                    <button class="btn-delete-history" data-id="${entry.id}" title="Eliminar">🗑️</button>
                </div>
            </div>
        `;
    }).join('');
    
    // Añadir eventos a los botones de eliminar
    document.querySelectorAll('.btn-delete-history').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const entryId = e.target.dataset.id;
            deleteHistoryEntry(entryId);
        });
    });
    
    // Actualizar paginación
    renderHistoryPagination(currentPage);
}

/**
 * Renderiza la paginación del historial
 */
function renderHistoryPagination(currentPage) {
    const paginationDiv = document.getElementById('history-pagination');
    if (!paginationDiv) return;
    
    const totalPages = Math.ceil(historyTotalEntries / HISTORY_PER_PAGE);
    if (totalPages <= 1) {
        paginationDiv.innerHTML = '';
        return;
    }
    
    let html = '';
    
    for (let i = 1; i <= totalPages; i++) {
        html += `<button class="page-btn ${i === currentPage ? 'active' : ''}" data-page="${i}">${i}</button>`;
    }
    
    paginationDiv.innerHTML = html;
    
    // Añadir eventos a los botones de página
    document.querySelectorAll('.page-btn').forEach(btn => {
        btn.addEventListener('click', (e) => {
            const page = parseInt(e.target.dataset.page);
            loadHistory(page);
        });
    });
}

/**
 * Refresca el historial (para el botón del HTML)
 */
function refreshHistory() {
    loadHistory(historyCurrentPage);
}

/**
 * Elimina una entrada del historial
 */
async function deleteHistoryEntry(entryId) {
    if (!confirm('¿Eliminar esta entrada del historial?')) return;
    
    try {
        const response = await fetch(`/api/optimization-history/${entryId}`, {
            method: 'DELETE',
            credentials: 'include'
        });
        
        const data = await response.json();
        
        if (data.success) {
            console.log(`[History] Entrada ${entryId} eliminada`);
            loadHistory(historyCurrentPage); // Recargar página actual
        } else {
            alert('Error al eliminar: ' + data.error);
        }
    } catch (error) {
        console.error('[History] Error eliminando:', error);
    }
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
 * AHORA: Siempre llama a refreshOptimizations para mantener sincronizado el estado
 */
async function pollAll() {
    console.log('[DEBUG] POLLING - ejecutando refreshDownloads y refreshOptimizations');
    console.log('[DEBUG] POLLING - activeTab:', state.activeTab);
    
    // Siempre refrescar descargas
    if (state.activeTab === 'downloads') {
        await refreshDownloads();
    }
    // SIEMPRE refrescar optimizaciones (no solo cuando la pestaña está activa)
    // Esto mantiene el estado de los botones actualizado
    await refreshOptimizations();
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
    const urlInput = document.getElementById('torrent-url');
    console.log('🔍 URL input:', urlInput);
    
    if (!urlInput) {
        showNotification('Error', 'Campo de URL no encontrado', 'error');
        return;
    }
    
    const url = urlInput.value.trim();
    console.log('📌 URL:', url);
    
    if (!url) {
        showNotification('Error', 'Por favor ingresa una URL', 'error');
        return;
    }
    
    const categorySelect = document.getElementById('category-select');
    const category = categorySelect?.value;
    
    if (!category) {
        showNotification('Error', 'Por favor selecciona una categoría', 'error');
        categorySelect?.focus();
        return;
    }
    
    // Llamar a downloadFromUrl con los parámetros
    downloadFromUrl(url, category);
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

    // Sincronizar checkbox de filtro español con el estado inicial
    const spanishCheckbox = document.getElementById('spanish-filter-checkbox');
    if (spanishCheckbox) {
        spanishCheckbox.checked = state.spanishFilterEnabled;
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

    // Event delegation para botones de optimización (funciona con botones renderizados dinámicamente)
    const downloadsList = document.getElementById('downloads-list');
    if (downloadsList) {
        downloadsList.addEventListener('click', (e) => {
            const btn = e.target.closest('.btn-optimize');
            if (!btn) return;
            
            // Prevenir comportamiento por defecto
            e.preventDefault();
            e.stopPropagation();
            
            const torrentId = btn.dataset.torrentId;
            const torrentName = decodeURIComponent(btn.dataset.torrentName || '');
            const torrentSize = btn.dataset.torrentSize;
            
            console.log('[Downloads] Botón optimize clickeado:', torrentId, torrentName);
            
            // Verificar que TorrentOptimize esté disponible
            if (typeof TorrentOptimize !== 'undefined' && TorrentOptimize.showOptimizeModal) {
                TorrentOptimize.showOptimizeModal({
                    id: torrentId,
                    name: torrentName,
                    size: torrentSize
                });
            } else {
                console.error('[Downloads] TorrentOptimize no está disponible');
            }
        });
    }
    
    // Verificar que TorrentOptimize esté cargado
    if (typeof TorrentOptimize === 'undefined') {
        console.warn('[Downloads] Esperando a TorrentOptimize...');
        const checkTorrentOptimize = setInterval(() => {
            if (typeof TorrentOptimize !== 'undefined') {
                clearInterval(checkTorrentOptimize);
                console.log('[Downloads] TorrentOptimize cargado correctamente');
                // Sincronizar estados de botones al cargar
                if (TorrentOptimize.syncWithActiveOptimizations) {
                    TorrentOptimize.syncWithActiveOptimizations();
                }
            }
        }, 500);
        // Cancelar después de 10 segundos
        setTimeout(() => clearInterval(checkTorrentOptimize), 10000);
    } else {
        // TorrentOptimize ya está cargado, sincronizar inmediatamente
        if (TorrentOptimize.syncWithActiveOptimizations) {
            TorrentOptimize.syncWithActiveOptimizations();
        }
    }

    // Iniciar polling
    startPolling();
    
    // Cargar historial automáticamente al iniciar la página
    loadHistory(1);

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
