/**
 * Search Page - Categories
 * Carga de categorías desde el backend
 */
(function() {
    'use strict';

    /**
     * Carga las categorías disponibles desde el backend
     */
    window.loadCategories = async function() {
        try {
            var endpoint = window.SEARCH_CONFIG ? window.SEARCH_CONFIG.endpoints.categories : '/api/categories';
            var response = await fetch(endpoint);
            var data = await response.json();

            if (data.success && data.categories) {
                var select = document.getElementById('category-select');
                if (!select) return;

                // Guardar la categoría actual si existe
                var currentCategory = select.value;

                // Limpiar opciones existentes (excepto la primera)
                while (select.options.length > 1) {
                    select.remove(1);
                }

                // Añadir nuevas categorías
                data.categories.forEach(function(category) {
                    var option = document.createElement('option');
                    option.value = category;
                    option.textContent = category;
                    select.appendChild(option);
                });

                // Restaurar categoría si existía
                if (currentCategory && data.categories.includes(currentCategory)) {
                    select.value = currentCategory;
                }

                window.searchState.currentCategory = select.value;
            }
        } catch (error) {
            console.error('Error cargando categorías:', error);
            if (typeof window.showStatus === 'function') {
                window.showStatus('Error al cargar categorías', 'error');
            }
        }
    };

})();
