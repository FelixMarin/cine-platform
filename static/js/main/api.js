// Depende de carousel.js

// Caché en memoria para el contenido del catálogo (solo sesión actual)
let contentMemoryCache = {
    data: null,
    timestamp: 0
};
const CACHE_TTL = 5 * 60 * 1000; // 5 minutos en milisegundos

// Obtener referencia al CacheManager
function getCacheManager() {
    return window.CacheManager || null;
}

// Obtener referencia al CatalogService
function getCatalogService() {
    return window.CatalogService || null;
}

async function loadContent(forceRefresh = false) {
    console.log('Cargando contenido...', forceRefresh ? '(forzando refresco)' : '');

    const catalogService = getCatalogService();

    // Verificar caché en memoria primero
    const now = Date.now();
    if (!forceRefresh && contentMemoryCache.data && 
        (now - contentMemoryCache.timestamp) < CACHE_TTL) {
        console.debug('📦 Contenido desde caché en memoria');
        renderContent(contentMemoryCache.data);
        return;
    }

    // Obtener datos del catálogo de la base de datos
    if (catalogService) {
        try {
            console.debug('🔍 CatalogService: Buscando en BBDD...');
            const dbMovies = await catalogService.getMovies(100, 0);
            const dbSeries = await catalogService.getSeries(50, 0);

            if ((dbMovies.movies && dbMovies.movies.length > 0) || 
                (dbSeries.series && dbSeries.series.length > 0)) {
                console.debug(`✅ CatalogService: ${(dbMovies.movies?.length || 0) + (dbSeries.series?.length || 0)} items encontrados en BBDD`);
                
                // Transformar datos de BBDD al formato esperado
                const data = transformCatalogToApiFormat(dbMovies.movies || [], dbSeries.series || []);
                
                // Guardar en caché en memoria
                contentMemoryCache.data = data;
                contentMemoryCache.timestamp = now;
                
                renderContent(data);
                return;
            }
        } catch (e) {
            console.warn('⚠️ CatalogService: Error obteniendo datos de BBDD:', e);
        }
    }

    // Si no hay datos, cargar del servidor
    fetchFromServer(forceRefresh);
}

// Transformar datos del catálogo de BBDD al formato de la API
function transformCatalogToApiFormat(movies, series) {
    const categorias = {};
    const novedades = [];
    
    // Agrupar películas por categoría (basado en la ruta del archivo)
    movies.forEach(movie => {
        // Determinar categoría desde la ruta del archivo (igual que el backend)
        let categoria = 'Otros';
        const filePath = movie.file_path;
        if (filePath) {
            const parts = filePath.split('/');
            const mkvIndex = parts.indexOf('mkv');
            if (mkvIndex !== -1 && mkvIndex + 1 < parts.length) {
                categoria = parts[mkvIndex + 1];
            }
        }
        
        if (!categorias[categoria]) {
            categorias[categoria] = [];
        }
        // Calcular si es una película nueva (menos de 30 días desde created_at)
        const now = new Date();
        const createdAt = movie.created_at ? new Date(movie.created_at) : null;
        let days_ago = -1;
        let is_new = false;
        if (createdAt) {
            days_ago = Math.floor((now - createdAt) / (1000 * 60 * 60 * 24));
            is_new = days_ago <= 30;
        }
        
        const movieData = {
            id: movie.id,
            title: movie.title,
            year: movie.year,
            imdb_id: movie.imdb_id,
            poster: movie.poster_url,
            thumbnail: movie.poster_url,
            plot: movie.plot,
            rating: movie.imdb_rating,
            genre: movie.genre,
            type: 'movie',
            file_path: movie.file_path,
            is_new: is_new,
            days_ago: days_ago,
            date_added: movie.created_at
        };
        
        // Añadir a novedades si es nueva
        if (is_new) {
            novedades.push(movieData);
        }
        
        categorias[categoria].push(movieData);
    });

    // Ordenar novedades por fecha (más recientes primero)
    novedades.sort((a, b) => {
        if (!a.date_added || !b.date_added) return 0;
        return new Date(b.date_added) - new Date(a.date_added);
    });

    // Crear lista de categorías con Novedades primero
    const categoriasArray = [];
    
    // Primero, añadir Novedades si existe (limitado a 20)
    if (novedades.length > 0) {
        categoriasArray.push(["🆕 Novedades", novedades.slice(0, 20)]);
    }
    
    // Añadir el resto de categorías ordenadas alfabéticamente
    for (const cat of Object.keys(categorias).sort()) {
        categoriasArray.push([cat, categorias[cat]]);
    }

    // Agrupar series
    const seriesObj = {};
    series.forEach(serie => {
        // Calcular si es una serie nueva
        const now = new Date();
        const createdAt = serie.created_at ? new Date(serie.created_at) : null;
        let days_ago = -1;
        let is_new = false;
        if (createdAt) {
            days_ago = Math.floor((now - createdAt) / (1000 * 60 * 60 * 24));
            is_new = days_ago <= 30;
        }
        
        seriesObj[serie.title] = [{
            id: serie.id,
            name: serie.title,
            year: serie.year,
            imdb_id: serie.imdb_id,
            poster: serie.poster_url,
            thumbnail: serie.poster_url,
            plot: serie.plot,
            rating: serie.imdb_rating,
            genre: serie.genre,
            type: 'series',
            totalSeasons: serie.total_seasons,
            file_path: serie.file_path,
            is_new: is_new,
            days_ago: days_ago,
            date_added: serie.created_at
        }];
    });

    return {
        categorias: categoriasArray,
        series: seriesObj
    };
}

