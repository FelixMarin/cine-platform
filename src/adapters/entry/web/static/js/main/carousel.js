// Caché de pósters de series (en memoria - solo sesión actual)
let seriePosterCache = {};

// Función para limpiar pósters en memoria (para uso manual si es necesario)
function clearSeriePosterCache() {
    seriePosterCache = {};
    
}

window.clearSeriePosterCache = clearSeriePosterCache;

// Función para desplazar el carrusel
function scrollCarousel(button, direction) {
    const carouselContainer = button.closest('.carousel-container');
    const track = carouselContainer.querySelector('.carousel-track');

    if (!track) return;

    const scrollAmount = 400;

    if (direction === 'prev') {
        track.scrollBy({
            left: -scrollAmount,
            behavior: 'smooth'
        });
    } else {
        track.scrollBy({
            left: scrollAmount,
            behavior: 'smooth'
        });
    }
}

// Función para renderizar películas en carruseles
async function renderMoviesByCategory(categoriasLista) {
    const moviesDiv = document.getElementById("moviesContainer");
    if (!moviesDiv) {
        console.error("No se encontró el contenedor de películas");
        return;
    }

    moviesDiv.innerHTML = "";

    if (!categoriasLista || categoriasLista.length === 0) {
        moviesDiv.innerHTML = '<div class="no-content-message">No hay películas disponibles</div>';
        return;
    }

    

    for (const [categoria, peliculas] of categoriasLista) {
        if (!peliculas || peliculas.length === 0) continue;

        const section = document.createElement("div");
        section.classList.add("category-section");

        const header = document.createElement("div");
        header.classList.add("category-header");
        header.innerHTML = `<h3 class="category-title">${window.formatCategoryName(categoria)}</h3>`;

        const carouselContainer = document.createElement("div");
        carouselContainer.classList.add("carousel-container");

        const prevBtn = document.createElement("button");
        prevBtn.classList.add("carousel-btn", "prev");
        prevBtn.innerHTML = "❮";
        prevBtn.setAttribute("aria-label", "Anterior");
        prevBtn.onclick = (e) => {
            e.stopPropagation();
            scrollCarousel(prevBtn, 'prev');
        };

        const nextBtn = document.createElement("button");
        nextBtn.classList.add("carousel-btn", "next");
        nextBtn.innerHTML = "❯";
        nextBtn.setAttribute("aria-label", "Siguiente");
        nextBtn.onclick = (e) => {
            e.stopPropagation();
            scrollCarousel(nextBtn, 'next');
        };

        const track = document.createElement("div");
        track.classList.add("carousel-track");
        track.id = `carousel-${categoria.replace(/\s+/g, '-')}`;

        // Crear todas las tarjetas de forma asíncrona
        const cardPromises = peliculas.map(movie => window.createMediaCard(movie));
        const cards = await Promise.all(cardPromises);

        cards.forEach(card => {
            const item = document.createElement("div");
            item.classList.add("carousel-item");
            item.appendChild(card);
            track.appendChild(item);
        });

        carouselContainer.appendChild(prevBtn);
        carouselContainer.appendChild(track);
        carouselContainer.appendChild(nextBtn);

        section.appendChild(header);
        section.appendChild(carouselContainer);
        moviesDiv.appendChild(section);
    }
}

// Función para limpiar nombre de serie
function cleanSerieName(name) {
    let cleaned = name;
    cleaned = cleaned.replace(/[Tt]\d+[Cc]\d+/g, '');  // T1C01
    cleaned = cleaned.replace(/[Ss]\d+[Ee]\d+/g, '');  // S01E01
    cleaned = cleaned.replace(/season\s*\d+/gi, '');    // Season 1
    cleaned = cleaned.replace(/episode\s*\d+/gi, ''); // Episode 1
    cleaned = cleaned.replace(/\d+x\d+/g, '');         // 1x01
    cleaned = cleaned.replace(/serie/gi, '');           // serie
    cleaned = cleaned.replace(/optimized/gi, '');       // optimized
    cleaned = cleaned.replace(/hd/gi, '');              // hd
    cleaned = cleaned.replace(/bluray/gi, '');          // bluray
    cleaned = cleaned.replace(/webrip/gi, '');          // webrip
    cleaned = cleaned.replace(/web-dl/gi, '');          // web-dl
    cleaned = cleaned.replace(/[-_(]/g, ' ');           // guiones y paréntesis
    cleaned = cleaned.replace(/\)/g, '');              // cerrar paréntesis
    cleaned = cleaned.replace(/\s+/g, ' ').trim();      // espacios múltiples
    return cleaned;
}

