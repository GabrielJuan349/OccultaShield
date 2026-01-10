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
  // Si estamos en el navegador, usamos la origin actual (ej: localhost:4200 en dev o localhost:4000 en prod)
  // Si estamos en el servidor (SSR), apuntamos al puerto interno 4000.
  baseURL: typeof window !== 'undefined'
    ? window.location.origin
    : (process.env['BASE_URL'] || 'http://localhost:4000'),
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
