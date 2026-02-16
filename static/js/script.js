const thumbnailCache = new Map();

// =========================
//  UTILIDADES DE CATEGORÍAS
// =========================

function formatCategoryName(cat) {
    // Si contiene /, tomar la parte después de la última /
    let cleanName = cat.includes('/') ? cat.split('/').pop() : cat;

    // Reemplazar guiones bajos por espacios
    cleanName = cleanName.replace(/_/g, " ");

    // Capitalizar cada palabra respetando acentos
    return cleanName.split(' ').map(word => {
        if (word.length === 0) return word;
        // Preservar la primera letra con su acento y poner el resto en minúsculas
        return word.charAt(0).toLocaleUpperCase() + word.slice(1).toLocaleLowerCase();
    }).join(' ');
}

// Función para obtener la URL del thumbnail con detección de formato
async function getThumbnailUrl(movie) {
    const name = movie.name || movie.title || '';
    const cleanName = name.trim().replace(/\s+/g, ' ');
    const cacheKey = cleanName;

    // Si ya está en caché, devolverlo
    if (thumbnailCache.has(cacheKey)) {
        return thumbnailCache.get(cacheKey);
    }

    // Si ya tiene thumbnail en los datos, usarlo
    if (movie.thumbnail) {
        thumbnailCache.set(cacheKey, movie.thumbnail);
        return movie.thumbnail;
    }

    const encodedName = encodeURIComponent(cleanName);

    // Verificar soporte WebP (una sola vez)
    if (!window.supportsWebP) {
        window.supportsWebP = await checkWebPSupport();
    }

    let thumbnailUrl;

    // Si soporta WebP, intentar obtener versión WebP
    if (window.supportsWebP) {
        try {
            const response = await fetch(`/thumbnails/detect/${encodedName}-optimized.jpg`);
            const data = await response.json();

            if (data.has_webp) {
                thumbnailUrl = data.webp_url;
            } else if (data.has_jpg) {
                thumbnailUrl = data.jpg_url;
            } else {
                thumbnailUrl = `/thumbnails/${encodedName}-optimized.jpg`;
            }
        } catch (error) {
            console.log('Error detectando formato, usando JPG');
            thumbnailUrl = `/thumbnails/${encodedName}-optimized.jpg`;
        }
    } else {
        thumbnailUrl = `/thumbnails/${encodedName}-optimized.jpg`;
    }

    // Guardar en caché
    thumbnailCache.set(cacheKey, thumbnailUrl);
    return thumbnailUrl;
}

// Función para verificar soporte de WebP
function checkWebPSupport() {
    return new Promise(resolve => {
        const webP = new Image();
        webP.onload = webP.onerror = function () {
            resolve(webP.height === 2);
        };
        webP.src = 'data:image/webp;base64,UklGRjoAAABXRUJQVlA4IC4AAACyAgCdASoCAAIALmk0mk0iIiIiIgBoSygABc6WWgAA/veff/0PP8bA//LwYAAA';
    });
}

async function createMovieCard(movie) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = movie.name || movie.title || 'Sin título';

    // Obtener la URL del thumbnail (ahora asíncrona)
    const thumbnailUrl = await getThumbnailUrl(movie);

    // Crear la imagen
    const img = document.createElement('img');
    img.className = 'movie-thumb';
    img.alt = title;
    img.src = thumbnailUrl;
    img.onerror = function () {
        console.log('Error cargando imagen, usando default:', this.src);
        this.src = '/static/thumbnails/default.jpg';
        this.onerror = null;
    };

    const titleDiv = document.createElement('div');
    titleDiv.className = 'movie-title';
    titleDiv.textContent = title;

    card.appendChild(img);
    card.appendChild(titleDiv);

    const playPath = movie.path || movie.id || movie.file;
    card.onclick = () => playMovie(playPath);

    return card;
}

