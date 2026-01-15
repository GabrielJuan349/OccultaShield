// Detectar si estamos en un dominio externo o localhost
const isLocalhost = typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

/**
 * URL del backend de video processing (Python FastAPI) - puerto 8980
 * En localhost, el proxy.conf.js redirige /api/v1 → localhost:8980
 */
const getApiUrl = () => {
  if (typeof window === 'undefined') {
    // SSR: usar relative path
    return '/api/v1';
  }

  if (isLocalhost) {
    // Localhost: usar proxy (configurado en proxy.conf.js)
    return '/api/v1';
  }

  // Dominio externo: usar URL absoluta al backend
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:8980/api/v1`;
};

/**
 * URL del servidor de autenticación (Better-Auth + Admin API) - puerto 4201
 * En localhost, el proxy.conf.js redirige /api → localhost:4201
 */
const getAuthUrl = () => {
  if (typeof window === 'undefined') {
    // SSR: el servidor de auth es el mismo que sirve el SSR
    return '/api';
  }

  if (isLocalhost) {
    // Localhost: usar proxy (configurado en proxy.conf.js)
    return '/api';
  }

  // Dominio externo: usar URL absoluta al auth server
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:4201/api`;
};

export const environment = {
  production: true,
  apiUrl: getApiUrl(),    // Backend video: http://host:8980/api/v1
  authUrl: getAuthUrl()   // Auth + Admin: http://host:4201/api
};
