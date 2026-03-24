// Archivo para manejar la vista de series con navegación Serie > Temporada > Episodio

// Función helper para añadir cache busting a URLs
function addCacheBuster(url) {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}_cb=${Date.now()}`;
}

// Caché para datos de series
let seriesDataCache = {
    series: [],
    seriesDetail: {}, // { serieId: { seasons: [], episodes: {} } }
    timestamp: 0
};
const SERIES_CACHE_TTL = 5 * 60 * 1000; // 5 minutos

// Forzar recarga de series (ignorar caché)
async function loadAllSeries(forceRefresh = false) {
    const now = Date.now();
    if (!forceRefresh && seriesDataCache.series.length > 0 && 
        (now - seriesDataCache.timestamp) < SERIES_CACHE_TTL) {
        console.debug('📺 Series desde caché:', seriesDataCache.series.length);
        return seriesDataCache.series;
    }

    try {
        // Usar el endpoint /api/catalog/series
        const response = await fetch(addCacheBuster('/api/catalog/series?limit=100'));
        
        if (!response.ok) {
            console.error('❌ Error响应:', response.status, response.statusText);
            return [];
        }
        
        const data = await response.json();
        
        
        seriesDataCache.series = data.series || [];
        seriesDataCache.timestamp = now;
        
        
        return seriesDataCache.series;
    } catch (error) {
        console.error('❌ Error cargando series:', error);
        return [];
    }
}

// Función para invalidar el caché de series (útil tras sincronización)
function invalidateSeriesCache() {
    seriesDataCache.series = [];
    seriesDataCache.timestamp = 0;
    seriesDataCache.seriesDetail = {};
    
}

// Exponer funciones globalmente
window.invalidateSeriesCache = invalidateSeriesCache;

// Cargar temporadas de una serie específica
async function loadSerieSeasons(serieId) {
    // Verificar caché
    if (seriesDataCache.seriesDetail[serieId] && 
        seriesDataCache.seriesDetail[serieId].seasons) {
        return seriesDataCache.seriesDetail[serieId].seasons;
    }

    try {
        const response = await fetch(`/api/${serieId}/seasons`);
        const data = await response.json();
        
        if (!seriesDataCache.seriesDetail[serieId]) {
            seriesDataCache.seriesDetail[serieId] = {};
        }
        seriesDataCache.seriesDetail[serieId].seasons = data.seasons || [];
        return seriesDataCache.seriesDetail[serieId].seasons;
    } catch (error) {
        console.error('Error cargando temporadas:', error);
        return [];
    }
}

// Cargar episodios de una temporada específica
async function loadSeasonEpisodes(serieId, season) {
    const cacheKey = `${serieId}_${season}`;
    
    // Verificar caché
    if (seriesDataCache.seriesDetail[serieId] && 
        seriesDataCache.seriesDetail[serieId].episodes &&
        seriesDataCache.seriesDetail[serieId].episodes[cacheKey]) {
        return seriesDataCache.seriesDetail[serieId].episodes[cacheKey];
    }

    try {
        const response = await fetch(`/api/${serieId}/season/${season}/episodes`);
        const data = await response.json();
        
        if (!seriesDataCache.seriesDetail[serieId]) {
            seriesDataCache.seriesDetail[serieId] = {};
        }
        if (!seriesDataCache.seriesDetail[serieId].episodes) {
            seriesDataCache.seriesDetail[serieId].episodes = {};
        }
        seriesDataCache.seriesDetail[serieId].episodes[cacheKey] = data.episodes || [];
        return seriesDataCache.seriesDetail[serieId].episodes[cacheKey];
    } catch (error) {
        console.error('Error cargando episodios:', error);
        return [];
    }
}

// Renderizar la vista de series (lista de tarjetas de series)
async function renderSeriesView() {
    const container = document.getElementById('seriesContainer');
    if (!container) return;

    container.innerHTML = '<div class="loading">Cargando series...</div>';
    
    // Invalidar caché para asegurar que se carguen las series
    invalidateSeriesCache();
    
    const series = await loadAllSeries(true);
    
    if (series.length === 0) {
        container.innerHTML = '<div class="empty-message">No hay series en el catálogo. Sincroniza el catálogo primero.</div>';
        return;
    }

    // Crear grid de tarjetas de series
    const grid = document.createElement('div');
    grid.className = 'series-grid';
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; padding: 20px 0;';

    for (const serie of series) {
        const card = await createSerieCardView(serie);
        grid.appendChild(card);
    }

    container.innerHTML = '';
    container.appendChild(grid);
}

// Crear tarjeta de serie para la vista
async function createSerieCardView(serie) {
    const card = document.createElement('div');
    card.className = 'serie-card';
    card.style.cssText = 'cursor: pointer; border-radius: 8px; overflow: hidden; background: var(--card-bg); transition: transform 0.2s;';
    
    card.onmouseover = () => card.style.transform = 'scale(1.05)';
    card.onmouseout = () => card.style.transform = 'scale(1)';
    
    // Imagen - priorizar poster_base64
    const img = document.createElement('img');
    img.style.cssText = 'width: 100%; height: 270px; object-fit: cover;';
    img.alt = serie.title || 'Serie';
    img.src = serie.poster_base64 || serie.poster_url || '/static/images/default.jpg';
    img.onerror = () => { img.src = '/static/images/default.jpg'; };
    
    // Título
    const title = document.createElement('div');
    title.style.cssText = 'padding: 10px; font-weight: bold; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
    title.textContent = serie.title || 'Sin título';
    
    // Info adicional
    const info = document.createElement('div');
    info.style.cssText = 'padding: 0 10px 10px; text-align: center; color: #888; font-size: 12px;';
    const seasons = serie.total_seasons || '?';
    info.textContent = `${seasons} temporada${seasons !== 1 ? 's' : ''}`;

    card.appendChild(img);
    card.appendChild(title);
    card.appendChild(info);

    // Click para mostrar temporadas
    card.onclick = () => showSerieDetail(serie.id, serie.title);

    return card;
}

// Mostrar detalle de una serie (temporadas)
async function showSerieDetail(serieId, serieTitleOrData) {
    const container = document.getElementById('seriesContainer');
    if (!container) return;

    // Determinar si el segundo argumento es un objeto (datos de la API) o un string (título)
    let serieTitle = '';
    let seasonsData = null;
    
    if (typeof serieTitleOrData === 'object' && serieTitleOrData !== null) {
        // Es un objeto con datos de la API
        serieTitle = serieTitleOrData.serie_title || '';
        seasonsData = serieTitleOrData.seasons || [];
    } else {
        // Es un string con el título
        serieTitle = serieTitleOrData || '';
    }
    
    // Breadcrumb
    const breadcrumb = document.createElement('div');
    breadcrumb.className = 'series-breadcrumb';
    breadcrumb.style.cssText = 'margin-bottom: 20px;';
    breadcrumb.innerHTML = `
        <a href="#" onclick="renderSeriesView(); return false;" style="color: var(--accent-color);">Series</a>
        <span style="margin: 0 10px;">›</span>
        <span>${serieTitle}</span>
        <button onclick="renderSeriesView()" style="margin-left: auto; padding: 8px 16px; background: var(--accent-color); color: white; border: none; border-radius: 4px; cursor: pointer;">Volver</button>
    `;

    container.innerHTML = '';
    container.appendChild(breadcrumb);

    // Cargar temporadas (desde datos pasados o desde la API)
    let seasons = seasonsData;
    if (!seasons) {
        seasons = await loadSerieSeasons(serieId);
    }
    
    if (seasons.length === 0) {
        container.innerHTML += '<div class="empty-message">No se encontraron temporadas.</div>';
        return;
    }

    // Grid de temporadas
    const grid = document.createElement('div');
    grid.className = 'seasons-grid';
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 20px; padding: 20px 0;';

    for (const season of seasons) {
        const seasonCard = createSeasonCard(serieId, serieTitle, season);
        grid.appendChild(seasonCard);
    }

    container.appendChild(grid);
}

// Crear tarjeta de temporada
function createSeasonCard(serieId, serieTitle, season) {
    const card = document.createElement('div');
    card.className = 'season-card';
    card.style.cssText = 'cursor: pointer; border-radius: 8px; overflow: hidden; background: var(--card-bg); transition: transform 0.2s; padding: 20px; text-align: center;';
    
    card.onmouseover = () => card.style.transform = 'scale(1.05)';
    card.onmouseout = () => card.style.transform = 'scale(1)';

    // Número de temporada
    const title = document.createElement('div');
    title.style.cssText = 'font-size: 24px; font-weight: bold; margin-bottom: 10px;';
    title.textContent = `Temporada ${season.season}`;

    // Carpeta
    const folder = document.createElement('div');
    folder.style.cssText = 'color: #888; font-size: 14px;';
    folder.textContent = season.folder;

    card.appendChild(title);
    card.appendChild(folder);

    // Click para mostrar episodios
    card.onclick = () => showSeasonEpisodes(serieId, serieTitle, season.season);

    return card;
}

// Mostrar episodios de una temporada
async function showSeasonEpisodes(serieId, serieTitle, seasonNum) {
    const container = document.getElementById('seriesContainer');
    if (!container) return;

    // Breadcrumb
    const breadcrumb = document.createElement('div');
    breadcrumb.className = 'series-breadcrumb';
    breadcrumb.style.cssText = 'margin-bottom: 20px;';
    breadcrumb.innerHTML = `
        <a href="#" onclick="renderSeriesView(); return false;" style="color: var(--accent-color);">Series</a>
        <span style="margin: 0 10px;">›</span>
        <a href="#" onclick="showSerieDetail(${serieId}, '${serieTitle}'); return false;" style="color: var(--accent-color);">${serieTitle}</a>
        <span style="margin: 0 10px;">›</span>
        <span>Temporada ${seasonNum}</span>
        <button onclick="showSerieDetail(${serieId}, '${serieTitle}')" style="margin-left: auto; padding: 8px 16px; background: var(--accent-color); color: white; border: none; border-radius: 4px; cursor: pointer;">Volver</button>
    `;

    container.innerHTML = '';
    container.appendChild(breadcrumb);

    // Cargar episodios
    const episodes = await loadSeasonEpisodes(serieId, seasonNum);
    
    if (episodes.length === 0) {
        container.innerHTML += '<div class="empty-message">No se encontraron episodios.</div>';
        return;
    }

    // Grid de episodios
    const grid = document.createElement('div');
    grid.className = 'episodes-grid';
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fill, minmax(250px, 1fr)); gap: 15px; padding: 20px 0;';

    for (const episode of episodes) {
        const episodeCard = createEpisodeCard(serieId, serieTitle, seasonNum, episode);
        grid.appendChild(episodeCard);
    }

    container.appendChild(grid);
}

// Crear tarjeta de episodio
function createEpisodeCard(serieId, serieTitle, seasonNum, episode) {
    const card = document.createElement('div');
    card.className = 'episode-card';
    card.style.cssText = 'cursor: pointer; border-radius: 8px; overflow: hidden; background: var(--card-bg); transition: transform 0.2s;';
    
    card.onmouseover = () => card.style.transform = 'scale(1.03)';
    card.onmouseout = () => card.style.transform = 'scale(1)';

    // Título del episodio
    const title = document.createElement('div');
    title.style.cssText = 'padding: 15px; font-weight: bold;';
    title.textContent = `E${episode.episode.toString().padStart(2, '0')}: ${serieTitle}`;

    // Info
    const info = document.createElement('div');
    info.style.cssText = 'padding: 0 15px 15px; color: #888; font-size: 12px;';
    info.textContent = episode.filename || '';

    card.appendChild(title);
    card.appendChild(info);

    // Click para reproducir
    card.onclick = () => {
        window.location.href = `/play/serie/${serieId}/${seasonNum}/${episode.episode}`;
    };

    return card;
}

// Inicializar vista de series cuando se cambia a la pestaña
function initSeriesView() {
    // Verificar si estamos en la pestaña de series
    const seriesTab = document.getElementById('series');
    if (seriesTab && seriesTab.style.display !== 'none') {
        renderSeriesView();
    }
}

// Detectar URL y cargar datos apropiados para series
function detectSeriesRoute() {
    const path = window.location.pathname;
    
    
    // Verificar si es una ruta de serie: /series/{id}/seasons o /series/{id}/season/{num}
    const seasonsMatch = path.match(/^\/series\/(\d+)\/seasons$/);
    const seasonMatch = path.match(/^\/series\/(\d+)\/season\/(\d+)$/);
    
    if (seasonsMatch) {
        const serieId = parseInt(seasonsMatch[1]);
        
        // Mostrar temporadas de la serie
        showSerieDetail(serieId, 'Cargando...');
        return true;
    } else if (seasonMatch) {
        const serieId = parseInt(seasonMatch[1]);
        const seasonNum = parseInt(seasonMatch[2]);
        
        // Mostrar episodios de la temporada
        showSeasonEpisodes(serieId, seasonNum, 'Cargando...');
        return true;
    }
    
    return false;
}

// Exponer funciones globalmente
window.renderSeriesView = renderSeriesView;
window.showSerieDetail = showSerieDetail;
window.showSeasonEpisodes = showSeasonEpisodes;
window.initSeriesView = initSeriesView;
window.detectSeriesRoute = detectSeriesRoute;


