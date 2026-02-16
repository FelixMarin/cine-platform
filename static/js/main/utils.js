function playMovie(path) {
    if (!path) {
        console.error('Ruta de reproducción no válida');
        return;
    }
    window.location.href = `/play/${path}`;
}

function setupClickOutside() {
    const overlay = document.querySelector('.menu-overlay');
    if (overlay) overlay.addEventListener('click', toggleMenu);
}

function setupEmptyLinks() {
    document.querySelectorAll('a[href="#"]').forEach(link => {
        link.addEventListener('click', e => e.preventDefault());
    });
}

function setupResizeHandler() {
    window.addEventListener('resize', function () {
        const menu = document.getElementById('sideMenu');
        const mainContent = document.getElementById('mainContent');

        if (!menu || !mainContent) return;

        if (window.innerWidth <= 768) {
            menu.classList.remove('collapsed');
            mainContent.classList.remove('expanded');
            if (menu.classList.contains('open')) toggleMenu();
        } else {
            const savedState = localStorage.getItem('menuCollapsed') === 'true';
            if (savedState !== isMenuCollapsed) {
                isMenuCollapsed = savedState;
                if (isMenuCollapsed) {
                    menu.classList.add('collapsed');
                    mainContent.classList.add('expanded');
                } else {
                    menu.classList.remove('collapsed');
                    mainContent.classList.remove('expanded');
                }
            }
        }
    });
}

window.playMovie = playMovie;
window.setupClickOutside = setupClickOutside;
window.setupEmptyLinks = setupEmptyLinks;
window.setupResizeHandler = setupResizeHandler;