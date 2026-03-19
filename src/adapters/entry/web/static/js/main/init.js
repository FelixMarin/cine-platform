// Punto de entrada principal que carga todos los módulos
// y configura los event listeners iniciales

// El CacheManager se carga desde cache.js en el HTML

document.addEventListener('DOMContentLoaded', function () {
    

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
        console.warn('Esperando 1000ms para que se carguen los módulos...');

        // Reintentar después de 1000ms para dar tiempo a que los scripts con defer se carguen
        setTimeout(() => {
            // Verificar de nuevo
            const stillMissing = requiredFunctions.filter(fn => typeof window[fn] !== 'function');
            if (stillMissing.length > 0) {
                console.warn('⚠️ Funciones aún no disponibles:', stillMissing);
                console.warn('Esperando otros 1000ms...');
                // Un segundo intento
                setTimeout(() => {
                    initializeApp();
                }, 1000);
            } else {
                initializeApp();
            }
        }, 1000);
    } else {
        initializeApp();
    }
});

function initializeApp() {
    

    // Inicializar CacheManager
    if (window.CacheManager) {
        window.CacheManager.init();
    }

    // Inicializar migración del catálogo (si hay datos legacy)
    if (window.initCatalogMigration) {
        
        setTimeout(() => {
            window.initCatalogMigration().then(result => {
                if (result && result.success) {
                    
                } else if (result && result.migrated === 0) {
                    
                }
            }).catch(err => {
                console.warn('⚠️ CatalogService: Error en migración automática:', err);
            });
        }, 1000);
    }

    // Inicializar funciones del menú (verificar que existen)
    if (typeof window.setupClickOutside === 'function') {
        window.setupClickOutside();
    }
    if (typeof window.setupEmptyLinks === 'function') {
        window.setupEmptyLinks();
    }
    if (typeof window.setupResizeHandler === 'function') {
        window.setupResizeHandler();
    }
    if (typeof window.loadSavedPreferences === 'function') {
        window.loadSavedPreferences();
    }

    // Detectar si estamos en una ruta de serie (/series/...)
    const path = window.location.pathname;
    if (path.startsWith('/series/')) {
        
        // No mostrar pestaña de películas, esperar a que series_view maneje la ruta
        if (window.detectSeriesRoute) {
            setTimeout(() => {
                window.detectSeriesRoute();
            }, 100); // Pequeño delay para asegurar que el DOM esté listo
        }
    } else {
        // Ruta normal - mostrar pestañas
        // Verificar que showTab existe antes de llamar
        if (typeof window.showTab === 'function') {
            window.showTab('movies');
        }
        // Cargar contenido
        if (typeof window.loadContent === 'function') {
            window.loadContent();
        }
    }
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