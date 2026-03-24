// Cine Platform - Servicio de Catálogo con Base de Datos
// Elimina localStorage y usa caché en memoria (solo sesión actual)

// Función helper para añadir cache busting a URLs
function addCacheBuster(url) {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}_cb=${Date.now()}`;
}

const CatalogService = {
    // Caché en memoria (solo dura durante la sesión)
    _memoryCache: {
        movies: { data: null, timestamp: 0 },
        series: { data: null, timestamp: 0 },
        posters: new Map()  // imdbId -> blob URL
    },
    // TTL para caché en memoria: 5 minutos
    _CACHE_TTL: 5 * 60 * 1000,

    async searchOMDB(query, limit = 10) {
        const params = new URLSearchParams({ q: query, limit: limit.toString() });
        const response = await fetch(addCacheBuster(`/api/omdb/search?${params}`));
        if (!response.ok) throw new Error('Error en búsqueda OMDB');
        return response.json();
    },

    async lookupOMDB(imdbId, refresh = false) {
        const params = new URLSearchParams({ imdb_id: imdbId });
        if (refresh) params.append('refresh', 'true');
        const response = await fetch(addCacheBuster(`/api/omdb/lookup?${params}`));
        if (!response.ok) throw new Error('Error en lookup OMDB');
        return response.json();
    },

    async getPoster(imdbId) {
        // Verificar caché en memoria primero
        if (this._memoryCache.posters.has(imdbId)) {
            const cachedUrl = this._memoryCache.posters.get(imdbId);
            return cachedUrl;
        }

        const response = await fetch(addCacheBuster(`/api/omdb/poster/${imdbId}`));
        if (!response.ok) return null;
        const blob = await response.blob();
        const url = URL.createObjectURL(blob);

        // Guardar en caché en memoria
        this._memoryCache.posters.set(imdbId, url);

        return url;
    },

    async getMovies(limit = 100, offset = 0) {
        // Verificar caché en memoria primero
        const now = Date.now();
        if (this._memoryCache.movies.data && 
            (now - this._memoryCache.movies.timestamp) < this._CACHE_TTL) {
            return this._memoryCache.movies.data;
        }

        // Siempre consultar a la API (sin fallback a localStorage)
        const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
        const response = await fetch(addCacheBuster(`/api/catalog/movies?${params}`));
        if (!response.ok) {
            // Si la API falla, no usamos localStorage como fallback
            throw new Error('Error obteniendo películas');
        }
        const data = await response.json();

        // Guardar en caché en memoria
        this._memoryCache.movies.data = data;
        this._memoryCache.movies.timestamp = now;

        return data;
    },

    async getSeries(limit = 100, offset = 0) {
        // Verificar caché en memoria primero
        const now = Date.now();
        if (this._memoryCache.series.data && 
            (now - this._memoryCache.series.timestamp) < this._CACHE_TTL) {
            return this._memoryCache.series.data;
        }

        // Siempre consultar a la API (sin fallback a localStorage)
        const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
        
        // Usar el endpoint /api/catalog/series
        const response = await fetch(addCacheBuster(`/api/catalog/series?${params}`));
        
        if (!response.ok) {
            // Si la API falla, no usamos localStorage como fallback
            throw new Error('Error obteniendo series');
        }
        const data = await response.json();

        // Guardar en caché en memoria
        this._memoryCache.series.data = data;
        this._memoryCache.series.timestamp = now;

        return data;
    },

    async getCatalogEntry(id) {
        const response = await fetch(addCacheBuster(`/api/catalog/${id}`));
        if (!response.ok) throw new Error('Error obteniendo entrada');
        return response.json();
    },

    async createCatalogEntry(data) {
        const response = await fetch(addCacheBuster('/api/catalog'), {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Error creando entrada');
        return response.json();
    },

    async updateCatalogEntry(id, data) {
        const response = await fetch(`/api/catalog/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        if (!response.ok) throw new Error('Error actualizando entrada');
        return response.json();
    },

    async deleteCatalogEntry(id) {
        const response = await fetch(`/api/catalog/${id}`, { method: 'DELETE' });
        if (!response.ok) throw new Error('Error eliminando entrada');
        return response.json();
    },

    // Método para invalidar el caché (útil después de añadir/modificar contenido)
    invalidateCache() {
        this._memoryCache.movies.data = null;
        this._memoryCache.movies.timestamp = 0;
        this._memoryCache.series.data = null;
        this._memoryCache.series.timestamp = 0;
        this._memoryCache.posters.clear();
        
    }
};

// Limpiar localStorage legacy al iniciar (una sola vez)
(function cleanLegacyStorage() {
    const LEGACY_KEYS = [
        'cine_movies_cache',
        'cine_movies_timestamp',
        'cine_series_posts',
        'cine_serie_posters',
        'cime_movies_cache',
        'cime_series_posts'
    ];

    try {
        LEGACY_KEYS.forEach(key => {
            if (localStorage.getItem(key)) {
                localStorage.removeItem(key);
                
            }
        });

        // Limpiar también las claves de thumbnails legacy
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('thumb_') || key.startsWith('serie_poster_')) {
                localStorage.removeItem(key);
            }
        });
    } catch (e) {
        console.warn('⚠️ Error limpiando legacy localStorage:', e);
    }
})();

// Exportar
window.CatalogService = CatalogService;
