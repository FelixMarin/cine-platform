HTMLImageElement.prototype.handleError = function () {
    const proxies = JSON.parse(this.dataset.proxies || '[]');
    const currentSrc = this.src;
    const currentIndex = proxies.indexOf(currentSrc);
    const nextIndex = currentIndex + 1;

    if (nextIndex < proxies.length) {
        
        this.src = proxies[nextIndex];
    } else {
        
        this.src = '/static/images/default-poster.jpg';
        this.onerror = null;
    }
};