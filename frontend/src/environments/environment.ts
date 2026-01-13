// Detectar si estamos en un dominio externo o localhost
const isLocalhost = typeof window !== 'undefined' &&
  (window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1');

const getApiUrl = () => {
  if (typeof window === 'undefined') {
    // SSR: usar relative path
    return '/api/v1';
  }

  if (isLocalhost) {
    // Localhost: usar proxy
    return '/api/v1';
  }

  // Dominio externo: usar URL absoluta al backend
  const protocol = window.location.protocol;
  const hostname = window.location.hostname;
  return `${protocol}//${hostname}:8980/api/v1`;
};

export const environment = {
  production: true,
  apiUrl: getApiUrl()
};
