// menu.js - Funciones del menú lateral

function toggleMenu() {
    const $menu = $('#sideMenu');
    const $overlay = $('.menu-overlay');
    $menu.toggleClass('open');
    $overlay.toggleClass('active');
}

function toggleCollapse() {
    const $menu = $('#sideMenu');
    const $mainContent = $('#mainContent');
    const $collapseBtn = $('.menu-collapse-btn');

    $menu.toggleClass('collapsed');
    $mainContent.toggleClass('expanded');

    if ($menu.hasClass('collapsed')) {
        $collapseBtn.html('▶').attr('title', 'Expandir menú');
    } else {
        $collapseBtn.html('◀').attr('title', 'Colapsar menú');
    }

    try {
        localStorage.setItem('menuCollapsed', $menu.hasClass('collapsed'));
    } catch (e) { }
}

function showTab(tabName) {
    window.location.href = '/?tab=' + tabName;
}

// Exportar al ámbito global
window.optimizerMenu = {
    toggleMenu,
    toggleCollapse,
    showTab
};