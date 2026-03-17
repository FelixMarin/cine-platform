/**
 * API del módulo de descargas
 */
(function() {
    'use strict';
    window.searchMovies = async function() {
        var q = document.getElementById('search-query').value.trim();
        if (!q) { window.showNotification('Error','Por favor ingresa un término de búsqueda','error'); return; }
        var btn = document.querySelector('.search-button');
        var rc = document.getElementById('results-container');
        var sc = document.getElementById('search-status');
        if (btn) { btn.disabled = true; btn.textContent = 'Buscando...'; }
        if (rc) rc.innerHTML = '<div class="empty-state"><p>Buscando en índices...</p></div>';
        if (sc) sc.textContent = 'Buscando...';
        try {
            var r = await fetch(window.CONFIG.endpoints.search, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:q})});
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Error en la búsqueda');
            window.state.originalSearchResults = d.results || [];
            window.state.searchResults = d.results || [];
            if (window.state.spanishFilterEnabled) window.state.searchResults = window.filterSpanishResults(window.state.originalSearchResults);
            window.renderSearchResults(window.state.searchResults);
        } catch(e) { console.error('Error:',e); rc.innerHTML='<div class="empty-state"><p>Error: '+e.message+'</p></div>'; window.showNotification('Error',e.message,'error'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = '🔍 Buscar'; } }
    };
    window.refreshDownloads = async function() {
        try {
            var r = await fetch(window.CONFIG.endpoints.downloadsActive);
            var d = await r.json();
            if (r.ok && d.success !== false) { window.state.downloads = d.downloads || []; window.state.activeDownloadsCount = d.stats ? d.stats.active_count : 0; window.renderDownloads(); }
        } catch(e) { console.error('Error:',e); }
    };
    window.cancelDownload = async function(id) {
        if (!confirm('¿Cancelar esta descarga?')) return;
        try {
            var r = await fetch(window.CONFIG.endpoints.downloadCancel(id), {method:'POST'});
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Error');
            window.showNotification('Descarga cancelada','La descarga ha sido eliminada','success');
            window.refreshDownloads();
        } catch(e) { window.showNotification('Error',e.message,'error'); }
    };
    window.removeTorrent = async function(id, del) {
        del = del || false;
        if (!confirm(del ? '¿Eliminar torrent y archivos?' : '¿Eliminar el torrent?')) return;
        try {
            var r = await fetch(window.CONFIG.endpoints.downloadRemove(id), {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({delete_files:del})});
            var d = await r.json();
            if (!r.ok) throw new Error(d.error);
            window.showNotification('Torrent eliminado',del?'Archivos eliminados':'Torrent eliminado','success');
            window.refreshDownloads();
        } catch(e) { window.showNotification('Error',e.message,'error'); }
    };
    window.refreshOptimizations = async function() {
        try {
            var r = await fetch(window.CONFIG.endpoints.torrentOptimizeActive,{credentials:'include'});
            if (r.status === 401) { window.showNotification('Sesión expirada','Por favor inicia sesión','warning'); setTimeout(function(){window.location.href='/login';},1500); return; }
            var d = await r.json();
            if (r.ok && d.success) {
                var ba = d.optimizations || [];
                var da = await Promise.all(ba.map(async function(o) {
                    try {
                        var sr = await fetch(window.CONFIG.endpoints.torrentOptimizeStatus(o.process_id),{credentials:'include'});
                        if (sr.status===401) return o;
                        var sd = await sr.json();
                        if (sr.ok && sd.success) return {...o,eta_seconds:sd.eta_seconds,output_file:sd.output_file,error:sd.error};
                    } catch(e) { console.error(e); }
                    return o;
                }));
                window.state.optimizations = da;
                var ce = document.getElementById('active-optimizations-count');
                if (ce) ce.textContent = d.active_count || 0;
                if (window.state.activeTab === 'downloads') window.renderDownloads();
                if (window.state.activeTab === 'optimizations' && window.renderOptimizations) window.renderOptimizations();
            }
        } catch(e) { console.error(e); }
    };
    window.loadCategories = async function() {
        var s = document.getElementById('category-select');
        var ms = document.getElementById('modal-category-select');
        var fc = function(c) { return c.replace(/_/g,' ').split(' ').map(function(w){return w.charAt(0).toUpperCase()+w.slice(1).toLowerCase();}).join(' '); };
        var ls = function(sel) { if(!sel)return; sel.disabled=true; if(sel.options[0]) sel.options[0].textContent='Cargando...'; };
        ls(s); ls(ms);
        try {
            var r = await fetch('/api/download/categories');
            var d = await r.json();
            if (!d.success) throw new Error(d.error);
            if (s) { while(s.options.length>1)s.remove(1); if(d.categories) d.categories.forEach(function(c){var o=document.createElement('option');o.value=c;o.textContent=fc(c);s.appendChild(o);}); s.disabled=false; if(s.options[0])s.options[0].textContent='Seleccionar...'; }
            if (ms) { while(ms.options.length>1)ms.remove(1); if(d.categories) d.categories.forEach(function(c){var o=document.createElement('option');o.value=c;o.textContent=fc(c);ms.appendChild(o);}); ms.disabled=false; if(ms.options[0])ms.options[0].textContent='Seleccionar...'; }
        } catch(e) { console.error(e); if(s&&s.options[0])s.options[0].textContent='Error'; window.showNotification('Error',e.message,'error'); }
    };
})();