// Función para pre-cargar pósters de series (una llamada por serie)
async function preloadSeriesPosters(series) {
    const uniqueSeries = {};

    // Obtener nombres únicos de series
    for (const serieName in series) {
        const cleanName = cleanSerieName(serieName);
        if (!uniqueSeries[cleanName]) {
            uniqueSeries[cleanName] = serieName; // maps clean name to original
        }
    }

    // Obtener referencia al CatalogService
    const catalogService = window.CatalogService || null;

    // Cargar póster para cada serie única
    for (const cleanName in uniqueSeries) {
        if (!seriePosterCache[cleanName]) {
            let posterUrl = null;

            // NUEVO: Intentar obtener póster desde la base de datos
            if (catalogService) {
                try {
                    // Buscar en el catálogo local por nombre
                    const dbSeries = await catalogService.getSeries(100, 0);
                    const matchingSeries = (dbSeries.series || []).find(s => 
                        s.title && s.title.toLowerCase().includes(cleanName.toLowerCase())
                    );
                    
                    if (matchingSeries && matchingSeries.imdb_id) {
                        posterUrl = await catalogService.getPoster(matchingSeries.imdb_id);
                    }
                } catch (e) {
                    console.warn('⚠️ CatalogService: Error obteniendo póster de BBDD:', e);
                }
            }

            // Fallback a OMDB si no se encontró en BBDD
            if (!posterUrl) {
                try {
                    const response = await fetch(`/api/serie-poster?name=${encodeURIComponent(cleanName)}`);
                    if (response.ok) {
                        const data = await response.json();
                        if (data.poster) {
                            posterUrl = data.poster;
                        }
                    }
                } catch (e) {
                    console.error(`Error cargando póster para ${cleanName}:`, e);
                }
            }

            if (posterUrl) {
                seriePosterCache[cleanName] = posterUrl;
                console.debug(`📺 Póster precargado para: ${cleanName}`);
            }
        }
    }
}

// Función para renderizar series en GRID (no carruseles) - CORREGIDO
// Formato de entrada: { "nombre_serie": [ {id, name, poster, totalSeasons, ...} ] }
async function renderSeries(series) {
    const seriesDiv = document.getElementById("seriesContainer");
    if (!seriesDiv) {
        console.error("No se encontró el contenedor de series");
        return;
    }

    seriesDiv.innerHTML = "";

    if (!series || Object.keys(series).length === 0) {
        seriesDiv.innerHTML = '<div class="no-content-message">No hay series disponibles</div>';
        return;
    }

    // Convertir el formato de objeto a array de series
    const seriesArray = [];
    for (const serieName in series) {
        const episodios = series[serieName];
        if (!episodios || episodios.length === 0) continue;
        
        // Tomar el primer elemento que tiene los datos de la serie
        const serieData = episodios[0];
        seriesArray.push({
            id: serieData.id,
            title: serieData.name || serieName,
            poster_url: serieData.poster || serieData.thumbnail,
            total_seasons: serieData.totalSeasons,
            year: serieData.year,
            imdb_id: serieData.imdb_id,
            rating: serieData.rating,
            plot: serieData.plot,
            genre: serieData.genre
        });
    }

    if (seriesArray.length === 0) {
        seriesDiv.innerHTML = '<div class="no-content-message">No hay series disponibles</div>';
        return;
    }

    // Crear grid de series (igual que renderSeriesView en series_view.js)
    const grid = document.createElement('div');
    grid.className = 'series-grid';
    grid.style.cssText = 'display: grid; grid-template-columns: repeat(auto-fill, minmax(180px, 1fr)); gap: 20px; padding: 20px 0;';

    for (const serie of seriesArray) {
        const card = document.createElement('div');
        card.className = 'serie-card';
        card.style.cssText = 'cursor: pointer; border-radius: 8px; overflow: hidden; background: var(--card-bg, #1a1a1a); transition: transform 0.2s;';
        
        card.onmouseover = () => card.style.transform = 'scale(1.05)';
        card.onmouseout = () => card.style.transform = 'scale(1)';
        
        // Imagen
        const img = document.createElement('img');
        img.style.cssText = 'width: 100%; height: 270px; object-fit: cover;';
        img.alt = serie.title || 'Serie';
        img.src = serie.poster_url || '/static/images/default.jpg';
        img.onerror = () => { img.src = '/static/images/default.jpg'; };
        
        // Título
        const title = document.createElement('div');
        title.style.cssText = 'padding: 10px; font-weight: bold; text-align: center; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;';
        title.textContent = serie.title || 'Sin título';
        
        // Info adicional (temporadas)
        const info = document.createElement('div');
        info.style.cssText = 'padding: 0 10px 10px; text-align: center; color: #888; font-size: 12px;';
        const seasons = serie.total_seasons || '?';
        info.textContent = `${seasons} temporada${seasons !== 1 ? 's' : ''}`;

        card.appendChild(img);
        card.appendChild(title);
        card.appendChild(info);

        // Click para navegar a la página de temporadas de la serie
        // NOTA: Cambiamos a usar JavaScript en lugar de navegación de página
        // para evitar problemas con las rutas del servidor
        card.onclick = async () => {
            try {
                // Llamar a la API para obtener las temporadas
                const response = await fetch(`/api/${serie.id}/seasons`);
                if (!response.ok) {
                    throw new Error('Error al obtener las temporadas');
                }
                const data = await response.json();
                
                // Llamar a la función del series_view.js para mostrar las temporadas
                if (window.showSerieDetail) {
                    window.showSerieDetail(serie.id, data);
                }
            } catch (error) {
                console.error('Error al mostrar las temporadas:', error);
                // Fallback: navegar a la página si la API falla
                window.location.href = `/series/${serie.id}/seasons`;
            }
        };

        grid.appendChild(card);
    }

    seriesDiv.appendChild(grid);
}

window.scrollCarousel = scrollCarousel;
window.renderMoviesByCategory = renderMoviesByCategory;
window.renderSeries = renderSeries;

// ============================================
// LEGACY: Limpiar localStorage antiguo (compatibilidad hacia atrás)
// ============================================
(function cleanLegacyLocalStorage() {
    const LEGACY_KEYS = [
        'cine_serie_posters',
        'cine_movies_cache',
        'cine_movies_timestamp',
        'cine_series_posts',
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