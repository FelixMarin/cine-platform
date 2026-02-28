/**
 * Cliente OAuth2 para el frontend
 * Maneja tokens, refresh automático y llamadas API con autorización
 */

const OAuthClient = {
    // Configuración
    config: {
        serverUrl: null,
        clientId: null,
        clientSecret: null,
        refreshEndpoint: '/oauth2/token',
        revokeEndpoint: '/oauth2/revoke',
        userinfoEndpoint: '/userinfo'
    },

    // Inicializar configuración
    init(config) {
        this.config = { ...this.config, ...config };
    },

    // Obtener access token
    getAccessToken() {
        return localStorage.getItem('access_token');
    },

    // Obtener refresh token
    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    // Verificar si está autenticado
    isAuthenticated() {
        return !!this.getAccessToken();
    },

    // Refresh del token
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();

        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        const response = await fetch(this.config.serverUrl + this.config.refreshEndpoint, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/x-www-form-urlencoded',
                'Authorization': 'Basic ' + btoa(this.config.clientId + ':' + this.config.clientSecret)
            },
            body: new URLSearchParams({
                grant_type: 'refresh_token',
                refresh_token: refreshToken
            })
        });

        if (response.ok) {
            const tokens = await response.json();
            localStorage.setItem('access_token', tokens.access_token);
            if (tokens.refresh_token) {
                localStorage.setItem('refresh_token', tokens.refresh_token);
            }
            return tokens.access_token;
        } else {
            // Refresh falló, limpiar tokens
            this.logout();
            throw new Error('Session expired');
        }
    },

    // Revocar token
    async revokeToken() {
        const token = this.getAccessToken();

        if (!token) {
            return;
        }

        try {
            await fetch(this.config.serverUrl + this.config.revokeEndpoint, {
                method: 'POST',
                headers: {
                    'Authorization': 'Bearer ' + token
                }
            });
        } catch (e) {
            console.warn('Error revocando token:', e);
        }
    },

    // Logout
    logout() {
        this.revokeToken();
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        sessionStorage.removeItem('oauth_code_verifier');
        sessionStorage.removeItem('oauth_state');
    },

    // Obtener info del usuario
    async getUserInfo() {
        const token = this.getAccessToken();

        if (!token) {
            return null;
        }

        const response = await fetch(this.config.serverUrl + this.config.userinfoEndpoint, {
            headers: {
                'Authorization': 'Bearer ' + token
            }
        });

        if (response.ok) {
            return response.json();
        }
        return null;
    },

    // Fetch con auto-refresh
    async fetch(url, options = {}) {
        let token = this.getAccessToken();

        // Añadir Authorization header
        if (token) {
            options.headers = {
                ...options.headers,
                'Authorization': 'Bearer ' + token
            };
        }

        let response = await fetch(url, options);

        // Si 401, intentar refresh
        if (response.status === 401 && token) {
            try {
                token = await this.refreshAccessToken();

                // Reintentar con nuevo token
                options.headers = {
                    ...options.headers,
                    'Authorization': 'Bearer ' + token
                };
                response = await fetch(url, options);
            } catch (e) {
                // Refresh falló, redirigir a login
                window.location.href = '/login?error=session_expired';
                throw e;
            }
        }

        return response;
    }
};

// Inicializar con configuración del servidor
(function () {
    // Obtener config del elemento meta o variable global
    const metaConfig = document.querySelector('meta[name="oauth-config"]');
    if (metaConfig) {
        const config = JSON.parse(metaConfig.getAttribute('content') || '{}');
        OAuthClient.init(config);
    }
})();

// Exportar para uso global
window.OAuthClient = OAuthClient;
