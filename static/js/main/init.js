// Punto de entrada principal que carga todos los módulos
// y configura los event listeners iniciales

document.addEventListener('DOMContentLoaded', function () {
    console.log('✅ DOM Content Loaded - iniciando...');

    // Verificar que todas las funciones necesarias existen
    const requiredFunctions = [
        'setupClickOutside',
        'setupEmptyLinks',
        'setupResizeHandler',
        'loadSavedPreferences',
        'showTab',
        'loadContent'
    ];

    const missingFunctions = requiredFunctions.filter(fn => typeof window[fn] !== 'function');

    if (missingFunctions.length > 0) {
        console.warn('⚠️ Funciones no disponibles:', missingFunctions);
        console.warn('Esperando 500ms para que se carguen los módulos...');

        // Reintentar después de 500ms
        setTimeout(() => {
            initializeApp();
        }, 500);
    } else {
        initializeApp();
    }
});

function initializeApp() {
    console.log('🚀 Inicializando aplicación...');

    window.setupClickOutside();
    window.setupEmptyLinks();
    window.setupResizeHandler();
    window.loadSavedPreferences();

    window.showTab('movies');

    // Cargar contenido
    window.loadContent();
}

// Segundo event listener para asegurar que la pestaña activa sea 'movies'
document.addEventListener('DOMContentLoaded', function () {
    setTimeout(() => {
        const activeTab = document.querySelector('.menu-item.active');
        if (!activeTab || activeTab.getAttribute('data-tab') !== 'movies') {
            if (typeof window.showTab === 'function') {
                window.showTab('movies');
            }
        }
    }, 100); // Pequeño delay para asegurar que showTab está disponible
});

// Prevenir comportamiento predeterminado de enlaces vacíos
document.addEventListener('click', function (e) {
    if (e.target.tagName === 'A' && e.target.getAttribute('href') === '#') {
        e.preventDefault();
    }
});

// Permitir scroll horizontal con la rueda del ratón sobre los carruseles
document.addEventListener('DOMContentLoaded', function () {
    const carousels = document.querySelectorAll('.carousel-track');

    carousels.forEach(carousel => {
        carousel.addEventListener('wheel', function (e) {
            if (Math.abs(e.deltaX) < Math.abs(e.deltaY)) {
                e.preventDefault();
                this.scrollLeft += e.deltaY;
            }
        });
    });
});