function showTab(tabId) {
    // Oculta todas las pestañas
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.style.display = 'none');

    // Muestra la pestaña seleccionada
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.style.display = 'block';
    }

    // Actualiza la pestaña activa
    const tabLinks = document.querySelectorAll('.tab-link');
    tabLinks.forEach(link => link.classList.remove('active'));
    const targetLink = document.getElementById(tabId + 'Tab');
    if (targetLink) {
        targetLink.classList.add('active');
    }
}

function toggleSeries(header) {
    header.classList.toggle('active');
    const content = header.nextElementSibling;
    if (content.classList.contains('active')) {
        content.classList.remove('active');
        content.style.display = 'none';
    } else {
        content.classList.add('active');
        content.style.display = 'grid';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Set initial active tab and section
    showTab('movies');
});

// ===== VARIABLES GLOBALES =====
let isMenuCollapsed = false;

// ===== FUNCIONES DEL MENÚ =====

/**
 * Toggle del menú móvil (abrir/cerrar)
 */
function toggleMenu() {
    const menu = document.getElementById('sideMenu');
    const overlay = document.querySelector('.menu-overlay');

    if (menu && overlay) {
        menu.classList.toggle('open');
        overlay.classList.toggle('active');
    }
}

/**
 * Toggle del menú colapsable en PC
 */
function toggleCollapse() {
    const menu = document.getElementById('sideMenu');
    const mainContent = document.getElementById('mainContent');
    const collapseBtn = document.querySelector('.menu-collapse-btn');

    if (!menu || !mainContent || !collapseBtn) return;

    isMenuCollapsed = !isMenuCollapsed;

    if (isMenuCollapsed) {
        menu.classList.add('collapsed');
        mainContent.classList.add('expanded');
        collapseBtn.innerHTML = '▶'; // Flecha derecha (expandir)
    } else {
        menu.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
        collapseBtn.innerHTML = '◀'; // Flecha izquierda (colapsar)
    }

    // Guardar preferencia en localStorage
    try {
        localStorage.setItem('menuCollapsed', isMenuCollapsed);
    } catch (e) {
        console.warn('No se pudo guardar la preferencia en localStorage', e);
    }
}

// ===== FUNCIONES DE PESTAÑAS =====

/**
 * Mostrar una pestaña específica (películas o series)
 * @param {string} tabName - 'movies' o 'series'
 */
function showTab(tabName) {
    // Prevenir comportamiento por defecto si existe evento
    if (event) {
        event.preventDefault();
    }

    // Actualizar items del menú (quitar active de todos)
    document.querySelectorAll('.menu-item').forEach(item => {
        item.classList.remove('active');
    });

    // Activar el item correcto
    if (tabName === 'movies') {
        const moviesTab = document.querySelector('.menu-item[onclick="showTab(\'movies\')"]');
        if (moviesTab) moviesTab.classList.add('active');
    } else {
        const seriesTab = document.querySelector('.menu-item[onclick="showTab(\'series\')"]');
        if (seriesTab) seriesTab.classList.add('active');
    }

    // Mostrar/ocultar contenido
    const moviesDiv = document.getElementById('movies');
    const seriesDiv = document.getElementById('series');

    if (moviesDiv && seriesDiv) {
        moviesDiv.style.display = tabName === 'movies' ? 'block' : 'none';
        seriesDiv.style.display = tabName === 'series' ? 'block' : 'none';
    }

    // Actualizar título de la página
    document.title = tabName === 'movies' ? 'Películas - Cine Platform' : 'Series - Cine Platform';

    // Cerrar menú en móvil si está abierto
    if (window.innerWidth <= 768) {
        const menu = document.getElementById('sideMenu');
        if (menu && menu.classList.contains('open')) {
            toggleMenu();
        }
    }

    return false;
}

// ===== FUNCIONES PARA SERIES =====

/**
 * Toggle para secciones colapsables de series
 * @param {HTMLElement} header - Elemento del header clickeado
 */
function toggleSeries(header) {
    if (!header) return;

    // Toggle clase active en el header
    header.classList.toggle('active');

    // Buscar el contenido (siguiente elemento hermano)
    const content = header.nextElementSibling;

    if (content) {
        content.classList.toggle('active');

        // Ajustar display según la clase
        if (content.classList.contains('active')) {
            content.style.display = 'grid';
        } else {
            content.style.display = 'none';
        }
    }
}

// ===== FUNCIONES AUXILIARES =====

/**
 * Cerrar menú al hacer clic fuera en móvil
 */
function setupClickOutside() {
    const overlay = document.querySelector('.menu-overlay');
    if (overlay) {
        overlay.addEventListener('click', toggleMenu);
    }
}

/**
 * Prevenir navegación en enlaces vacíos
 */
function setupEmptyLinks() {
    document.querySelectorAll('a[href="#"]').forEach(link => {
        link.addEventListener('click', (e) => e.preventDefault());
    });
}

/**
 * Guardar el estado del menú al redimensionar
 */
function setupResizeHandler() {
    window.addEventListener('resize', function () {
        const menu = document.getElementById('sideMenu');
        const mainContent = document.getElementById('mainContent');

        if (!menu || !mainContent) return;

        if (window.innerWidth <= 768) {
            // En móvil: resetear clases de colapso
            menu.classList.remove('collapsed');
            mainContent.classList.remove('expanded');

            // Cerrar menú si está abierto
            if (menu.classList.contains('open')) {
                toggleMenu();
            }
        } else {
            // En PC: restaurar estado guardado
            const savedState = localStorage.getItem('menuCollapsed') === 'true';
            if (savedState !== isMenuCollapsed) {
                isMenuCollapsed = savedState;
                if (isMenuCollapsed) {
                    menu.classList.add('collapsed');
                    mainContent.classList.add('expanded');
                    const collapseBtn = document.querySelector('.menu-collapse-btn');
                    if (collapseBtn) collapseBtn.innerHTML = '▶';
                } else {
                    menu.classList.remove('collapsed');
                    mainContent.classList.remove('expanded');
                    const collapseBtn = document.querySelector('.menu-collapse-btn');
                    if (collapseBtn) collapseBtn.innerHTML = '◀';
                }
            }
        }
    });
}

/**
 * Cargar preferencias guardadas
 */
function loadSavedPreferences() {
    try {
        // Recuperar estado del menú
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

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function () {
    console.log('✅ Script cargado correctamente');

    // Configurar event listeners
    setupClickOutside();
    setupEmptyLinks();
    setupResizeHandler();

    // Cargar preferencias guardadas
    loadSavedPreferences();

    // Asegurar que la pestaña activa sea 'movies' al inicio
    showTab('movies');

    // Inicializar collapsibles de series (por defecto cerrados)
    document.querySelectorAll('.collapsible-content').forEach(content => {
        content.style.display = 'none';
    });
});

// ===== EXPORTAR FUNCIONES PARA USO GLOBAL =====
// (útil si usas módulos, aunque con funciones globales no es necesario)
window.toggleMenu = toggleMenu;
window.toggleCollapse = toggleCollapse;
window.showTab = showTab;
window.toggleSeries = toggleSeries;