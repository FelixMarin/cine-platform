/**
 * Lógica de descargas
 */
(function() {
    'use strict';
    window.downloadFromUrl = async function(url, cat) {
        if (url === undefined || cat === undefined) {
            url = document.getElementById('torrent-url').value.trim();
            var cs = document.getElementById('category-select');
            cat = cs ? cs.value : undefined;
        }
        if (!url) { window.showNotification('Error','Por favor ingresa una URL','error'); return; }
        if (!cat) { window.showNotification('Error','Por favor selecciona una categoría','error'); var cse=document.getElementById('category-select');if(cse)cse.focus();return; }
        var btn = document.getElementById('download-url-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Iniciando...'; }
        try {
            var r = await fetch(window.CONFIG.endpoints.downloadUrl || window.CONFIG.endpoints.downloadTorrent, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({url:url,category:cat})});
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Error');
            window.showNotification('Descarga iniciada','Descargando: '+(d.title||'Torrent'),'success');
            window.closeDownloadModal();
            window.switchTab('downloads');
        } catch(e) { window.showNotification('Error',e.message,'error'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = '⬇️ Iniciar Descarga'; } }
    };
    window.downloadSelected = async function() {
        var ui = document.getElementById('modal-torrent-url');
        var url = ui ? ui.value.trim() : '';
        var rid = document.getElementById('download-result-id') ? document.getElementById('download-result-id').value : undefined;
        var cs = document.getElementById('modal-category-select');
        var cat = cs ? cs.value : undefined;
        if (!url) { window.showNotification('Error','Por favor ingresa una URL','error'); return; }
        if (!cat) { window.showNotification('Error','Por favor selecciona una categoría','error'); if(cs)cs.focus();return; }
        var btn = document.getElementById('modal-download-btn');
        if (btn) { btn.disabled = true; btn.textContent = 'Iniciando...'; }
        try {
            var p = {url:url,category:cat};
            if (rid) p.resultId = rid;
            var r = await fetch(window.CONFIG.endpoints.downloadTorrent, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Error');
            window.showNotification('Descarga iniciada','Descargando: '+(d.title||'Torrent'),'success');
            window.closeDownloadModal();
            window.switchTab('downloads');
        } catch(e) { window.showNotification('Error',e.message,'error'); }
        finally { if (btn) { btn.disabled = false; btn.textContent = '⬇️ Iniciar Descarga'; } }
    };
})();