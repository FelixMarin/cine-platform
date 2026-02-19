// Punto de entrada principal que carga todos los módulos
// y configura los event listeners iniciales

document.addEventListener('DOMContentLoaded', function () {

    setupClickOutside();
    setupEmptyLinks();
    setupResizeHandler();
    loadSavedPreferences();

    showTab('movies');

    loadContent();
});

// Segundo event listener para asegurar que la pestaña activa sea 'movies'
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