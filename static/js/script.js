// =========================
//  UTILIDADES DE CATEGORÍAS
// =========================

function formatCategoryName(cat) {
    return cat
        .replace(/_/g, " ")
        .replace(/\b\w/g, c => c.toUpperCase());
}

function createMovieCard(movie) {
    const card = document.createElement("div");
    card.classList.add("movie-card");

    card.innerHTML = `
        <img src="${movie.thumbnail}" class="movie-thumb">
        <div class="movie-title">${movie.name}</div>
    `;

    card.onclick = () => playMovie(movie.path);
    return card;
}

function renderMoviesByCategory(categorias) {
    const moviesDiv = document.getElementById("movies");
    moviesDiv.innerHTML = "";

    for (const categoria in categorias) {
        const section = document.createElement("div");
        section.classList.add("category-section");

        // Header colapsable
        const header = document.createElement("h3");
        header.classList.add("collapsible-header");
        header.textContent = formatCategoryName(categoria);
        header.onclick = () => toggleSeries(header); // Reutilizamos la misma función

        // Contenido colapsable
        const content = document.createElement("div");
        content.classList.add("category-content", "collapsible-content");
        content.style.display = "none";

        categorias[categoria].forEach(movie => {
            const card = createMovieCard(movie);
            content.appendChild(card);
        });

        section.appendChild(header);
        section.appendChild(content);
        moviesDiv.appendChild(section);
    }
}

function renderSeries(series) {
    const seriesDiv = document.getElementById("seriesContainer");
    seriesDiv.innerHTML = "";

    for (const serie in series) {
        const section = document.createElement("div");
        section.classList.add("series-section");

        const header = document.createElement("h3");
        header.classList.add("collapsible-header");
        header.textContent = serie;
        header.setAttribute("role", "button");
        header.setAttribute("aria-expanded", "false");
        header.onclick = () => toggleSeries(header);

        const content = document.createElement("div");
        content.classList.add("card-container", "collapsible-content");
        content.style.display = "none";

        series[serie].forEach(ep => {
            const card = document.createElement("article");
            card.classList.add("card");

            card.innerHTML = `
                <img src="${ep.thumbnail}" alt="${ep.name}" loading="lazy">
                <a href="/play/${ep.path}" class="card-link">${ep.name}</a>
            `;

            content.appendChild(card);
        });

        section.appendChild(header);
        section.appendChild(content);
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
//  SERIES
// =========================

function toggleSeries(header) {
    if (!header) return;

    header.classList.toggle('active');
    const content = header.nextElementSibling;

    if (content) {
        content.classList.toggle('active');
        content.style.display = content.classList.contains('active') ? 'grid' : 'none';
    }
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
    window.location.href = `/play/${path}`;
}

// =========================
//  CARGA DE DATOS DEL BACKEND
// =========================

function loadContent() {
    fetch("/api/movies")
        .then(r => r.json())
        .then(data => {
            renderMoviesByCategory(data.categorias);
            renderSeries(data.series);
        })
        .catch(err => console.error("Error cargando contenido:", err));
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

// Exportar funciones globales
window.toggleMenu = toggleMenu;
window.toggleCollapse = toggleCollapse;
window.showTab = showTab;
window.toggleSeries = toggleSeries;
