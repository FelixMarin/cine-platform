/**
 * Lógica específica de la página de login
 * Maneja el flujo OAuth2 para autenticación
 */

// ========== CONFIGURACIÓN ==========

// Configuración desde el servidor (se define en el HTML)
// const APP_CONFIG = { ... };
// const OAUTH2_CONFIG = { ... };

// ========== FUNCIONES AUXILIARES ==========

// Generar code_verifier (43-128 caracteres)
function generateCodeVerifier() {
    const array = new Uint8Array(32);
    crypto.getRandomValues(array);
    return btoa(String.fromCharCode.apply(null, array))
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '')
        .substring(0, 43);
}

// Generar code_challenge
async function generateCodeChallenge(verifier) {
    const encoder = new TextEncoder();
    const data = encoder.encode(verifier);
    const digest = await crypto.subtle.digest('SHA-256', data);

    const hashArray = new Uint8Array(digest);
    let hashString = '';
    for (let i = 0; i < hashArray.length; i++) {
        hashString += String.fromCharCode(hashArray[i]);
    }

    return btoa(hashString)
        .replace(/\+/g, '-')
        .replace(/\//g, '_')
        .replace(/=/g, '');
}

// Mostrar error
function showError(message) {
    const container = document.getElementById('login-container');
    container.innerHTML =
        '<h2 class="menu-title-full">Cine<span>Platform</span></h2>' +
        '<p class="error-msg">' + message + '</p>' +
        '<button type="button" onclick="window.location.href=\'/login?client_id=' + APP_CONFIG.clientId + '\'" class="oauth-btn">Volver a intentar</button>';
}

// ========== FUNCIÓN PRINCIPAL ==========

// Iniciar flujo OAuth2
async function startOAuth2Flow() {
    const btn = document.getElementById('oauth-login-btn');
    btn.disabled = true;
    btn.textContent = 'Redirigiendo a OAuth2...';

    try {
        // Generar code_verifier y code_challenge
        const codeVerifier = generateCodeVerifier();

        const codeChallenge = await generateCodeChallenge(codeVerifier);

        // Generar state aleatorio para CSRF
        const actualState = Math.random().toString(36).substring(2) + Date.now().toString(36);

        // Guardar en sessionStorage
        sessionStorage.setItem('oauth_code_verifier', codeVerifier);
        sessionStorage.setItem('oauth_state', actualState);

        // Construir URL correcta para OAuth2 authorize
        const authUrl = new URL(APP_CONFIG.oauth2Url + '/oauth2/authorize');
        authUrl.searchParams.set('response_type', 'code');
        authUrl.searchParams.set('client_id', APP_CONFIG.clientId);
        authUrl.searchParams.set('redirect_uri', APP_CONFIG.redirectUri);
        authUrl.searchParams.set('scope', APP_CONFIG.scopes);
        authUrl.searchParams.set('code_challenge', codeChallenge);
        authUrl.searchParams.set('code_challenge_method', 'S256');
        authUrl.searchParams.set('state', actualState);

        // Redirigir al servidor OAuth2
        window.location.href = authUrl.toString();

    } catch (error) {
        console.error('Error:', error);
        btn.disabled = false;
        btn.textContent = 'Iniciar sesión con OAuth2';

        const errorMsg = document.createElement('p');
        errorMsg.className = 'error-msg';
        errorMsg.textContent = 'Error: ' + error.message;
        document.getElementById('login-container').appendChild(errorMsg);
    }
}

// ========== MANEJAR CALLBACK ==========

// Ejecutar cuando carga la página
function handleOAuthCallback() {
    const params = new URLSearchParams(window.location.search);
    const code = params.get('code');
    const error = params.get('error');
    const errorDescription = params.get('error_description');

    if (error) {
        showError(error + (errorDescription ? ': ' + errorDescription : ''));
        return;
    }

    if (code) {
        // Recuperar code_verifier de sessionStorage
        const codeVerifier = sessionStorage.getItem('oauth_code_verifier');

        if (!codeVerifier) {
            showError('Code verifier no encontrado. Intenta de nuevo.');
            return;
        }

        // Mostrar estado de carga
        const container = document.getElementById('login-container');
        container.innerHTML = '<h2 class="menu-title-full">Cine<span>Platform</span></h2><p>Completando autenticación...</p>';

        // Enviar al backend para canjear el código
        fetch('/api/auth/exchange-token', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                code: code,
                code_verifier: codeVerifier,
                redirect_uri: APP_CONFIG.redirectUri
            })
        })
        .then(async (response) => {
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Error al canjear código');
            }
            return response.json();
        })
        .then((tokens) => {

            // Guardar tokens en localStorage
            localStorage.setItem('access_token', tokens.access_token);
            if (tokens.refresh_token) {
                localStorage.setItem('refresh_token', tokens.refresh_token);
            }

            // Limpiar sessionStorage
            sessionStorage.removeItem('oauth_code_verifier');
            sessionStorage.removeItem('oauth_state');

            // Redirigir a página principal
            window.location.href = '/';
        })
        .catch((err) => {
            console.error('Error:', err);
            showError('Error al completar autenticación: ' + err.message);
        });
    }
}

// ========== INICIALIZACIÓN ==========

// Inicializar cuando el DOM esté listo
document.addEventListener('DOMContentLoaded', function() {
    // Manejar callback OAuth si viene de redirección
    handleOAuthCallback();

    // Configurar event listener para el botón OAuth
    const btn = document.getElementById('oauth-login-btn');
    if (btn) {
        btn.addEventListener('click', startOAuth2Flow);
    } else {
        console.error('Botón OAuth no encontrado');
    }
});
