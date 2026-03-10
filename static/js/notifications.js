// ============================================
// SISTEMA DE NOTIFICACIONES (TOASTS)
// ============================================

class NotificationManager {
    constructor() {
        this.container = document.getElementById('notificationContainer');
        if (!this.container) {
            this.createContainer();
        }
        this.notifications = new Map();
        this.counter = 0;
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'notificationContainer';
        this.container.className = 'notification-container';
        document.body.appendChild(this.container);
    }

    show(title, message, type = 'info', duration = 5000) {
        const id = this.counter++;
        const element = this.createNotificationElement(id, title, message, type);
        
        this.container.appendChild(element);
        this.notifications.set(id, element);
        
        const timeoutId = setTimeout(() => {
            this.close(id);
        }, duration);
        
        element.dataset.timeoutId = timeoutId;
        
        return id;
    }

    createNotificationElement(id, title, message, type) {
        const div = document.createElement('div');
        div.className = `notification ${type}`;
        div.dataset.id = id;
        
        const icons = {
            success: '✅',
            error: '❌',
            warning: '⚠️',
            info: 'ℹ️'
        };
        
        div.innerHTML = `
            <span class="notification-icon">${icons[type] || '📢'}</span>
            <div class="notification-content">
                <div class="notification-title">${this.escapeHtml(title)}</div>
                <div class="notification-message">${this.escapeHtml(message)}</div>
            </div>
            <button class="notification-close" onclick="notifications.close(${id})">&times;</button>
            <div class="notification-progress"></div>
        `;
        
        return div;
    }

    close(id) {
        const element = this.notifications.get(id);
        if (!element) return;
        
        if (element.dataset.timeoutId) {
            clearTimeout(parseInt(element.dataset.timeoutId));
        }
        
        element.classList.add('closing');
        
        setTimeout(() => {
            if (element.parentNode) {
                element.parentNode.removeChild(element);
            }
            this.notifications.delete(id);
        }, 300);
    }

    closeAll() {
        this.notifications.forEach((_, id) => this.close(id));
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
}

const notifications = new NotificationManager();

function showNotification(title, message, type = 'info') {
    return notifications.show(title, message, type);
}
