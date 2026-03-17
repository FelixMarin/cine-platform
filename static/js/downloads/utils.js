/**
 * Utilidades del módulo de descargas
 */
(function() {
    'use strict';
    window.showNotification = function(t, m, type) {
        type = type || 'info';
        var c = document.getElementById('notifications');
        if (!c) return;
        var n = document.createElement('div');
        n.className = 'notification ' + type;
        n.innerHTML = '<div class="notification-title">' + t + '</div><div class="notification-message">' + m + '</div><button class="notification-close" onclick="this.parentElement.remove()">&times;</button>';
        c.appendChild(n);
        setTimeout(function() { n.remove(); }, 5000);
    };
    window.formatBytes = function(b) {
        if (b === 0) return '0 B';
        var k = 1024, s = ['B','KB','MB','GB','TB'], i = Math.floor(Math.log(b) / Math.log(k));
        return parseFloat((b / Math.pow(k, i)).toFixed(2)) + ' ' + s[i];
    };
    window.formatTime = function(s) {
        if (!s || s < 0) return '--';
        var h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = Math.floor(s % 60);
        if (h > 0) return h + 'h ' + m + 'm';
        if (m > 0) return m + 'm ' + sec + 's';
        return sec + 's';
    };
    window.formatDate = function(ts) {
        if (!ts) return '';
        var d = new Date(ts * 1000);
        return d.toLocaleDateString('es-ES', {day:'2-digit',month:'short',year:'numeric',hour:'2-digit',minute:'2-digit'});
    };
    window.getStatusClass = function(s) {
        var m = {'downloading':'downloading','seeding':'completed','completed':'completed','paused':'pending','stopped':'failed','failed':'failed','checking':'running','queued':'pending','0':'failed','1':'pending','2':'running','3':'pending','4':'downloading','5':'pending','6':'completed'};
        var str = typeof s === 'number' ? String(s) : s;
        return m[str ? str.toLowerCase() : ''] || 'pending';
    };
    window.updateHeaderStats = function() {
        var de = document.getElementById('active-downloads-count') || document.getElementById('stats-downloads');
        var oe = document.getElementById('active-optimizations-count') || document.getElementById('stats-optimizations');
        if (de) {
            var ac = window.state.activeDownloadsCount;
            if (ac === undefined || ac === null) ac = (window.state.downloads || []).filter(function(d) { return d.status === 4 || d.status === 6 || d.status === 'downloading' || d.status === 'seeding'; }).length;
            de.textContent = ac;
        }
        if (oe) oe.textContent = window.state.optimizations ? window.state.optimizations.length : 0;
    };
})();
