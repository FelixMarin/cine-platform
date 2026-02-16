function showTab(tabName) {
    if (event) event.preventDefault();

    document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('active'));

    if (tabName === 'movies') {
        const moviesTab = document.querySelector('.menu-item[onclick="showTab(\'movies\')"]');
        if (moviesTab) moviesTab.classList.add('active');
    } else {
        const seriesTab = document.querySelector('.menu-item[onclick="showTab(\'series\')"]');
        if (seriesTab) seriesTab.classList.add('active');
    }

    const moviesDiv = document.getElementById('movies');
    const seriesDiv = document.getElementById('series');

    if (moviesDiv && seriesDiv) {
        moviesDiv.style.display = tabName === 'movies' ? 'block' : 'none';
        seriesDiv.style.display = tabName === 'series' ? 'block' : 'none';
    }

    document.title = tabName === 'movies' ? 'Películas - Cine Platform' : 'Series - Cine Platform';

    if (window.innerWidth <= 768) {
        const menu = document.getElementById('sideMenu');
        if (menu && menu.classList.contains('open')) toggleMenu();
    }

    return false;
}

window.showTab = showTab;