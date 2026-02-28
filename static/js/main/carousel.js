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
        const cardPromises = episodios.map(ep => window.createSerieCard(ep));
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