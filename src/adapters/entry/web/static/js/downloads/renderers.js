/**
 * Downloads - UI Renderers
 */

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function renderDownloadsList(downloads) {
    const container = document.getElementById('downloads-list');
    if (!container) return;

    container.innerHTML = '';

    if (!downloads || downloads.length === 0) {
        container.innerHTML = '<p class="no-results">No hay descargas activas</p>';
        return;
    }

    downloads.forEach(download => {
        const item = createDownloadItem(download);
        container.appendChild(item);
    });
}

function createDownloadItem(download) {
    const item = document.createElement('div');
    item.className = 'download-item';
    item.dataset.id = download.id;

    const progress = download.progress || 0;
    const status = download.status_display || download.status || 'unknown';
    const statusClass = getStatusClass(status);
    const name = download.title || download.name || 'Descarga';
    const downloadSpeed = formatSpeed(download.download_speed || download.downloadSpeed || 0);
    const uploadSpeed = formatSpeed(download.upload_speed || download.uploadSpeed || 0);
    const eta = download.eta_formatted || download.etaFormatted || formatEta(download.eta);
    const isActive = status === 'downloading' || status === 'seeding' || status === 'downloading' || status === 1;
    const actionIcon = isActive ? '⏸️' : '▶️';

    item.innerHTML = `
        <div class="download-header">
            <h4>${escapeHtml(name)}</h4>
            <span class="status ${statusClass}">${status}</span>
        </div>
        <div class="download-info-row">
            <div class="download-progress">
                <div class="progress-bar">
                    <div class="progress-fill" style="width: ${progress}%"></div>
                </div>
            </div>
            <div class="download-stats">
                <span class="stat-item"><span class="stat-icon">📊</span> ${progress.toFixed(1)}%</span>
                <span class="stat-item"><span class="stat-icon">↓</span> ${downloadSpeed}</span>
                <span class="stat-item"><span class="stat-icon">↑</span> ${uploadSpeed}</span>
                <span class="stat-item"><span class="stat-icon">⏱️</span> ${eta}</span>
            </div>
            <div class="download-actions">
                <button onclick="cancelDownload('${download.id}')" class="btn-action" title="Pausar/Reanudar">${actionIcon}</button>
                <button onclick="removeDownload('${download.id}')" class="btn-action" title="Eliminar">🗑️</button>
            </div>
        </div>
    `;

    return item;
}

function renderOptimizationsList(optimizations) {
    const container = document.getElementById('optimizations-list');
    if (!container) return;

    container.innerHTML = '';

    if (!optimizations || optimizations.length === 0) {
        container.innerHTML = '<p class="no-results">No hay optimizaciones activas</p>';
        return;
    }

    optimizations.forEach(opt => {
        const item = createOptimizationItem(opt);
        container.appendChild(item);
    });
}

function createOptimizationItem(opt) {
    const item = document.createElement('div');
    item.className = 'optimization-item';
    item.dataset.id = opt.process_id;

    const progress = opt.progress || 0;
    const statusClass = getStatusClass(opt.status);

    item.innerHTML = `
        <div class="optimization-info">
            <h4>${escapeHtml(opt.output_filename || opt.process_id)}</h4>
            <div class="optimization-meta">
                <span class="status ${statusClass}">${opt.status}</span>
                <span>${opt.category || ''}</span>
            </div>
        </div>
        <div class="optimization-progress">
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            <span class="progress-text">${progress.toFixed(1)}%</span>
        </div>
    `;

    return item;
}

function renderHistoryList(history) {
    const container = document.getElementById('history-list');
    if (!container) return;

    container.innerHTML = '';

    if (!history || history.length === 0) {
        container.innerHTML = '<p class="no-results">No hay historial</p>';
        return;
    }

    history.forEach(item => {
        const row = createHistoryItem(item);
        container.appendChild(row);
    });
}

function createHistoryItem(item) {
    const row = document.createElement('tr');
    row.innerHTML = `
        <td>${escapeHtml(item.torrent_name || 'N/A')}</td>
        <td>${item.category || ''}</td>
        <td>${item.status}</td>
        <td>${item.compression_ratio ? item.compression_ratio + '%' : '-'}</td>
        <td>${formatDate(item.optimization_end)}</td>
    `;
    return row;
}

function getStatusClass(status) {
    const statusMap = {
        'downloading': 'status-downloading',
        'seeding': 'status-seeding',
        'optimizing': 'status-optimizing',
        'completed': 'status-completed',
        'error': 'status-error',
        'cancelled': 'status-cancelled'
    };
    return statusMap[status] || '';
}

function formatSpeed(bytesPerSec) {
    if (!bytesPerSec || bytesPerSec <= 0) return '0 B/s';
    const k = 1024;
    const sizes = ['B/s', 'KB/s', 'MB/s', 'GB/s'];
    const i = Math.floor(Math.log(bytesPerSec) / Math.log(k));
    return (bytesPerSec / Math.pow(k, i)).toFixed(1) + ' ' + sizes[i];
}

function formatEta(seconds) {
    if (!seconds || seconds < 0) return '∞';
    if (seconds < 60) return `${seconds}s`;
    if (seconds < 3600) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}m ${secs}s`;
    }
    const hours = Math.floor(seconds / 3600);
    const mins = Math.floor((seconds % 3600) / 60);
    return `${hours}h ${mins}m`;
}

function formatDate(dateStr) {
    if (!dateStr) return '-';
    try {
        const d = new Date(dateStr);
        return d.toLocaleDateString('es-ES', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return dateStr;
    }
}

window.renderDownloadsList = renderDownloadsList;
window.renderOptimizationsList = renderOptimizationsList;
window.renderHistoryList = renderHistoryList;
window.cancelDownload = cancelDownload;
window.removeDownload = removeDownload;
window.formatEta = formatEta;
window.formatDate = formatDate;
