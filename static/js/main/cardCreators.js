// Depende de categoryUtils.js

// Caché para thumbnails (24 horas)
const THUMBNAIL_CACHE_TTL = 24 * 60 * 60 * 1000; // 24 horas en ms

function createMovieCard(movie) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = movie.name || movie.title || 'Sin título';

    // Si es una película nueva, añadir clase especial
    if (movie.is_new) {
        card.classList.add("new-movie");
    }

    // Crear imagen con placeholder
    const img = document.createElement('img');
    img.className = 'movie-thumb';
    img.alt = title;
    img.src = '/static/images/default.jpg'; // Placeholder inicial
    img.dataset.movieTitle = title;
    if (movie.year) {
        img.dataset.movieYear = movie.year;
    }
    if (movie.filename) {
        img.dataset.movieFilename = movie.filename;
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
    if (movie.is_new) {
        const badge = document.createElement('span');
        badge.className = 'new-badge';

        // Texto dinámico según antigüedad
        if (movie.days_ago === 0) {
            badge.textContent = 'HOY';
            badge.classList.add('hoy');
        } else if (movie.days_ago === 1) {
            badge.textContent = 'AYER';
            badge.classList.add('ayer');
        } else if (movie.days_ago <= 7) {
            badge.textContent = `HACE ${movie.days_ago} DÍAS`;
            badge.classList.add('semana');
        } else {
            badge.textContent = 'NUEVO';
        }

        card.appendChild(badge);

        // Añadir fecha exacta como tooltip
        if (movie.date_added) {
            card.setAttribute('title', `Añadida: ${movie.date_added}`);
        }

        // Añadir indicador visual de novedad
        const newIndicator = document.createElement('div');
        newIndicator.className = 'new-indicator';
        card.appendChild(newIndicator);
    }

    const playPath = movie.id || movie.path || movie.file;
    card.onclick = () => window.playMovie(playPath);

    // Cargar thumbnail en segundo plano
    loadMovieThumbnail(img, title, movie.year, movie.filename);

    return card;
}

async function loadMovieThumbnail(imgElement, title, year, filename) {
    // Limpiar título
    const searchTitle = title.replace(/\s*\(?\d{4}\)?\s*/g, '').trim();
    const cacheKey = `thumb_${searchTitle}_${year || 'no-year'}`;

    // Intentar cargar de caché
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
        try {
            const cachedData = JSON.parse(cached);
            if (Date.now() - cachedData.timestamp < THUMBNAIL_CACHE_TTL) {
                console.log(`📦 Thumbnail en caché para: ${searchTitle}`);
                imgElement.src = cachedData.url;
                return;
            } else {
                localStorage.removeItem(cacheKey);
            }
        } catch (e) {
            localStorage.removeItem(cacheKey);
        }
    }

    try {
        // Construir URL base
        let url = `/api/movie-thumbnail?title=${encodeURIComponent(searchTitle)}`;
        if (year) url += `&year=${year}`;

        // Añadir filename SOLO si existe (para fallback local)
        if (filename) {
            url += `&filename=${encodeURIComponent(filename)}`;
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

        const data = await response.json();

        if (data.thumbnail) {
            // Guardar en caché
            localStorage.setItem(cacheKey, JSON.stringify({
                url: data.thumbnail,
                timestamp: Date.now()
            }));

            // Cargar imagen
            imgElement.src = data.thumbnail;
            console.log(`✅ Thumbnail cargado para: ${searchTitle}`);
        }
    } catch (error) {
        console.error('Error cargando thumbnail:', error);
    }
}

// Función para series (mantener igual, pero podemos mejorar)
async function createSerieCard(episodio) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = episodio.name || episodio.title || 'Sin título';

    // Extraer nombre de la serie
    let serieName = episodio.serie_name || title.replace(/[Tt]\d+[Cc]\d+/g, '').trim();

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

    const playPath = episodio.id || episodio.path || episodio.file;
    card.onclick = () => window.playMovie(playPath);

    // Cargar póster (pasando el filename para fallback local)
    loadSeriePoster(img, serieName, episodio.filename);

    return card;
}

