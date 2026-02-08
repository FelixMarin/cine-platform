function showTab(tabId) {
    // Oculta todas las pestañas
    const tabs = document.querySelectorAll('.tab-content');
    tabs.forEach(tab => tab.style.display = 'none');

    // Muestra la pestaña seleccionada
    const targetTab = document.getElementById(tabId);
    if (targetTab) {
        targetTab.style.display = 'block';
    }

    // Actualiza la pestaña activa
    const tabLinks = document.querySelectorAll('.tab-link');
    tabLinks.forEach(link => link.classList.remove('active'));
    const targetLink = document.getElementById(tabId + 'Tab');
    if (targetLink) {
        targetLink.classList.add('active');
    }
}

function toggleSeries(header) {
    header.classList.toggle('active');
    const content = header.nextElementSibling;
    if (content.classList.contains('active')) {
        content.classList.remove('active');
        content.style.display = 'none';
    } else {
        content.classList.add('active');
        content.style.display = 'grid';
    }
}

document.addEventListener('DOMContentLoaded', () => {
    // Set initial active tab and section
    showTab('movies');
});
