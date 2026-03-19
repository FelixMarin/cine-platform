/**
 * OAuth Token Manager
 */

const OAuthTokenManager = {
    setAccessToken(token) {
        localStorage.setItem('access_token', token);
    },

    getAccessToken() {
        return localStorage.getItem('access_token');
    },

    setRefreshToken(token) {
        localStorage.setItem('refresh_token', token);
    },

    getRefreshToken() {
        return localStorage.getItem('refresh_token');
    },

    clearTokens() {
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
    },

    clearSession() {
        sessionStorage.removeItem('oauth_code_verifier');
        sessionStorage.removeItem('oauth_state');
    },

    isAuthenticated() {
        return !!this.getAccessToken();
    },

    setCodeVerifier(verifier) {
        sessionStorage.setItem('oauth_code_verifier', verifier);
    },

    getCodeVerifier() {
        return sessionStorage.getItem('oauth_code_verifier');
    },

    setOAuthState(state) {
        sessionStorage.setItem('oauth_state', state);
    },

    getOAuthState() {
        return sessionStorage.getItem('oauth_state');
    }
};