async function loadSeriePoster(imgElement, serieName, firstEpisodeFilename) {
    const cacheKey = `serie_poster_${serieName.replace(/\s+/g, '_').toLowerCase()}`;

    // Intentar cargar de caché
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
        try {
            const cachedData = JSON.parse(cached);
            if (Date.now() - cachedData.timestamp < THUMBNAIL_CACHE_TTL) {
                console.log(`📦 Póster de serie en caché para: ${serieName}`);
                imgElement.src = cachedData.url;
                return;
            } else {
                localStorage.removeItem(cacheKey);
            }
        } catch (e) {
            localStorage.removeItem(cacheKey);
        }
    }

    try {
        // 1. Intentar con OMDB
        console.log(`🔍 Buscando póster para serie: "${serieName}"`);
        const response = await fetch(`/api/serie-poster?name=${encodeURIComponent(serieName)}`);

        if (response.ok) {
            const data = await response.json();
            if (data.poster) {
                localStorage.setItem(cacheKey, JSON.stringify({
                    url: data.poster,
                    timestamp: Date.now()
                }));
                imgElement.src = data.poster;
                console.log(`✅ Póster de serie cargado desde OMDB para: ${serieName}`);
                return;
            }
        }

        // 2. SIEMPRE intentar thumbnail local después de OMDB (incluso si falla)
        console.log(`📁 Intentando thumbnail local para serie: ${serieName}`);

        if (firstEpisodeFilename) {
            // Quitar extensión (ej: .mkv)
            const baseName = firstEpisodeFilename.replace(/\.[^/.]+$/, '');

            // === LOGS PARA DEPURACIÓN ===
            console.log(`📁 firstEpisodeFilename: ${firstEpisodeFilename}`);
            console.log(`📁 baseName generado: ${baseName}`);

            const localJpg = `/thumbnails/${baseName}.jpg`;
            const localWebp = `/thumbnails/${baseName}.webp`;

            console.log(`🖼️ Intentando thumbnail local JPG: ${localJpg}`);
            console.log(`🖼️ Intentando thumbnail local WEBP: ${localWebp}`);
            // === FIN LOGS ===

            // Guardar en caché
            localStorage.setItem(cacheKey, JSON.stringify({
                url: localJpg,
                timestamp: Date.now()
            }));

            imgElement.src = localJpg;
            console.log(`🖼️ Estableciendo src a: ${localJpg}`);
        } else {
            console.log(`❌ No hay firstEpisodeFilename para thumbnail local`);
        }

    } catch (error) {
        console.error(`❌ Error cargando póster de serie:`, error);
        if (firstEpisodeFilename) {
            const baseName = firstEpisodeFilename.replace(/\.[^/.]+$/, '');
            imgElement.src = `/thumbnails/${baseName}.jpg`;
        }
    }
}

// Función para limpiar caché antiguo (llamar al inicio)
function cleanThumbnailCache() {
    const now = Date.now();
    let removed = 0;

    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('thumb_')) {
            try {
                const data = JSON.parse(localStorage.getItem(key));
                if (now - data.timestamp > THUMBNAIL_CACHE_TTL) {
                    localStorage.removeItem(key);
                    removed++;
                }
            } catch (e) {
                // Si no se puede parsear, eliminar
                localStorage.removeItem(key);
                removed++;
            }
        }
    }

    if (removed > 0) {
        console.log(`🧹 Limpiados ${removed} thumbnails antiguos de caché`);
    }
}

// Función para limpiar el caché de thumbnails manualmente
function clearThumbnailCache() {
    let count = 0;
    for (let i = 0; i < localStorage.length; i++) {
        const key = localStorage.key(i);
        if (key && key.startsWith('thumb_')) {
            localStorage.removeItem(key);
            count++;
        }
    }
    console.log(`🧹 Caché de thumbnails limpiado: ${count} entradas eliminadas`);
    return count;
}

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


// Limpiar caché al inicio
cleanThumbnailCache();

// Exportar funciones
window.createMovieCard = createMovieCard;
window.createSerieCard = createSerieCard;
window.cleanThumbnailCache = cleanThumbnailCache;
window.clearThumbnailCache = clearThumbnailCache;