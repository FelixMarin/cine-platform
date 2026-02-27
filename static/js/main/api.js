// Depende de carousel.js

const CACHE_KEY = 'cine_movies_cache';
const CACHE_TIMESTAMP_KEY = 'cine_movies_timestamp';
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos en milisegundos

function loadContent(forceRefresh = false) {
    console.log('Cargando contenido...', forceRefresh ? '(forzando refresco)' : '');

    // Si se fuerza refresco, ignorar caché
    if (!forceRefresh) {
        // Por ahora, siempre invalidar caché para obtener datos frescos
        // Esto se puede cambiar después cuando todo funcione
        console.log('🗑️ Invalidando caché para obtener datos frescos...');
        localStorage.removeItem(CACHE_KEY);
        localStorage.removeItem(CACHE_TIMESTAMP_KEY);

        /*
        const cachedData = loadFromCache();
        if (cachedData) {
            console.log('📦 Usando datos cacheados');
            renderContent(cachedData);
            // Refrescar en segundo plano (opcional)
            refreshInBackground();
            return;
        }
        */
    }

    // No hay caché, expiró o se fuerza refresco → cargar del servidor
    fetchFromServer(forceRefresh);
}

function loadFromCache() {
    try {
        const cached = localStorage.getItem(CACHE_KEY);
        const timestamp = localStorage.getItem(CACHE_TIMESTAMP_KEY);

        if (!cached || !timestamp) return null;

        // Verificar si el caché ha expirado
        const now = Date.now();
        if (now - parseInt(timestamp) > CACHE_TTL) {
            console.log('🗑️ Caché expirado');
            localStorage.removeItem(CACHE_KEY);
            localStorage.removeItem(CACHE_TIMESTAMP_KEY);
            return null;
        }

        return JSON.parse(cached);
    } catch (e) {
        console.error('Error leyendo caché:', e);
        return null;
    }
}

function saveToCache(data) {
    try {
        // Guardar tal cual, sin modificar el orden
        localStorage.setItem(CACHE_KEY, JSON.stringify(data));
        localStorage.setItem(CACHE_TIMESTAMP_KEY, Date.now().toString());
        console.log('💾 Datos guardados en caché:', data);
        console.log('💾 Estructura de categorías en caché:', data && data.categorias ? `${data.categorias.length} categorías` : 'SIN categorías');
    } catch (e) {
        console.error('Error guardando en caché:', e);
    }
}

function fetchFromServer(forceRefresh = false) {
    console.log('🌐 Cargando del servidor...');

    // Construir URL con parámetro refresh si es necesario
    let url = "/api/movies";
    if (forceRefresh) {
        url += "?refresh=true";
        console.log('🔄 Forzando refresco en servidor');
    }

    fetch(url)
        .then(r => {
            if (!r.ok) {
                throw new Error(`Error HTTP: ${r.status}`);
            }
            return r.json();
        })
        .then(async data => {
            console.log('Datos recibidos:', data);

            // Guardar en caché
            saveToCache(data);

            // Renderizar
            await renderContent(data);
        })
        .catch(err => {
            console.error("Error cargando contenido:", err);
            document.getElementById('movies').innerHTML = '<div class="no-content-message">Error al cargar las películas</div>';
            document.getElementById('seriesContainer').innerHTML = '<div class="no-content-message">Error al cargar las series</div>';
        });
}

