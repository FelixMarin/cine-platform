// Depende de categoryUtils.js

// Caché para thumbnails - Ahora solo usa CacheManager (Cache API)
const THUMBNAIL_CACHE_TTL = 24 * 60 * 60 * 1000;

// Caché en memoria para thumbnails (complementa CacheManager)
const thumbnailMemoryCache = new Map();

// === LIMITADOR DE CONCURRENCIA PARA PETICIONES DE THUMBNAILS ===
const thumbnailQueue = [];
let activeThumbnailRequests = 0;
const MAX_CONCURRENT_THUMBNAIL_REQUESTS = 5;

// Procesar la cola de thumbnails
async function processThumbnailQueue() {
    if (activeThumbnailRequests >= MAX_CONCURRENT_THUMBNAIL_REQUESTS || thumbnailQueue.length === 0) {
        return;
    }
    
    const { imgElement, title, year, filename, imdbId, resolve } = thumbnailQueue.shift();
    activeThumbnailRequests++;
    
    try {
        await loadMovieThumbnailInternal(imgElement, title, year, filename, imdbId);
    } finally {
        activeThumbnailRequests--;
        resolve();
        // Procesar siguiente en la cola
        processThumbnailQueue();
    }
}

// Función wrapper que añade a la cola
function enqueueThumbnailLoad(imgElement, title, year, filename, imdbId) {
    return new Promise((resolve) => {
        thumbnailQueue.push({ imgElement, title, year, filename, imdbId, resolve });
        processThumbnailQueue();
    });
}

// Importar el gestor de caché dinámicamente
let cacheManager = null;
async function getCacheManager() {
    if (!cacheManager && window.CacheManager) {
        cacheManager = window.CacheManager;
    }
    return cacheManager;
}

// Obtener referencia al CatalogService
let catalogService = null;
async function getCatalogService() {
    if (!catalogService && window.CatalogService) {
        catalogService = window.CatalogService;
    }
    return catalogService;
}

function createMediaCard(media) {
    const card = document.createElement("div");
    card.classList.add("media-card");

    const title = media.name || media.title || 'Sin título';

    // Si es nuevo, añadir clase especial
    if (media.is_new) {
        card.classList.add("new-movie");
    }

    // Crear imagen con placeholder
    const img = document.createElement('img');
    img.className = 'movie-thumb';
    img.alt = title;
    img.src = '/static/images/default.jpg'; // Placeholder inicial
    img.dataset.movieTitle = title;
    if (media.year) {
        img.dataset.movieYear = media.year;
    }
    if (media.filename) {
        img.dataset.movieFilename = media.filename;
    }

    // Manejar error de carga
    img.onerror = function () {
        console.log(`🖼️ Error cargando imagen, usando default: ${this.src}`);
        this.src = '/static/images/default.jpg';
        this.onerror = null;
    };

    const titleDiv = document.createElement('div');
    titleDiv.className = 'movie-title';
    titleDiv.textContent = title;

    card.appendChild(img);
    card.appendChild(titleDiv);

    // Añadir badge de novedad si corresponde
    if (media.is_new) {
        const badge = document.createElement('span');
        badge.className = 'new-badge';

        // Texto dinámico según antigüedad
        if (media.days_ago === 0) {
            badge.textContent = 'HOY';
            badge.classList.add('hoy');
        } else if (media.days_ago === 1) {
            badge.textContent = 'AYER';
            badge.classList.add('ayer');
        } else if (media.days_ago <= 7) {
            badge.textContent = `HACE ${media.days_ago} DÍAS`;
            badge.classList.add('semana');
        } else {
            badge.textContent = 'NUEVO';
        }

        card.appendChild(badge);

        // Añadir fecha exacta como tooltip
        if (media.date_added) {
            card.setAttribute('title', `Añadida: ${media.date_added}`);
        }

        // Añadir indicador visual de novedad
        const newIndicator = document.createElement('div');
        newIndicator.className = 'new-indicator';
        card.appendChild(newIndicator);
    }

    // DECISIÓN CRÍTICA SEGÚN EL TIPO
    if (media.type === 'series') {
        // Si es serie, va a la vista de temporadas
        card.onclick = () => window.location = `/series/${media.id}`;
    } else {
        // Si es película (o cualquier otro), va al reproductor
        const playPath = media.file_path || media.path || media.id || media.file;
        card.onclick = () => window.playMovie(playPath);
    }

    // Cargar thumbnail en segundo plano - pasar imdb_id si está disponible
    loadMovieThumbnail(img, title, media.year, media.filename, media.imdb_id);

    return card;
}

