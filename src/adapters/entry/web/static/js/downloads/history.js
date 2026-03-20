/**
 * Lógica del historial
 */
(function() {
    'use strict';
    
    // Función helper para añadir cache busting a URLs
    function addCacheBuster(url) {
        var separator = url.includes('?') ? '&' : '?';
        return url + separator + '_cb=' + Date.now();
    }
    
    window.loadHistory = async function(pg) {
        pg = pg || 1;
        try {
            var url = addCacheBuster(window.CONFIG.endpoints.optimizationHistory + '?limit=' + window.HISTORY_PER_PAGE + '&offset=' + ((pg-1)*window.HISTORY_PER_PAGE));
            var r = await fetch(url, {credentials:'include'});
            if (r.status === 401) { window.showNotification('Sesión expirada','Por favor inicia sesión','warning'); setTimeout(function(){window.location.href='/login';},1500); return; }
            var d = await r.json();
            if (d.success) { window.historyData = d.entries; window.historyCurrentPage = pg; window.historyTotalEntries = d.total; window.renderHistoryTable(window.historyData, pg); }
            else { console.error(d.error); window.loadHistoryFromLocalStorage(); }
        } catch(e) { console.error(e); window.loadHistoryFromLocalStorage(); }
    };
    window.loadHistoryFromLocalStorage = function() {
        try { var s = localStorage.getItem('cine-platform-history'); if (s) window.state.history = JSON.parse(s); }
        catch(e) { window.state.history = []; }
        window.renderHistory();
    };
    window.renderHistoryTable = function(ents, cp) {
        var c = document.getElementById('history-list');
        if (!c) { window.renderHistory(); return; }
        if (!ents || ents.length === 0) { c.innerHTML = '<div class="empty-state"><div class="empty-icon">📜</div><h3>Sin historial</h3><p>Las optimizaciones aparecerán aquí</p></div>'; return; }
        c.innerHTML = ents.map(function(e) {
            var dt = e.created_at ? new Date(e.created_at).toLocaleString('es-ES') : '-';
            var od = '-'; if (e.optimization_started && e.optimization_completed) { var st = new Date(e.optimization_started), en = new Date(e.optimization_completed); od = window.formatTime(Math.round((en-st)/1000)); }
            var dd = '-'; if (e.download_started && e.download_completed) { var st = new Date(e.download_started), en = new Date(e.download_completed); dd = window.formatTime(Math.round((en-st)/1000)); }
            var si = '', sc = '';
            if (e.status === 'completed') { si = '✅'; sc = 'status-completed'; }
            else if (e.status === 'error') { si = '❌'; sc = 'status-error'; }
            else { si = '⏳'; sc = 'status-pending'; }
            var cr = '-'; if (e.original_size_bytes && e.optimized_size_bytes) cr = ((1 - e.optimized_size_bytes/e.original_size_bytes)*100).toFixed(1) + '%';
            var os = e.original_size_bytes ? window.formatBytes(e.original_size_bytes) : '-';
            var os_ = e.optimized_size_bytes ? window.formatBytes(e.optimized_size_bytes) : '-';
            var eh = e.error_message ? '<div class="history-card-error">⚠️ ' + e.error_message + '</div>' : '';
            return '<div class="history-card"><div class="history-card-header"><h4 class="history-card-title">'+(e.torrent_name||e.movie_name||'Optimización')+'</h4><span class="history-card-status '+sc+'">'+si+' '+e.status+'</span></div><div class="history-card-meta"><span class="history-meta-item">📁 '+(e.category||'default')+'</span><span class="history-meta-item">📅 '+dt+'</span></div><div class="history-card-meta"><span class="history-meta-item">⬇️ Descarga: '+dd+'</span><span class="history-meta-item">⚡ Optimización: '+od+'</span></div><div class="history-card-meta"><span class="history-meta-item">📊 Tamaño original: '+os+'</span><span class="history-meta-item">📊 Tamaño optimizado: '+os_+'</span></div><div class="history-card-meta"><span class="history-meta-item">🔽 Compresión: '+cr+'</span>'+(e.error_message?'<span class="history-meta-item error-message">⚠️ Error</span>':'')+'</div>'+eh+'<div class="history-card-actions"><button class="btn-delete-history" data-id="'+e.id+'" title="Eliminar">🗑️</button></div></div>';
        }).join('');
        document.querySelectorAll('.btn-delete-history').forEach(function(b){b.addEventListener('click',function(e){window.deleteHistoryEntry(e.target.dataset.id);});});
        window.renderHistoryPagination(cp);
    };
    window.renderHistoryPagination = function(cp) {
        var p = document.getElementById('history-pagination');
        if (!p) return;
        var tp = Math.ceil(window.historyTotalEntries / window.HISTORY_PER_PAGE);
        if (tp <= 1) { p.innerHTML = ''; return; }
        var h = '';
        for (var i = 1; i <= tp; i++) h += '<button class="page-btn '+(i===cp?'active':'')+'" data-page="'+i+'">'+i+'</button>';
        p.innerHTML = h;
        document.querySelectorAll('.page-btn').forEach(function(b){b.addEventListener('click',function(e){window.loadHistory(parseInt(e.target.dataset.page));});});
    };
    window.refreshHistory = function() { window.loadHistory(window.historyCurrentPage); };
    window.deleteHistoryEntry = async function(id) {
        if (!confirm('¿Eliminar esta entrada?')) return;
        try {
            var r = await fetch(addCacheBuster('/api/optimization-history/'+id), {method:'DELETE',credentials:'include'});
            var d = await r.json();
            if (d.success) { window.showNotification('Eliminado','Entrada eliminada','success'); window.loadHistory(window.historyCurrentPage); }
            else alert('Error: '+d.error);
        } catch(e) { alert('Error al eliminar'); }
    };
    window.saveHistory = function() {
        try { var ts = window.state.history.slice(0,window.CONFIG.maxHistoryItems); localStorage.setItem('cine-platform-history',JSON.stringify(ts)); }
        catch(e) { console.error(e); }
    };
    window.renderHistory = function() {
        var c = document.getElementById('history-list');
        if (!window.state.history || window.state.history.length === 0) { c.innerHTML = '<div class="empty-state"><div class="empty-icon">📜</div><h3>Sin historial</h3><p>Las descargas y optimizaciones aparecerán aquí</p></div>'; return; }
        c.innerHTML = window.state.history.map(function(i) {
            var sc = i.type === 'download' ? (i.status === 'completed' ? 'completed' : 'failed') : (i.status === 'completed' ? 'completed' : 'failed');
            return '<div class="history-item"><div class="history-item-info"><div class="history-item-title">'+i.title+'</div><div class="history-item-meta">'+(i.type==='download'?'📥':'⚡')+' '+(i.type==='download'?'Descarga':'Optimización')+' • '+window.formatDate(i.completedAt||i.startedAt)+'</div></div><span class="history-item-status process-status '+sc+'">'+i.status+'</span></div>';
        }).join('');
    };
    window.addToHistory = function(it) {
        window.state.history.unshift({...it,completedAt:Math.floor(Date.now()/1000)});
        window.saveHistory();
        if (window.state.activeTab === 'history') window.renderHistory();
    };
})();