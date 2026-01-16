/**
 * OccultaShield Server - Bun.serve() con Better-Auth y Angular SSR
 *
 * Este servidor maneja:
 * 1. Autenticación via Better-Auth (/api/auth/*)
 * 2. Archivos estáticos desde /browser
 * 3. SSR de Angular para el resto de rutas
 */
import '@angular/compiler';
import {
  AngularNodeAppEngine,
  createNodeRequestHandler,
  isMainModule,
  writeResponseToNodeResponse,
} from '@angular/ssr/node';
import express from 'express';
import cors from 'cors';
import { join } from 'node:path';
import { getAuth } from '#server/auth';
import { getDb, prepareDataForSurreal } from '#server/db';
import { ENV } from '#server/env';
import { initializeAdminUser } from '#server/init-admin';
import { logger, logStartup, logReady } from '#server/logger';
import { requestLogger } from '#server/req-logger';

// Rutas de archivos
const browserDistFolder = join(import.meta.dirname, '../browser');

// Motor de Angular SSR (se inicializa solo si está disponible el manifiesto)
let angularApp: AngularNodeAppEngine | null = null;
try {
  angularApp = new AngularNodeAppEngine();
} catch (e) {
  logger.warn('⚠️ Angular SSR Engine not initialized (Normal in dev mode)', { error: (e as Error).message });
}

// Aplicación Express (usada también por Angular CLI)
const app = express();

// =========================================================================
// MIDDLEWARE: Configuración de CORS y JSON
// =========================================================================
app.use(cors({
  origin: ['http://localhost:4200', 'http://127.0.0.1:4200', 'http://mise-ralph.uab.cat:4200', ENV.BASE_URL].filter(Boolean) as string[],
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS', 'PATCH'],
  allowedHeaders: ['Content-Type', 'Authorization', 'x-requested-with'],
}));

app.use(express.json());

// Request logging middleware
app.use(requestLogger);

// =========================================================================
// RUTAS DE AUTENTICACIÓN (/api/auth/*)
// Better-Auth usa Web Standard Request/Response
// =========================================================================
app.all('/api/auth/*splat', async (req, res) => {
  try {
    // ✅ Esperar a que auth esté listo
    const auth = await getAuth();

    // Convertir Express Request a Web Standard Request
    const protocol = req.protocol;
    const host = req.get('host') ?? 'localhost';
    const url = `${protocol}://${host}${req.originalUrl}`;

    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (value) {
        headers.set(key, Array.isArray(value) ? value.join(', ') : value);
      }
    }

    const webRequest = new Request(url, {
      method: req.method,
      headers,
      body: ['GET', 'HEAD'].includes(req.method)
        ? undefined
        : JSON.stringify(req.body),
    });

    // Better-Auth maneja la petición
    const response = await auth.handler(webRequest);

    // Convertir Web Response a Express Response
    res.status(response.status);

    response.headers.forEach((value, key) => {
      // No duplicar headers de CORS que ya maneja el middleware de Express
      if (!key.toLowerCase().startsWith('access-control-')) {
        res.setHeader(key, value);
      }
    });

    const body = await response.text();
    res.send(body);
  } catch (error) {
    logger.error('Auth handler error', { error: (error as Error).message });
    res.status(500).json({ error: 'Authentication error' });
  }
});

// =========================================================================
// RUTAS DE ADMINISTRACIÓN (/api/admin/*)
// Importado desde admin.ts - incluye approval workflow, settings, audit log
// =========================================================================
import { adminRouter } from '#server/admin';

app.use('/api/admin', adminRouter);

// =========================================================================
// RUTAS DE API GENERAL
// =========================================================================

// POST /api/upload/log - Registrar actividad de subida
app.post('/api/upload/log', async (req, res) => {
  try {
    const auth = await getAuth(); // ✅ Esperar a que auth esté listo

    const headers = new Headers();
    for (const [key, value] of Object.entries(req.headers)) {
      if (value) headers.set(key, Array.isArray(value) ? value.join(', ') : value);
    }

    const session = await auth.api.getSession({ headers });
    if (!session) {
      res.status(401).json({ error: 'Unauthorized' });
      return;
    }

    const { fileName, fileSize, action, status } = req.body;
    const db = await getDb();

    // prepareDataForSurreal convierte userId a record<user> automáticamente
    const logData = prepareDataForSurreal({
      userId: session.user.id,
      action: action || 'upload',
      fileName: fileName || 'unknown',
      fileSize: fileSize || 0,
      status: status || 'success',
      metadata: {}
    });

    await db.create('processing_log', logData);

    res.json({ success: true });
  } catch (error) {
    logger.error('Upload log error', { error: (error as Error).message });
    res.status(500).json({ error: 'Failed to log activity' });
  }
});

// =========================================================================
// ARCHIVOS ESTÁTICOS
// =========================================================================
app.use(
  express.static(browserDistFolder, {
    maxAge: '1y',
    index: false,
    redirect: false,
  })
);

// =========================================================================
// ANGULAR SSR (Todas las demás rutas)
// =========================================================================
app.use((req, res, next) => {
  if (!angularApp) {
    next(); // Si no hay motor SSR, pasamos al siguiente middleware (archivos estáticos)
    return;
  }
  angularApp
    .handle(req)
    .then((response) =>
      response ? writeResponseToNodeResponse(response, res) : next()
    )
    .catch(next);
});

// ============================================================================
// INICIALIZACIÓN DEL SERVIDOR
// ============================================================================
if (isMainModule(import.meta.url) || ENV.RUN_UNDER_PROCESS_MANAGER) {
  const PORT = Number(ENV.PORT ?? 4201);
  logStartup(PORT);

  // Inicializar conexión a SurrealDB y Better-Auth
  Promise.all([getDb(), getAuth()])
    .then(async () => {
      logger.info('✅ DB and Auth initialized successfully');
      logger.info('🔧 Starting admin user initialization...');
      // Initialize admin user after DB and Auth are ready
      try {
        await initializeAdminUser();
      } catch (error) {
        logger.warn('⚠️ Admin initialization failed (non-fatal)', { error: (error as Error).message });
      }

      app.listen(PORT, () => {
        logReady(PORT);
      });
    })
    .catch((error) => {
      logger.error('❌ Failed to initialize server', { error: (error as Error).message });
      // Iniciar servidor sin DB para desarrollo
      app.listen(PORT, () => {
        logger.warn(`⚠️ Server running with errors at http://localhost:${PORT}`);
        logger.warn('   Start SurrealDB and restart the server for full functionality');
      });
    });
}

/**
 * Request handler usado por Angular CLI (dev-server y build)
 */
export const reqHandler = createNodeRequestHandler(app);
