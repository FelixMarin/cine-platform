/**
 * Tabs Scroll Indicators
 * Gestiona los indicadores visuales de scroll horizontal en los tabs
 */
(function() {
    'use strict';

    /**
     * Detectar si hay scroll disponible y actualizar clases
     */
    function updateScrollIndicators(container) {
        const tabsContainer = container.querySelector('.tabs, .downloads-tabs');
        
        if (!tabsContainer) return;
        
        const hasHorizontalScroll = tabsContainer.scrollWidth > tabsContainer.clientWidth;
        const scrollLeft = tabsContainer.scrollLeft;
        const maxScroll = tabsContainer.scrollWidth - tabsContainer.clientWidth;
        
        if (hasHorizontalScroll) {
            container.classList.add('has-scroll');
            
            if (scrollLeft > 5) {
                container.classList.add('scrollable-left');
            } else {
                container.classList.remove('scrollable-left');
            }
            
            if (scrollLeft < maxScroll - 5) {
                container.classList.add('scrollable-right');
            } else {
                container.classList.remove('scrollable-right');
            }
        } else {
            container.classList.remove('has-scroll', 'scrollable-left', 'scrollable-right');
        }
    }

    /**
     * Inicializar indicadores de scroll para todos los contenedores de tabs
     */
    function initTabsScroll() {
        // Buscar contenedores de tabs existentes
        const tabsContainers = document.querySelectorAll('.tabs, .downloads-tabs');
        
        tabsContainers.forEach(tabs => {
            // Obtener o crear el contenedor padre
            let container = tabs.parentElement;
            
            // Si el padre no es un contenedor específico, envolverlo
            if (!container.classList.contains('tabs-container') && 
                !container.classList.contains('downloads-tabs-container') &&
                !container.classList.contains('tabs-scroll-container')) {
                // Verificar si ya fue envuelto
                if (!container.classList.contains('has-scroll')) {
                    container.classList.add('tabs-scroll-container');
                }
            }
            
            // Agregar listeners de scroll
            tabs.addEventListener('scroll', function() {
                updateScrollIndicators(container);
            });
            
            // Actualizar al redimensionar
            window.addEventListener('resize', function() {
                updateScrollIndicators(container);
            });
            
            // Actualizar inicial después de un pequeño delay para asegurar que el DOM está listo
            setTimeout(function() {
                updateScrollIndicators(container);
            }, 100);
        });
    }

    // Inicializar cuando el DOM esté listo
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', initTabsScroll);
    } else {
        initTabsScroll();
    }

    // También inicializar después de cualquier cambio dinámico en los tabs
    window.addEventListener('load', initTabsScroll);

    /**
     * Cambiar entre pestañas (Películas/Series)
     */
    function showTab(tabName) {
        // Verificar si hay pestañas en la página actual
        const contents = document.querySelectorAll('.tab-content');
        
        // Si no hay pestañas en la página actual, navegar a la página principal
        if (contents.length === 0) {
            window.location.href = '/?tab=' + tabName;
            return;
        }
        
        // Ocultar todos los contenidos de pestañas
        contents.forEach(content => {
            content.style.display = 'none';
        });

        // Mostrar el contenido seleccionado
        const selectedContent = document.getElementById(tabName);
        if (selectedContent) {
            selectedContent.style.display = 'block';
        }

        // Actualizar clase active en los tabs
        const tabs = document.querySelectorAll('.tab-link, .menu-item[data-tab]');
        tabs.forEach(tab => {
            const isActive = tab.getAttribute('data-tab') === tabName || 
                            (tab.id === tabName + 'Tab');
            if (isActive) {
                tab.classList.add('active');
                tab.setAttribute('aria-selected', 'true');
            } else {
                tab.classList.remove('active');
                tab.setAttribute('aria-selected', 'false');
            }
        });

        // Guardar preferencia en localStorage
        try {
            localStorage.setItem('activeTab', tabName);
        } catch (e) {}
    }

    /**
     * Cargar contenido según la pestaña activa
     */
    function loadContent() {
        // Esta función es llamada desde init.js para cargar datos
        // La implementación real está en catalogService.js
        if (window.catalogService && window.catalogService.loadMovies) {
            const activeTab = document.querySelector('.tab-link.active')?.id === 'seriesTab' ? 'series' : 'movies';
            window.catalogService.loadMovies(activeTab);
        }
    }

    // Exponer funciones para uso externo
    window.initTabsScroll = initTabsScroll;
    window.updateScrollIndicators = updateScrollIndicators;
    window.showTab = showTab;
    window.loadContent = loadContent;

})();
