// Punto de entrada principal que carga todos los módulos
// y configura los event listeners iniciales

// El CacheManager se carga desde cache.js en el HTML

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

    // Inicializar CacheManager
    if (window.CacheManager) {
        window.CacheManager.init();
    }

    // Inicializar migración del catálogo (si hay datos legacy)
    if (window.initCatalogMigration) {
        console.log('📦 CatalogService: Iniciando migración de localStorage...');
        setTimeout(() => {
            window.initCatalogMigration().then(result => {
                if (result && result.success) {
                    console.log(`✅ CatalogService: Migración completada - ${result.result?.omdb_entries || 0} entradas OMDB, ${result.result?.local_content || 0} contenido local`);
                } else if (result && result.migrated === 0) {
                    console.log('📦 CatalogService: No hay datos legacy para migrar');
                }
            }).catch(err => {
                console.warn('⚠️ CatalogService: Error en migración automática:', err);
            });
        }, 1000);
    }

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