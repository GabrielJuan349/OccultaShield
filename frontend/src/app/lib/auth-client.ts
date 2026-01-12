/**
 * Better-Auth Client for Angular
 * Cliente de autenticación para usar en componentes Angular
 */
import { createAuthClient } from 'better-auth/client';
import { environment } from '#environments/environment';

/**
 * Cliente de autenticación configurado
 * Usa las APIs de Better-Auth para comunicarse con el servidor
 */
export const authClient = createAuthClient({
  // En el navegador, usar URL relativa para que el proxy de Angular funcione
  // El proxy en proxy.conf.json redirige /api/* a http://localhost:4201
  // Esto asegura que las cookies se creen en el mismo origen (localhost:4200)
  // En SSR, conectamos directamente al servidor de auth en el puerto 4201
  baseURL: typeof window !== 'undefined'
    ? ''  // URL relativa - usa el mismo origen que la página
    : 'http://localhost:4201',
});

// Exportar métodos específicos para facilitar el uso
export const {
  signIn,
  signUp,
  signOut,
  getSession,
  useSession,
} = authClient;

// Tipos útiles
export type Session = Awaited<ReturnType<typeof getSession>>;
export type User = NonNullable<Session>['user'];
