/**
 * UI del módulo de descargas
 */
(function() {
    'use strict';
    window.renderSearchResults = function(rs) {
        var c = document.getElementById('results-container');
        var sc = document.getElementById('search-status');
        if (!rs || rs.length === 0) {
            var hor = window.state.originalSearchResults && window.state.originalSearchResults.length > 0;
            var msg = hor && window.state.spanishFilterEnabled ? 'No se encontraron resultados en español' : 'No se encontraron películas';
            c.innerHTML = '<div class="empty-state"><div class="empty-icon">🔍</div><h3>Sin resultados</h3><p>' + msg + '</p></div>';
            if (sc && window.state.originalSearchResults) {
                var oc = window.state.originalSearchResults.length;
                sc.textContent = window.state.spanishFilterEnabled ? 'Mostrando 0 de ' + oc + ' resultados' : 'Mostrando ' + oc + ' resultados';
            }
            return;
        }
        if (sc) {
            var fc = rs.length, oc = window.state.originalSearchResults ? window.state.originalSearchResults.length : fc;
            sc.textContent = window.state.spanishFilterEnabled && fc < oc ? 'Mostrando ' + fc + ' de ' + oc + ' resultados' : 'Mostrando ' + fc + ' resultados';
        }
        c.innerHTML = rs.map(function(m,i) {
            var es = window.isSpanishContent(m);
            return '<div class="process-card '+(es?'spanish-content':'')+')"><div class="process-header"><h3 class="process-title">'+(m.title||'Sin título')+'</h3><span class="process-status downloading">'+(m.seeders||0)+' seeders '+(es?'<span class="spanish-badge">🇪🇸 Español</span>':'')+'</span></div><div class="process-meta"><span class="process-meta-item">📅 '+(m.year||'N/A')+'</span><span class="process-meta-item">📊 '+(m.size||'N/A')+'</span><span class="process-meta-item">🔗 '+(m.indexer||'N/A')+'</span></div><div class="process-actions"><button class="btn-process btn-view" onclick="selectResult('+i+')">⬇️ Descargar</button></div></div>';
        }).join('');
    };
    window.selectResult = function(i) {
        var m = window.state.searchResults[i];
        if (m) window.showDownloadModal(m);
    };
    window.showDownloadModal = function(m) {
        var mod = document.getElementById('download-modal');
        if (!mod) return;
        var te = document.getElementById('download-name');
        var ie = document.getElementById('download-category');
        var ue = document.getElementById('modal-torrent-url');
        if (te) te.textContent = m.title || 'Sin título';
        if (ie) ie.textContent = (m.year || 'N/A') + ' • ' + (m.size || 'N/A');
        if (ue) ue.value = m.url || m.downloadUrl || '';
        mod.style.display = 'flex';
    };
    window.closeDownloadModal = function() {
        var m = document.getElementById('download-modal');
        if (m) m.style.display = 'none';
    };
    window.renderDownloads = function() {
        var c = document.getElementById('downloads-list');
        if (!window.state.downloads || window.state.downloads.length === 0) {
            c.innerHTML = '<div class="empty-state"><div class="empty-icon">📥</div><h3>Sin descargas activas</h3><p>Inicia una descarga desde la pestaña de búsqueda</p></div>';
            window.updateHeaderStats();
            return;
        }
        if (typeof window.renderDownloadsList === 'function') {
            window.renderDownloadsList(window.state.downloads);
        } else {
            c.innerHTML = window.state.downloads.map(function(d) {
                var sv = d.status_display || d.status || 'unknown';
                var p = d.progress || 0;
                var sc = window.getStatusClass(sv);
                var ds = d.download_speed || d.downloadSpeed || 0;
                var us = d.upload_speed || d.uploadSpeed || 0;
                var sd = d.status_display || d.statusDisplay || d.status;
                var ef = d.eta_formatted || d.etaFormatted || '--';
                var ic = p >= 99.9 || sv === 'seeding' || sv === 6 || sv === 'completed';
                var if_ = (p >= 0 && sv === 'failed') || sv === '0' || sv === 'failed';
                var isc = ic || sv === 'stopped' || sv === '0' || sv === 'completed';
                var isPaused = sv === 'stopped' || sv === 0 || sv === 'paused';
                var pp = p > 100 ? 100 : p;
                var btns = '';
                // Si está pausado, mostrar botón de reanudar
                if (isPaused && !ic && !if_) {
                    btns += '<button class="btn-process btn-pause" onclick="resumeDownload(\''+d.id+'\')">▶️ Reanudar</button>';
                    btns += '<button class="btn-process btn-cancel" onclick="cancelDownload(\''+d.id+'\')">❌ Cancelar</button>';
                } else if (!ic && !if_) {
                    // Si está descargando, mostrar botón de pausa
                    btns += '<button class="btn-process btn-pause" onclick="pauseDownload(\''+d.id+'\')">⏸️ Pausar</button>';
                    btns += '<button class="btn-process btn-cancel" onclick="cancelDownload(\''+d.id+'\')">❌ Cancelar</button>';
                }
                if (ic) {
                    var os = window.getOptimizationState(d.id);
                    var io = window.hasActiveOptimization(d.id);
                    var io_ = window.hasCompletedOptimization(d.id);
                    var oe = window.getOptimizationError(d.id);
                    if (io) btns += '<button class="btn-process btn-optimize optimizing" data-torrent-id="'+d.id+'" data-torrent-name="'+encodeURIComponent(d.title)+'" data-torrent-size="'+(d.size_total||d.sizeTotal||0)+'" disabled>⏳ Optimizing...</button>';
                    else if (io_) btns += '<button class="btn-process btn-optimize optimized" data-torrent-id="'+d.id+'" data-torrent-name="'+encodeURIComponent(d.title)+'" data-torrent-size="'+(d.size_total||d.sizeTotal||0)+'" disabled>✅ Optimized</button>';
                    else if (oe) btns += '<button class="btn-process btn-optimize error" data-torrent-id="'+d.id+'" data-torrent-name="'+encodeURIComponent(d.title)+'" data-torrent-size="'+(d.size_total||d.sizeTotal||0)+'" title="Error: '+oe+'">❌ Error</button>';
                    else btns += '<button class="btn-process btn-optimize" data-torrent-id="'+d.id+'" data-torrent-name="'+encodeURIComponent(d.title)+'" data-torrent-size="'+(d.size_total||d.sizeTotal||0)+'">🚀 GPU Optimize</button>';
                }
                if (isc) { btns += '<button class="btn-process btn-remove" onclick="removeTorrent(\''+d.id+'\',false)" title="Eliminar">🗑️ Eliminar</button><button class="btn-process btn-remove-files" onclick="removeTorrent(\''+d.id+'\',true)" title="Eliminar todo">🗑️📁 Eliminar todo</button>'; }
                return '<div class="process-card" data-id="'+d.id+'"><div class="process-header"><h3 class="process-title">'+(d.title||'Descarga')+'</h3><span class="process-status '+sc+'">'+sd+'</span></div><div class="process-meta"><span class="process-meta-item">📊 '+(typeof pp==='number'?pp.toFixed(1):0)+'%</span><span class="process-meta-item">⬇️ '+window.formatBytes(ds)+'/s</span><span class="process-meta-item">⬆️ '+window.formatBytes(us)+'/s</span><span class="process-meta-item">⏱️ '+ef+'</span><span class="process-meta-item">📁 '+(d.category||'N/A')+'</span></div><div class="process-progress"><div class="progress-container"><div class="progress-bar" style="width:'+(typeof pp==='number'?pp:0)+'%"></div></div></div><div class="process-actions">'+btns+'</div></div>';
            }).join('');
        }
        window.updateHeaderStats();
    };
})();