HTMLImageElement.prototype.handleError = function () {
    const proxies = JSON.parse(this.dataset.proxies || '[]');
    const currentSrc = this.src;
    const currentIndex = proxies.indexOf(currentSrc);
    const nextIndex = currentIndex + 1;

    if (nextIndex < proxies.length) {
        console.log(`🖼️ Probando proxy ${nextIndex + 1}/${proxies.length}`);
        this.src = proxies[nextIndex];
    } else {
        console.log('❌ Usando imagen por defecto');
        this.src = '/static/images/default-poster.jpg';
        this.onerror = null;
    }
};