async function loadMovieThumbnail(imgElement, title, year, filename, imdbId) {
    // Usar la cola para limitar concurrencia
    return enqueueThumbnailLoad(imgElement, title, year, filename, imdbId);
}

async function loadMovieThumbnailInternal(imgElement, title, year, filename, imdbId) {
    // Limpiar título: eliminar año, sufijos como -optimized, (2024), etc.
    let searchTitle = title;
    // Eliminar año entre paréntesis o al final
    searchTitle = searchTitle.replace(/\s*\(?\d{4}\)?\s*$/g, '');
    // Eliminar sufijos comunes
    searchTitle = searchTitle.replace(/[-_]?optimized/gi, '');
    searchTitle = searchTitle.replace(/[-_]?hd/gi, '');
    searchTitle = searchTitle.replace(/[-_]?bluray/gi, '');
    searchTitle = searchTitle.replace(/[-_]?webrip/gi, '');
    searchTitle = searchTitle.replace(/[-_]?web-dl/gi, '');
    // Eliminar cualquier patrón restante de (año)
    searchTitle = searchTitle.replace(/\s*\([^)]*\)\s*/g, ' ');
    // Limpiar espacios
    searchTitle = searchTitle.replace(/\s+/g, ' ').trim();

    const cacheKey = `thumb_${searchTitle}_${year || 'no-year'}`;

    // NUEVO: Intentar primero obtener póster desde la base de datos usando imdb_id
    if (imdbId) {
        try {
            const cs = await getCatalogService();
            if (cs) {
                const posterUrl = await cs.getPoster(imdbId);
                if (posterUrl) {
                    console.debug(`🖼️ CatalogService: Póster para ${imdbId} obtenido desde BBDD`);
                    imgElement.src = posterUrl;
                    return;
                } else {
                    console.debug(`⚠️ CatalogService: Póster no encontrado en BBDD para ${imdbId}, usando fallback`);
                }
            }
        } catch (e) {
            console.warn('⚠️ CatalogService: Error obteniendo póster de BBDD:', e);
        }
    }

    // Intentar primero con CacheManager (nueva implementación)
    const cm = await getCacheManager();

    try {
        // Construir URL base
        let url = `/api/movie-thumbnail?title=${encodeURIComponent(searchTitle)}`;
        if (year) url += `&year=${year}`;

        // Añadir filename SOLO si existe (para fallback local)
        if (filename) {
            url += `&filename=${encodeURIComponent(filename)}`;
        }

        // Si tenemos CacheManager, intentar obtener del caché
        if (cm) {
            const cachedUrl = await cm.getCachedImageUrl(url);
            if (cachedUrl !== url) {
                console.debug(`📦 Thumbnail desde Cache API para: ${searchTitle}`);
                imgElement.src = cachedUrl;
                return;
            }
        }

        // También verificar caché en memoria
        if (thumbnailMemoryCache.has(cacheKey)) {
            const cachedData = thumbnailMemoryCache.get(cacheKey);
            if (Date.now() - cachedData.timestamp < THUMBNAIL_CACHE_TTL) {
                console.debug(`📦 Thumbnail desde memoria para: ${searchTitle}`);
                imgElement.src = cachedData.url;
                return;
            } else {
                thumbnailMemoryCache.delete(cacheKey);
            }
        }

        console.log(`🔍 Solicitando thumbnail: ${url}`);
        const response = await fetch(url);

        if (!response.ok) {
            if (response.status === 404) {
                console.log(`ℹ️ No hay thumbnail para: ${searchTitle}`);
            } else {
                console.warn(`⚠️ Error ${response.status}`);
            }
            return;
        }

        // Verificar si la respuesta es una imagen o JSON
        const contentType = response.headers.get('content-type') || '';
        
        if (contentType.startsWith('image/')) {
            // La respuesta es una imagen directamente (desde BD u OMDB)
            const blob = await response.blob();
            const imageUrl = URL.createObjectURL(blob);
            
            // Guardar en caché en memoria
            thumbnailMemoryCache.set(cacheKey, {
                url: imageUrl,
                timestamp: Date.now()
            });
            
            imgElement.src = imageUrl;
            console.log(`✅ Thumbnail cargado (imagen directa) para: ${searchTitle}`);
            return;
        }

        // La respuesta es JSON (thumbnail local)
        const data = await response.json();

        if (data.thumbnail) {
            // Guardar en caché en memoria
            thumbnailMemoryCache.set(cacheKey, {
                url: data.thumbnail,
                timestamp: Date.now()
            });

            // Cargar imagen
            imgElement.src = data.thumbnail;
            console.log(`✅ Thumbnail cargado para: ${searchTitle}`);
        }
    } catch (error) {
        console.error('Error cargando thumbnail:', error);
    }
}

