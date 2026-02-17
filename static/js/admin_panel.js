// ===== VARIABLES GLOBALES =====
let statsData = null;
let loadingTimeout = null;

// ===== INICIALIZACIÓN =====
document.addEventListener('DOMContentLoaded', function () {
    console.log('✅ Panel de Administración cargado');

    // Inicializar componentes
    initTooltips();
    initStatsCards();
    loadSystemStats();
    setupEventListeners();
});

// ===== ESTADÍSTICAS DEL SISTEMA =====

/**
 * Cargar estadísticas del sistema (simuladas por ahora)
 * En el futuro, aquí se haría fetch a la API
 */
function loadSystemStats() {
    // Mostrar estado de carga
    showLoadingState();

    // Simular carga de datos (reemplazar con fetch real)
    loadingTimeout = setTimeout(() => {
        // Datos de ejemplo - aquí iría la llamada real a la API
        const mockStats = {
            movies: 24,
            series: 12,
            users: 8,
            storage: '156 GB',
            processed: 156
        };

        updateStatsDisplay(mockStats);
        hideLoadingState();
    }, 800);
}

/**
 * Actualizar la UI con las estadísticas
 * @param {Object} stats - Objeto con las estadísticas
 */
function updateStatsDisplay(stats) {
    const statCards = document.querySelectorAll('.stat-card');

    if (statCards.length >= 4) {
        // Actualizar cada card con su dato correspondiente
        // Películas y Series
        const moviesSeriesCount = (stats.movies || 0) + (stats.series || 0);
        statCards[0].querySelector('h3').textContent = moviesSeriesCount;

        // Usuarios activos
        statCards[1].querySelector('h3').textContent = stats.users || '0';

        // Almacenamiento
        statCards[2].querySelector('h3').textContent = stats.storage || '0 GB';

        // Videos procesados
        statCards[3].querySelector('h3').textContent = stats.processed || '0';
    }
}

/**
 * Mostrar estado de carga en las estadísticas
 */
function showLoadingState() {
    const statCards = document.querySelectorAll('.stat-card h3');
    statCards.forEach(card => {
        const originalContent = card.textContent;
        card.setAttribute('data-original', originalContent);
        card.innerHTML = '<div class="spinner" style="margin: 0 auto;"></div>';
        card.style.fontSize = '0';
    });
}

/**
 * Ocultar estado de carga
 */
function hideLoadingState() {
    if (loadingTimeout) {
        clearTimeout(loadingTimeout);
        loadingTimeout = null;
    }

    const statCards = document.querySelectorAll('.stat-card h3');
    statCards.forEach(card => {
        card.style.fontSize = '';
        const spinner = card.querySelector('.spinner');
        if (spinner) {
            spinner.remove();
        }
    });
}

// ===== EVENTOS Y UTILIDADES =====

/**
 * Configurar event listeners adicionales
 */
function setupEventListeners() {
    // Botón de volver con efecto
    const backBtn = document.querySelector('.back-btn');
    if (backBtn) {
        backBtn.addEventListener('click', function (e) {
            // Puedes agregar un efecto de transición si lo deseas
            console.log('Navegando al dashboard...');
        });
    }

    // Agregar efecto de hover a las cards
    document.querySelectorAll('.stat-card').forEach(card => {
        card.addEventListener('mouseenter', function () {
            this.style.transition = 'all 0.3s ease';
        });
    });
}

/**
 * Inicializar tooltips (si los hubiera)
 */
function initTooltips() {
    // Placeholder para futuros tooltips
    const elements = document.querySelectorAll('[data-tooltip]');
    elements.forEach(el => {
        el.addEventListener('mouseenter', showTooltip);
        el.addEventListener('mouseleave', hideTooltip);
    });
}

function showTooltip(e) {
    // Implementar tooltips si se necesitan
}

function hideTooltip(e) {
    // Implementar tooltips si se necesitan
}

/**
 * Inicializar efectos en las cards de estadísticas
 */
function initStatsCards() {
    document.querySelectorAll('.stat-card').forEach((card, index) => {
        // Agregar delay de animación basado en índice
        card.style.animationDelay = `${index * 0.1}s`;

        // Agregar atributo data-stat para identificación
        const statTypes = ['movies-series', 'users', 'storage', 'processed'];
        if (statTypes[index]) {
            card.setAttribute('data-stat', statTypes[index]);
        }
    });
}

// ===== FUNCIONES PARA FUTURAS IMPLEMENTACIONES =====

/**
 * Cargar logs del sistema (para implementar después)
 */
function loadSystemLogs() {
    // Aquí se implementará la carga de logs
    console.log('Cargando logs del sistema...');
}

/**
 * Exportar datos (para implementar después)
 */
function exportData(format = 'json') {
    console.log(`Exportando datos en formato ${format}...`);
    // Implementar exportación
}

/**
 * Refrescar estadísticas manualmente
 */
function refreshStats() {
    showLoadingState();
    loadSystemStats();
}

// ===== CLEANUP =====
window.addEventListener('beforeunload', function () {
    // Limpiar timeouts al salir
    if (loadingTimeout) {
        clearTimeout(loadingTimeout);
    }
});

document.addEventListener('DOMContentLoaded', function () {
    // Marcar el item activo correctamente
    const currentPath = window.location.pathname;
    document.querySelectorAll('.menu-item').forEach(item => {
        if (item.getAttribute('href') === currentPath) {
            item.classList.add('active');
        }
    });
});