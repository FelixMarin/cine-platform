/**
 * OAuth Client - Configuration
 */

const OAuthConfig = {
    serverUrl: null,
    clientId: null,
    clientSecret: null,
    authorizeEndpoint: '/oauth2/authorize',
    tokenEndpoint: '/oauth2/token',
    refreshEndpoint: '/oauth2/token',
    revokeEndpoint: '/oauth2/revoke',
    userinfoEndpoint: '/userinfo'
};

function initOAuthConfig(config) {
    Object.assign(OAuthConfig, config);
}

function getOAuthConfig() {
    return OAuthConfig;
}