// Nueva función asíncrona para crear tarjetas de series
async function createSerieCard(episodio) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    const title = episodio.name || episodio.title || 'Sin título';

    // Determinar la URL del thumbnail
    let thumbnailUrl;
    if (episodio.thumbnail) {
        thumbnailUrl = episodio.thumbnail;
    } else {
        // Intentar usar getThumbnailUrl para series también
        thumbnailUrl = await getThumbnailUrl(episodio);
    }

    // Crear imagen
    const img = document.createElement('img');
    img.className = 'movie-thumb';
    img.alt = title;
    img.src = thumbnailUrl;
    img.onerror = function () {
        console.log('Error en serie, usando default:', this.src);
        this.src = '/static/thumbnails/default.jpg';
        this.onerror = null;
    };

    const titleDiv = document.createElement('div');
    titleDiv.className = 'movie-title';
    titleDiv.textContent = title;

    card.appendChild(img);
    card.appendChild(titleDiv);

    const playPath = episodio.path || episodio.id || episodio.file;
    card.onclick = () => playMovie(playPath);

    return card;
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
async function renderMoviesByCategory(categorias) {
    const moviesDiv = document.getElementById("movies");
    if (!moviesDiv) {
        console.error("No se encontró el contenedor de películas");
        return;
    }

    moviesDiv.innerHTML = "";

    if (!categorias || Object.keys(categorias).length === 0) {
        moviesDiv.innerHTML = '<div class="no-content-message">No hay películas disponibles</div>';
        return;
    }

    for (const categoria in categorias) {
        const peliculas = categorias[categoria];

        if (!peliculas || peliculas.length === 0) continue;

        const section = document.createElement("div");
        section.classList.add("category-section");

        const header = document.createElement("div");
        header.classList.add("category-header");
        header.innerHTML = `<h3 class="category-title">${formatCategoryName(categoria)}</h3>`;

        const carouselContainer = document.createElement("div");
        carouselContainer.classList.add("carousel-container");

        const carouselId = `carousel-${categoria.replace(/\s+/g, '-')}`;

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

        // Crear todas las tarjetas de forma asíncrona
        const cardPromises = peliculas.map(movie => createMovieCard(movie));
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

    console.log("Series recibidas:", series);

    for (const serieName in series) {
        const episodios = series[serieName];

        if (!episodios || episodios.length === 0) continue;

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

        // Crear todas las tarjetas de series de forma asíncrona
        const cardPromises = episodios.map(ep => createSerieCard(ep));
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

// =========================
//  PESTAÑAS
// =========================

function showTab(tabName) {
    if (event) event.preventDefault();

    document.querySelectorAll('.menu-item').forEach(item => item.classList.remove('active'));

    if (tabName === 'movies') {
        const moviesTab = document.querySelector('.menu-item[onclick="showTab(\'movies\')"]');
        if (moviesTab) moviesTab.classList.add('active');
    } else {
        const seriesTab = document.querySelector('.menu-item[onclick="showTab(\'series\')"]');
        if (seriesTab) seriesTab.classList.add('active');
    }

    const moviesDiv = document.getElementById('movies');
    const seriesDiv = document.getElementById('series');

    if (moviesDiv && seriesDiv) {
        moviesDiv.style.display = tabName === 'movies' ? 'block' : 'none';
        seriesDiv.style.display = tabName === 'series' ? 'block' : 'none';
    }

    document.title = tabName === 'movies' ? 'Películas - Cine Platform' : 'Series - Cine Platform';

    if (window.innerWidth <= 768) {
        const menu = document.getElementById('sideMenu');
        if (menu && menu.classList.contains('open')) toggleMenu();
    }

    return false;
}

// =========================
//  MENÚ
// =========================

let isMenuCollapsed = false;

function toggleMenu() {
    const menu = document.getElementById('sideMenu');
    const overlay = document.querySelector('.menu-overlay');

    if (menu && overlay) {
        menu.classList.toggle('open');
        overlay.classList.toggle('active');
    }
}

function toggleCollapse() {
    const menu = document.getElementById('sideMenu');
    const mainContent = document.getElementById('mainContent');
    const collapseBtn = document.querySelector('.menu-collapse-btn');

    if (!menu || !mainContent || !collapseBtn) return;

    isMenuCollapsed = !isMenuCollapsed;

    if (isMenuCollapsed) {
        menu.classList.add('collapsed');
        mainContent.classList.add('expanded');
        collapseBtn.innerHTML = '▶';
    } else {
        menu.classList.remove('collapsed');
        mainContent.classList.remove('expanded');
        collapseBtn.innerHTML = '◀';
    }

    try {
        localStorage.setItem('menuCollapsed', isMenuCollapsed);
    } catch (e) {
        console.warn('No se pudo guardar la preferencia', e);
    }
}

// =========================
//  UTILIDADES
// =========================

function setupClickOutside() {
    const overlay = document.querySelector('.menu-overlay');
    if (overlay) overlay.addEventListener('click', toggleMenu);
}

function setupEmptyLinks() {
    document.querySelectorAll('a[href="#"]').forEach(link => {
        link.addEventListener('click', e => e.preventDefault());
    });
}

function setupResizeHandler() {
    window.addEventListener('resize', function () {
        const menu = document.getElementById('sideMenu');
        const mainContent = document.getElementById('mainContent');

        if (!menu || !mainContent) return;

        if (window.innerWidth <= 768) {
            menu.classList.remove('collapsed');
            mainContent.classList.remove('expanded');
            if (menu.classList.contains('open')) toggleMenu();
        } else {
            const savedState = localStorage.getItem('menuCollapsed') === 'true';
            if (savedState !== isMenuCollapsed) {
                isMenuCollapsed = savedState;
                if (isMenuCollapsed) {
                    menu.classList.add('collapsed');
                    mainContent.classList.add('expanded');
                } else {
                    menu.classList.remove('collapsed');
                    mainContent.classList.remove('expanded');
                }
            }
        }
    });
}

function loadSavedPreferences() {
    try {
        const savedMenuState = localStorage.getItem('menuCollapsed');

        if (savedMenuState !== null && window.innerWidth > 768) {
            isMenuCollapsed = savedMenuState === 'true';

            const menu = document.getElementById('sideMenu');
            const mainContent = document.getElementById('mainContent');
            const collapseBtn = document.querySelector('.menu-collapse-btn');

            if (menu && mainContent && collapseBtn) {
                if (isMenuCollapsed) {
                    menu.classList.add('collapsed');
                    mainContent.classList.add('expanded');
                    collapseBtn.innerHTML = '▶';
                } else {
                    menu.classList.remove('collapsed');
                    mainContent.classList.remove('expanded');
                    collapseBtn.innerHTML = '◀';
                }
            }
        }
    } catch (e) {
        console.warn('No se pudieron cargar las preferencias', e);
    }
}

function playMovie(path) {
    if (!path) {
        console.error('Ruta de reproducción no válida');
        return;
    }
    window.location.href = `/play/${path}`;
}

// =========================
//  CARGA DE DATOS DEL BACKEND
// =========================

function loadContent() {
    console.log('Cargando contenido...');

    fetch("/api/movies")
        .then(r => {
            if (!r.ok) {
                throw new Error(`Error HTTP: ${r.status}`);
            }
            return r.json();
        })
        .then(async data => {  // Hacer esta función async
            console.log('Datos recibidos:', data);

            if (data.categorias) {
                await renderMoviesByCategory(data.categorias);
            } else {
                console.warn('No hay categorías en los datos');
                document.getElementById('movies').innerHTML = '<div class="no-content-message">No hay películas disponibles</div>';
            }

            if (data.series) {
                await renderSeries(data.series);
            } else {
                console.warn('No hay series en los datos');
                document.getElementById('seriesContainer').innerHTML = '<div class="no-content-message">No hay series disponibles</div>';
            }
        })
        .catch(err => {
            console.error("Error cargando contenido:", err);
            document.getElementById('movies').innerHTML = '<div class="no-content-message">Error al cargar las películas</div>';
            document.getElementById('seriesContainer').innerHTML = '<div class="no-content-message">Error al cargar las series</div>';
        });
}

// =========================
//  INICIALIZACIÓN
// =========================

document.addEventListener('DOMContentLoaded', function () {
    console.log('✅ Script cargado correctamente');

    setupClickOutside();
    setupEmptyLinks();
    setupResizeHandler();
    loadSavedPreferences();

    showTab('movies');

    loadContent();
});

document.addEventListener('DOMContentLoaded', function () {
    const activeTab = document.querySelector('.menu-item.active');
    if (!activeTab || activeTab.getAttribute('data-tab') !== 'movies') {
        window.showTab('movies');
    }
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

// Exportar funciones globales
window.toggleMenu = toggleMenu;
window.toggleCollapse = toggleCollapse;
window.showTab = showTab;
window.scrollCarousel = scrollCarousel;