// Cine Platform - Servicio de Catálogo con Base de Datos
// Reemplaza el sistema de localStorage con llamadas a la API

const CatalogService = {
    // Keys de localStorage legacy
    LEGACY_KEYS: {
        MOVIES_CACHE: 'cine_movies_cache',
        MOVIES_TIMESTAMP: 'cine_movies_timestamp',
        SERIES_POSTS: 'cine_series_posts',
    },

    async searchOMDB(query, limit = 10) {
        const params = new URLSearchParams({ q: query, limit: limit.toString() });
        const response = await fetch(`/api/omdb/search?${params}`);
        if (!response.ok) throw new Error('Error en búsqueda OMDB');
        return response.json();
    },

    async lookupOMDB(imdbId, refresh = false) {
        const params = new URLSearchParams({ imdb_id: imdbId });
        if (refresh) params.append('refresh', 'true');
        const response = await fetch(`/api/omdb/lookup?${params}`);
        if (!response.ok) throw new Error('Error en lookup OMDB');
        return response.json();
    },

    async getPoster(imdbId) {
        const response = await fetch(`/api/omdb/poster/${imdbId}`);
        if (!response.ok) return null;
        const blob = await response.blob();
        return URL.createObjectURL(blob);
    },

    async getMovies(limit = 100, offset = 0) {
        const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
        const response = await fetch(`/api/catalog/movies?${params}`);
        if (!response.ok) throw new Error('Error obteniendo películas');
        return response.json();
    },

    async getSeries(limit = 100, offset = 0) {
        const params = new URLSearchParams({ limit: limit.toString(), offset: offset.toString() });
        const response = await fetch(`/api/catalog/series?${params}`);
        if (!response.ok) throw new Error('Error obteniendo series');
        return response.json();
    },

    async getCatalogEntry(id) {
        const response = await fetch(`/api/catalog/${id}`);
        if (!response.ok) throw new Error('Error obteniendo entrada');
        return response.json();
    },

    async createCatalogEntry(data) {
        const response = await fetch('/api/catalog', {
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

    // Migración desde localStorage
    getLegacyData() {
        const data = {
            movies_cache: [],
            series_posts: {}
        };

        try {
            const moviesCache = localStorage.getItem(this.LEGACY_KEYS.MOVIES_CACHE);
            if (moviesCache) {
                data.movies_cache = JSON.parse(moviesCache);
            }

            const seriesPosts = localStorage.getItem(this.LEGACY_KEYS.SERIES_POSTS);
            if (seriesPosts) {
                data.series_posts = JSON.parse(seriesPosts);
            }
        } catch (e) {
            console.error('Error leyendo localStorage legacy:', e);
        }

        return data;
    },

    async migrateFromLocalStorage() {
        const legacyData = this.getLegacyData();
        
        if (!legacyData.movies_cache.length && !Object.keys(legacyData.series_posts).length) {
            console.log('No hay datos legacy para migrar');
            return { success: true, migrated: 0 };
        }

        console.log('Iniciando migración desde localStorage...', {
            movies: legacyData.movies_cache.length,
            series: Object.keys(legacyData.series_posts).length
        });

        try {
            const response = await fetch('/api/migrate/localstorage', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(legacyData)
            });
            
            if (!response.ok) throw new Error('Error en migración');
            
            const result = await response.json();
            console.log('Migración completada:', result);
            return result;
        } catch (e) {
            console.error('Error en migración:', e);
            throw e;
        }
    },

    hasLegacyData() {
        return localStorage.getItem(this.LEGACY_KEYS.MOVIES_CACHE) || 
               localStorage.getItem(this.LEGACY_KEYS.SERIES_POSTS);
    },

    clearLegacyCache() {
        localStorage.removeItem(this.LEGACY_KEYS.MOVIES_CACHE);
        localStorage.removeItem(this.LEGACY_KEYS.MOVIES_TIMESTAMP);
        localStorage.removeItem(this.LEGACY_KEYS.SERIES_POSTS);
        
        // Limpiar también las claves de thumbnails
        Object.keys(localStorage).forEach(key => {
            if (key.startsWith('thumb_')) {
                localStorage.removeItem(key);
            }
        });
        
        console.log('Legacy cache limpiado');
    }
};

// Auto-migración al cargar la página
async function initCatalogMigration() {
    if (!CatalogService.hasLegacyData()) {
        console.log('No hay datos legacy para migrar');
        return;
    }

    console.log('Datos legacy detectados, iniciando migración...');
    
    try {
        const result = await CatalogService.migrateFromLocalStorage();
        
        if (result.success) {
            // Solo limpiar después de una migración exitosa
            const confirmClear = confirm(
                `Migración completada: ${result.result.omdb_entries} entradas OMDB, ${result.result.local_content} contenido local.\n\n¿Deseas limpiar los datos antiguos de localStorage?`
            );
            
            if (confirmClear) {
                CatalogService.clearLegacyCache();
            }
        }
    } catch (e) {
        console.error('Error en migración automática:', e);
    }
}

// Exportar
window.CatalogService = CatalogService;
window.initCatalogMigration = initCatalogMigration;