// Función para cargar desde el servidor
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

            // Guardar en caché en memoria
            contentMemoryCache.data = data;
            contentMemoryCache.timestamp = Date.now();

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
                // Solo actualizar caché en memoria si los datos son diferentes
                if (JSON.stringify(contentMemoryCache.data) !== JSON.stringify(data)) {
                    contentMemoryCache.data = data;
                    contentMemoryCache.timestamp = Date.now();
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

    // Invalidar caché en memoria
    contentMemoryCache.data = null;
    contentMemoryCache.timestamp = 0;

    // También invalidar en CatalogService
    const catalogService = getCatalogService();
    if (catalogService && catalogService.invalidateCache) {
        catalogService.invalidateCache();
    }

    if (forceReload) {
        // Recargar la página completamente (útil si hay cambios estructurales)
        window.location.reload();
    } else {
        // Cargar desde servidor forzando refresco
        loadContent(true);
    }
}

function invalidateCache() {
    // Invalidar caché en memoria
    contentMemoryCache.data = null;
    contentMemoryCache.timestamp = 0;

    // También invalidar en CacheManager si está disponible
    const cm = getCacheManager();
    if (cm) {
        cm.invalidateApiCache('/api/movies');
    }

    // Y en CatalogService
    const catalogService = getCatalogService();
    if (catalogService && catalogService.invalidateCache) {
        catalogService.invalidateCache();
    }

    console.log('🗑️ Caché invalidado manualmente (memoria + Cache API + CatalogService)');
}

// Nueva función: Precargar thumbnails en segundo plano usando CacheManager
async function preloadThumbnails(data) {
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

    // Usar CacheManager para precargar si está disponible
    const cm = getCacheManager();
    if (cm && thumbnailsToPreload.length > 0) {
        console.log(`🖼️ Precargando ${Math.min(thumbnailsToPreload.length, 20)} thumbnails con CacheManager...`);
        await cm.preloadImages(thumbnailsToPreload.slice(0, 20), 'thumbnail');
    } else {
        // Fallback al método original
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
}

// Modificar renderContent para incluir precarga
const originalRenderContent = renderContent;
renderContent = async function (data) {
    await originalRenderContent(data);
    // Precargar thumbnails después de renderizar (ahora es async)
    setTimeout(async () => {
        await preloadThumbnails(data);
    }, 500);
};

// Exportar funciones
window.loadContent = loadContent;
window.refreshContent = refreshContent;
window.invalidateCache = invalidateCache;

console.log('✅ api.js cargado - loadContent disponible');