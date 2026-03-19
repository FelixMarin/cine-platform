/**
 * Gestión de pestañas
 */
(function() {
    'use strict';
    window.switchTab = function(tn) {
        window.state.activeTab = tn;
        document.querySelectorAll('.download-tab').forEach(function(t) { t.classList.remove('active'); });
        var at = document.querySelector('.download-tab[data-tab="' + tn + '"]');
        if (at) at.classList.add('active');
        document.querySelectorAll('.download-tab-content').forEach(function(c) { c.classList.remove('active'); });
        var ce = document.getElementById('tab-' + tn);
        if (ce) ce.classList.add('active');
        switch (tn) {
            case 'downloads': if (window.refreshDownloads) window.refreshDownloads(); break;
            case 'optimizations': if (window.refreshOptimizations) window.refreshOptimizations(); break;
            case 'history': if (window.loadHistory) window.loadHistory(1); break;
        }
    };
})();