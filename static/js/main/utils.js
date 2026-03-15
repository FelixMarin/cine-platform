function playMovie(path) {
    if (!path) {
        console.error('Ruta de reproducción no válida');
        return;
    }
    
    // Si es un ID de película (formato mov_xxxx), usar ruta específica
    if (path.startsWith('mov_') || path.startsWith('ser_')) {
        window.location.href = `/play/id/${path}`;
        return;
    }
    
    // Si es una ruta absoluta (ej: /mnt/DATA_2TB/audiovisual/mkv/action/pelicula.mkv)
    // convertir a ruta relativa (mkv/action/pelicula.mkv)
    let relativePath = path;
    const commonPrefixes = [
        '/mnt/DATA_2TB/audiovisual/',
        '/mnt/servidor/Data2TB/audiovisual/',
        '/mnt/DATA_2TB/',
    ];
    
    for (const prefix of commonPrefixes) {
        if (path.startsWith(prefix)) {
            relativePath = path.substring(prefix.length);
            console.log('🎬 Convertida ruta absoluta a relativa:', path, '->', relativePath);
            break;
        }
    }
    
    // Es una ruta relativa, usar ruta original
    window.location.href = `/play/${relativePath}`;
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