// Función para series (optimizada para una sola llamada por serie)
async function createSerieCard(episodio, preloadedPoster = null) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = episodio.name || episodio.title || 'Sin título';

    // Si es una serie nueva, añadir clase especial
    if (episodio.is_new) {
        card.classList.add("new-movie");
    }

    // Extraer nombre de la serie y limpiar sufijos
    let serieName = episodio.serie_name || title;
    // Limpiar nombre de serie: eliminar patrones de episodio y sufijos
    serieName = serieName.replace(/[Tt]\d+[Cc]\d+/g, '');  // T1C01
    serieName = serieName.replace(/[Ss]\d+[Ee]\d+/g, '');  // S01E01
    serieName = serieName.replace(/season\s*\d+/gi, '');    // Season 1
    serieName = serieName.replace(/episode\s*\d+/gi, '');   // Episode 1
    serieName = serieName.replace(/\d+x\d+/g, '');         // 1x01
    serieName = serieName.replace(/serie/gi, '');            // serie
    serieName = serieName.replace(/optimized/gi, '');        // optimized
    serieName = serieName.replace(/hd/gi, '');              // hd
    serieName = serieName.replace(/bluray/gi, '');           // bluray
    serieName = serieName.replace(/webrip/gi, '');           // webrip
    serieName = serieName.replace(/web-dl/gi, '');          // web-dl
    serieName = serieName.replace(/[-_(]/g, ' ');            // guiones y paréntesis
    serieName = serieName.replace(/\)/g, '');               // cerrar paréntesis
    serieName = serieName.replace(/\s+/g, ' ').trim();      // espacios múltiples

    // Crear imagen con placeholder
    const img = document.createElement('img');
    img.className = 'movie-thumb';
    img.alt = title;
    img.src = '/static/images/default.jpg';
    img.onerror = function () {
        this.src = '/static/images/default.jpg';
        this.onerror = null;
    };

    const titleDiv = document.createElement('div');
    titleDiv.className = 'movie-title';
    titleDiv.textContent = title;

    card.appendChild(img);
    card.appendChild(titleDiv);

    // Añadir badge de novedad para series si corresponde
    if (episodio.is_new) {
        const badge = document.createElement('span');
        badge.className = 'new-badge';

        // Texto dinámico según antigüedad
        if (episodio.days_ago === 0) {
            badge.textContent = 'HOY';
            badge.classList.add('hoy');
        } else if (episodio.days_ago === 1) {
            badge.textContent = 'AYER';
            badge.classList.add('ayer');
        } else if (episodio.days_ago <= 7) {
            badge.textContent = `HACE ${episodio.days_ago} DÍAS`;
            badge.classList.add('semana');
        } else {
            badge.textContent = 'NUEVO';
        }

        card.appendChild(badge);

        // Añadir indicador visual de novedad
        const newIndicator = document.createElement('div');
        newIndicator.className = 'new-indicator';
        card.appendChild(newIndicator);
    }

    const playPath = episodio.file_path || episodio.path || episodio.id || episodio.file;
    
    // DECISIÓN CRÍTICA SEGÚN EL TIPO
    if (episodio.type === 'series') {
        // Si es serie completa, ir a la vista de temporadas
        card.onclick = () => window.location = `/series/${episodio.id}`;
    } else {
        // Si es episodio individual, ir al reproductor
        card.onclick = () => window.playMovie(playPath);
    }

    // Si tenemos póster pre-cargado, usarlo directamente
    if (preloadedPoster) {
        img.src = preloadedPoster;
        console.log(`📺 Usando póster pre-cargado para: ${serieName}`);
    } else {
        // Cargar póster solo si no hay pre-carga
        loadSeriePoster(img, serieName, episodio.filename);
    }

    return card;
}

