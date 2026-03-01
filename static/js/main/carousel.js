// Caché de pósters de series (en memoria)
let seriePosterCache = {};

// Inicializar caché de localStorage al cargar
(function initSeriePosterCache() {
    try {
        const cached = localStorage.getItem('cine_serie_posters');
        if (cached) {
            seriePosterCache = JSON.parse(cached);
            console.log('📺 Caché de pósters de series cargado:', Object.keys(seriePosterCache).length, 'series');
        }
    } catch (e) {
        console.warn('No se pudo cargar el caché de pósters:', e);
    }
})();

// Función para guardar pósters en localStorage
function saveSeriePosterCache() {
    try {
        localStorage.setItem('cine_serie_posters', JSON.stringify(seriePosterCache));
    } catch (e) {
        console.warn('No se pudo guardar el caché de pósters:', e);
    }
}

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

    console.log('Orden de categorías recibido:', categoriasLista.map(([cat]) => cat));

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
        const cardPromises = peliculas.map(movie => window.createMovieCard(movie));
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

// Caché global para pósters de series (una sola llamada a OMDB por serie)
// Ahora persistente con localStorage
(function initSeriePosterCache() {
    try {
        const cached = localStorage.getItem('cine_serie_posters');
        if (cached) {
            seriePosterCache = JSON.parse(cached);
            console.log('📺 Caché de pósters de series cargado:', Object.keys(seriePosterCache).length, 'series');
        }
    } catch (e) {
        console.warn('No se pudo cargar el caché de pósters:', e);
    }
})();

// Función para guardar pósters en localStorage
function saveSeriePosterCache() {
    try {
        localStorage.setItem('cine_serie_posters', JSON.stringify(seriePosterCache));
    } catch (e) {
        console.warn('No se pudo guardar el caché de pósters:', e);
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

    // Cargar póster para cada serie única
    for (const cleanName in uniqueSeries) {
        if (!seriePosterCache[cleanName]) {
            try {
                const response = await fetch(`/api/serie-poster?name=${encodeURIComponent(cleanName)}`);
                if (response.ok) {
                    const data = await response.json();
                    if (data.poster) {
                        seriePosterCache[cleanName] = data.poster;
                        saveSeriePosterCache(); // Guardar en localStorage
                        console.log(`📺 Póster precargado para: ${cleanName}`);
                    }
                }
            } catch (e) {
                console.error(`Error cargando póster para ${cleanName}:`, e);
            }
        }
    }
}

// Función para renderizar series en carruseles (AHORA ASÍNCRONA)
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

    // Pre-cargar pósters de todas las series (UNA llamada por serie)
    await preloadSeriesPosters(series);

    for (const serieName in series) {
        const episodios = series[serieName];

        if (!episodios || episodios.length === 0) continue;

        // Obtener el nombre limpio de la serie
        const cleanName = cleanSerieName(serieName);
        const cachedPoster = seriePosterCache[cleanName];

        const section = document.createElement("div");
        section.classList.add("category-section");

        const header = document.createElement("div");
        header.classList.add("category-header");
        header.innerHTML = `<h3 class="category-title">${serieName}</h3>`;

        const carouselContainer = document.createElement("div");
        carouselContainer.classList.add("carousel-container");

        const carouselId = `carousel-series-${serieName.replace(/\s+/g, '-')}`;

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
        track.id = carouselId;

        // Crear todas las tarjetas de series pasando el póster pre-cargado
        const cardPromises = episodios.map(ep => window.createSerieCard(ep, cachedPoster));
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
        seriesDiv.appendChild(section);
    }
}

window.scrollCarousel = scrollCarousel;
window.renderMoviesByCategory = renderMoviesByCategory;
window.renderSeries = renderSeries;