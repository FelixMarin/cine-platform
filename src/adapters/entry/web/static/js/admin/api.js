/**
 * Admin Panel - Stats API
 */

const ADMIN_API = {
    endpoints: {
        stats: '/api/admin/stats',
        users: '/api/admin/users',
        system: '/api/admin/system'
    }
};

function loadSystemStats() {
    showLoadingState();

    const timeout = setTimeout(() => {
        const mockStats = {
            movies: 24,
            series: 12,
            users: 8,
            storage: '156 GB',
            processed: 156
        };

        updateStatsDisplay(mockStats);
        hideLoadingState();
    }, 800);

    setLoadingTimeout(timeout);
}

function updateStatsDisplay(stats) {
    const statCards = document.querySelectorAll('.stat-card');

    if (statCards.length >= 4) {
        const moviesSeriesCount = (stats.movies || 0) + (stats.series || 0);
        statCards[0].querySelector('h3').textContent = moviesSeriesCount;
        statCards[1].querySelector('h3').textContent = stats.users || '0';
        statCards[2].querySelector('h3').textContent = stats.storage || '0 GB';
        statCards[3].querySelector('h3').textContent = stats.processed || '0';
    }

    setStatsData(stats);
}

function showLoadingState() {
    const statCards = document.querySelectorAll('.stat-card h3');
    statCards.forEach(card => {
        const originalContent = card.textContent;
        card.setAttribute('data-original', originalContent);
        card.innerHTML = '<div class="spinner" style="margin: 0 auto;"></div>';
        card.style.fontSize = '0';
    });
}

function hideLoadingState() {
    const timeout = getLoadingTimeout();
    if (timeout) {
        clearTimeout(timeout);
        setLoadingTimeout(null);
    }

    const statCards = document.querySelectorAll('.stat-card h3');
    statCards.forEach(card => {
        card.style.fontSize = '';
        const spinner = card.querySelector('.spinner');
        if (spinner) {
            spinner.remove();
        }
    });
}
