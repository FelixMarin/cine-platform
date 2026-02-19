// Depende de carousel.js

function loadContent() {

    fetch("/api/movies")
        .then(r => {
            if (!r.ok) {
                throw new Error(`Error HTTP: ${r.status}`);
            }
            return r.json();
        })
        .then(async data => {

            if (data.categorias) {
                await window.renderMoviesByCategory(data.categorias);
            } else {
                console.warn('No hay categorías en los datos');
                document.getElementById('movies').innerHTML = '<div class="no-content-message">No hay películas disponibles</div>';
            }

            if (data.series) {
                await window.renderSeries(data.series);
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

window.loadContent = loadContent;