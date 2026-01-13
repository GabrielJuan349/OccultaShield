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
import { sendPendingNotification } from './email';

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
    // URL base del servidor de autenticación (puerto 4201)
    // Las peticiones desde el cliente (4200) se proxean a este puerto
    baseURL: `http://localhost:${ENV.PORT}`,

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
        usageType: {
          type: 'string',
          required: false,
          defaultValue: 'individual',
        },
      },
    },

    // Database hooks - enviar email al registrarse
    databaseHooks: {
      user: {
        create: {
          after: async (user) => {
            // Skip email notification for admin user
            const adminEmail = process.env['ADMIN_EMAIL'];
            if (adminEmail && user.email === adminEmail) {
              console.log(`⏭️  Skipping email notification for admin user: ${user.email}`);
              return;
            }

            // Enviar email de notificación de registro pendiente
            if (user.email && user.name) {
              try {
                await sendPendingNotification(user.email, user.name);
                console.log(`📧 Pending notification sent to ${user.email}`);
              } catch (error) {
                console.error('Failed to send pending notification:', error);
              }
            }
          },
        },
      },
    },

    // Configuración avanzada
    advanced: {
      cookiePrefix: 'occultashield',
      useSecureCookies: ENV.NODE_ENV === 'production',
      // Cookies deben funcionar en desarrollo con localhost/127.0.0.1
      crossSubDomainCookies: {
        enabled: false,
      },
      defaultCookieAttributes: {
        sameSite: 'lax',
        httpOnly: true,
        path: '/',
      },
    },

    // Trusted origins para CORS
    trustedOrigins: [
      'http://localhost:4200',  // Angular dev server
      'http://localhost:4201',  // Better-Auth server
      'http://localhost:8980',  // Backend FastAPI
      'http://127.0.0.1:4200',
      'http://127.0.0.1:4201',
      'http://127.0.0.1:8980',
      'http://mise-ralph.uab.cat:4200',
      'http://mise-ralph.uab.cat:4201',
      'http://mise-ralph.uab.cat:8980',
      ENV.BASE_URL,
    ].filter(Boolean) as string[],
  });
}

// Singleton promise for auth instance
// Singleton promise for auth instance
let authInstancePromise: ReturnType<typeof createAuth> | null = null;

export function getAuth() {
  if (!authInstancePromise) {
    authInstancePromise = createAuth().catch(err => {
      console.error('❌ Failed to create Better-Auth instance:', err);
      throw err;
    }) as ReturnType<typeof createAuth>;
  }
  return authInstancePromise;
}

export type Auth = Awaited<ReturnType<typeof createAuth>>;
