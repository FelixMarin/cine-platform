/**
 * Downloads - UI Renderers
 */

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
    const statusClass = getStatusClass(download.status);

    item.innerHTML = `
        <div class="download-info">
            <h4>${escapeHtml(download.name)}</h4>
            <div class="download-meta">
                <span class="status ${statusClass}">${download.status}</span>
                <span>${formatBytes(download.size_total)}</span>
                <span>${formatSpeed(download.rate_download)}</span>
            </div>
        </div>
        <div class="download-progress">
            <div class="progress-bar">
                <div class="progress-fill" style="width: ${progress}%"></div>
            </div>
            <span class="progress-text">${progress.toFixed(1)}%</span>
        </div>
        <div class="download-actions">
            <button onclick="cancelDownload(${download.id})" class="btn-cancel">Cancelar</button>
            <button onclick="removeDownload(${download.id})" class="btn-remove">Eliminar</button>
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

window.renderDownloadsList = renderDownloadsList;
window.renderOptimizationsList = renderOptimizationsList;
window.renderHistoryList = renderHistoryList;
window.cancelDownload = cancelDownload;
window.removeDownload = removeDownload;
