/**
 * Cliente OAuth2 para el frontend
 * Maneja tokens, refresh automático y llamadas API con autorización
 */

// Función helper para añadir cache busting a URLs
function addCacheBuster(url) {
    const separator = url.includes('?') ? '&' : '?';
    return `${url}${separator}_cb=${Date.now()}`;
}

const OAuthClient = {
    // Configuración
    config: {
        serverUrl: null,
        clientId: null,
        clientSecret: null,
        authorizeEndpoint: '/oauth2/authorize',
        tokenEndpoint: '/oauth2/token',
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

    // Intercambiar código por token (POST desde el backend)
    async exchangeCodeForToken(code, codeVerifier, redirectUri) {
        const response = await fetch(addCacheBuster('/api/auth/exchange-token'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                code_verifier: codeVerifier,
                redirect_uri: redirectUri
            })
        });

        if (response.ok) {
            const data = await response.json();
            localStorage.setItem('access_token', data.access_token);
            if (data.refresh_token) {
                localStorage.setItem('refresh_token', data.refresh_token);
            }
            return data;
        } else {
            throw new Error('Error exchanging code for token');
        }
    },

    // Refresh del token (también por backend)
    async refreshAccessToken() {
        const refreshToken = this.getRefreshToken();

        if (!refreshToken) {
            throw new Error('No refresh token available');
        }

        // El refresh se hace a través de nuestro backend
        const response = await fetch(addCacheBuster('/api/auth/refresh-token'), {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
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

    // Revocar token (opcional)
    async revokeToken() {
        const token = this.getAccessToken();

        if (!token) {
            return;
        }

        try {
            // Se puede hacer también por backend
            await fetch(addCacheBuster('/api/auth/revoke-token'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ token })
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

    // Obtener info del usuario (también por backend)
    async getUserInfo() {
        const response = await fetch(addCacheBuster('/api/auth/userinfo'));
        if (response.ok) {
            return response.json();
        }
        return null;
    },

    // Fetch con auto-refresh (para llamadas API)
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