async function loadSeriePoster(imgElement, serieName, firstEpisodeFilename) {
    const cacheKey = `serie_poster_${serieName.replace(/\s+/g, '_').toLowerCase()}`;

    // Intentar primero con CacheManager
    const cm = await getCacheManager();

    // Construir URL de OMDB
    const omdbUrl = `/api/serie-poster?name=${encodeURIComponent(serieName)}`;

    // Si tenemos CacheManager, intentar obtener del caché
    if (cm) {
        try {
            const cachedUrl = await cm.getCachedImageUrl(omdbUrl);
            if (cachedUrl !== omdbUrl) {
                console.log(`📦 Póster desde Cache API para: ${serieName}`);
                imgElement.src = cachedUrl;
                return;
            }
        } catch (e) {
            // Continuar con otras opciones
        }
    }

    // Verificar caché en memoria
    const memoryCached = thumbnailMemoryCache.get(cacheKey);
    if (memoryCached && (Date.now() - memoryCached.timestamp) < THUMBNAIL_CACHE_TTL) {
        console.log(`📦 Póster de serie en memoria para: ${serieName}`);
        imgElement.src = memoryCached.url;
        return;
    }

    try {
        // 1. Intentar con OMDB
        console.log(`🔍 Buscando póster para serie: "${serieName}"`);
        const response = await fetch(`/api/serie-poster?name=${encodeURIComponent(serieName)}`);

        if (response.ok) {
            const data = await response.json();
            if (data.poster) {
                // Guardar en caché en memoria
                thumbnailMemoryCache.set(cacheKey, {
                    url: data.poster,
                    timestamp: Date.now()
                });
                imgElement.src = data.poster;
                console.log(`✅ Póster de serie cargado desde OMDB para: ${serieName}`);
                return;
            }
        }

        // 2. SIEMPRE intentar thumbnail local después de OMDB (incluso si falla)
        console.log(`📁 Intentando thumbnail local para serie: ${serieName}`);

        if (firstEpisodeFilename) {
            // Quitar extensión y limpiar sufijos (ej: .mkv)
            let baseName = firstEpisodeFilename.replace(/\.[^/.]+$/, '');
            // Limpiar sufijos del filename
            baseName = baseName.replace(/T\d+C\d+/gi, '');
            baseName = baseName.replace(/S\d+E\d+/gi, '');
            baseName = baseName.replace(/serie/gi, '');
            baseName = baseName.replace(/optimized/gi, '');
            baseName = baseName.replace(/hd/gi, '');
            baseName = baseName.replace(/bluray/gi, '');
            baseName = baseName.replace(/webrip/gi, '');
            baseName = baseName.replace(/web-dl/gi, '');
            baseName = baseName.replace(/[-_]/g, ' ');
            baseName = baseName.replace(/\s+/g, ' ').trim();

            // === LOGS PARA DEPURACIÓN ===
            console.log(`📁 firstEpisodeFilename: ${firstEpisodeFilename}`);
            console.log(`📁 baseName generado: ${baseName}`);

            const localJpg = `/thumbnails/${baseName}.jpg`;
            const localWebp = `/thumbnails/${baseName}.webp`;

            console.log(`🖼️ Intentando thumbnail local JPG: ${localJpg}`);
            console.log(`🖼️ Intentando thumbnail local WEBP: ${localWebp}`);
            // === FIN LOGS ===

            // Guardar en caché en memoria
            thumbnailMemoryCache.set(cacheKey, {
                url: localJpg,
                timestamp: Date.now()
            });

            imgElement.src = localJpg;
            console.log(`🖼️ Estableciendo src a: ${localJpg}`);
        } else {
            console.log(`❌ No hay firstEpisodeFilename para thumbnail local`);
        }

    } catch (error) {
        console.error(`❌ Error cargando póster de serie:`, error);
        if (firstEpisodeFilename) {
            // Limpiar sufijos del filename
            let baseName = firstEpisodeFilename.replace(/\.[^/.]+$/, '');
            baseName = baseName.replace(/T\d+C\d+/gi, '');
            baseName = baseName.replace(/S\d+E\d+/gi, '');
            baseName = baseName.replace(/serie/gi, '');
            baseName = baseName.replace(/optimized/gi, '');
            baseName = baseName.replace(/hd/gi, '');
            baseName = baseName.replace(/bluray/gi, '');
            baseName = baseName.replace(/webrip/gi, '');
            baseName = baseName.replace(/web-dl/gi, '');
            baseName = baseName.replace(/[-_]/g, ' ');
            baseName = baseName.replace(/\s+/g, ' ').trim();
            imgElement.src = `/thumbnails/${baseName}.jpg`;
        }
    }
}

// Función para limpiar caché de thumbnails en memoria (para uso manual si es necesario)
function clearThumbnailMemoryCache() {
    thumbnailMemoryCache.clear();
    console.log('🧹 Caché de thumbnails en memoria limpiado');
}