async function renderContent(data) {
    const startTime = performance.now();

    // === LOGS DE DEPURACIÓN ===
    console.log('📊 Datos recibidos en renderContent:', data);
    console.log('📊 Tipo de data:', typeof data);
    console.log('📊 ¿data.categorias existe?:', data && data.categorias !== undefined);
    console.log('📊 ¿data.categorias tiene contenido?:', data && data.categorias ? ` length=${data.categorias.length}` : 'undefined/null');
    console.log('📊 ¿data.series existe?:', data && data.series !== undefined);
    console.log('📊 ¿data.series tiene contenido?:', data && data.series ? ` keys=${Object.keys(data.series).length}` : 'undefined/null');
    // ==========================

    if (data.categorias) {
        console.log('📂 Renderizando películas por categoría...');
        await window.renderMoviesByCategory(data.categorias);
    } else {
        console.warn('⚠️ No hay categorías en los datos - mostrando mensaje');
        document.getElementById('moviesContainer').innerHTML = '<div class="no-content-message">No hay películas disponibles</div>';
    }

    if (data.series) {
        console.log('📺 Renderizando series...');
        await window.renderSeries(data.series);
    } else {
        console.warn('⚠️ No hay series en los datos - mostrando mensaje');
        document.getElementById('seriesContainer').innerHTML = '<div class="no-content-message">No hay series disponibles</div>';
    }

    const renderTime = performance.now() - startTime;
    console.log(`⏱️ Renderizado completado en ${renderTime.toFixed(2)}ms`);
}

function refreshInBackground() {
    // Refrescar en segundo plano después de 1 segundo
    setTimeout(() => {
        console.log('🔄 Refrescando caché en segundo plano...');
        fetch("/api/movies?refresh=true")
            .then(r => r.json())
            .then(data => {
                // Solo actualizar caché si los datos son diferentes
                const currentCache = localStorage.getItem(CACHE_KEY);
                if (currentCache !== JSON.stringify(data)) {
                    saveToCache(data);
                    console.log('✅ Caché actualizado con nuevos datos');
                } else {
                    console.log('📦 Caché ya está actualizado');
                }
            })
            .catch(err => console.error('Error refrescando caché:', err));
    }, 1000);
}

function refreshContent(forceReload = false) {
    console.log('🔄 Refrescando contenido...');

    // Invalidar caché del frontend
    localStorage.removeItem(CACHE_KEY);
    localStorage.removeItem(CACHE_TIMESTAMP_KEY);

    if (forceReload) {
        // Recargar la página completamente (útil si hay cambios estructurales)
        window.location.reload();
    } else {
        // Cargar desde servidor forzando refresco
        loadContent(true);
    }
}

function invalidateCache() {
    // Forzar invalidación del caché
    localStorage.removeItem(CACHE_KEY);
    localStorage.removeItem(CACHE_TIMESTAMP_KEY);
    console.log('🗑️ Caché invalidado manualmente');
}

// Nueva función: Precargar thumbnails en segundo plano
function preloadThumbnails(data) {
    if (!data || !data.categorias) return;

    const thumbnailsToPreload = [];

    // Recoplar URLs de thumbnails
    Object.values(data.categorias).forEach(categoria => {
        categoria.forEach(item => {
            if (item.thumbnail && item.thumbnail !== '/static/images/default.jpg') {
                thumbnailsToPreload.push(item.thumbnail);
            }
        });
    });

    // Precargar en segundo plano (solo los primeros 20)
    console.log(`🖼️ Precargando ${Math.min(thumbnailsToPreload.length, 20)} thumbnails...`);

    let loaded = 0;
    thumbnailsToPreload.slice(0, 20).forEach(url => {
        const img = new Image();
        img.onload = () => {
            loaded++;
            if (loaded === 20 || loaded === thumbnailsToPreload.length) {
                console.log(`✅ Precarga de thumbnails completada (${loaded})`);
            }
        };
        img.src = url;
    });
}

// Modificar renderContent para incluir precarga
const originalRenderContent = renderContent;
renderContent = async function (data) {
    await originalRenderContent(data);
    // Precargar thumbnails después de renderizar
    setTimeout(() => preloadThumbnails(data), 500);
};

// Exportar funciones
window.loadContent = loadContent;
window.refreshContent = refreshContent;
window.invalidateCache = invalidateCache;

console.log('✅ api.js cargado - loadContent disponible');