/**
 * Better-Auth Client for Angular
 * Cliente de autenticación para usar en componentes Angular
 */
import { createAuthClient } from 'better-auth/client';
import { environment } from '../../environments/environment';

/**
 * Cliente de autenticación configurado
 * Usa las APIs de Better-Auth para comunicarse con el servidor
 */
export const authClient = createAuthClient({
  baseURL: environment.baseUrl,
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
