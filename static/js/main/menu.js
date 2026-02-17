let isMenuCollapsed = false;

function toggleMenu() {
    const menu = document.getElementById('sideMenu');
    const overlay = document.querySelector('.menu-overlay');

    if (menu && overlay) {
        menu.classList.toggle('open');
        overlay.classList.toggle('active');
    }
}

function toggleCollapse() {
    const menu = document.getElementById('sideMenu');
    const mainContent = document.getElementById('mainContent');
    const collapseBtn = document.querySelector('.menu-collapse-btn');

    if (!menu || !mainContent || !collapseBtn) return;

    isMenuCollapsed = !isMenuCollapsed;

    if (isMenuCollapsed) {
        menu.classList.add('collapsed');
        mainContent.classList.add('expanded');
        collapseBtn.innerHTML = '▶';
    } else {
        menu.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
        collapseBtn.innerHTML = '◀';
    }

    try {
        localStorage.setItem('menuCollapsed', isMenuCollapsed);
    } catch (e) {
        console.warn('No se pudo guardar la preferencia', e);
    }
}

function loadSavedPreferences() {
    try {
        const savedMenuState = localStorage.getItem('menuCollapsed');

        if (savedMenuState !== null && window.innerWidth > 768) {
            isMenuCollapsed = savedMenuState === 'true';

            const menu = document.getElementById('sideMenu');
            const mainContent = document.getElementById('mainContent');
            const collapseBtn = document.querySelector('.menu-collapse-btn');

            if (menu && mainContent && collapseBtn) {
                if (isMenuCollapsed) {
                    menu.classList.add('collapsed');
                    mainContent.classList.add('expanded');
                    collapseBtn.innerHTML = '▶';
                } else {
                    menu.classList.remove('collapsed');
                    mainContent.classList.remove('expanded');
                    collapseBtn.innerHTML = '◀';
                }
            }
        }
    } catch (e) {
        console.warn('No se pudieron cargar las preferencias', e);
    }
}

window.toggleMenu = toggleMenu;
window.toggleCollapse = toggleCollapse;
window.loadSavedPreferences = loadSavedPreferences;