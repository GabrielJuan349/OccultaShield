/**
 * Better-Auth Configuration with SurrealDB Adapter
 * Configuración de autenticación usando Better-Auth con adaptador oficial surreal-better-auth
 */
import { betterAuth } from 'better-auth';
import { surrealdbAdapter } from 'surreal-better-auth';
/*import {
  twoFactor,           // ✅ 2FA con TOTP
  organization,        // ✅ Organizaciones y equipos
  admin,              // ✅ Panel de administración
  bearer,             // ✅ Autenticación con Bearer tokens
  multiSession,       // ✅ Múltiples sesiones simultáneas
  oneTap,             // ✅ Google One Tap
  magicLink,          // ✅ Magic links (sin contraseña)
  phoneNumber,        // ✅ Autenticación con teléfono
  username,           // ✅ Login con username en vez de email
  anonymous,          // ✅ Usuarios anónimos
} from "better-auth/plugins";*/

import { getDb } from './db';
import { ENV } from './env';

// ============================================================================
// BETTER-AUTH CONFIGURATION
// ============================================================================

/**
 * Inicializa y configura Better-Auth con SurrealDB
 * Se ejecuta de forma asíncrona al importar el módulo
 */
async function createAuth() {
  // Obtener instancia de SurrealDB
  const db = await getDb();

  return betterAuth({
    // URL base de la aplicación
    //plugins: [twoFactor(), organization(), passkey()],
    baseURL: ENV.BASE_URL,

    // Secreto para firmar tokens (DEBE ser seguro en producción)
    secret: ENV.AUTH_SECRET,

    // Adaptador de base de datos usando surreal-better-auth
    database: surrealdbAdapter(db, {
      // Logs de debug para desarrollo
      debugLogs: ENV.NODE_ENV === 'development',
      // IDs ordenables generados por SurrealDB
      idGenerator: 'surreal.UUIDv7',
      // Usar nombres singulares (user, session, account, verification)
      usePlural: false,
    }),

    // Configuración de sesiones
    session: {
      expiresIn: 60 * 60 * 24 * 7, // 7 días
      updateAge: 60 * 60 * 24, // Actualizar si tiene más de 1 día
      cookieCache: {
        enabled: true,
        maxAge: 60 * 5, // Cache de cookie por 5 minutos
      },
    },

    // Métodos de autenticación habilitados
    emailAndPassword: {
      enabled: true,
      requireEmailVerification: false, // Cambiar a true en producción
      minPasswordLength: 8,
      maxPasswordLength: 128,
    },

    // Configuración de cuenta
    account: {
      accountLinking: {
        enabled: true,
        trustedProviders: ['email'],
      },
    },

    // Campos adicionales del usuario (rol personalizado)
    user: {
      additionalFields: {
        role: {
          type: 'string',
          required: false,
          defaultValue: 'user',
        },
      },
    },

    // Configuración avanzada
    advanced: {
      cookiePrefix: 'occultashield',
      useSecureCookies: ENV.NODE_ENV === 'production',
    },

    // Trusted origins para CORS
    trustedOrigins: [
      'http://localhost:4000',
      'http://localhost:4200',
      ENV.BASE_URL,
    ].filter(Boolean),
  });
}

// Exportar la promesa de auth
export const authPromise = createAuth();

// Exportar auth sincrónico (se resolverá cuando esté listo)
export let auth: Awaited<ReturnType<typeof createAuth>>;

// Inicializar auth inmediatamente
authPromise.then((a) => {
  auth = a;
  console.log('✅ Better-Auth initialized');
}).catch((error) => {
  console.error('❌ Failed to initialize Better-Auth:', error);
  process.exit(1);
});

// Tipo exportado para el cliente
export type Auth = Awaited<ReturnType<typeof createAuth>>;
