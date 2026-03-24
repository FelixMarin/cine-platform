/**
 * Lógica de optimizaciones
 */
(function() {
    'use strict';
    window.renderOptimizations = function() {
        var c = document.getElementById('optimizations-list');
        if (!window.state.optimizations || window.state.optimizations.length === 0) {
            c.innerHTML = '<div class="empty-state"><div class="empty-icon">⚡</div><h3>Sin optimizaciones activas</h3><p>Los archivos descargados aparecerán aquí para optimizar</p></div>';
            return;
        }
        c.innerHTML = window.state.optimizations.map(function(o) {
            var p = o.progress || 0;
            var nm = o.input_file ? o.input_file.split('/').pop().split('\\').pop() : (o.input_path ? o.input_path.split('/').pop().split('\\').pop() : 'Optimización');
            var st = o.status || 'unknown';
            var rn = st === 'running';
            var cp = st === 'completed';
            var er = st === 'error' || st === 'failed';
            var eta = o.eta_seconds || o.eta;
            var err = o.error || null;
            var sc = 'pending';
            if (rn) sc = 'running'; else if (cp) sc = 'completed'; else if (er) sc = 'error';
            var tx = st;
            if (rn) tx = '⚡ ' + p.toFixed(1) + '%';
            else if (cp) tx = '✅ Completado';
            else if (er) tx = '❌ Error';
            var ofh = o.output_file ? '<span class="process-meta-item">📁 ' + o.output_file.split('/').pop().split('\\').pop() + '</span>' : '';
            var erh = err ? '<div class="process-error"><span class="error-message">⚠️ ' + err + '</span></div>' : '';
            return '<div class="process-card" data-id="'+(o.process_id||o.id)+'"><div class="process-header"><h3 class="process-title">'+nm+'</h3><span class="process-status '+sc+'">'+tx+'</span></div><div class="process-meta"><span class="process-meta-item">📋 '+(o.category||'default')+'</span><span class="process-meta-item">⏱️ '+(eta?window.formatTime(eta):'--')+'</span>'+ofh+'</div>'+erh+'<div class="process-progress"><div class="progress-container"><div class="progress-bar" style="width:'+p+'%"></div></div><div class="progress-text">'+p.toFixed(1)+'%</div></div><div class="process-actions"><button class="btn-process btn-cancel" onclick="cancelOptimization(\''+(o.process_id||o.id)+'\')">❌ Cancelar</button></div></div>';
        }).join('');
    };
    window.startOptimization = async function(did, title, fp) {
        var td = decodeURIComponent(title);
        var pf = document.getElementById('optimize-profile') ? document.getElementById('optimize-profile').value : 'balanced';
        try {
            var r = await fetch(window.CONFIG.endpoints.optimizeStart, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({file_path:fp,profile:pf})});
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Error');
            window.showNotification('Optimización iniciada','Procesando: '+td,'success');
            window.switchTab('optimizations');
        } catch(e) { window.showNotification('Error',e.message,'error'); }
    };
    window.cancelOptimization = async function(id) {
        if (!confirm('¿Cancelar esta optimización?')) return;
        try {
            var r = await fetch(window.CONFIG.endpoints.optimizeCancel, {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({process_id:id})});
            var d = await r.json();
            if (!r.ok) throw new Error(d.error || 'Error');
            window.showNotification('Optimización cancelada','La optimización ha sido detenida','success');
            window.refreshOptimizations();
        } catch(e) { window.showNotification('Error',e.message,'error'); }
    };
    window.updateDownloadButton = function(tid, txt, err) {
        err = err || false;
        var btn = document.querySelector('.btn-optimize[data-torrent-id="'+tid+'"]');
        if (btn) {
            btn.textContent = txt;
            if (err) btn.classList.add('btn-error');
            else if (txt.includes('✅')) { btn.classList.add('btn-success'); btn.disabled = true; }
            else if (txt.includes('⏳')) { btn.classList.add('btn-pending'); btn.disabled = true; }
        }
    };
})();