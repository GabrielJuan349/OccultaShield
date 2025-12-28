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
  // Point to the Node/SSR server where Better-Auth is mounted, NOT the Python Backend.
  // In Docker/Prod, this is valid if serving on same port? 
  // If served via Nginx or same origin, relative is best.
  // For local dev, we need http://localhost:4000 (where server.ts runs).
  baseURL: 'http://localhost:4000',
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