// Exponer función para uso externo
window.clearThumbnailMemoryCache = clearThumbnailMemoryCache;

// CSS para los placeholders y animaciones
const style = document.createElement('style');
style.textContent = `
    /* ===== NOVEDADES ===== */
    .movie-card {
        position: relative;
        overflow: visible;
    }

    .movie-thumb {
        width: 100%;
        height: 240px;
        object-fit: cover;
        background: linear-gradient(110deg, #2a2a2a 8%, #3a3a3a 18%, #2a2a2a 33%);
        background-size: 200% 100%;
        animation: shimmer 1.5s infinite;
        transition: opacity 0.3s ease;
    }

    .movie-thumb[src*="placeholder"] {
        opacity: 0.7;
    }

    .movie-thumb[src*="default.jpg"] {
        animation: none;
        background: #2a2a2a;
    }

    @keyframes shimmer {
        0% { background-position: 200% 0; }
        100% { background-position: -200% 0; }
    }

    .new-badge {
        position: absolute;
        top: -8px;
        right: -8px;
        background: linear-gradient(135deg, var(--accent-color), #ff4d4d);
        color: white;
        font-size: 0.7rem;
        font-weight: bold;
        padding: 4px 8px;
        border-radius: 20px;
        z-index: 10;
        box-shadow: 0 4px 10px rgba(229, 9, 20, 0.5);
        animation: pulse 2s infinite;
        text-transform: uppercase;
        letter-spacing: 0.5px;
        white-space: nowrap;
    }

    .new-badge.hoy {
        background: linear-gradient(135deg, #ff6b6b, var(--accent-color));
        animation: intense-pulse 1s infinite;
        font-weight: 800;
    }

    .new-badge.ayer {
        background: linear-gradient(135deg, #ff8a8a, var(--accent-color));
        animation: pulse 1.5s infinite;
    }

    .new-badge.semana {
        background: linear-gradient(135deg, var(--accent-color), #ffaa00);
        animation: soft-pulse 3s infinite;
    }

    .movie-card.new-movie {
        border: 2px solid var(--accent-color);
        box-shadow: 0 0 15px rgba(229, 9, 20, 0.3);
        transition: all 0.3s ease;
    }

    .movie-card.new-movie:hover {
        transform: translateY(-8px);
        box-shadow: 0 0 25px rgba(229, 9, 20, 0.5);
        border-color: var(--accent-hover);
    }

    .new-indicator {
        position: absolute;
        top: 0;
        left: 0;
        width: 4px;
        height: 100%;
        background: linear-gradient(to bottom, var(--accent-color), #ff8a8a);
        border-radius: 4px 0 0 4px;
        opacity: 0.8;
    }

    @keyframes pulse {
        0% { transform: scale(1); box-shadow: 0 4px 10px rgba(229, 9, 20, 0.5); }
        50% { transform: scale(1.05); box-shadow: 0 4px 15px rgba(229, 9, 20, 0.7); }
        100% { transform: scale(1); box-shadow: 0 4px 10px rgba(229, 9, 20, 0.5); }
    }

    @keyframes intense-pulse {
        0% { transform: scale(1); box-shadow: 0 4px 15px rgba(229, 9, 20, 0.7); }
        50% { transform: scale(1.1); box-shadow: 0 4px 25px rgba(229, 9, 20, 0.9); }
        100% { transform: scale(1); box-shadow: 0 4px 15px rgba(229, 9, 20, 0.7); }
    }

    @keyframes soft-pulse {
        0% { transform: scale(1); opacity: 0.9; }
        50% { transform: scale(1.03); opacity: 1; }
        100% { transform: scale(1); opacity: 0.9; }
    }

    /* Tooltip personalizado */
    .movie-card[title] {
        position: relative;
        cursor: pointer;
    }

    .movie-card[title]:hover::after {
        content: attr(title);
        position: absolute;
        bottom: 100%;
        left: 50%;
        transform: translateX(-50%);
        background: rgba(0, 0, 0, 0.8);
        color: white;
        padding: 4px 8px;
        border-radius: 4px;
        font-size: 0.7rem;
        white-space: nowrap;
        z-index: 20;
        pointer-events: none;
        margin-bottom: 5px;
    }
`;

// Añadir el estilo al documento si no existe
if (!document.getElementById('movie-card-styles')) {
    style.id = 'movie-card-styles';
    document.head.appendChild(style);
}

// Exportar funciones
window.createMovieCard = createMovieCard;
window.createSerieCard = createSerieCard;
window.createMediaCard = createMediaCard;